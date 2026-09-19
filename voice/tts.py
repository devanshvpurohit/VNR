"""
voice/tts.py — Priority-based, Preemptive Voice Engine for SURDAS.

Features:
  • Single unified TTS worker thread (Requirement 8)
  • Priority-based queue using SpeechPriority:
      1: CRITICAL_SAFETY (immediate collision/danger, interrupts everything)
      2: NAVIGATION (turn guidance, approaching waypoint)
      3: USER_COMMAND (direct response to user instructions)
      4: LLM_RESPONSE (conversational response)
      5: STATUS (periodic status / path is clear)
  • Preemption: higher-priority messages immediately interrupt lower-priority playback
  • Full Barge-In support: wake-word detection interrupts current speech instantly
  • Device recovery: catches and recovers from audio/subprocess errors without crash (Requirement 38)
  • Bilingual: English (default/Samantha) and Hindi (Lekha) on macOS; pyttsx3 fallback on Linux
"""
from __future__ import annotations

import sys
import os
import subprocess
import threading
import queue
import time
import re
from typing import Optional, Tuple

from system_state import SpeechPriority

_MACOS_RATE = 200
_HI_VOICE = "Lekha"   # macOS Hindi voice
_EN_VOICE = None      # System default


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

    # Remove bold/italic markers and punctuation clutter
    t = t.replace("*", "").replace("_", "").replace("~", "")
    t = t.replace('"', "").replace("'", "").replace("#", "")
    t = t.replace("[", "").replace("]", "").replace("{", "").replace("}", "")
    t = t.replace("(", "").replace(")", "").replace("\\", "")

    # Normalize whitespace
    t = re.sub(r"\s+", " ", t).strip()
    return t


