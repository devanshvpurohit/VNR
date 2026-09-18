"""
command_router.py — SURDAS Voice Command Dispatcher (bilingual EN + HI)

Priority order:
  1. App launch / close commands          → app_launcher (instant, no LLM)
  2. SURDAS hardware / mode commands      → deterministic handlers (instant)
  3. Vision description queries           → fast heuristic (instant)
  4. General knowledge / conversation     → LocalLLM via Ollama (streamed)

All phrase matching uses voice.i18n_phrases.match() so both English and
Hindi commands are handled without any explicit language switch.
"""
import re
import subprocess
from typing import TYPE_CHECKING

from voice.app_launcher import open_app, close_app, get_app_list
import voice.i18n_phrases as _p
from voice.i18n_phrases import match as _match, HINDI_FILLERS

if TYPE_CHECKING:
    from surdas_brain import SurdasBrain
    from voice.llm import LocalLLM


# ── helpers ──────────────────────────────────────────────────────────────────

def _extract_app_name(text: str, trigger: str) -> str:
    """Pull out the app name that follows a trigger word/phrase."""
    idx = text.find(trigger)
    if idx == -1:
        return ""
    after = text[idx + len(trigger):].strip()
    # Strip English and Hindi filler words
    for filler in HINDI_FILLERS:
        after = after.replace(filler, "").strip()
    return after.strip()


# ── main router ──────────────────────────────────────────────────────────────

