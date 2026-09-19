"""
workers.py — Independent Background Workers for SURDAS.

Architecture:
  • VisionWorker  — Camera → YOLO → MiDaS → publishes PerceptionResult to SystemState
  • SafetyWorker  — Reads PerceptionResult → runs SafetyEngine → triggers CRITICAL_SAFETY TTS
  • LLMWorker     — Async LLM queue; never blocks voice or safety loops

Key guarantees:
  1. Voice is NEVER blocked by vision inference (YOLO/MiDaS run in their own thread).
  2. Safety critical TTS fires immediately via SpeechPriority.CRITICAL_SAFETY.
  3. LLM query/response is fully async — user command ACKs before LLM starts.
  4. Camera down → voice and safety continue (last known world state).
  5. All workers catch exceptions internally and continue without crashing.
"""
from __future__ import annotations

import threading
import queue
import time
import numpy as np
from typing import TYPE_CHECKING, Optional, Dict, Any, List
from dataclasses import dataclass, field

if TYPE_CHECKING:
    import cv2
    import torch
    from surdas_brain import SurdasBrain
    from voice.tts import VoiceEngine

from system_state import (
    SpeechPriority, SafetyLevel, VisionState, LLMState,
    SubsystemHealth
)


# ── Perception Result Dataclass ───────────────────────────────────────────────

@dataclass
class PerceptionResult:
    """Output from VisionWorker, consumed by SafetyWorker and brain."""
    frame: Optional[np.ndarray] = None            # annotated BGR frame
    depth_colormap: Optional[np.ndarray] = None   # depth heatmap
    raw_depth: Optional[np.ndarray] = None        # raw depth array
    detected_obstacles: List[tuple] = field(default_factory=list)
    current_objects: List[str] = field(default_factory=list)
    yolo_detections: List[Dict[str, Any]] = field(default_factory=list)
    wall_detected: bool = False
    immediate_danger: Optional[str] = None
    guidance_text: Optional[str] = None
    fps: float = 0.0
    timestamp: float = field(default_factory=time.time)

    # Indoor perception
    indoor_result: Any = None

    # Corridor medians (from MiDaS)
    center_med: float = 0.0
    left_med: float = 0.0
    right_med: float = 0.0


# ── VisionWorker ─────────────────────────────────────────────────────────────

