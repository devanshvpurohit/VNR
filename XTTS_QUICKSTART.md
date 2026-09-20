# XTTS-v2 Quick Start Guide

## 3-Step Setup

### Step 1: Install Dependencies

```bash
cd /Users/devanshvpurohit/VNR/suradas
pip install TTS sounddevice
```

### Step 2: Add Reference Voice

Create a 10-20 second WAV file of clean speech and place it here:

```bash
/Users/devanshvpurohit/VNR/suradas/voice_models/surdas_reference.wav
```

**Recording tips:**
- Quiet environment
- Clear, natural speech
- WAV format (mono or stereo)
- Example: "Hello, I am SURDAS, your vision assistant..."

### Step 3: Test

```bash
# Run test suite
python3 test_xtts_integration.py

# Start SURDAS
python3 surdas_brain.py

# Test with wake word
"Hey SURDAS, what do you see?"
```

## Troubleshooting

**No audio?**
```bash
pip install sounddevice
python3 -c "import sounddevice as sd; print(sd.query_devices())"
```

**TTS not installed?**
```bash
pip install TTS torch torchaudio
```

**Reference voice not found?**
```bash
ls -lh voice_models/surdas_reference.wav
# If missing, record and place WAV file there
```

**Want to use system TTS instead?**
```bash
export XTTS_ENABLED=false
python3 surdas_brain.py
```

## That's it!

SURDAS will now speak with your cloned voice automatically.

See `XTTS_INTEGRATION.md` for complete documentation.
