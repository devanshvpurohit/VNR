# SURDAS - Real Time Assistive Vision and Local Voice Assistant

SURDAS is an AI assisted perception and voice assistant for low-cost visually-impaired use-cases, which utilizes simultaneous real-time computer vision (YOLOv8, MiDaS Depth, Indian Banknote Recognition, EasyOCR) and a 100% offline/self-hosted voice-assistant (Silero VAD, Wake Word, Whisper STT, Command Router, Local LLM via Ollama, and TTS.)
---

##  System Architecture
```

SURDAS
|
+--------------+--------------+
|               |
v               v
Vision System         Voice System
|               |
ESP32-CAM             Microphone
|               |
OpenCV / YOLO           VAD (Silero)
|               |
Depth (MiDaS) / OCR       Speech-to-Text
|            (faster-whisper)
Object Detection          |
|               |
+-------------+---------------+
|
v
Command Router
|
+------------+-------------+
|      |       |
v      v       v
Navigation    OCR      Torch
|      |       |
+------------+--------------+
|
v
Vision Context
|
v
Local LLM
(Ollama)
|
v
Unified TTS
(pyttsx3 / Piper)
|
v
Speaker
```
---

## 📁 Package Structure
```

surdas_ai/
├── voice/
│  ├── __init__.py
│  ├── vad.py        # Voice Activity Detection (Silero VAD + Energy Fallback)
│  ├── wakeword.py     # Wake Word Detection ("Hey Surdas" / openWakeWord)
│  ├── stt.py        # Speech to Text (faster-whisper / Whisper)
│  ├── tts.py        # Unified Text-to-Speech (Piper + pyttsx3)
│  ├── llm.py        # Local LLM integration (Ollama with live Vision Context)
│  ├── command_router.py  # Deterministic Command Router vs LLM Query Router
│  └── assistant.py     # Non-blocking audio capture & background listener
├── surdas_brain.py     # Main Unified Vision & Voice System
├── currency_detector.py   # Indian Banknote Recognition (Rs. 10 - Rs. 500)
├── surdas_esp32_cam/
│  └── surdas_esp32_cam.ino # ESP32-CAM Firmware (AP Stream, High-Res Capture, Flashlight)
├── requirements.txt
└── README.md
```
---

## Spoken Voice Commands

The assistant wakes up on either "Hey Surdas" or "Surdas":

### 1. Deterministic Commands (Zero Latency, No LLM required):
Navigation: "Hey Surdas, start navigation" or "Navigation mode"
Read Text: "Hey Surdas, read text" or "Read this sign" (automatically turns on torch, snaps image, reads aloud, and turns off torch)
Flashlight On: "Hey Surdas, turn on light" or "Torch on"
Flashlight Off: "Hey Surdas, turn off light" or "Torch off"
Fast Scene Check: "Hey Surdas, what do you see?" or "What is in front of me?"
Stop / Silence: "Hey Surdas, stop" or "Silence"
Status: "Hey Surdas, status"

### 2. Conversational / Visual Q&A (Powered by Local Ollama):
"Hey Surdas, is there a chair I can sit on?"
"Hey Surdas, where is the person standing?"
(The local LLM is automatically provided with the live vision context: detected objects, proximity, and torch status to answer accurately.)
---

## OFFLINE NAVIGATION

SURDAS now includes a fully offline pedestrian navigation system built using OpenStreetMap data. No internet connection or live API routing is required during use.

**Important**: Map data must be downloaded while online before going offline.

1. Install dependencies:
```bash
pip install osmnx networkx shapely
```

2. Connect to the internet once and download a city map:
```bash
python setup_offline_maps.py --place "Hyderabad, Telangana, India"
```

3. Verify offline readiness:
```bash
python -m navigation.offline_test
```

4. Disable networking. Start SURDAS. Say:
> "Hey SURDAS, navigate to Charminar."
> "सुरदास, चारमीनार तक ले चलो।"

- Routing uses the locally stored graph (no Google Maps).
- Different cities/regions require their own offline map package.
- The map data can become outdated and should periodically be refreshed while online.
- No live internet routing is used during offline operation.
- **Safety Note**: GPS does not provide exact positioning. SURDAS may say "Crossing ahead", but ALWAYS check traffic manually before crossing.
---

## How to Run

1. (Optional) Start Ollama (for conversational AI):
```
ollama run llama3.2
```
2. Run SURDAS:
```
cd /Users/devanshvpurohit/surdas_ai
python3 surdas_brain.py
```

Keyboard Fallbacks: `[N]` Navigation Mode, `[T]` Read Text, `[L]` Toggle Flashlight, `[Q]` Quit.
