# AI Voice Mode - Quick Reference Card

## 🚀 Quick Start

```bash
python3 surdas_brain.py
# Press 'A' → Ask question → Auto-exits
```

## ⌨️ Key Commands

| Key | Action |
|-----|--------|
| `A` | Activate AI Voice Mode |
| (auto) | Exit after 1 question |

## 🔄 What Happens

```
Press 'A'
  ↓
Vision PAUSES ⏸️
  ↓
Ask Question 🎙️
  ↓
AI Answers 🤖
  ↓
Vision RESUMES ▶️
```

## ⚙️ System States

### Normal Mode
- ✅ Vision processing active
- ✅ Safety monitoring active
- ✅ Obstacle announcements
- ❌ AI voice inactive

### AI Voice Mode (Press 'A')
- ❌ Vision processing paused
- ❌ Safety monitoring paused
- ❌ Obstacle announcements paused
- ✅ AI voice active
- ✅ Microphone listening
- ✅ Ollama responding

## 🎯 Features

- ✓ Single-key activation ('A')
- ✓ Auto-pause vision workers
- ✓ One question per session
- ✓ Auto-exit and resume
- ✓ Echo cancellation (3 layers)
- ✓ Clean integration

## ⚠️ Safety Warning

**AI mode pauses obstacle detection!**
- Use only when stationary
- Find safe spot first
- Keep questions brief

## 🔧 Troubleshooting

| Problem | Solution |
|---------|----------|
| 'A' doesn't work | Terminal window must have focus |
| No voice input | Check mic permissions |
| Echo loop | Lower volume or use headphones |
| No Ollama response | Run `ollama serve` |
| Vision not resuming | Restart: `python3 surdas_brain.py` |

## 📊 Performance

- **Transcription**: 0.5-2s
- **AI Response**: 1-5s
- **Total Latency**: 2-8s
- **CPU Usage**: +15-25%

## 🧪 Test Before Use

```bash
python3 test_ai_mode.py
# Should show: ✓ ALL TESTS PASSED
```

## 📦 Dependencies

```bash
pip3 install pyaudio numpy whisper pyttsx3 requests pynput
ollama pull llama3.2
```

## 📁 Key Files

- `surdas_brain.py` - Main integration
- `simple_voice_assistant.py` - AI logic
- `workers.py` - Pause/resume
- `test_ai_mode.py` - Tests

## 🎤 Example Questions

- "What time is it?"
- "Tell me a joke"
- "How does SURDAS work?"
- "What's 25 times 37?"
- "What's the weather?"

## 🔍 Quick Debug

```bash
# Test microphone
python3 -c "import pyaudio; print(pyaudio.PyAudio().get_default_input_device_info())"

# Test Ollama
curl http://localhost:11434/api/tags

# Test full system
python3 test_ai_mode.py
```

---

**💡 TIP**: Keep questions short - system auto-exits after ONE answer!