class CommandRouter:
    """
    Routes transcribed voice text to the correct handler.
    lang is now threaded through from the STT result so TTS can reply
    in the same language.
    """

    def __init__(self, brain: "SurdasBrain", llm: "LocalLLM"):
        self.brain = brain
        self.llm = llm
        self.navigator = getattr(brain, "navigator", None)

    # ─────────────────────────────────────────────────────────────────────────
    def route_command(self, raw_text: str, lang: str = "en") -> bool:
        text = raw_text.strip().lower()
        if not text:
            return False

        print(f"[ROUTER] ▶ '{text}'  [lang={lang}]")

        # ── 0. OFFLINE NAVIGATION ─────────────────────────────────────────────
        if self._handle_navigation_commands(text, raw_text, lang):
            return True

        # ── 1. APP LAUNCHER ───────────────────────────────────────────────────
        if self._handle_app_commands(text, raw_text, lang):
            return True

        # ── 2. HARDWARE / MODE COMMANDS ───────────────────────────────────────
        if self._handle_hardware_commands(text, lang):
            return True

        # ── 3. FAST VISION DESCRIPTION ────────────────────────────────────────
        if self._handle_vision_query(text, lang):
            return True

        # ── 4. MODEL MANAGEMENT ───────────────────────────────────────────────
        if self._handle_model_commands(text, lang):
            return True

        # ── 5. GENERAL KNOWLEDGE / CONVERSATION (Ollama LLM) ─────────────────
        self._handle_llm_query(raw_text, lang)
        return True

    # ─────────────────────────────────────────────────────────────────────────
    # Category 0 — Offline Navigation Commands
    # ─────────────────────────────────────────────────────────────────────────
    def _handle_navigation_commands(self, text: str, raw_text: str, lang: str) -> bool:
        if not self.navigator:
            return False

        # Stop navigation
        if _match(_p.NAV_STOP, text):
            self.navigator.stop(lang)
            return True

        # Repeat instructions
        if _match(_p.NAV_REPEAT, text):
            self.navigator.repeat_instruction()
            return True

        # Where am I
        if _match(_p.NAV_WHERE_AM_I, text):
            status = self.navigator.get_status()
            loc = getattr(self.navigator, "_current_location", None)
            if not loc:
                from navigation.voice_guidance import NavigationVoiceGuide
                self.brain.voice.speak(NavigationVoiceGuide.gps_unavailable(lang), lang)
                return True
            results = self.navigator._manager.search_place("", loc, limit=1)
            if results:
                from navigation.voice_guidance import NavigationVoiceGuide
                msg = NavigationVoiceGuide.where_am_i(results[0]["name"], results[0]["distance_m"], loc.get("accuracy", 10.0), lang)
                self.brain.voice.speak(msg, lang)
            return True

        # Nearest <category>
        if _match(_p.NAV_NEAREST, raw_text):
            loc = getattr(self.navigator, "_current_location", None)
            from navigation.voice_guidance import NavigationVoiceGuide
            # strip filler
            q = text
            for trigger in _p.NAV_NEAREST["en"] + _p.NAV_NEAREST["hi"]:
                q = q.replace(trigger, "").strip()
            # Try to search
            results = self.navigator._manager.search_place(raw_text, loc, limit=1)
            if results:
                msg = NavigationVoiceGuide.nearest_result(results[0], results[0]["type"] or "place", lang)
                self.brain.voice.speak(msg, lang)
            else:
                self.brain.voice.speak(NavigationVoiceGuide.no_nearby("place", lang), lang)
            return True

        # Navigate to <destination>
        for trigger in _p.NAV_NAVIGATE_TO["en"]:
            if trigger in text:
                dest = _extract_app_name(text, trigger)  # re-use the app name extractor
                if dest:
                    self.navigator.start(dest, lang=lang)
                    return True
        for trigger in _p.NAV_NAVIGATE_TO["hi"]:
            if trigger in raw_text:
                dest = _extract_app_name(raw_text, trigger)
                if dest:
                    self.navigator.start(dest, lang=lang)
                    return True

        return False

    # ─────────────────────────────────────────────────────────────────────────
    # Category 1 — App commands
    # ─────────────────────────────────────────────────────────────────────────
    def _handle_app_commands(self, text: str, raw_text: str, lang: str) -> bool:

        # OPEN triggers — check English triggers in lowercased text and
        # Hindi triggers (matched via i18n_phrases) in original text.
        open_en_triggers = [
            "open ", "launch ", "start ", "run ",
            "open up ", "open the ", "launch the ", "can you open ",
        ]
        open_hi_triggers = _p.APP_OPEN["hi"]

        for trigger in open_en_triggers:
            if trigger in text:
                app_name = _extract_app_name(text, trigger)
                if not app_name:
                    continue
                success, msg = open_app(app_name)
                self.brain.voice.speak(msg, lang=lang)
                return True

        for trigger in open_hi_triggers:
            if trigger in raw_text:
                app_name = _extract_app_name(raw_text, trigger)
                if not app_name:
                    continue
                success, msg = open_app(app_name)
                self.brain.voice.speak(msg, lang=lang)
                return True

        # CLOSE / QUIT triggers
        close_en_triggers = [
            "close ", "quit ", "exit ", "kill ",
            "close the ", "quit the ",
        ]
        close_hi_triggers = _p.APP_CLOSE["hi"]

        for trigger in close_en_triggers:
            if trigger in text:
                app_name = _extract_app_name(text, trigger)
                if not app_name:
                    continue
                success, msg = close_app(app_name)
                self.brain.voice.speak(msg, lang=lang)
                return True

        for trigger in close_hi_triggers:
            if trigger in raw_text:
                app_name = _extract_app_name(raw_text, trigger)
                if not app_name:
                    continue
                success, msg = close_app(app_name)
                self.brain.voice.speak(msg, lang=lang)
                return True

        # App list query
        if _match(_p.APP_LIST, raw_text):
            self.brain.voice.speak(get_app_list(), lang=lang)
            return True

        return False

    # ─────────────────────────────────────────────────────────────────────────
    # Category 2 — Hardware / SURDAS mode commands
    # ─────────────────────────────────────────────────────────────────────────
    def _handle_hardware_commands(self, text: str, lang: str) -> bool:

        # Navigation mode
        if _match(_p.NAV_MODE, text):
            self.brain.mode = "NAV"
            if lang == "hi":
                self.brain.voice.speak("नेविगेशन मोड चालू।", lang="hi")
            else:
                self.brain.voice.speak("Navigation mode active.")
            return True

        # OCR / Read text mode
        if _match(_p.OCR_MODE, text):
            self.brain.mode = "OCR"
            return True

        # Flashlight ON
        if _match(_p.TORCH_ON, text):
            self.brain.toggle_esp32_led(True)
            if lang == "hi":
                self.brain.voice.speak("टॉर्च चालू।", lang="hi")
            else:
                self.brain.voice.speak("Flashlight on.")
            return True

        # Flashlight OFF
        if _match(_p.TORCH_OFF, text):
            self.brain.toggle_esp32_led(False)
            if lang == "hi":
                self.brain.voice.speak("टॉर्च बंद।", lang="hi")
            else:
                self.brain.voice.speak("Flashlight off.")
            return True

        # Stop / silence
        if _match(_p.STOP_SILENCE, text) or text in ("stop", "quiet", "silence", "be quiet", "shut up", "cancel"):
            self.brain.voice.speak("", force=True)
            return True

        # System status
        if _match(_p.STATUS, text):
            self.brain.voice.speak(self.brain.get_status_summary(), lang=lang)
            return True

        # Time
        if _match(_p.TIME_QUERY, text):
            import datetime
            now = datetime.datetime.now().strftime("%I:%M %p").lstrip("0")
            if lang == "hi":
                self.brain.voice.speak(f"अभी {now} बजे हैं।", lang="hi", force=True)
            else:
                self.brain.voice.speak(f"The time is {now}.", force=True)
            return True

        # Date
        if _match(_p.DATE_QUERY, text):
            import datetime
            today = datetime.datetime.now().strftime("%A, %B %d, %Y")
            if lang == "hi":
                self.brain.voice.speak(f"आज {today} है।", lang="hi", force=True)
            else:
                self.brain.voice.speak(f"Today is {today}.", force=True)
            return True

        # Volume up
        if _match(_p.VOLUME_UP, text):
            subprocess.run(["osascript", "-e", "set volume output volume (output volume of (get volume settings) + 10)"])
            if lang == "hi":
                self.brain.voice.speak("आवाज़ बढ़ाई।", lang="hi")
            else:
                self.brain.voice.speak("Volume increased.")
            return True

        # Volume down
        if _match(_p.VOLUME_DOWN, text):
            subprocess.run(["osascript", "-e", "set volume output volume (output volume of (get volume settings) - 10)"])
            if lang == "hi":
                self.brain.voice.speak("आवाज़ कम की।", lang="hi")
            else:
                self.brain.voice.speak("Volume decreased.")
            return True

        # Mute
        if _match(_p.VOLUME_MUTE, text):
            subprocess.run(["osascript", "-e", "set volume with output muted"])
            if lang == "hi":
                self.brain.voice.speak("म्यूट।", lang="hi")
            else:
                self.brain.voice.speak("Muted.")
            return True

        # Screenshot
        if _match(_p.SCREENSHOT, text):
            subprocess.Popen(["screencapture", "-i", "/tmp/surdas_screenshot.png"])
            if lang == "hi":
                self.brain.voice.speak("स्क्रीनशॉट ले रहा हूँ।", lang="hi")
            else:
                self.brain.voice.speak("Taking a screenshot.")
            return True

        # Lock screen
        if _match(_p.LOCK_SCREEN, text):
            subprocess.Popen(["osascript", "-e",
                'tell application "System Events" to keystroke "q" using {command down, control down}'])
            if lang == "hi":
                self.brain.voice.speak("स्क्रीन लॉक हो रही है।", lang="hi")
            else:
                self.brain.voice.speak("Locking your screen.")
            return True

        return False

    # ─────────────────────────────────────────────────────────────────────────
    # Category 3 — Fast vision description (no LLM latency)
    # ─────────────────────────────────────────────────────────────────────────
    def _handle_vision_query(self, text: str, lang: str) -> bool:
        if not _match(_p.WHAT_DO_YOU_SEE, text):
            return False

        ctx = self.brain.get_vision_context()
        objects = ctx.get("detected_objects", [])
        closest = ctx.get("closest_obstacle", None)
        wall = ctx.get("wall_ahead", False)

        if wall:
            if lang == "hi":
                reply = "सावधान! सामने दीवार है।"
            else:
                reply = "Warning! There is a wall or barrier directly ahead."
        elif not objects:
            if lang == "hi":
                reply = "रास्ता साफ है। कोई रुकावट नहीं।"
            else:
                reply = "The path ahead looks clear. No obstacles detected."
        else:
            unique = list(dict.fromkeys(objects))
            obj_str = ", ".join(unique[:4])
            if lang == "hi":
                reply = f"मुझे दिख रहा है: {obj_str}। {closest if closest else 'सावधान रहें।'}"
            else:
                reply = f"I can see: {obj_str}. {closest if closest else 'Use caution.'}"

        self.brain.voice.speak(reply, lang=lang)
        return True

    # ─────────────────────────────────────────────────────────────────────────
    # Category 4 — Model management commands
    # ─────────────────────────────────────────────────────────────────────────
    def _handle_model_commands(self, text: str, lang: str) -> bool:

        if _match(_p.MODEL_LIST, text):
            msg = self.llm.spoken_model_list()
            self.brain.voice.speak(msg, lang=lang)
            return True

        if _match(_p.MODEL_CURRENT, text):
            self.brain.voice.speak(
                f"I am using {self.llm.get_current_model()}.", lang=lang
            )
            return True

        for trigger in ("switch to ", "use model ", "change model to ",
                        "switch model to ", "use ", "load model "):
            if trigger in text:
                after = text[text.find(trigger) + len(trigger):].strip()
                if after.startswith("model "):
                    after = after[6:]
                model_name = after.strip()
                if not model_name:
                    continue
                if not re.search(r"[\d\.]", model_name) and model_name not in (
                    "llama", "mistral", "gemma", "phi", "qwen", "deepseek",
                    "tinyllama", "codellama", "dolphin", "vicuna", "orca",
                ):
                    continue

                success = self.llm.switch_model(model_name)
                if success:
                    self.brain.voice.speak(
                        f"Switched to {self.llm.get_current_model()}.", lang=lang
                    )
                    try:
                        from telemetry import broadcast_event
                        broadcast_event("model_change", {"model": self.llm.model_name})
                    except Exception:
                        pass
                else:
                    available = self.llm.get_available_models()
                    names = ", ".join(m.replace(":latest", "") for m in available[:4])
                    self.brain.voice.speak(
                        f"Model {model_name} not found. Available: {names}.", lang=lang
                    )
                return True

        return False

    # ─────────────────────────────────────────────────────────────────────────
    # Category 5 — General LLM query
    # ─────────────────────────────────────────────────────────────────────────
    def _handle_llm_query(self, raw_text: str, lang: str = "en"):
        if not self.llm.is_available():
            if lang == "hi":
                self.brain.voice.speak(
                    "Ollama नहीं चल रहा। ollama serve चलाएँ।", lang="hi"
                )
            else:
                self.brain.voice.speak(
                    "Ollama is not running. Start it with: ollama serve."
                )
            return

        print("[ROUTER] → Ollama LLM (streaming)…")
        vision_ctx = self.brain.get_vision_context()

        for sentence in self.llm.query(raw_text, vision_context=vision_ctx, lang=lang):
            if sentence:
                print(f"[LLM] {sentence}")
                self.brain.voice.speak(sentence, lang=lang)