class VisionWorker:
    """
    Runs YOLO + MiDaS inference in a dedicated thread.
    Publishes the latest PerceptionResult to a shared slot.
    The main thread / SafetyWorker reads this slot without blocking.
    """

    def __init__(self, brain: "SurdasBrain"):
        self.brain = brain
        self._latest: Optional[PerceptionResult] = None
        self._lock = threading.Lock()
        self._running = False
        self._paused = False
        self._thread: Optional[threading.Thread] = None
        self._prev_time = time.time()

    def start(self):
        self._running = True
        self._thread = threading.Thread(
            target=self._loop, daemon=True, name="VisionWorker"
        )
        self._thread.start()
        print("[VISION] VisionWorker started.")

    def stop(self):
        self._running = False

    def pause(self):
        """Pause vision processing without stopping the thread."""
        self._paused = True
        print("[VISION] VisionWorker paused.")

    def resume(self):
        """Resume vision processing."""
        self._paused = False
        print("[VISION] VisionWorker resumed.")

    @property
    def latest(self) -> Optional[PerceptionResult]:
        with self._lock:
            return self._latest

    def _publish(self, result: PerceptionResult):
        with self._lock:
            self._latest = result

    def _loop(self):
        import cv2
        from config import (
            DEPTH_WALL_DENSE_THRESHOLD, DEPTH_WALL_CENTER_RATIO,
            DEPTH_WALL_IMMEDIATE_THRESHOLD, YOLO_CONFIDENCE_THRESHOLD,
            DEPTH_ADAPTIVE_NORMALIZATION,
            classify_depth_proximity, classify_depth_proximity_adaptive,
            get_proximity_description
        )

        while self._running:
            try:
                # Check if paused
                if self._paused:
                    time.sleep(0.1)
                    continue

                frame = self.brain.stream.get_frame()
                if frame is None:
                    time.sleep(0.05)
                    continue

                # FPS
                now = time.time()
                fps = 1.0 / max(0.001, now - self._prev_time)
                self._prev_time = now

                # Flip frame if configured
                frame = cv2.flip(frame, 1)

                h, w = frame.shape[:2]
                third_w = w // 3

                result = PerceptionResult(fps=fps, timestamp=now)

                # ── MiDaS Depth ───────────────────────────────────────────
                try:
                    raw_depth, depth_vis = self.brain.compute_depth(frame)

                    center_crop = raw_depth[:, third_w: 2 * third_w]
                    left_crop   = raw_depth[:, :third_w]
                    right_crop  = raw_depth[:, 2 * third_w:]

                    result.center_med = float(np.median(center_crop)) if center_crop.size > 0 else 0
                    result.left_med   = float(np.median(left_crop))   if left_crop.size > 0 else 0
                    result.right_med  = float(np.median(right_crop))  if right_crop.size > 0 else 0
                    center_close_ratio = float(np.mean(center_crop > DEPTH_WALL_DENSE_THRESHOLD)) if center_crop.size > 0 else 0

                    result.raw_depth = raw_depth

                    depth_colormap = cv2.applyColorMap(depth_vis, cv2.COLORMAP_INFERNO)
                    cv2.line(depth_colormap, (third_w, 0), (third_w, h), (255, 255, 255), 1)
                    cv2.line(depth_colormap, (2 * third_w, 0), (2 * third_w, h), (255, 255, 255), 1)
                    result.depth_colormap = depth_colormap

                    # Update health
                    if hasattr(self.brain, "state"):
                        self.brain.state.set_health("midas", SubsystemHealth.OK)
                except Exception as e:
                    print(f"[VISION] MiDaS error: {e}")
                    center_close_ratio = 0
                    raw_depth = None
                    if hasattr(self.brain, "state"):
                        self.brain.state.set_health("midas", SubsystemHealth.DEGRADED, str(e))

                # ── YOLO Detection ────────────────────────────────────────
                detected_obstacles = []
                current_objects = []
                yolo_detections = []
                center_object_found = False

                try:
                    yolo_results = self.brain.yolo(
                        frame, conf=self.brain.conf_threshold, verbose=False
                    )[0]

                    for box in yolo_results.boxes:
                        cls_id = int(box.cls[0])
                        conf   = float(box.conf[0])
                        label  = self.brain.yolo.names[cls_id]
                        current_objects.append(label)

                        x1, y1, x2, y2 = map(int, box.xyxy[0].tolist())
                        cx = (x1 + x2) / 2

                        yolo_detections.append({
                            "class": label,
                            "confidence": conf,
                            "bbox": [x1, y1, x2, y2]
                        })

                        if cx < third_w:
                            pos, color = "on your left", (255, 200, 0)
                        elif cx > 2 * third_w:
                            pos, color = "on your right", (0, 200, 255)
                        else:
                            pos, color = "ahead", (0, 255, 0)
                            center_object_found = True

                        if raw_depth is not None:
                            crop = raw_depth[max(0, y1):min(h, y2), max(0, x1):min(w, x2)]
                            med_depth = float(np.median(crop)) if crop.size > 0 else 0
                        else:
                            med_depth = 0

                        if DEPTH_ADAPTIVE_NORMALIZATION and raw_depth is not None and raw_depth.size > 0:
                            proximity = classify_depth_proximity_adaptive(med_depth, raw_depth)
                        else:
                            proximity = classify_depth_proximity(med_depth)

                        proximity_desc = get_proximity_description(proximity, lang="en")

                        if proximity == "VERY_CLOSE" and pos == "ahead":
                            color = (0, 0, 255)
                            result.immediate_danger = f"Caution! {label} directly ahead."
                        elif proximity == "VERY_CLOSE":
                            color = (0, 100, 255)
                        elif proximity == "CLOSE":
                            color = (0, 200, 255)

                        detected_obstacles.append((label, pos, proximity, med_depth, conf, proximity_desc))

                        # Annotate frame
                        cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
                        tag = f"{label} {int(conf*100)}% | {proximity_desc}"
                        (tw, th), _ = cv2.getTextSize(tag, cv2.FONT_HERSHEY_SIMPLEX, 0.45, 1)
                        cv2.rectangle(frame, (x1, max(0, y1 - 20)), (x1 + tw + 6, max(0, y1)), color, -1)
                        cv2.putText(frame, tag, (x1 + 3, max(14, y1 - 5)),
                                    cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 0, 0), 1, cv2.LINE_AA)

                    if hasattr(self.brain, "state"):
                        self.brain.state.set_health("yolo", SubsystemHealth.OK)

                except Exception as e:
                    print(f"[VISION] YOLO error: {e}")
                    if hasattr(self.brain, "state"):
                        self.brain.state.set_health("yolo", SubsystemHealth.DEGRADED, str(e))

                result.detected_obstacles = detected_obstacles
                result.current_objects = current_objects
                result.yolo_detections = yolo_detections

                # ── Wall Detection (MiDaS) ────────────────────────────────
                if raw_depth is not None and center_close_ratio > DEPTH_WALL_CENTER_RATIO and not center_object_found:
                    result.wall_detected = True
                    if result.center_med > DEPTH_WALL_IMMEDIATE_THRESHOLD:
                        result.immediate_danger = "Stop! Wall directly in front of you."
                    else:
                        result.immediate_danger = "Caution! Wall ahead."

                    if result.left_med < result.center_med - 150 and result.left_med < result.right_med:
                        result.guidance_text = "Wall ahead. Path is clear on your left."
                    elif result.right_med < result.center_med - 150:
                        result.guidance_text = "Wall ahead. Path is clear on your right."

                    if result.depth_colormap is not None:
                        cv2.rectangle(result.depth_colormap, (third_w + 10, 10), (2 * third_w - 10, 50), (0, 0, 255), -1)
                        cv2.putText(result.depth_colormap, "WALL AHEAD", (third_w + 20, 38),
                                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)

                # ── Indoor Perception ─────────────────────────────────────
                if hasattr(self.brain, "indoor_perception") and hasattr(self.brain, "indoor_navigator"):
                    try:
                        indoor_result = self.brain.indoor_perception.process_frame(
                            yolo_detections=yolo_detections,
                            depth_map=raw_depth if raw_depth is not None else np.zeros((h, w)),
                            img_width=w,
                            img_height=h
                        )
                        self.brain.indoor_navigator.update(indoor_result)
                        result.indoor_result = indoor_result
                    except Exception as e:
                        pass  # indoor perception failure never crashes vision loop

                # ── Voice indicator overlay ───────────────────────────────
                if self.brain.is_voice_active():
                    cv2.rectangle(frame, (10, h - 40), (200, h - 10), (0, 150, 255), -1)
                    cv2.putText(frame, "Voice Active", (20, h - 18),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 2)

                result.frame = frame
                self._publish(result)

                # Update shared brain state
                self.brain.latest_detected_objects = current_objects
                self.brain.wall_detected = result.wall_detected

                # Update VisionState in system_state
                if hasattr(self.brain, "state"):
                    self.brain.state.set_health("camera", SubsystemHealth.OK)

            except Exception as e:
                print(f"[VISION] Worker loop error: {e}")
                time.sleep(0.1)


