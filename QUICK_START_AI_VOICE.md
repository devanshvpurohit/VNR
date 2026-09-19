# 🎤 SURDAS AI Voice Mode - Quick Start

## ✅ Ready to Use!

The AI Voice Mode is now integrated into SURDAS.

## 🚀 Start SURDAS

```bash
cd /Users/devanshvpurohit/VNR/suradas
python3 surdas_brain.py
```

Wait for the camera window to open and initialization to complete.

## 🎮 Activate AI Voice

**Press the `A` key** on your keyboard while the SURDAS window is focused.

You'll hear: *"AI voice mode activated. Just speak, no wake word needed."*

## 💬 Start Talking!

Just speak naturally - no "Hey Surdas" required:

```
You: "What is machine learning?"
[System transcribes and sends to Ollama]
AI: [Responds with explanation]

You: "Give me an example"
AI: [Provides example]
```

## 🔇 Echo Protection

The system automatically:
- ✅ Ignores its own voice while speaking
- ✅ Waits 500ms after speech ends
- ✅ Filters similar text (echo detection)

You'll see: `[AI_VOICE] 🔇 Echo suppression active` (shown once)

## 🛑 Stop AI Voice

**Press `A` key again** to deactivate AI Voice Mode.

You'll hear: *"AI voice mode deactivated."*

## ⌨️ All Keyboard Controls

While SURDAS window is focused:

| Key | Function |
|-----|----------|
| **A** | Toggle AI Voice Mode |
| **N** | Navigation Mode |
| **T** | Read Text (OCR) |
| **L** | Toggle Flashlight |
| **Q** | Quit SURDAS |

## 📊 What You'll See

```
[AI_VOICE] 🎤 Listening... (Press 'A' again to exit)
[AI_VOICE] 🔇 Echo suppression active
[AI_VOICE] 🔴 Listening... Done.
[AI_VOICE] 💬 You: what do you see?
[AI_VOICE] 🤖 Ollama: I can see a chair in front of you...
[AI_VOICE] ✓

[AI_VOICE] 🔴 Listening... Done.
[AI_VOICE] 💬 You: tell me more
[AI_VOICE] 🤖 Ollama: The chair is positioned...
[AI_VOICE] ✓
```

## 🔧 Troubleshooting

### "AI voice mode not activating"
- Make sure SURDAS window is focused (click on it)
- Press `A` key clearly
- Check terminal for error messages

### "No response from Ollama"
```bash
# Check if Ollama is running
ollama serve

# Or start as service
brew services start ollama
```

### "Not hearing my voice"
- Check System Preferences → Security → Microphone
- Enable for Terminal/Python
- Speak louder
- Check microphone is not muted

### "System hearing itself"
- Echo suppression should handle this automatically
- If persists, use headphones
- Or increase the distance between mic and speakers

## 🎯 Tips

**For Best Results:**
- Speak clearly at normal volume
- Pause ~1 second after finishing your sentence
- Wait for "Done" before speaking again
- Use in a quiet environment

**Vision Features Continue:**
- YOLO object detection still running
- Depth mapping active
- Safety announcements working
- All vision features available

**AI Knows What You See:**
- Ollama gets vision context
- Can answer "what do you see?"
- Can describe detected objects
- Can help with navigation

## 🎉 Example Conversation

```
[Start SURDAS, press 'A']

You: "What do you see?"
AI: "I can see a chair approximately 2 meters ahead on your left..."

You: "Is it safe to walk forward?"
AI: "Based on the current view, the path ahead looks clear..."

You: "What is machine learning?"
AI: "Machine learning is a subset of artificial intelligence..."

[Press 'A' to exit AI mode]
```

## ✅ Ready!

**Start now:**
```bash
python3 surdas_brain.py
# Press 'A' key
# Start talking!
```

That's it! Enjoy chatting with Ollama through SURDAS! 🚀
