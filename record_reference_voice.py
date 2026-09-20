#!/usr/bin/env python3
"""
Simple script to record a reference voice for XTTS-v2 voice cloning.

Records a 15-second WAV file that can be used as the reference voice.
"""

import sounddevice as sd
import numpy as np
import wave
from pathlib import Path

# Configuration
SAMPLE_RATE = 22050  # XTTS works well with this rate
DURATION = 15  # seconds
OUTPUT_PATH = Path(__file__).parent / "voice_models" / "surdas_reference.wav"

print("=" * 60)
print("XTTS-v2 Reference Voice Recorder")
print("=" * 60)
print()
print("This script will record a 15-second reference voice sample.")
print()
print("📋 Instructions:")
print("  1. Find a quiet environment")
print("  2. Speak clearly and naturally")
print("  3. Read the sample text below (or speak freely)")
print()
print("📝 Sample Text (speak this):")
print("-" * 60)
print("""
Hello, I am SURDAS, your vision and navigation assistant.
I can help you navigate safely, detect obstacles, read text,
recognize currency, and answer questions about your surroundings.
I use computer vision and artificial intelligence to assist you.
""")
print("-" * 60)
print()

input("Press Enter when ready to start recording...")
print()
print(f"🎙️  Recording for {DURATION} seconds...")
print("   Speak now!")
print()

# Record audio
recording = sd.rec(
    int(DURATION * SAMPLE_RATE),
    samplerate=SAMPLE_RATE,
    channels=1,  # Mono
    dtype='int16'
)
sd.wait()  # Wait until recording is finished

print("✅ Recording complete!")
print()

# Save to WAV file
OUTPUT_PATH.parent.mkdir(exist_ok=True)

with wave.open(str(OUTPUT_PATH), 'w') as wf:
    wf.setnchannels(1)  # Mono
    wf.setsampwidth(2)  # 16-bit
    wf.setframerate(SAMPLE_RATE)
    wf.writeframes(recording.tobytes())

print(f"💾 Saved to: {OUTPUT_PATH}")
print()

# Show file info
size_kb = OUTPUT_PATH.stat().st_size / 1024
print("📊 File Information:")
print(f"   Path: {OUTPUT_PATH}")
print(f"   Size: {size_kb:.1f} KB")
print(f"   Duration: {DURATION} seconds")
print(f"   Sample Rate: {SAMPLE_RATE} Hz")
print(f"   Channels: Mono")
print(f"   Format: WAV (16-bit PCM)")
print()

# Play back
print("🔊 Playing back your recording...")
input("   Press Enter to play...")
sd.play(recording, SAMPLE_RATE)
sd.wait()

print()
print("✅ Done! Your reference voice is ready.")
print()
print("🚀 Next Steps:")
print(f"   1. If you're happy with the recording, you're done!")
print(f"   2. If not, run this script again to re-record.")
print(f"   3. Start SURDAS: python3 surdas_brain.py")
print(f"   4. Test with: 'Hey SURDAS, what do you see?'")
print()
print("💡 Tips for best results:")
print("   • Quiet environment (no background noise)")
print("   • Clear, natural speech (don't over-enunciate)")
print("   • Speak at normal conversational volume")
print("   • Avoid long pauses")
print()