# ── SafetyWorker ──────────────────────────────────────────────────────────────

class SafetyWorker:
    """
    Reads PerceptionResult from VisionWorker and fires CRITICAL_SAFETY
    TTS announcements. Never blocked by voice, LLM, or navigation.
    Uses cooldown to avoid repeating the same warning continuously.
    """

    # How often (seconds) to re-announce the same danger
    DANGER_COOLDOWN = 5.0      # Increased from 3.0 to reduce interruptions
    ROUTINE_COOLDOWN = 8.0     # Increased from 5.0 to reduce interruptions
    CLEAR_COOLDOWN = 15.0      # Increased from 12.0

    def __init__(self, brain: "SurdasBrain", vision: VisionWorker):
        self.brain = brain
        self.vision = vision
        self._running = False
        self._paused = False
        self._thread: Optional[threading.Thread] = None
        self._last_danger_time = 0.0
        self._last_routine_time = 0.0
        self._last_spoken = ""

    def start(self):
        self._running = True
        self._thread = threading.Thread(
            target=self._loop, daemon=True, name="SafetyWorker"
        )
        self._thread.start()
        print("[SAFETY] SafetyWorker started.")

    def stop(self):
        self._running = False

    def pause(self):
        """Pause safety monitoring without stopping the thread."""
        self._paused = True
        print("[SAFETY] SafetyWorker paused.")

    def resume(self):
        """Resume safety monitoring."""
        self._paused = False
        print("[SAFETY] SafetyWorker resumed.")

    def _loop(self):
        while self._running:
            try:
                # Check if paused
                if self._paused:
                    time.sleep(0.1)
                    continue

                result = self.vision.latest
                if result is None:
                    time.sleep(0.05)
                    continue

                now = time.time()

                # ── Check if user is actively using voice assistant ──────
                is_voice_command_active = self._is_voice_busy()

                # ── CRITICAL SAFETY: wall / very close object ─────────────
                # ONLY announce if it's truly critical AND not during voice command
                # OR if it's a new danger that wasn't announced recently
                if result.immediate_danger:
                    speech = result.guidance_text if result.guidance_text else result.immediate_danger
                    is_new_danger = (speech != self._last_spoken or 
                                    now - self._last_danger_time > self.DANGER_COOLDOWN)
                    
                    # Critical safety ONLY if:
                    # 1. Very close wall/obstacle directly ahead AND
                    # 2. User not speaking OR it's a brand new danger
                    is_truly_critical = (
                        "Stop!" in speech or 
                        "very close" in speech.lower() or
                        "directly ahead" in speech
                    )
                    
                    if is_new_danger and (is_truly_critical or not is_voice_command_active):
                        # Use CRITICAL_SAFETY only for stop commands, otherwise use NAVIGATION
                        priority = SpeechPriority.CRITICAL_SAFETY if is_truly_critical else SpeechPriority.NAVIGATION
                        
                        self.brain.voice.speak(
                            speech,
                            priority=priority,
                            force=is_truly_critical,  # Only force interrupt for stop commands
                            lang="en"
                        )
                        self._last_danger_time = now
                        self._last_spoken = speech
                        
                        # Update system state
                        if hasattr(self.brain, "state"):
                            from system_state import SafetyLevel as SL
                            self.brain.state.safety_level = SL.CRITICAL

                # ── Routine obstacle announcements ────────────────────────
                # SKIP entirely if voice command is active
                elif not is_voice_command_active and now - self._last_routine_time > self.ROUTINE_COOLDOWN:
                    # Check if indoor navigator is active — it handles its own guidance
                    indoor_nav_active = (
                        hasattr(self.brain, "indoor_navigator")
                        and self.brain.indoor_navigator.get_status().state not in ["IDLE"]
                    )

                    if not indoor_nav_active and result.detected_obstacles:
                        obstacles_sorted = sorted(result.detected_obstacles, key=lambda x: x[3], reverse=True)
                        top_lbl, top_pos, _, _, _, top_prox_desc = obstacles_sorted[0]
                        speech_text = f"{top_lbl} {top_pos}, {top_prox_desc}."
                        
                        # Only announce if it's different from last announcement
                        if speech_text != self._last_spoken:
                            self.brain.voice.speak(
                                speech_text,
                                priority=SpeechPriority.STATUS,
                                lang="en"
                            )
                            self._last_spoken = speech_text
                            self._last_routine_time = now
                            
                    elif not indoor_nav_active and not result.detected_obstacles:
                        # Only announce "clear" occasionally, not repeatedly
                        if self._last_spoken != "clear" and now - self._last_routine_time > self.CLEAR_COOLDOWN:
                            self.brain.voice.speak(
                                "Path is clear.",
                                priority=SpeechPriority.STATUS,
                                lang="en"
                            )
                            self._last_spoken = "clear"
                            self._last_routine_time = now

                    # Update safety level
                    if hasattr(self.brain, "state"):
                        from system_state import SafetyLevel as SL
                        if result.immediate_danger:
                            self.brain.state.safety_level = SL.CRITICAL
                        elif result.wall_detected:
                            self.brain.state.safety_level = SL.BLOCKED
                        elif result.detected_obstacles:
                            self.brain.state.safety_level = SL.CAUTION
                        else:
                            self.brain.state.safety_level = SL.CLEAR

                time.sleep(0.1)

            except Exception as e:
                print(f"[SAFETY] Worker error: {e}")
                time.sleep(0.2)

    def _is_voice_busy(self) -> bool:
        """
        True if voice assistant is actively recording or processing a command.
        Also checks if TTS is speaking at HIGH priority (user commands).
        """
        va = getattr(self.brain, "voice_assistant", None)
        if va is None:
            return False
        
        # Check if actively recording or processing voice command
        if (getattr(va, "_is_recording", False) or getattr(va, "_processing", False)):
            return True
        
        # Check if voice engine is speaking a user command or LLM response
        voice_engine = getattr(self.brain, "voice", None)
        if voice_engine and voice_engine.is_speaking:
            # Check if current speech is high priority (don't interrupt user interactions)
            return True
            
        return False


