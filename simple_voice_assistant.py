#!/usr/bin/env python3
"""
simple_voice_assistant.py — Simplified always-listening voice assistant

NO wake word required - always listening
Simple loop: Listen → Transcribe → Ollama → Speak

This bypasses all the complex wake-word detection to isolate
whether the basic voice pipeline works.

Usage:
    python3 simple_voice_assistant.py
"""

import sys
import os
import time
import numpy as np
import queue
import threading

# Suppress warnings
import warnings
warnings.filterwarnings("ignore")
os.environ["PYTHONWARNINGS"] = "ignore"

print("="*70)
print("  SURDAS SIMPLE VOICE ASSISTANT")
print("  (Always listening - NO wake word)")
print("="*70)

# Initialize components
print("\nInitializing...")

try:
    import sounddevice as sd
    from voice.stt import SpeechToText
    from voice.llm import LocalLLM
    from voice.tts import VoiceEngine
    from voice.vad import VoiceActivityDetector
    
    print("✓ Imports loaded")
    
    # Initialize
    stt = SpeechToText()
    llm = LocalLLM()
    voice = VoiceEngine()
    vad = VoiceActivityDetector(sample_rate=16000)
    
    print("✓ Components initialized")
    
    if not llm.is_available():
        print("\n✗ Ollama not available!")
        print("  Start Ollama: ollama serve")
        sys.exit(1)
    
    print(f"✓ Ollama ready - Model: {llm.model_name}")
    
except Exception as e:
    print(f"\n✗ Initialization failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Audio settings
SAMPLE_RATE = 16000
CHUNK_MS = 30
CHUNK_SIZE = int(SAMPLE_RATE * CHUNK_MS / 1000)
SILENCE_CHUNKS = 20  # 600ms of silence = end of utterance

# Audio queue
audio_queue = queue.Queue()

def audio_callback(indata, frames, time_info, status):
    """Called by sounddevice for each audio chunk."""
    if status:
        print(f"Audio status: {status}")
    # Flatten to 1D array immediately
    audio_queue.put(indata.flatten().copy())

print("\n" + "="*70)
print("  READY - Speak anytime (NO wake word needed)")
print("  System will respond to everything you say")
print("  Press Ctrl+C to stop")
print("="*70 + "\n")

# Start audio stream
try:
    stream = sd.InputStream(
        samplerate=SAMPLE_RATE,
        channels=1,
        dtype='float32',
        blocksize=CHUNK_SIZE,
        callback=audio_callback
    )
    
    stream.start()
    print("🎤 Microphone active - listening...\n")
    
    recording = False
    speech_buffer = []
    silence_count = 0
    echo_suppression_active = False  # Track when we're ignoring audio due to TTS
    echo_message_shown = False  # Only show echo message once
    last_spoken_text = ""  # Track what AI just said to detect echo
    
    while True:
        try:
            chunk = audio_queue.get(timeout=0.1)
        except queue.Empty:
            continue
        
        # Check if AI is speaking - don't record then (ECHO CANCELLATION)
        if voice.is_speaking:
            if recording:
                # Was recording but TTS started - abort this recording
                print(" [TTS started, aborting recording]")
                recording = False
                speech_buffer = []
                silence_count = 0
            # Discard all audio while TTS is playing
            if not echo_suppression_active:
                echo_suppression_active = True
                if not echo_message_shown:
                    print("🔇 [Echo suppression active - not listening while AI speaks]")
                    echo_message_shown = True
            continue
        
        # Also ignore audio for 0.5s AFTER TTS finishes (echo tail)
        time_since_tts = time.time() - voice.last_speech_time
        if time_since_tts < 0.5:
            if recording:
                recording = False
                speech_buffer = []
                silence_count = 0
            # Still in echo suppression period
            continue
        
        # Echo suppression ended - resume listening
        if echo_suppression_active:
            echo_suppression_active = False
            if not echo_message_shown:
                print("🎤 [Listening resumed]\n")
                echo_message_shown = True
        
        # Voice activity detection
        is_speech = vad.is_speech(chunk)
        
        if is_speech:
            if not recording:
                print("🔴 Listening...", end="", flush=True)
                recording = True
                speech_buffer = []
                silence_count = 0
            speech_buffer.append(chunk)
            silence_count = 0
            
        elif recording:
            speech_buffer.append(chunk)
            silence_count += 1
            
            # End of utterance
            if silence_count >= SILENCE_CHUNKS:
                print(" Done.")
                recording = False
                
                # Concatenate and ensure 1D array
                audio = np.concatenate(speech_buffer)
                if audio.ndim > 1:
                    audio = audio.flatten()
                
                speech_buffer = []
                silence_count = 0
                
                # Check length
                if len(audio) < SAMPLE_RATE * 0.3:
                    print("  (Too short, ignored)\n")
                    continue
                
                # Check audio level
                audio_level = np.abs(audio).max()
                print(f"  Audio: {len(audio)} samples, level: {audio_level:.4f}")
                
                if audio_level < 0.001:
                    print("  (Audio too quiet, ignored)\n")
                    continue
                
                # Transcribe
                print("⏳ Transcribing...", end="", flush=True)
                t0 = time.time()
                try:
                    text, lang = stt.transcribe(audio, sample_rate=SAMPLE_RATE)
                    dt = time.time() - t0
                    print(f" ({int(dt*1000)}ms)")
                except Exception as e:
                    print(f" Error: {e}")
                    print("  (Transcription failed)\n")
                    continue
                
                if not text or not text.strip():
                    print("  (No speech detected)\n")
                    continue
                
                print(f"💬 You said: \"{text}\"")
                
                # Skip if just noise/filler
                if len(text.strip()) < 3:
                    print("  (Too short, ignored)\n")
                    continue
                
                # ECHO DETECTION: Check if this is very similar to what we just said
                # This catches cases where echo suppression timing wasn't perfect
                if last_spoken_text:
                    text_lower = text.lower().strip()
                    last_lower = last_spoken_text.lower().strip()
                    
                    # Simple similarity check - if >60% of words match, likely echo
                    text_words = set(text_lower.split())
                    last_words = set(last_lower.split())
                    if text_words and last_words:
                        overlap = len(text_words & last_words) / len(text_words)
                        if overlap > 0.6:
                            print(f"  (Detected as echo of AI output, ignored)\n")
                            continue
                
                # Send to Ollama
                print(f"🤖 Ollama: ", end="", flush=True)
                response = ""
                try:
                    for chunk in llm.query(text, vision_context={}):
                        response += chunk
                        print(chunk, end="", flush=True)
                    print()
                    
                    # Speak response
                    if response.strip():
                        print("🔊 Speaking...")
                        voice.speak(response, force=True)
                        
                        # Remember what we said for echo detection
                        last_spoken_text = response
                        
                        # Wait for TTS to finish
                        while voice.is_speaking:
                            time.sleep(0.1)
                        
                        print("✓ Done\n")
                    else:
                        print("  (Empty response)\n")
                        
                except Exception as e:
                    print(f"\n✗ Error: {e}\n")
                
except KeyboardInterrupt:
    print("\n\nStopping...")
    stream.stop()
    stream.close()
    print("Goodbye!")
    
except Exception as e:
    print(f"\n✗ Error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