class VoiceEngine:
    """
    Priority-based Text-to-Speech Engine with preemption and barge-in.
    """

    def __init__(self):
        self.is_macos = (sys.platform == "darwin")
        # PriorityQueue items: (priority_int, counter, text, lang)
        self._queue: queue.PriorityQueue[Tuple[int, int, str, str]] = queue.PriorityQueue(maxsize=50)
        self._counter = 0
        self._proc: Optional[subprocess.Popen] = None
        self._proc_lock = threading.Lock()
        self._running = True
        self._pyttsx = None
        self._hi_voice_id = None
        
        self._speaking = False
        self._current_priority: Optional[int] = None
        self._last_spoke = 0.0
        self._error_count = 0

        if not self.is_macos:
            self._init_pyttsx()

        self._worker_thread = threading.Thread(target=self._worker, daemon=True, name="TTSWorker")
        self._worker_thread.start()

    @property
    def is_speaking(self) -> bool:
        """Returns True if speech is actively playing or queued."""
        if self._speaking or not self._queue.empty():
            return True
        with self._proc_lock:
            return self._proc is not None and self._proc.poll() is None

    @property
    def current_priority(self) -> Optional[int]:
        return self._current_priority

    @property
    def last_speech_time(self) -> float:
        return self._last_spoke

    # ── pyttsx3 fallback initialization ──────────────────────────────────────
    def _init_pyttsx(self):
        try:
            import pyttsx3
            e = pyttsx3.init()
            e.setProperty("rate", _MACOS_RATE)
            self._pyttsx = e

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
                print("[TTS] pyttsx3: no Hindi voice found — will use default voice.")
        except Exception as ex:
            print(f"[TTS] pyttsx3 init error: {ex}")

    # ── Background Worker ────────────────────────────────────────────────────
    def _worker(self):
        while self._running:
            try:
                # Wait for next priority item
                item = self._queue.get(timeout=0.05)
                prio_int, _, text, lang = item

                self._speaking = True
                self._current_priority = prio_int

                # Play speech
                self._say(text, lang)

                self._speaking = False
                self._current_priority = None
                self._last_spoke = time.time()
                self._queue.task_done()
            except queue.Empty:
                self._speaking = False
                self._current_priority = None
            except Exception as ex:
                self._speaking = False
                self._current_priority = None
                self._error_count += 1
                print(f"[TTS] Worker error: {ex}")
                time.sleep(0.05)

    # ── Audio Playback ───────────────────────────────────────────────────────
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
                # Wait for process to complete (can be terminated by _interrupt)
                if self._proc:
                    self._proc.wait()
            except Exception as ex:
                print(f"[TTS] macOS 'say' error: {ex}")
                self._recover_device()
            finally:
                with self._proc_lock:
                    self._proc = None

        elif self._pyttsx:
            try:
                if lang == "hi" and self._hi_voice_id:
                    self._pyttsx.setProperty("voice", self._hi_voice_id)
                elif lang != "hi" and self._hi_voice_id:
                    self._pyttsx.setProperty("voice", "")
                self._pyttsx.say(clean)
                self._pyttsx.runAndWait()
            except Exception as ex:
                print(f"[TTS] pyttsx3 error: {ex}")
                self._recover_device()

    # ── Interruption / Preemption ────────────────────────────────────────────
    def _interrupt(self):
        """Immediately terminate currently playing audio process."""
        with self._proc_lock:
            proc = self._proc
            if proc and proc.poll() is None:
                try:
                    proc.kill()
                    proc.wait(timeout=0.1)
                except Exception:
                    pass
            self._proc = None
        self._speaking = False
        self._current_priority = None

    def _drain(self, min_priority: int = 1):
        """
        Drain items from queue whose priority is >= min_priority (i.e. equal or lower importance).
        """
        items_to_keep = []
        while not self._queue.empty():
            try:
                item = self._queue.get_nowait()
                prio_int, _, _, _ = item
                if prio_int < min_priority:
                    items_to_keep.append(item)
                self._queue.task_done()
            except queue.Empty:
                break

        for item in items_to_keep:
            self._queue.put(item)

    def interrupt_for_barge_in(self):
        """
        Called when user speaks wake word or commands.
        Immediately stops currently playing speech and clears non-critical queue.
        """
        self._interrupt()
        # Drain everything except CRITICAL_SAFETY
        self._drain(min_priority=int(SpeechPriority.NAVIGATION))
        print("[TTS] ⚡ Barge-in: interrupted current playback for user voice.")

    # ── Public Speak API ─────────────────────────────────────────────────────
    def speak(
        self,
        text: str,
        priority: SpeechPriority = SpeechPriority.STATUS,
        force: bool = False,
        lang: str = "en"
    ):
        """
        Queue text for speech with specified priority.

        Args:
            text: What to say.
            priority: SpeechPriority enum (CRITICAL_SAFETY, NAVIGATION, USER_COMMAND, LLM_RESPONSE, STATUS)
            force: If True, immediately interrupts currently playing speech and drains lower/equal priority.
            lang: "en" or "hi"
        """
        if not text or not text.strip():
            return

        clean = clean_speech_text(text)
        if not clean:
            return

        # Print immediately to terminal
        prio_name = priority.name if hasattr(priority, "name") else str(priority)
        print(f"[SPEECH OUT ({prio_name})] 🔊  {clean}")

        # Broadcast to caregiver dashboard
        try:
            from telemetry import broadcast_event
            broadcast_event("speech", {"text": clean, "lang": lang, "priority": prio_name})
        except Exception:
            pass

        prio_int = int(priority)

        # Preemption check:
        # If force=True OR this priority is strictly higher than what's currently playing, preempt!
        should_preempt = force
        if self._speaking and self._current_priority is not None:
            if prio_int < self._current_priority:
                should_preempt = True

        if should_preempt:
            self._interrupt()
            if force or priority == SpeechPriority.CRITICAL_SAFETY:
                # Clear pending queue items of equal or lower priority
                self._drain(min_priority=prio_int)

        # Enqueue with incremented counter for FIFO stability
        self._counter += 1
        try:
            self._queue.put((prio_int, self._counter, clean, lang), timeout=0.2)
        except queue.Full:
            print(f"[TTS] Warning: queue full, dropping speech: {clean[:30]}...")

    def _recover_device(self):
        """Attempt recovery if speech synthesis fails (Requirement 38)."""
        print("[TTS] ⚠️  TTS failure detected. Performing recovery...")
        self._interrupt()
        time.sleep(0.1)
        if not self.is_macos:
            self._init_pyttsx()
        print("[TTS] ✅ TTS recovery complete.")

    def stop(self):
        """Stop TTS worker entirely."""
        self._running = False
        self._drain(min_priority=1)
        self._interrupt()
