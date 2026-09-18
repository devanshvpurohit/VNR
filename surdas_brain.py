import os
import sys
import warnings
import argparse

# Suppress background PyTorch MPS & OpenCV warnings
warnings.filterwarnings("ignore")
os.environ["PYTHONWARNINGS"] = "ignore"
os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"
os.environ["YOLO_VERBOSE"] = "False"
os.environ["YOLO_OFFLINE"] = "True"
os.environ["YOLO_SETTINGS_ANALYTICS"] = "False"
os.environ["OFFLINE_MODE"] = "1"
os.environ["HF_HUB_OFFLINE"] = "1"
os.environ["TRANSFORMERS_OFFLINE"] = "1"
os.environ["TORCH_HOME"] = os.path.expanduser("~/.cache/torch")

# ── CLI argument parsing (must happen before heavy imports) ──────────────────
_parser = argparse.ArgumentParser(description="SURDAS Assistive Vision Brain")
_parser.add_argument(
    "--model", "-m",
    default="",
    metavar="MODEL",
    help="Ollama model name to use for LLM. Defaults to gemma3:1b.",
)
_parser.add_argument(
    "--mic",
    default=None,
    metavar="DEVICE",
    help="Audio input device name keyword or index (e.g. 'airpods', 'boat', 'buds', '0'). Auto-detects TWS by default.",
)
_parser.add_argument(
    "--mic-gain",
    type=float,
    default=1.0,
    metavar="GAIN",
    help="Software gain multiplier for microphone (e.g. 1.5, 2.0, 2.5 for quiet TWS). Defaults to 1.8x for TWS.",
)
_args, _ = _parser.parse_known_args()
LLM_MODEL = _args.model  # empty string = use LocalLLM default (gemma3:1b)
MIC_DEVICE = _args.mic
MIC_GAIN = _args.mic_gain

# Get script directory for path resolution (DO NOT change working directory)
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

# Import configuration BEFORE other modules
import sys
sys.path.insert(0, SCRIPT_DIR)
from config import *

import cv2
import torch
import numpy as np
import threading
import queue
import time
import urllib.request
from ultralytics import YOLO
import easyocr

from voice.tts import VoiceEngine
from voice.assistant import VoiceAssistant
from voice.llm import LocalLLM
from voice.app_launcher import open_app, close_app
from telemetry import start_telemetry, broadcast_event

# =====================================================
# CONFIGURATION
# =====================================================
# Camera settings from config
ESP32_IP = ESP32_IP  # from config.py
STREAM_URL = STREAM_URL  # from config.py
LED_URL = LED_URL  # from config.py

# Best available compute accelerator (CUDA / Apple Silicon MPS / CPU)
DEVICE = get_device()

print(f"[SYSTEM] Hardware Acceleration: {DEVICE}")
if LLM_MODEL:
    print(f"[SYSTEM] LLM Model (CLI): {LLM_MODEL}")


# =====================================================
# 1. ROBUST VIDEO STREAM RECEIVER
# =====================================================
class CameraStream:
    def __init__(self, src):
        self.src = src
        print(f"[STREAM] Attempting to connect to {src}...")
        self.cap = cv2.VideoCapture(src)
        
        # Fallback to local webcam (0) if stream is completely unreachable
        if not self.cap.isOpened():
            print(f"[STREAM] Warning: {src} unreachable. Falling back to local webcam ({CAMERA_FALLBACK}).")
            self.cap = cv2.VideoCapture(CAMERA_FALLBACK)
            
        self.frame = None
        self.lock = threading.Lock()
        self.stopped = False
        self.connected = False
        threading.Thread(target=self._read_loop, daemon=True).start()

    def _read_loop(self):
        while not self.stopped:
            ret, frame = self.cap.read()
            if ret and frame is not None:
                self.connected = True
                with self.lock:
                    self.frame = frame
            else:
                self.connected = False
                time.sleep(0.05)

    def get_frame(self):
        with self.lock:
            return self.frame.copy() if self.frame is not None else None

    def stop(self):
        self.stopped = True
        self.cap.release()

