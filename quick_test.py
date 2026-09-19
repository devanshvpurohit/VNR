#!/usr/bin/env python3
import numpy as np
from voice.stt import SpeechToText

print("Testing STT with different array shapes...")

stt = SpeechToText()

# Test 1: 1D array (should work)
print("\n1. Testing 1D array (16000 samples)...")
audio_1d = np.random.randn(16000).astype(np.float32) * 0.01
text, lang = stt.transcribe(audio_1d, 16000)
print(f"   Result: '{text}' (lang={lang})")

# Test 2: 2D array (should auto-flatten)
print("\n2. Testing 2D array (16000, 1)...")
audio_2d = np.random.randn(16000, 1).astype(np.float32) * 0.01
text, lang = stt.transcribe(audio_2d, 16000)
print(f"   Result: '{text}' (lang={lang})")

# Test 3: Actual recording simulation
print("\n3. Testing sounddevice-style array...")
import sounddevice as sd
recording = sd.rec(int(1.0 * 16000), samplerate=16000, channels=1, dtype='float32')
sd.wait()
print(f"   Shape before: {recording.shape}")
audio_flat = recording.flatten()
print(f"   Shape after flatten: {audio_flat.shape}")
text, lang = stt.transcribe(audio_flat, 16000)
print(f"   Result: '{text}' (lang={lang})")

print("\n✓ All tests passed!")