# ── LLMWorker ─────────────────────────────────────────────────────────────────

class LLMWorker:
    """
    Async LLM query worker. Commands are enqueued and processed in background.
    The voice assistant NEVER blocks waiting for Ollama.
    """

    def __init__(self, brain: "SurdasBrain"):
        self.brain = brain
        self._queue: queue.Queue = queue.Queue(maxsize=4)
        self._running = False
        self._thread: Optional[threading.Thread] = None

    def start(self):
        self._running = True
        self._thread = threading.Thread(
            target=self._loop, daemon=True, name="LLMWorker"
        )
        self._thread.start()
        print("[LLM] LLMWorker started (async).")

    def stop(self):
        self._running = False

    def submit(self, prompt: str, lang: str = "en", vision_context: Optional[dict] = None):
        """
        Enqueue an LLM query. Non-blocking — returns immediately.
        If queue is full (backlog), drops oldest item.
        """
        if hasattr(self.brain, "state"):
            self.brain.state.llm_state = LLMState.QUERYING
        try:
            self._queue.put_nowait((prompt, lang, vision_context))
        except queue.Full:
            try:
                self._queue.get_nowait()  # drop oldest
            except queue.Empty:
                pass
            self._queue.put_nowait((prompt, lang, vision_context))

    def _loop(self):
        while self._running:
            try:
                item = self._queue.get(timeout=0.5)
            except queue.Empty:
                continue

            prompt, lang, vision_context = item

            try:
                if hasattr(self.brain, "state"):
                    self.brain.state.llm_state = LLMState.STREAMING

                llm = getattr(self.brain, "llm", None)
                if llm is None or not llm.is_available():
                    self.brain.voice.speak(
                        "Language model not available. Start Ollama first.",
                        priority=SpeechPriority.USER_COMMAND,
                        lang=lang
                    )
                    if hasattr(self.brain, "state"):
                        self.brain.state.llm_state = LLMState.UNAVAILABLE
                    self._queue.task_done()
                    continue

                ctx = vision_context or self.brain.get_vision_context()
                for sentence in llm.query(prompt, vision_context=ctx):
                    if sentence:
                        self.brain.voice.speak(
                            sentence,
                            priority=SpeechPriority.LLM_RESPONSE,
                            lang=lang
                        )

                if hasattr(self.brain, "state"):
                    self.brain.state.llm_state = LLMState.READY

            except Exception as e:
                print(f"[LLM] Worker error: {e}")
                self.brain.voice.speak(
                    "Sorry, there was an error processing your request.",
                    priority=SpeechPriority.USER_COMMAND,
                    lang=lang
                )
                if hasattr(self.brain, "state"):
                    self.brain.state.llm_state = LLMState.TIMEOUT
            finally:
                try:
                    self._queue.task_done()
                except Exception:
                    pass