# =====================================================
# 2. SURDAS PERCEPTION & VOICE BRAIN (YOLO + MIDAS WALLS + VOICE)
# =====================================================
class SurdasBrain:
    def __init__(self):
        # Start Dashboard Telemetry
        start_telemetry()
        
        # 1. TTS Voice Output Engine
        self.voice = VoiceEngine()
        self.voice.speak("SURDAS Vision and Voice System starting.")

        # Connect to ESP32 stream in background
        print(f"[STREAM] Connecting to: {STREAM_URL}")
        self.stream = CameraStream(STREAM_URL)

        # 2. Parallel AI Model Loading (YOLOv8, MiDaS, EasyOCR, Voice/Whisper)
        print("[SYSTEM] ⚡ Loading AI models in parallel (YOLOv8, MiDaS, EasyOCR, Whisper/Voice)...")
        t0_load = time.time()

        def _load_yolo():
            # Use config system to get model path
            yolo_path = get_yolo_model_path()
            self.yolo = YOLO(yolo_path)
            print(f"[AI] ✅ YOLOv8 loaded from {yolo_path}")

        def _load_midas():
            # Use config system
            midas_cache_str = str(MIDAS_CACHE_DIR)
            ft_midas_path = get_midas_model_path()

            # Load transforms — always from local cache
            if not MIDAS_CACHE_DIR.exists():
                raise RuntimeError(
                    f"[AI] MiDaS local cache not found at {MIDAS_CACHE_DIR}. "
                    "Run setup_offline_models.py while online first."
                )
            midas_transforms = torch.hub.load(midas_cache_str, "transforms", source="local")
            self.transform = midas_transforms.small_transform

            if ft_midas_path:
                print(f"[AI] Using fine-tuned MiDaS_small from {ft_midas_path}")
                base = torch.hub.load(midas_cache_str, "MiDaS_small", source="local", pretrained=False)
                state = torch.load(ft_midas_path, map_location="cpu")
                base.load_state_dict(state)
                self.midas = base.to(DEVICE).eval()
            else:
                self.midas = torch.hub.load(
                    midas_cache_str, "MiDaS_small", source="local", pretrained=True
                ).to(DEVICE).eval()
            print("[AI] ✅ MiDaS Depth Estimator loaded.")

        def _load_ocr():
            self.ocr = easyocr.Reader(['en', 'hi'], gpu=(DEVICE == "cuda"), download_enabled=False)
            print("[AI] ✅ EasyOCR loaded (en + hi).")


        def _load_voice():
            self.llm = LocalLLM(model_name=LLM_MODEL)
            if self.llm.is_available():
                print(f"[AI] ✅ Ollama ready — model: {self.llm.model_name}")
            else:
                print("[AI] Ollama not detected. Start with: ollama serve")
            try:
                self.voice_assistant = VoiceAssistant(self, mic_device=MIC_DEVICE, mic_gain=MIC_GAIN)
                self.voice_assistant.start()
                print("[AI] ✅ Voice Assistant active.")
            except Exception as e:
                print(f"[VOICE] Voice Assistant warning: {e}. Vision continues normally.")
                self.voice_assistant = None

        from concurrent.futures import ThreadPoolExecutor
        with ThreadPoolExecutor(max_workers=4) as executor:
            f_yolo = executor.submit(_load_yolo)
            f_midas = executor.submit(_load_midas)
            f_ocr = executor.submit(_load_ocr)
            f_voice = executor.submit(_load_voice)

            f_yolo.result()
            f_midas.result()
            f_ocr.result()
            f_voice.result()

        print(f"[SYSTEM] 🚀 All AI models loaded in parallel in {time.time() - t0_load:.2f}s!")

        self.mode = "NAV"  # 'NAV' or 'OCR'
        self.last_speech_time = 0
        self.last_spoken = ""
        self.led_on = False
        self.conf_threshold = YOLO_CONFIDENCE_THRESHOLD

        # Live Vision Context State
        self.latest_detected_objects = []
        self.latest_closest_obstacle = None
        self.wall_detected = False
        
        # Offline Navigation with proper location provider
        from navigation import OfflineMapManager, Navigator
        from navigation.location import GPSSerialLocation, ManualLocation, LocationUnavailableError
        
        self.map_manager = OfflineMapManager()
        self.map_manager.auto_load()
        self.navigator = Navigator(self.map_manager, self)
        
        # Indoor Navigation & Spatial Memory
        from spatial_memory import SpatialMemory
        from indoor_navigator import IndoorNavigator
        from indoor_perception import IndoorPerception
        
        print("[SYSTEM] Initializing indoor navigation and spatial memory...")
        self.spatial_memory = SpatialMemory()
        self.indoor_navigator = IndoorNavigator(self.spatial_memory, self.voice)
        self.indoor_perception = IndoorPerception(grid_size=32)
        
        # Get memory stats
        stats = self.spatial_memory.get_stats()
        print(f"[SPATIAL_MEMORY] Loaded: {stats['rooms']} rooms, {stats['objects']} objects, {stats['landmarks']} landmarks")
        
        # State for indoor navigation
        self.indoor_nav_mode = False  # Toggle for indoor navigation processing
        
        # Initialize location provider based on configuration
        gps_enabled = GPS_ENABLED  # Use local variable to avoid shadowing
        if gps_enabled:
            try:
                print(f"[GPS] Initializing GPS on port {GPS_PORT}...")
                self.location_provider = GPSSerialLocation(
                    port=GPS_PORT,
                    baudrate=GPS_BAUD,
                    timeout=GPS_TIMEOUT,
                    stale_threshold=GPS_STALE_THRESHOLD,
                    max_jump_distance=GPS_MAX_JUMP_DISTANCE_M
                )
                self.location_provider.start()
                # Try to get initial fix
                try:
                    initial_loc = self.location_provider.get_location()
                    print(f"[GPS] ✅ GPS fix acquired: ({initial_loc['lat']:.4f}, {initial_loc['lon']:.4f})")
                    self.navigator._current_location = initial_loc
                except Exception as e:
                    print(f"[GPS] ⚠️  Initial GPS fix failed: {e}")
                    print("[GPS] Navigation will work once GPS acquires a fix.")
            except Exception as e:
                print(f"[GPS] ❌ GPS initialization failed: {e}")
                print("[GPS] Falling back to manual test location for development.")
                gps_enabled = False
        
        if not gps_enabled:
            # Use manual location for testing
            test_loc = DEFAULT_TEST_LOCATION
            self.location_provider = ManualLocation(
                lat=test_loc["lat"],
                lon=test_loc["lon"],
                name=test_loc["name"]
            )
            self.navigator._current_location = self.location_provider.get_location()

        self.voice.speak("Ready. Navigation mode active. Say Hey Surdas.")
        
        # Dashboard integration state
        self.log_history = []
        self.latest_display_frame = None
        self.headless = False

    # ── LLM helper ─────────────────────────────────────────────────
    def query_llm(self, prompt: str, speak: bool = True) -> str:
        """Ask the LLM a question. Streams response sentence-by-sentence.
        Returns the full response as a string."""
        full = []
        for sentence in self.llm.query(prompt, vision_context=self.get_vision_context()):
            if sentence:
                full.append(sentence)
                if speak:
                    self.voice.speak(sentence)
        return " ".join(full)

    # ── App launcher helpers ─────────────────────────────────────────
    def launch_app(self, app_name: str, speak: bool = True) -> bool:
        """Open a macOS app by name. Returns True on success."""
        success, msg = open_app(app_name)
        if speak:
            self.voice.speak(msg)
        return success

    def quit_app(self, app_name: str, speak: bool = True) -> bool:
        """Close a macOS app by name. Returns True on success."""
        success, msg = close_app(app_name)
        if speak:
            self.voice.speak(msg)
        return success
        
    def add_log(self, msg: str):
        print(msg)
        timestamp = time.strftime("%H:%M:%S")
        self.log_history.append(f"[{timestamp}] {msg}")
        if len(self.log_history) > 100:
            self.log_history.pop(0)

    def get_vision_context(self) -> dict:
        """Provides current live scene state for LLM and Command Router."""
        ctx = {
            "mode": self.mode,
            "torch_on": self.led_on,
            "detected_objects": list(self.latest_detected_objects),
            "closest_obstacle": self.latest_closest_obstacle,
            "wall_ahead": self.wall_detected
        }
        if hasattr(self, "navigator") and self.navigator:
            ctx["navigation"] = self.navigator.get_status()
        return ctx

    def get_status_summary(self) -> str:
        """Returns verbal status report."""
        stream_stat = "connected" if self.stream.connected else "disconnected"
        torch_stat = "on" if self.led_on else "off"
        obj_count = len(self.latest_detected_objects)
        wall_stat = "Wall detected ahead." if self.wall_detected else "No wall."
        return f"System status: Camera is {stream_stat}. Flashlight is {torch_stat}. Mode is {self.mode}. Detecting {obj_count} objects. {wall_stat}"

    def is_voice_active(self) -> bool:
        """Returns True if a voice command is being received, processed, or spoken."""
        if self.voice_assistant is not None and getattr(self.voice_assistant, "is_active", False):
            return True
        if self.voice.is_speaking or not self.voice._queue.empty():
            return True
        return False

    def toggle_esp32_led(self, state: bool):
        """Toggles the ESP32-CAM flash torch."""
        try:
            val = "on" if state else "off"
            urllib.request.urlopen(f"{LED_URL}?state={val}", timeout=0.8)
            self.led_on = state
        except Exception:
            pass

    def compute_depth(self, frame):
        """Computes dense relative depth map."""
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        input_tensor = self.transform(rgb).to(DEVICE)
        
        with torch.no_grad():
            depth = self.midas(input_tensor)
            depth = torch.nn.functional.interpolate(
                depth.unsqueeze(1),
                size=frame.shape[:2],
                mode="bicubic",
                align_corners=False
            ).squeeze()

        depth_np = depth.cpu().numpy()
        depth_vis = cv2.normalize(depth_np, None, 0, 255, norm_type=cv2.NORM_MINMAX, dtype=cv2.CV_8U)
        return depth_np, depth_vis

    def process_navigation(self, frame):
        """
        Processes both Discrete Objects (YOLO) and Dense Continuous Barriers/Walls (MiDaS).
        NOW ALSO: Indoor navigation perception and guidance.
        
        SAFETY CRITICAL: Vision processing continues ALWAYS, even during voice activity.
        Only non-critical voice announcements are suppressed during voice commands.
        """
        # Update navigation location from GPS/location provider
        if hasattr(self, "navigator") and self.navigator:
            try:
                current_loc = self.location_provider.get_location()
                self.navigator.update_location(current_loc)
            except Exception as e:
                # GPS unavailable or stale - navigation continues with last known position
                pass

        h, w, _ = frame.shape
        third_w = w // 3

        # -------------------------------------------------------------
        # ALWAYS RUN SAFETY PERCEPTION (YOLO + MIDAS)
        # Safety perception MUST continue during voice processing
        # -------------------------------------------------------------
        raw_depth, depth_vis = self.compute_depth(frame)
        
        # -------------------------------------------------------------
        # 1. DENSE MIDAS SPATIAL ANALYSIS (WALL & BARRIER DETECTION)
        # -------------------------------------------------------------
        third_w = w // 3
        center_depth_crop = raw_depth[:, third_w : 2 * third_w]
        left_depth_crop = raw_depth[:, :third_w]
        right_depth_crop = raw_depth[:, 2 * third_w:]

        center_med = np.median(center_depth_crop) if center_depth_crop.size > 0 else 0
        left_med = np.median(left_depth_crop) if left_depth_crop.size > 0 else 0
        right_med = np.median(right_depth_crop) if right_depth_crop.size > 0 else 0

        # Close proximity pixel density in central walking corridor
        center_close_ratio = np.mean(center_depth_crop > DEPTH_WALL_DENSE_THRESHOLD) if center_depth_crop.size > 0 else 0

        self.wall_detected = False
        immediate_danger = None
        guidance_text = None

        # -------------------------------------------------------------
        # 2. RUN YOLOV8 OBJECT DETECTION
        # -------------------------------------------------------------
        results = self.yolo(frame, conf=self.conf_threshold, verbose=False)[0]

        detected_obstacles = []
        current_objects_in_view = []
        center_object_found = False
        
        # Prepare YOLO detections for indoor perception
        yolo_detections = []

        for box in results.boxes:
            cls_id = int(box.cls[0])
            conf = float(box.conf[0])
            label = self.yolo.names[cls_id]
            current_objects_in_view.append(label)

            x1, y1, x2, y2 = map(int, box.xyxy[0].tolist())
            cx = (x1 + x2) / 2
            
            # Prepare for indoor perception
            yolo_detections.append({
                "class": label,
                "confidence": conf,
                "bbox": [x1, y1, x2, y2]
            })
            
            # Spatial position
            if cx < third_w:
                pos = "on your left"
                color = (255, 200, 0)
            elif cx > 2 * third_w:
                pos = "on your right"
                color = (0, 200, 255)
            else:
                pos = "ahead"
                color = (0, 255, 0)
                center_object_found = True

            # Sample depth inside object bounding box
            crop_depth = raw_depth[max(0, y1):min(h, y2), max(0, x1):min(w, x2)]
            med_depth = np.median(crop_depth) if crop_depth.size > 0 else 0

            # Classify relative proximity using config thresholds
            proximity = classify_depth_proximity(med_depth)
            proximity_desc = get_proximity_description(proximity, lang="en")
            
            # Color coding based on proximity
            if proximity == "VERY_CLOSE" and pos == "ahead":
                color = (0, 0, 255)  # Red for close obstacle directly ahead
            elif proximity == "VERY_CLOSE":
                color = (0, 100, 255)  # Orange for close obstacle to side
            elif proximity == "CLOSE":
                color = (0, 200, 255)  # Yellow
            else:
                color = (0, 255, 0)  # Green

            if proximity == "VERY_CLOSE" and pos == "ahead":
                immediate_danger = f"Caution! {label} directly ahead."

            detected_obstacles.append((label, pos, proximity, med_depth, conf, proximity_desc))

            # Draw standard YOLO Bounding Box
            cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
            # Display relative proximity instead of fake metric distance
            tag = f"{label} {int(conf*100)}% | {proximity_desc}"
            
            (tw, th), _ = cv2.getTextSize(tag, cv2.FONT_HERSHEY_SIMPLEX, 0.45, 1)
            cv2.rectangle(frame, (x1, max(0, y1 - 20)), (x1 + tw + 6, max(0, y1)), color, -1)
            cv2.putText(frame, tag, (x1 + 3, max(14, y1 - 5)),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 0, 0), 1, cv2.LINE_AA)

        # -------------------------------------------------------------
        # 2.5 INDOOR NAVIGATION PERCEPTION & GUIDANCE
        # -------------------------------------------------------------
        indoor_perception_result = None
        if hasattr(self, "indoor_perception") and hasattr(self, "indoor_navigator"):
            try:
                # Process frame for indoor navigation
                indoor_perception_result = self.indoor_perception.process_frame(
                    yolo_detections=yolo_detections,
                    depth_map=raw_depth,
                    img_width=w,
                    img_height=h
                )
                
                # Update indoor navigator with perception
                self.indoor_navigator.update(indoor_perception_result)
                
                # Check navigation status
                nav_status = self.indoor_navigator.get_status()
                
                # Broadcast indoor navigation telemetry
                if nav_status.state != "IDLE":
                    try:
                        broadcast_event("indoor_navigation", {
                            "state": nav_status.state.value,
                            "destination": nav_status.destination,
                            "confidence": nav_status.confidence.value,
                            "distance_remaining": nav_status.distance_remaining,
                            "safe_directions": nav_status.safe_directions_count,
                            "hold_reason": nav_status.hold_reason.value if nav_status.hold_reason else None
                        })
                    except Exception:
                        pass
                
            except Exception as e:
                # Indoor perception failure should not crash main loop
                print(f"[INDOOR_PERCEPTION] Error: {e}")

        # -------------------------------------------------------------
        # 3. WALL / CONTINUOUS SURFACE DETECTION (MIDAS)
        # -------------------------------------------------------------
        # If central area is blocked across a broad field with high depth and no single object explains it
        if center_close_ratio > DEPTH_WALL_CENTER_RATIO and not center_object_found:
            self.wall_detected = True
            if center_med > DEPTH_WALL_IMMEDIATE_THRESHOLD:
                immediate_danger = "Stop! Wall directly in front of you."
            else:
                immediate_danger = "Caution! Wall ahead."

            # Calculate best clearance bypass
            if left_med < center_med - 150 and left_med < right_med:
                guidance_text = "Wall ahead. Path is clear on your left."
            elif right_med < center_med - 150:
                guidance_text = "Wall ahead. Path is clear on your right."

        # Update Live Vision State
        self.latest_detected_objects = current_objects_in_view

        # -------------------------------------------------------------
        # 4. VOICE FEEDBACK DECISION ENGINE
        # -------------------------------------------------------------
        now = time.time()

        # Check if voice assistant is busy (but NEVER block safety warnings)
        assistant_busy = (
            self.voice_assistant is not None
            and (
                self.voice_assistant._processing
                or getattr(self.voice_assistant, "is_recording", False)
                or not self.voice._queue.empty()
                or self.voice.is_speaking
            )
        )

        # Priority 1: SAFETY-CRITICAL Immediate Collision Hazard
        # These ALWAYS fire and can interrupt voice processing
        if immediate_danger:
            self.latest_closest_obstacle = immediate_danger
            speech_to_say = guidance_text if guidance_text else immediate_danger
            if speech_to_say != self.last_spoken or now - self.last_speech_time > SAFETY_ANNOUNCEMENT_COOLDOWN:
                # Safety warnings use force=True to interrupt other voice activity
                self.voice.speak(speech_to_say, force=True)
                self.last_speech_time = now
                self.last_spoken = speech_to_say

        # Priority 2: Routine navigation announcements
        # These are suppressed during voice commands to avoid interrupting user interaction
        # AND during indoor navigation mode (indoor navigator handles its own guidance)
        elif not assistant_busy and now - self.last_speech_time > ROUTINE_ANNOUNCEMENT_COOLDOWN:
            # Check if indoor navigator is active
            indoor_nav_active = (
                hasattr(self, "indoor_navigator") 
                and self.indoor_navigator.get_status().state not in ["IDLE"]
            )
            
            if not indoor_nav_active and detected_obstacles:
                detected_obstacles.sort(key=lambda x: x[3], reverse=True)
                top_lbl, top_pos, top_prox, _, _, top_prox_desc = detected_obstacles[0]
                speech_text = f"{top_lbl} {top_pos}, {top_prox_desc}."
                self.latest_closest_obstacle = speech_text

                if speech_text != self.last_spoken or now - self.last_speech_time > LONG_ANNOUNCEMENT_COOLDOWN:
                    self.voice.speak(speech_text)
                    self.last_spoken = speech_text
                    self.last_speech_time = now
            elif not indoor_nav_active:
                self.latest_closest_obstacle = None
                if self.last_spoken != "clear":
                    self.voice.speak("Path is clear.")
                    self.last_spoken = "clear"
                    self.last_speech_time = now

        # -------------------------------------------------------------
        # 5. DEPTH HEATMAP & CORRIDOR VISUALIZATION
        # -------------------------------------------------------------
        depth_colormap = cv2.applyColorMap(depth_vis, cv2.COLORMAP_INFERNO)
        
        # Draw spatial corridor lines (Left | Center | Right)
        cv2.line(depth_colormap, (third_w, 0), (third_w, h), (255, 255, 255), 1)
        cv2.line(depth_colormap, (2 * third_w, 0), (2 * third_w, h), (255, 255, 255), 1)

        # Draw Wall indicator on depth map
        if self.wall_detected:
            cv2.rectangle(depth_colormap, (third_w + 10, 10), (2 * third_w - 10, 50), (0, 0, 255), -1)
            cv2.putText(depth_colormap, "WALL AHEAD", (third_w + 20, 38),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
        
        # Draw indoor navigation status overlay
        if indoor_perception_result and hasattr(self, "indoor_navigator"):
            nav_status = self.indoor_navigator.get_status()
            if nav_status.state != "IDLE":
                # Draw navigation confidence indicator
                conf_color = {
                    "HIGH": (0, 255, 0),
                    "MEDIUM": (0, 200, 255),
                    "LOW": (0, 100, 255),
                    "INVALID": (0, 0, 255)
                }.get(indoor_perception_result.nav_confidence.value, (100, 100, 100))
                
                cv2.rectangle(depth_colormap, (10, 10), (220, 80), conf_color, 2)
                cv2.putText(depth_colormap, f"NAV: {nav_status.state.value}", (20, 30),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
                cv2.putText(depth_colormap, f"Conf: {indoor_perception_result.nav_confidence.value}", (20, 50),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
                if nav_status.destination:
                    dest_text = nav_status.destination[:15]  # Truncate long names
                    cv2.putText(depth_colormap, f"→ {dest_text}", (20, 70),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
        
        # Visual indicator when voice command is active (but vision continues)
        if self.is_voice_active():
            cv2.rectangle(frame, (10, h - 40), (200, h - 10), (0, 150, 255), -1)
            cv2.putText(frame, "🎤 Voice Active", (20, h - 18),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 2)
                        
        # Broadcast for Caregiver Dashboard
        broadcast_event("vision", self.get_vision_context())

        self._last_depth_colormap = depth_colormap.copy()
        return frame, depth_colormap, len(detected_obstacles)

    def process_ocr(self, frame):
        """Document / Sign Text Reading Mode."""
        self.toggle_esp32_led(True)
        self.voice.speak("Reading text...")
        time.sleep(0.3)

        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = self.ocr.readtext(rgb, detail=0)
        self.toggle_esp32_led(False)

        if results:
            text = " ".join(results)
            self.add_log(f"[OCR] Text: {text}")
            self.voice.speak(f"Text says: {text}")
        else:
            self.voice.speak("No clear text detected.")

        self.mode = "NAV"

    def run(self):
        print("\n" + "="*65)
        print(" SURDAS ASSISTIVE VISION & VOICE ASSISTANT RUNNING")
        print(" Features:")
        print("   • YOLOv8 Object & Obstacle Detection")
        print("   • MiDaS Dense Depth & Wall / Barrier Detection")
        print("   • Natural Voice Assistant ('Hey Surdas')")
        print(" Controls: [N] Nav Mode | [T] Read Text | [L] Torch | [Q] Quit")
        print("="*65 + "\n")

        prev_time = time.time()

        while True:
            frame = self.stream.get_frame()
            if frame is None:
                blank = np.zeros((360, 640, 3), dtype=np.uint8)
                cv2.putText(blank, "Waiting for ESP32-CAM Stream...", (60, 160),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 200, 255), 2)
                cv2.putText(blank, f"Connecting to {STREAM_URL}", (60, 200),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.5, (180, 180, 180), 1)
                cv2.putText(blank, "Make sure PC is connected to Wi-Fi: SURDAS_EYES", (60, 240),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.5, (100, 255, 100), 1)
                
                self.latest_display_frame = blank.copy()
                
                if not self.headless:
                    cv2.imshow("SURDAS - Vision Monitor", blank)
                    key = cv2.waitKey(100) & 0xFF
                    if key == ord('q'):
                        break
                else:
                    time.sleep(0.1)
                continue

            curr_time = time.time()
            fps = 1.0 / max(0.001, (curr_time - prev_time))
            prev_time = curr_time

            if self.mode == "NAV":
                rgb_view, depth_view, count = self.process_navigation(frame)
                combined = np.hstack((rgb_view, depth_view))
                display_frame = cv2.resize(combined, (1024, 400))
                
                wall_tag = " | 🧱 WALL DETECTED" if self.wall_detected else ""
                cv2.putText(display_frame, f"FPS: {int(fps)} | Objects: {count}{wall_tag}", (15, 30),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.65, (0, 255, 255), 2)
                
                self.latest_display_frame = display_frame.copy()
                
                if not self.headless:
                    cv2.imshow("SURDAS - Vision Monitor", display_frame)

            elif self.mode == "OCR":
                self.process_ocr(frame)
                
            if not self.headless:
                key = cv2.waitKey(1) & 0xFF
                if key == ord('q'):
                    break
                elif key == ord('n'):
                    self.mode = "NAV"
                    self.voice.speak("Navigation mode active.")
                elif key == ord('t'):
                    self.mode = "OCR"
                elif key == ord('l'):
                    self.toggle_esp32_led(not self.led_on)
            else:
                time.sleep(0.01)

        if self.voice_assistant:
            self.voice_assistant.stop()
        self.stream.stop()
        cv2.destroyAllWindows()


if __name__ == "__main__":
    brain = SurdasBrain()
    brain.run()
