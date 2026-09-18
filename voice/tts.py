"""
tts.py — Zero-latency Voice Engine for SURDAS

Design goals:
  • Print to terminal INSTANTLY (before audio even starts)
  • Non-blocking audio playback via background worker thread
  • Reliable is_speaking flag to prevent microphone echo self-interruption
  • Clean subprocess execution with '--' option delimiter on macOS
  • Bilingual support: lang="hi" uses Lekha voice on macOS / hi voice on pyttsx3
"""
import threading
import queue
import sys
import subprocess
import time
import re

_MACOS_RATE = 200
_HI_VOICE   = "Lekha"   # macOS Hindi voice (pre-installed on Indian locale Macs)
_EN_VOICE   = None       # None = system default


def clean_speech_text(text: str) -> str:
    """Strip markdown, symbols, bullets, emojis, and formatting for clean TTS."""
    if not text:
        return ""

    # Remove code blocks and inline code
    t = re.sub(r"```[\s\S]*?```", "", text)
    t = re.sub(r"`([^`]+)`", r"\1", t)

    # Remove markdown links [label](url) -> label
    t = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", t)

    # Remove markdown headers #, ##, etc.
    t = re.sub(r"^#+\s*", "", t, flags=re.MULTILINE)

    # Remove bullet markers (- , * , + , > )
    t = re.sub(r"^[\s\*\-\+\>]+\s*", "", t, flags=re.MULTILINE)

    # Remove numbered bullets (1. , 2. )
    t = re.sub(r"^\d+\.\s*", "", t, flags=re.MULTILINE)

    # Remove bold/italic markers
    t = t.replace("*", "").replace("_", "").replace("~", "")
    t = t.replace('"', "").replace("'", "").replace("#", "")
    t = t.replace("[", "").replace("]", "").replace("{", "").replace("}", "")
    t = t.replace("(", "").replace(")", "").replace("\\", "")

    # Normalize whitespace
    t = re.sub(r"\s+", " ", t).strip()
    return t


class VoiceEngine:
    def __init__(self):
        self.is_macos    = (sys.platform == "darwin")
        self._queue      = queue.Queue(maxsize=30)
        self._proc       = None
        self._proc_lock  = threading.Lock()
        self._running    = True
        self._pyttsx     = None
        self._hi_voice_id = None   # pyttsx3 Hindi voice id (non-macOS)
        self._speaking   = False
        self._last_spoke = 0

        if not self.is_macos:
            self._init_pyttsx()

        threading.Thread(target=self._worker, daemon=True, name="TTSWorker").start()

    @property
    def is_speaking(self) -> bool:
        """Returns True if speech audio is currently playing or queued."""
        if self._speaking or not self._queue.empty():
            return True
        with self._proc_lock:
            return self._proc is not None and self._proc.poll() is None

    @property
    def last_speech_time(self) -> float:
        return self._last_spoke

    # ── pyttsx3 fallback ────────────────────────────────────────────────────
    def _init_pyttsx(self):
        try:
            import pyttsx3
            e = pyttsx3.init()
            e.setProperty("rate", _MACOS_RATE)
            self._pyttsx = e

            # Scan for a Hindi voice
            voices = e.getProperty("voices")
            for v in voices:
                vid = (v.id or "").lower()
                vlangs = " ".join(
                    (l.decode() if isinstance(l, bytes) else l)
                    for l in (v.languages or [])
                ).lower()
                if "hi" in vid or "hindi" in vid or "hi" in vlangs or "hindi" in vlangs:
                    self._hi_voice_id = v.id
                    break

            if self._hi_voice_id:
                print(f"[TTS] pyttsx3 Hindi voice found: {self._hi_voice_id}")
            else:
                print("[TTS] pyttsx3: no Hindi voice found — Hindi will use default voice.")

        except Exception as ex:
            print(f"[TTS] pyttsx3 init: {ex}")

    # ── Worker: drains queue in background ──────────────────────────────────
    def _worker(self):
        while self._running:
            try:
                item = self._queue.get(timeout=0.05)
                if isinstance(item, tuple):
                    text, lang = item
                else:
                    text, lang = item, "en"
                self._speaking = True
                self._say(text, lang)
                self._speaking = False
                self._last_spoke = time.time()
                self._queue.task_done()
            except queue.Empty:
                self._speaking = False
            except Exception as ex:
                self._speaking = False
                print(f"[TTS] worker error: {ex}")

    # ── Core speech call ─────────────────────────────────────────────────────
    def _say(self, text: str, lang: str = "en"):
        if not text or not text.strip():
            return
        clean = text.strip()
        if self.is_macos:
            voice = _HI_VOICE if lang == "hi" else (_EN_VOICE or "")
            cmd = ["say", "-r", str(_MACOS_RATE)]
            if voice:
                cmd += ["-v", voice]
            cmd += ["--", clean]
            try:
                with self._proc_lock:
                    self._proc = subprocess.Popen(
                        cmd,
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                    )
                self._proc.wait()
            except Exception as ex:
                print(f"[TTS] macOS 'say' error: {ex}")
            finally:
                with self._proc_lock:
                    self._proc = None
        elif self._pyttsx:
            try:
                if lang == "hi" and self._hi_voice_id:
                    self._pyttsx.setProperty("voice", self._hi_voice_id)
                elif lang != "hi" and self._hi_voice_id:
                    # Reset to default if we had changed it
                    self._pyttsx.setProperty("voice", "")
                self._pyttsx.say(clean)
                self._pyttsx.runAndWait()
            except Exception as ex:
                print(f"[TTS] pyttsx3 error: {ex}")

    # ── Interrupt speech ────────────────────────────────────────────────────
    def _interrupt(self):
        with self._proc_lock:
            proc = self._proc
        if proc and proc.poll() is None:
            try:
                proc.terminate()
                proc.wait(timeout=0.2)
            except Exception:
                pass
        self._speaking = False

    # ── Public API ───────────────────────────────────────────────────────────
    def speak(self, text: str, force: bool = False, lang: str = "en"):
        """
        Queue text for speech.

        Args:
            text:   What to say.
            force:  If True, clear any pending queue items and say immediately.
            lang:   "en" or "hi" — selects voice accordingly.
        """
        if not text or not text.strip():
            if force:
                self._drain()
            return

        clean = clean_speech_text(text)
        if not clean:
            return

        # Print immediately to terminal
        print(f"[SPEECH OUT] 🔊  {clean}")

        # Broadcast to dashboard
        try:
            from telemetry import broadcast_event
            broadcast_event("speech", {"text": clean, "lang": lang})
        except Exception:
            pass

        if force:
            self._drain()
            self._interrupt()

        try:
            self._queue.put((clean, lang), timeout=0.5)
        except queue.Full:
            pass

    def _drain(self):
        """Empty pending speech queue."""
        while not self._queue.empty():
            try:
                self._queue.get_nowait()
                self._queue.task_done()
            except queue.Empty:
                break

    def stop(self):
        self._running = False
        self._drain()
        self._interrupt()
