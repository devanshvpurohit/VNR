"""
stt.py — Low-latency Speech-to-Text for SURDAS

Offline-first design:
  • Attempts faster-whisper with local_files_only=True first.
  • On failure, tries openai-whisper from cache only.
  • If neither is cached, logs ONE clear message and sets model=None.
    transcribe() returns ("", "en") silently from that point on.

Language detection:
  • language=None lets Whisper auto-detect (en or hi).
  • transcribe() returns (text: str, lang: str) so callers can route
    Hindi vs English responses.
"""
import os
import logging
import numpy as np

logger = logging.getLogger(__name__)

_OFFLINE_MODE = os.environ.get("OFFLINE_MODE", "0") == "1"


class SpeechToText:
    def __init__(self, model_size: str = "tiny"):
        self.model_size  = model_size
        self.engine_type = None
        self.model       = None
        self._warned_no_model = False   # log unavailability only once
        self._init_model()

    def _init_model(self):
        # ── 1. faster-whisper (CTranslate2 — fastest) ────────────────────────
        from faster_whisper import WhisperModel
        for size in [self.model_size, "tiny", "tiny.en"]:
            try:
                print(f"[STT] Loading faster-whisper ({size}) [local_files_only] ...")
                self.model = WhisperModel(
                    size,
                    device="cpu",
                    compute_type="int8",
                    num_workers=1,
                    local_files_only=True,   # NEVER hit the network at runtime
                )
                self.engine_type = "faster-whisper"
                self.model_size = size
                print(f"[STT] ✅ faster-whisper ({size}) ready (offline).")
                return
            except Exception as e:
                pass

        print("[STT] faster-whisper local cache miss. Trying openai-whisper ...")

        # ── 2. openai-whisper fallback — local cache only ────────────────────
        try:
            import whisper
            import os as _os
            for size in [self.model_size, "tiny", "tiny.en"]:
                cache_file = _os.path.expanduser(f"~/.cache/whisper/{size}.pt")
                if _os.path.exists(cache_file):
                    print(f"[STT] Loading openai-whisper ({size}) from local cache ...")
                    self.model = whisper.load_model(size)
                    self.engine_type = "whisper"
                    self.model_size = size
                    print(f"[STT] ✅ openai-whisper ({size}) ready (offline).")
                    return
        except Exception as e:
            print(f"[STT] openai-whisper local cache miss ({e}).")

        # ── No model available ───────────────────────────────────────────────
        print(
            "[STT] ⚠️  No cached Whisper model found — run "
            "setup_offline_models.py while online first."
        )
        self.model       = None
        self.engine_type = None

    # ── Public API ─────────────────────────────────────────────────────────────

    def transcribe(self, audio_data: np.ndarray, sample_rate: int = 16000):
        """
        Transcribe audio.

        Returns:
            (text: str, lang: str)  — lang is ISO 639-1 code, e.g. "en" or "hi".
            Returns ("", "en") when no model is loaded or audio is empty.
        """
        if self.model is None:
            if not self._warned_no_model:
                print(
                    "[STT] transcribe() called but no model is loaded. "
                    "Run setup_offline_models.py while online."
                )
                self._warned_no_model = True
            return "", "en"

        if len(audio_data) == 0:
            return "", "en"

        # Ensure 1D array
        if audio_data.ndim > 1:
            audio_data = audio_data.flatten()
        
        # Normalise to float32 [-1, 1]
        if audio_data.dtype == np.int16:
            audio = audio_data.astype(np.float32) / 32768.0
        else:
            audio = audio_data.astype(np.float32)
        
        # Double-check it's 1D
        if audio.ndim > 1:
            audio = audio.flatten()

        try:
            if self.engine_type == "faster-whisper":
                segments, info = self.model.transcribe(
                    audio,
                    language=None,          # auto-detect (en or hi)
                    beam_size=1,            # greedy — fastest
                    temperature=0.0,
                    vad_filter=True,        # skip silence
                    vad_parameters=dict(
                        min_silence_duration_ms=300,
                        threshold=0.4,
                    ),
                    condition_on_previous_text=False,
                    word_timestamps=False,
                )
                text = " ".join(s.text for s in segments).strip()
                detected_lang = getattr(info, "language", "en") or "en"
                return text, detected_lang

            elif self.engine_type == "whisper":
                result = self.model.transcribe(audio, fp16=False)
                text = result.get("text", "").strip()
                detected_lang = result.get("language", "en") or "en"
                return text, detected_lang

        except Exception as e:
            print(f"[STT] Transcription error: {e}")

        return "", "en"
