import os
import sys
import warnings
import argparse

# Suppress PyTorch MPS & OpenCV warnings
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

# ── CLI argument parsing ─────────────────────────────────────────────────────
_parser = argparse.ArgumentParser(description="SURDAS AI Test Pipeline (Webcam)")
_parser.add_argument(
    "--model", "-m",
    default="",
    metavar="MODEL",
    help="Ollama model name. Defaults to gemma3:1b.",
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
_parser.add_argument(
    "--gui",
    action="store_true",
    help="Launch PyQt5 desktop GUI instead of OpenCV window.",
)
_args, _ = _parser.parse_known_args()
LLM_MODEL = _args.model  # empty string = use LocalLLM default (gemma3:1b)
MIC_DEVICE = _args.mic
MIC_GAIN = _args.mic_gain
USE_GUI = _args.gui

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
from ultralytics import YOLO
import easyocr

from voice.tts import VoiceEngine
from voice.assistant import VoiceAssistant
from voice.llm import LocalLLM
from voice.app_launcher import open_app, close_app
from telemetry import start_telemetry, broadcast_event

# Auto-detect best hardware accelerator
if torch.cuda.is_available():
    DEVICE = "cuda"
elif torch.backends.mps.is_available():
    DEVICE = "mps"
else:
    DEVICE = "cpu"

print("=" * 65)
print(f"  SURDAS COMPLETE AI TEST SUITE (WEBCAM + VOICE + WALL DETECTION)")
print(f"  Compute Acceleration: {DEVICE}")
if LLM_MODEL:
    print(f"  LLM Model (CLI):      {LLM_MODEL}")
print("=" * 65)


# =====================================================
# TEST SURDAS CONTROLLER (LOCAL WEBCAM & SIMULATED HARDWARE)
# =====================================================
class SurdasWebcamTester:
    def __init__(self):
        # 0. Start Dashboard Telemetry Server
        start_telemetry()

        # 1. Voice Engine
        self.voice = VoiceEngine()
        self.voice.speak("SURDAS Webcam and Voice Test Suite starting.")

        # Open Local Webcam in parallel with model initialization
        print("[CAMERA] Opening Mac Built-in Webcam (Index 0)...")
        self.cap = cv2.VideoCapture(0)
        if not self.cap.isOpened():
            print("⚠️ Could not open webcam 0. Trying webcam 1...")
            self.cap = cv2.VideoCapture(1)

        # 2. Parallel AI Model Loading (YOLOv8, MiDaS, EasyOCR, Voice/Whisper)
        print("[SYSTEM] ⚡ Loading AI models in parallel (YOLOv8, MiDaS, EasyOCR, Whisper/Voice)...")
        t0_load = time.time()

        def _load_yolo():
            ft_path = os.path.join(SCRIPT_DIR, "models", "yolov8n_india_ft.pt")
            stock_path = os.path.join(SCRIPT_DIR, "yolov8n.pt")
            yolo_path = ft_path if os.path.isfile(ft_path) else stock_path
            if os.path.isfile(ft_path):
                print("[AI] Using fine-tuned YOLOv8n (yolov8n_india_ft.pt).")
            self.yolo = YOLO(yolo_path)
            print("[AI] ✅ YOLOv8 loaded.")

        def _load_midas():
            ft_midas = os.path.join(SCRIPT_DIR, "models", "midas_small_india_ft.pt")
            midas_repo = os.path.expanduser("~/.cache/torch/hub/intel-isl_MiDaS_master")

            if not os.path.isdir(midas_repo):
                raise RuntimeError(
                    "[AI] MiDaS local cache not found at ~/.cache/torch/hub/intel-isl_MiDaS_master. "
                    "Run setup_offline_models.py while online first."
                )
            midas_transforms = torch.hub.load(midas_repo, "transforms", source="local")
            self.transform = midas_transforms.small_transform

            if os.path.isfile(ft_midas):
                print("[AI] Using fine-tuned MiDaS_small (midas_small_india_ft.pt).")
                base = torch.hub.load(midas_repo, "MiDaS_small", source="local", pretrained=False)
                state = torch.load(ft_midas, map_location="cpu")
                base.load_state_dict(state)
                self.midas = base.to(DEVICE).eval()
            else:
                self.midas = torch.hub.load(
                    midas_repo, "MiDaS_small", source="local", pretrained=True
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
                print(f"[VOICE] Voice Assistant warning ({e}). Vision remains active.")
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

        # State management
        self.mode = "NAV"  # 'NAV' or 'OCR'
        self.last_speech_time = 0
        self.last_spoken = ""
        self.led_on = False  # Simulated torch state
        self.conf_threshold = 0.25

        # Live Vision Context State
        self.latest_detected_objects = []
        self.latest_closest_obstacle = None
        self.wall_detected = False

        # Offline Navigation - Use ManualLocation for webcam testing
        from navigation import OfflineMapManager, Navigator
        from navigation.location import ManualLocation
        
        self.map_manager = OfflineMapManager()
        self.map_manager.auto_load()
        self.navigator = Navigator(self.map_manager, self)
        
        # For testing, we use a manual location provider with clear warning
        test_loc = DEFAULT_TEST_LOCATION
        self.location_provider = ManualLocation(
            lat=test_loc["lat"],
            lon=test_loc["lon"],
            name=f"{test_loc['name']} - WEBCAM TEST MODE"
        )
        self.navigator._current_location = self.location_provider.get_location()

        self.voice.speak("Test suite ready. Say Hey Surdas or speak commands.")

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

    def get_vision_context(self) -> dict:
        """Returns live scene state for LLM queries."""
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
        cam_stat   = "active" if self.cap.isOpened() else "error"
        torch_stat = "on" if self.led_on else "off"
        obj_count  = len(self.latest_detected_objects)
        wall_stat  = "Wall detected." if self.wall_detected else "No wall."
        model_name = self.llm.get_current_model() if self.llm else "none"
        return (
            f"Webcam is {cam_stat}. "
            f"Flashlight is {torch_stat}. "
            f"Mode is {self.mode}. "
            f"Detecting {obj_count} objects. "
            f"{wall_stat} "
            f"AI model is {model_name}."
        )

    def is_voice_active(self) -> bool:
        """Returns True if a voice command is being received, processed, or spoken."""
        if self.voice_assistant is not None and getattr(self.voice_assistant, "is_active", False):
            return True
        if self.voice.is_speaking or not self.voice._queue.empty():
            return True
        return False

    def toggle_esp32_led(self, state: bool):
        """Simulate torch toggle in local test mode."""
        self.led_on = state
        print(f"[HARDWARE SIMULATION] Torch state changed to: {'ON' if state else 'OFF'}")

    def compute_depth(self, frame):
        """Generates relative depth map from MiDaS."""
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
        if hasattr(self, "navigator") and self.navigator:
            try:
                self.navigator.update_location(self.location_provider.get_location())
            except Exception:
                pass
        
        h, w, _ = frame.shape
        third_w = w // 3

        # -------------------------------------------------------------
        # STOP YOLO & MIDAS INFERENCE WHILE VOICE COMMAND IS ACTIVE
        # -------------------------------------------------------------
        if self.is_voice_active():
            if getattr(self, "_last_depth_colormap", None) is not None:
                depth_colormap = self._last_depth_colormap.copy()
            else:
                depth_colormap = np.zeros_like(frame)

            # Visual overlay indicating vision paused for voice priority
            cv2.rectangle(frame, (10, 10), (w - 10, 52), (0, 0, 180), -1)
            cv2.putText(frame, "🎤 VOICE COMMAND ACTIVE - YOLO & MIDAS PAUSED", (20, 38),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.55, (255, 255, 255), 2)

            cv2.rectangle(depth_colormap, (third_w, 10), (2 * third_w, 52), (0, 0, 180), -1)
            cv2.putText(depth_colormap, "VISION PAUSED", (third_w + 15, 38),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.55, (255, 255, 255), 2)

            time.sleep(0.03)  # Yield CPU/GPU cycles to STT & LLM
            return frame, depth_colormap, len(self.latest_detected_objects)

        raw_depth, depth_vis = self.compute_depth(frame)
        
        # -------------------------------------------------------------
        # 1. DENSE MIDAS SPATIAL ANALYSIS (WALL DETECTION)
        # -------------------------------------------------------------
        center_depth_crop = raw_depth[:, third_w : 2 * third_w]
        left_depth_crop = raw_depth[:, :third_w]
        right_depth_crop = raw_depth[:, 2 * third_w:]

        center_med = np.median(center_depth_crop) if center_depth_crop.size > 0 else 0
        left_med = np.median(left_depth_crop) if left_depth_crop.size > 0 else 0
        right_med = np.median(right_depth_crop) if right_depth_crop.size > 0 else 0

        center_close_ratio = np.mean(center_depth_crop > 950) if center_depth_crop.size > 0 else 0

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

        for box in results.boxes:
            cls_id = int(box.cls[0])
            conf = float(box.conf[0])
            label = self.yolo.names[cls_id]
            current_objects_in_view.append(label)

            x1, y1, x2, y2 = map(int, box.xyxy[0].tolist())
            cx = (x1 + x2) / 2
            
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

            # Sample depth
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

            # Bounding Box
            cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
            # Display relative proximity instead of fake metric distance
            tag = f"{label} {int(conf*100)}% | {proximity_desc}"
            
            (tw, th), _ = cv2.getTextSize(tag, cv2.FONT_HERSHEY_SIMPLEX, 0.45, 1)
            cv2.rectangle(frame, (x1, max(0, y1 - 20)), (x1 + tw + 6, max(0, y1)), color, -1)
            cv2.putText(frame, tag, (x1 + 3, max(14, y1 - 5)),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 0, 0), 1, cv2.LINE_AA)

        # -------------------------------------------------------------
        # 3. WALL DETECTION VIA MIDAS DENSE DEPTH
        # -------------------------------------------------------------
        if center_close_ratio > 0.38 and not center_object_found:
            self.wall_detected = True
            if center_med > 1150:
                immediate_danger = "Stop! Wall directly in front of you."
            else:
                immediate_danger = "Caution! Wall ahead."

            if left_med < center_med - 150 and left_med < right_med:
                guidance_text = "Wall ahead. Path is clear on your left."
            elif right_med < center_med - 150:
                guidance_text = "Wall ahead. Path is clear on your right."

        # Update Live Vision Context
        self.latest_detected_objects = current_objects_in_view

        # -------------------------------------------------------------
        # 4. VOICE FEEDBACK DECISION ENGINE
        # -------------------------------------------------------------
        now = time.time()

        # Don't queue nav chatter while voice assistant is active or user is speaking
        assistant_busy = (
            self.voice_assistant is not None
            and (
                self.voice_assistant._processing
                or getattr(self.voice_assistant, "is_recording", False)
                or not self.voice._queue.empty()
                or self.voice.is_speaking
            )
        )

        if immediate_danger:
            self.latest_closest_obstacle = immediate_danger
            speech_to_say = guidance_text if guidance_text else immediate_danger
            if speech_to_say != self.last_spoken or now - self.last_speech_time > 3.0:
                self.voice.speak(speech_to_say, force=True)
                self.last_speech_time = now
                self.last_spoken = speech_to_say

        elif not assistant_busy and now - self.last_speech_time > 4.0:
            if detected_obstacles:
                detected_obstacles.sort(key=lambda x: x[3], reverse=True)
                top_lbl, top_pos, top_prox, _, _, top_dist = detected_obstacles[0]
                speech_text = f"{top_lbl} {top_pos}, about {top_dist} meters away."
                self.latest_closest_obstacle = speech_text

                if speech_text != self.last_spoken or now - self.last_speech_time > 8.0:
                    self.voice.speak(speech_text)
                    self.last_spoken = speech_text
                    self.last_speech_time = now
            else:
                self.latest_closest_obstacle = None
                if self.last_spoken != "clear":
                    self.voice.speak("Path is clear.")
                    self.last_spoken = "clear"
                    self.last_speech_time = now

        depth_colormap = cv2.applyColorMap(depth_vis, cv2.COLORMAP_INFERNO)
        
        # Draw spatial corridor lines
        cv2.line(depth_colormap, (third_w, 0), (third_w, h), (255, 255, 255), 1)
        cv2.line(depth_colormap, (2 * third_w, 0), (2 * third_w, h), (255, 255, 255), 1)

        # Draw Wall indicator
        if self.wall_detected:
            cv2.rectangle(depth_colormap, (third_w + 10, 10), (2 * third_w - 10, 50), (0, 0, 255), -1)
            cv2.putText(depth_colormap, "WALL AHEAD", (third_w + 20, 38),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)

        try:
            broadcast_event("vision", self.get_vision_context())
        except Exception:
            pass

        self._last_depth_colormap = depth_colormap.copy()
        return frame, depth_colormap, len(detected_obstacles)

    def process_ocr(self, frame):
        """Document / Sign Text Reading Mode."""
        self.voice.speak("Reading text...")
        time.sleep(0.2)

        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = self.ocr.readtext(rgb, detail=0)

        if results:
            text = " ".join(results)
            print(f"[OCR] Text: {text}")
            self.voice.speak(f"Text says: {text}")
        else:
            self.voice.speak("No clear text detected.")

        self.mode = "NAV"

    def run(self):
        print("\n" + "="*65)
        print(" SURDAS TEST SUITE RUNNING (WEBCAM + VOICE ASSISTANT + WALLS)")
        print(" Spoken Commands:")
        print("   • 'Hey Surdas, start navigation'")
        print("   • 'Hey Surdas, read text'")
        print("   • 'Hey Surdas, what do you see?'")
        print("   • 'Hey Surdas, turn on light'")
        print(" Keyboard Shortcuts:")
        print("   • [N] Nav Mode | [T] Read Text (OCR) | [L] Toggle Light | [Q] Quit")
        print("="*65 + "\n")

        prev_time = time.time()

        while True:
            ret, frame = self.cap.read()
            if not ret:
                print("❌ Failed to grab frame from webcam.")
                break
            frame = cv2.flip(frame, 1)  # Mirror horizontally (selfie view)

            curr_time = time.time()
            fps = 1.0 / max(0.001, (curr_time - prev_time))
            prev_time = curr_time

            if self.mode == "NAV":
                rgb_view, depth_view, count = self.process_navigation(frame)
                combined = np.hstack((rgb_view, depth_view))
                display_frame = cv2.resize(combined, (1280, 480))

                # HUD Indicators
                torch_status = "💡 Torch: ON" if self.led_on else "Torch: OFF"
                wall_status = " | 🧱 WALL DETECTED" if self.wall_detected else ""
                
                cv2.putText(display_frame, f"FPS: {int(fps)} | Objects: {count}{wall_status} | {torch_status}", (20, 35),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)
                cv2.putText(display_frame, "🎤 Voice: Say 'Hey Surdas' | [T] OCR | [Q] Quit", (20, 70),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.55, (100, 255, 100), 2)

                cv2.imshow("SURDAS - Webcam & Voice Assistant Test Suite", display_frame)

            elif self.mode == "OCR":
                self.process_ocr(frame)

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

        if self.voice_assistant:
            self.voice_assistant.stop()
        self.cap.release()
        cv2.destroyAllWindows()


if __name__ == "__main__":
    tester = SurdasWebcamTester()
    tester.run()
