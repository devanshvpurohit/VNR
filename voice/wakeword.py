import os
import numpy as np

from voice.i18n_phrases import WAKE_WORDS, match as _i18n_match

_OFFLINE_MODE = os.environ.get("OFFLINE_MODE", "0") == "1"

# Flatten all wake phrases across both languages for text matching.
_ALL_WAKE_PHRASES = WAKE_WORDS["en"] + WAKE_WORDS["hi"]


class WakeWordDetector:
    """
    Wake word detector supporting openWakeWord with fallback to bilingual
    text-based keyword matching.

    Offline-first: openWakeWord models are only loaded from the local cache
    that setup_offline_models.py populated.  If init fails for any reason
    (import error, missing local files, etc.) we fall back to text matching
    immediately — no network attempt at runtime.

    Text matching covers both English and Hindi wake words via i18n_phrases.
    """

    def __init__(self, target_phrases=None, model_path=None):
        # target_phrases is kept for API compatibility but is no longer used
        # to override the bilingual set — i18n_phrases is the single source of truth.
        self.target_phrases = _ALL_WAKE_PHRASES
        self.oww_model = None
        self._init_openwakeword(model_path)

    def _init_openwakeword(self, model_path):
        if _OFFLINE_MODE:
            # Strict offline mode: skip any attempt that could touch the network.
            print(
                "[WAKEWORD] OFFLINE_MODE: skipping openWakeWord init. "
                "Using text-based bilingual wake-word matching."
            )
            return

        try:
            import openwakeword
            from openwakeword.model import Model

            if model_path and os.path.exists(model_path):
                # User supplied an explicit local model path.
                self.oww_model = Model(wakeword_models=[model_path])
                print(f"[WAKEWORD] Loaded custom openWakeWord model from: {model_path}")
                return

            # Load from the cache that setup_offline_models.py populated.
            # openwakeword stores models under ~/.local/share/openwakeword (Linux)
            # or ~/Library/Application Support/openwakeword (macOS).
            # Model() with no path uses that cache automatically.
            self.oww_model = Model()
            print("[WAKEWORD] ✅ openWakeWord loaded from local cache.")

        except Exception as e:
            # ANY failure (import error, missing cache, ONNX runtime issue, etc.)
            # → silent graceful degradation to text matching, no network retry.
            self.oww_model = None
            print(
                f"[WAKEWORD] openWakeWord not available ({e}). "
                "Using bilingual text-based wake-word matching (Hey Surdas / सुरदास)."
            )

    def process_audio(self, audio_chunk: np.ndarray) -> bool:
        """
        Process raw 16kHz audio chunk through openWakeWord if available.
        Returns True if a wake word is detected.
        """
        if self.oww_model is not None:
            try:
                if audio_chunk.dtype == np.float32:
                    audio_int16 = (audio_chunk * 32767).astype(np.int16)
                else:
                    audio_int16 = audio_chunk

                prediction = self.oww_model.predict(audio_int16)
                for model_name, score in prediction.items():
                    if score > 0.5:
                        print(f"[WAKEWORD] Wake word '{model_name}' triggered (score: {score:.2f})")
                        return True
            except Exception:
                pass
        return False

    def check_transcription(self, text: str) -> tuple[bool, str]:
        """
        Checks if transcribed text (English or Hindi) contains any wake word.
        Returns (is_wake_word_present, remaining_command).

        Supports two modes:
        1. Same-utterance: "Surdas, navigate to door" → command extracted
        2. Traditional wake: "Hey Surdas" → activates, waits for next utterance

        Works on both Latin and Devanagari scripts via i18n_phrases.match().
        """
        if not text or not text.strip():
            return False, ""

        text_stripped = text.strip()
        text_lower = text_stripped.lower()

        # Priority 1: Check for same-utterance wake words at the START of phrase
        # This enables: "Surdas, what do you see?" in a single utterance
        same_utterance_wakes = [
            "surdas", "सुरदास", "सूरदास", "soordas", "sura das"
        ]
        
        for wake in same_utterance_wakes:
            # Check if text starts with wake word (case-insensitive for English)
            if wake in ["surdas", "soordas", "sura das"]:
                if text_lower.startswith(wake):
                    # Extract command after wake word
                    remaining = text_stripped[len(wake):].strip(" ,.?!")
                    if remaining:
                        # Found command in same utterance
                        print(f"[WAKEWORD] Same-utterance wake: '{wake}' → command: '{remaining}'")
                        return True, remaining
            else:
                # Hindi wake word - case-sensitive
                if text_stripped.startswith(wake):
                    remaining = text_stripped[len(wake):].strip(" ,.?!।")
                    if remaining:
                        print(f"[WAKEWORD] Same-utterance wake: '{wake}' → command: '{remaining}'")
                        return True, remaining

        # Priority 2: Check for traditional wake phrases (with "Hey", etc.)
        if _i18n_match(WAKE_WORDS, text):
            # Strip the matched wake phrase from the rest of the text.
            remaining = text_stripped

            # Try to find and remove the matched English phrase
            for phrase in WAKE_WORDS["en"]:
                if phrase in text_lower:
                    idx = text_lower.find(phrase)
                    remaining = text_stripped[idx + len(phrase):].strip(" ,.?!")
                    
                    # If there's a command after "Hey Surdas", treat as same-utterance
                    if remaining:
                        print(f"[WAKEWORD] Traditional wake with command: '{phrase}' → '{remaining}'")
                        return True, remaining
                    else:
                        # Just wake word, no command (traditional activation)
                        print(f"[WAKEWORD] Traditional wake-only: '{phrase}'")
                        return True, ""

            # Try to find and remove the matched Hindi phrase
            for phrase in WAKE_WORDS["hi"]:
                if phrase in text:
                    idx = text.find(phrase)
                    remaining = text_stripped[idx + len(phrase):].strip(" ,.?!।")
                    
                    if remaining:
                        print(f"[WAKEWORD] Traditional wake with command: '{phrase}' → '{remaining}'")
                        return True, remaining
                    else:
                        print(f"[WAKEWORD] Traditional wake-only: '{phrase}'")
                        return True, ""

            # Match found but couldn't strip — return as wake-only
            return True, ""

        return False, text_stripped
