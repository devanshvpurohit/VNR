#!/usr/bin/env python3
"""
test_basic_voice.py — Minimal voice test to verify microphone → STT → Ollama → TTS

Tests the absolute basics:
1. Can we capture audio from microphone?
2. Can we transcribe it?
3. Can we send to Ollama?
4. Can we speak the response?

Usage:
    python3 test_basic_voice.py
"""

import sys
import os
import time
import numpy as np

# Suppress warnings
import warnings
warnings.filterwarnings("ignore")
os.environ["PYTHONWARNINGS"] = "ignore"

print("="*70)
print("  SURDAS BASIC VOICE TEST")
print("="*70)

# Test 1: Microphone
print("\n[1/5] Testing microphone...")
try:
    import sounddevice as sd
    
    # List devices
    devices = sd.query_devices()
    print(f"✓ Found {len(devices)} audio devices")
    
    # Find input devices
    input_devices = [i for i, d in enumerate(devices) if d['max_input_channels'] > 0]
    print(f"✓ Found {len(input_devices)} input devices")
    
    if input_devices:
        default_input = sd.query_devices(kind='input')
        print(f"✓ Default input: {default_input['name']}")
    else:
        print("✗ No input devices found!")
        sys.exit(1)
        
except Exception as e:
    print(f"✗ Microphone test failed: {e}")
    sys.exit(1)

# Test 2: Speech-to-Text
print("\n[2/5] Testing Speech-to-Text...")
try:
    from voice.stt import SpeechToText
    
    stt = SpeechToText()
    print(f"✓ STT initialized")
    
    # Test with dummy audio
    dummy_audio = np.random.randn(16000).astype(np.float32) * 0.01
    text, lang = stt.transcribe(dummy_audio, sample_rate=16000)
    print(f"✓ STT working (test transcription: '{text}')")
    
except Exception as e:
    print(f"✗ STT test failed: {e}")
    sys.exit(1)

# Test 3: Ollama LLM
print("\n[3/5] Testing Ollama...")
try:
    from voice.llm import LocalLLM
    
    llm = LocalLLM()
    
    if llm.is_available():
        print(f"✓ Ollama available - Model: {llm.model_name}")
        
        # Quick test query
        print("  Testing quick query...")
        response = ""
        for chunk in llm.query("Say hello in one word", vision_context={}):
            response += chunk
        print(f"✓ Ollama response: {response.strip()}")
    else:
        print("✗ Ollama not available")
        print("  Start with: ollama serve")
        sys.exit(1)
        
except Exception as e:
    print(f"✗ Ollama test failed: {e}")
    sys.exit(1)

# Test 4: Text-to-Speech
print("\n[4/5] Testing Text-to-Speech...")
try:
    from voice.tts import VoiceEngine
    
    voice = VoiceEngine()
    print(f"✓ TTS initialized")
    
    # Quick test
    voice.speak("Testing text to speech", force=True)
    time.sleep(2)
    print(f"✓ TTS working")
    
except Exception as e:
    print(f"✗ TTS test failed: {e}")
    sys.exit(1)

# Test 5: Live voice recording
print("\n[5/5] Testing live voice recording...")
print("\n" + "="*70)
print("  LIVE VOICE TEST")
print("="*70)
print("\n🎤 Recording for 3 seconds...")
print("   Say something now!\n")

try:
    # Record audio
    duration = 3
    sample_rate = 16000
    
    recording = sd.rec(
        int(duration * sample_rate),
        samplerate=sample_rate,
        channels=1,
        dtype='float32'
    )
    sd.wait()
    
    audio = recording.flatten()
    
    print(f"✓ Recorded {len(audio)} samples")
    print(f"  Audio level: {np.abs(audio).max():.4f}")
    
    if np.abs(audio).max() < 0.001:
        print("\n⚠️  WARNING: Audio level very low!")
        print("   - Check microphone is not muted")
        print("   - Check correct input device selected")
        print("   - Speak louder")
    
    # Transcribe
    print("\n⏳ Transcribing...")
    text, lang = stt.transcribe(audio, sample_rate=sample_rate)
    
    if text and text.strip():
        print(f"\n✓ Heard: \"{text}\"")
        print(f"  Language: {lang}")
        
        # Send to Ollama
        print(f"\n⏳ Sending to Ollama...")
        response = ""
        for chunk in llm.query(text, vision_context={}):
            response += chunk
            print(chunk, end="", flush=True)
        print()
        
        # Speak response
        print(f"\n🔊 Speaking response...")
        voice.speak(response, force=True)
        time.sleep(len(response.split()) * 0.5)  # Rough estimate
        
        print("\n" + "="*70)
        print("  ✅ ALL TESTS PASSED!")
        print("  Voice system is working correctly.")
        print("="*70)
        
    else:
        print(f"\n⚠️  No speech detected in recording")
        print("  - Try speaking louder")
        print("  - Check microphone permissions")
        print("  - Ensure microphone is not muted")
        
except KeyboardInterrupt:
    print("\n\nTest interrupted by user")
    sys.exit(1)
except Exception as e:
    print(f"\n✗ Live test failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print("\nIf this test passed, your voice system is working!")
print("The issue may be with wake-word detection or voice assistant loop.")
print("\nNext steps:")
print("  1. Check wake-word model: models/surdas.onnx")
print("  2. Run: python3 surdas_brain.py")
print("  3. Say 'Hey Surdas' clearly and wait")
