# AI Voice Mode - Complete Guide

## Overview

AI Voice Mode is an integrated feature in SURDAS that allows you to pause vision processing and have a quick voice conversation with the Ollama AI assistant. Perfect for asking questions without the distraction of obstacle announcements.

## Features

✓ **Single-Key Activation** - Press 'A' to instantly activate  
✓ **Vision Pause** - All vision and safety workers pause during AI mode  
✓ **Single Question Mode** - System answers ONE question then auto-exits  
✓ **Auto-Resume** - Vision and safety automatically resume after exit  
✓ **Echo Cancellation** - Triple-layer protection prevents feedback loops  
✓ **Clean Integration** - No interference with normal SURDAS operation

## How It Works

### Activation Flow
1. **Press 'A' key** → AI Voice Mode activates
2. **Vision workers pause** → No obstacle announcements
3. **Safety workers pause** → No interruptions
4. **Microphone active** → System listens for your question
5. **Voice transcribed** → Using Whisper STT
6. **Ollama responds** → Answer spoken via TTS
7. **Auto-exit** → Returns to normal mode after ONE question
8. **Workers resume** → Vision and safety monitoring restart

### Architecture

```
User presses 'A'
    ↓
start_ai_voice_mode()
    ↓
├── Set ai_voice_mode = True
├── Pause vision_worker
├── Pause safety_worker
├── Start AI thread
    ↓
AI Voice Thread
├── Initialize audio stream
├── Listen continuously
├── Transcribe with Whisper
├── Send to Ollama
├── Speak response via TTS
├── Set question_answered = True
    ↓
stop_ai_voice_mode()
├── Set ai_voice_mode = False
├── Resume vision_worker
├── Resume safety_worker
```

## Usage

### Basic Usage

```bash
# Start SURDAS
python3 surdas_brain.py

# Press 'A' key when ready
# Speak your question
# Listen to AI response
# System auto-exits and resumes vision
```

### Example Questions

- "What's the weather today?"
- "Tell me a joke"
- "Explain how SURDAS works"
- "What's the capital of France?"
- "Calculate 25 times 37"

## Technical Details

### Worker Pause Mechanism

```python
# VisionWorker
class VisionWorker:
    def pause(self):
        """Pause vision processing without stopping the thread."""
        self._paused = True
    
    def resume(self):
        """Resume vision processing."""
        self._paused = False
    
    def _loop(self):
        while self._running:
            if self._paused:
                time.sleep(0.1)  # Wait while paused
                continue
            # ... normal processing
```

### Single-Question Enforcement

```python
def start_ai_voice_mode(self):
    """Start AI Voice Mode with single-question behavior."""
    if self.ai_voice_mode:
        return  # Already active
    
    self.ai_voice_mode = True
    self.vision_worker.pause()
    self.safety_worker.pause()
    
    def ai_thread():
        question_answered = False
        
        while self.ai_voice_mode and not question_answered:
            # Process one question
            # ...
            if user_text_received and response_spoken:
                question_answered = True
                self.stop_ai_voice_mode()  # Auto-exit
    
    threading.Thread(target=ai_thread, daemon=True).start()
```

### Echo Cancellation

Three layers prevent feedback:

1. **TTS Active Flag** - No listening during speech output
2. **Post-TTS Delay** - 500ms buffer after TTS completes
3. **Text Similarity** - Rejects transcriptions >60% similar to last output

```python
# Layer 1: TTS flag
if tts_manager.is_speaking():
    continue  # Skip audio processing

# Layer 2: Post-TTS delay
if time.time() - last_tts_time < 0.5:
    continue

# Layer 3: Similarity check
similarity = text_similarity(transcription, last_spoken_text)
if similarity > 0.6:
    print("[ECHO] Ignoring similar text")
    continue
```

## Configuration

### Audio Settings

Located in `simple_voice_assistant.py`:

```python
CHUNK = 1024
FORMAT = pyaudio.paInt16
CHANNELS = 1
RATE = 16000
SILENCE_THRESHOLD = 500
SILENCE_DURATION = 2.0  # seconds
```

### Ollama Settings

```python
OLLAMA_MODEL = "llama3.2"
OLLAMA_URL = "http://localhost:11434/api/generate"
```

### Echo Prevention Tuning

```python
TTS_TAIL_DELAY = 0.5  # seconds after TTS
SIMILARITY_THRESHOLD = 0.6  # 60% similarity = echo
```

## Troubleshooting

### AI Mode Won't Activate

**Symptom**: Pressing 'A' does nothing

**Solutions**:
- Check keyboard focus is on terminal window
- Verify pynput is installed: `pip3 install pynput`
- Check logs for keyboard listener errors

### Voice Not Recognized

**Symptom**: Speaking but no transcription

**Solutions**:
- Check microphone permissions in System Preferences
- Verify audio input device: `python3 -c "import pyaudio; p=pyaudio.PyAudio(); print([p.get_device_info_by_index(i)['name'] for i in range(p.get_device_count())])"`
- Increase SILENCE_THRESHOLD if room is noisy
- Decrease SILENCE_DURATION if responses are slow

### Echo Loop Detected

**Symptom**: "Echo detected" messages repeatedly

**Solutions**:
- Lower speaker volume
- Use headphones instead of speakers
- Increase SIMILARITY_THRESHOLD to 0.7
- Increase TTS_TAIL_DELAY to 1.0 second

### Vision Doesn't Resume

**Symptom**: After AI mode, no obstacle warnings

**Solutions**:
- Check worker threads: They should auto-resume
- Restart SURDAS: `python3 surdas_brain.py`
- Verify pause/resume in logs: Look for "[VISION] resumed"

### Ollama Not Responding

**Symptom**: Question transcribed but no answer

**Solutions**:
- Check Ollama is running: `ollama list`
- Start Ollama: `ollama serve`
- Verify model exists: `ollama pull llama3.2`
- Check network: `curl http://localhost:11434/api/generate -d '{"model":"llama3.2","prompt":"test"}'`

## Advanced Customization

### Multiple Questions Mode

To allow multiple questions before manual exit:

```python
# In start_ai_voice_mode(), remove:
# question_answered = True
# self.stop_ai_voice_mode()

# Add manual exit trigger:
# Press 'X' to exit AI mode
```

### Different AI Model

```python
# In simple_voice_assistant.py
OLLAMA_MODEL = "mistral"  # or "codellama", "neural-chat", etc.
```

### Custom Wake Phrase

```python
# Add wake phrase detection before Ollama
if "hey surdas" in user_text.lower():
    # Process command
```

### Volume Control

```python
# In TTS section
tts_manager.set_volume(0.7)  # 70% volume
```

## File Locations

- **Main Integration**: `surdas_brain.py` (start_ai_voice_mode, stop_ai_voice_mode)
- **AI Logic**: `simple_voice_assistant.py` (voice processing, Ollama, TTS)
- **Worker Pause**: `workers.py` (VisionWorker.pause/resume, SafetyWorker.pause/resume)
- **Tests**: `test_ai_mode.py` (validation suite)
- **Documentation**: This file

## Performance Notes

- **CPU Usage**: ~15-25% during AI mode (mostly Whisper STT)
- **Memory**: ~200MB additional for audio buffers
- **Latency**: 
  - Transcription: 0.5-2 seconds
  - Ollama response: 1-5 seconds (depends on model)
  - TTS: 0.5-1 second
  - **Total**: 2-8 seconds end-to-end

## Safety Considerations

⚠️ **Important**: While in AI Voice Mode, vision and safety monitoring are **PAUSED**. This means:

- No obstacle detection
- No fall hazard warnings
- No critical safety announcements

**Best Practices**:
- Use AI mode only when stationary
- Find a safe spot before activating
- Keep questions brief (auto-exits after one)
- Don't use while walking or navigating

## Future Enhancements

Possible improvements for future versions:

- [ ] Multi-turn conversations with manual exit
- [ ] Voice-activated exit phrase ("stop listening")
- [ ] Conversation history during session
- [ ] Different AI models for different question types
- [ ] Partial vision mode (obstacles only, no navigation)
- [ ] Adjustable volume during AI mode
- [ ] Visual indicator in GUI when AI mode active

## Testing

Run the test suite to verify everything works:

```bash
python3 test_ai_mode.py
```

Expected output:
```
=== Testing Worker Pause/Resume ===
✓ VisionWorker has pause/resume methods
✓ SafetyWorker has pause/resume methods
...
✓ ALL TESTS PASSED
```

## Support

If you encounter issues:

1. Check the troubleshooting section above
2. Review logs in terminal output
3. Test components individually:
   - Microphone: `python3 -c "import pyaudio; pyaudio.PyAudio().get_default_input_device_info()"`
   - Whisper: `python3 -c "import whisper; whisper.load_model('base')"`
   - Ollama: `curl http://localhost:11434/api/tags`
   - TTS: `python3 -c "import pyttsx3; pyttsx3.init().say('test'); pyttsx3.init().runAndWait()"`

4. Check dependencies:
   ```bash
   pip3 install pyaudio numpy whisper pyttsx3 requests pynput
   ```

## Version History

- **v1.0** (Current) - Initial release with single-question mode
  - 'A' key activation
  - Worker pause/resume
  - Triple-layer echo cancellation
  - Auto-exit after one question

---

**Ready to use AI Voice Mode!** Press 'A' and start asking questions. 🎙️
