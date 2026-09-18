# SURDAS - Real-Time Assistive Vision and Local Voice Assistant

SURDAS is an AI-assisted perception and voice assistant for low-cost visually-impaired use-cases. It combines real-time computer vision (YOLOv8 object detection, MiDaS relative depth estimation, Indian banknote recognition, and EasyOCR text reading) with a fully offline/self-hosted voice assistant system (Silero VAD, Wake Word Detection, Whisper STT, Command Router, Local LLM via Ollama, and TTS).

**⚠️ IMPORTANT LIMITATIONS:**
- **MiDaS provides RELATIVE depth/proximity estimation, NOT metric distance.** Announcements like "nearby" or "very close" are based on relative depth values, not calibrated measurements in meters.
- **Real-world navigation requires GPS hardware.** Without GPS, navigation uses manual test coordinates only.
- **Safety features are assistive tools, not collision avoidance systems.** Always exercise caution and manual awareness.

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

##  Core Features

### ✅ WORKING FEATURES
- **Object Detection**: YOLOv8n real-time detection with relative proximity estimation
- **Relative Depth Perception**: MiDaS provides proximity categories (very close, nearby, medium distance, far)
- **Wall & Barrier Detection**: Dense depth analysis for continuous surfaces
- **Indian Currency Recognition**: OCR + color-based denomination detection with confidence categories
- **Text Reading (OCR)**: EasyOCR for English and Hindi text
- **Offline Voice Assistant**: Wake word detection, Whisper STT, command routing, Ollama LLM integration
- **Offline Pedestrian Navigation**: Uses pre-downloaded OpenStreetMap data (requires online setup once)

### 🔧 REQUIRES HARDWARE
- **GPS Navigation**: Real-world dynamic navigation requires a GPS module (USB/Bluetooth serial GPS)
- **ESP32-CAM**: Optional wireless camera (can use local webcam for testing)

### 🧪 EXPERIMENTAL / OPTIONAL
- **Ollama LLM Integration**: Conversational AI for visual Q&A (requires Ollama server)
- **Caregiver Dashboard**: Real-time telemetry web interface

---

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

SURDAS includes a fully offline pedestrian navigation system using OpenStreetMap data.

**⚠️ CRITICAL REQUIREMENTS:**
- **Map data must be downloaded once while online** (see setup below)
- **Real navigation requires GPS hardware** (USB/Bluetooth GPS module with NMEA output)
- **Without GPS**: System uses manual test coordinates for development only

### Setup (One-Time, Requires Internet)

1. Install dependencies:
```bash
pip install osmnx networkx shapely
```

2. Download map data for your area:
```bash
python setup_offline_maps.py --place "Hyderabad, Telangana, India"
```

3. Verify offline readiness:
```bash
python -m navigation.offline_test
```

### GPS Configuration (For Real Navigation)

Edit environment variables or `config.py`:
```bash
export SURDAS_GPS_ENABLED=true
export SURDAS_GPS_PORT=/dev/ttyUSB0  # Your GPS serial port
export SURDAS_GPS_BAUD=9600
```

### Usage

After setup, start SURDAS and say:
> "Hey SURDAS, navigate to Charminar."
> "सुरदास, चारमीनार तक ले चलो।"
> "सुरदास, चारमीनार तक ले चलो।"

- Routing uses the locally stored graph (no Google Maps).
- Different cities/regions require their own offline map package.
- The map data can become outdated and should periodically be refreshed while online.
- No live internet routing is used during offline operation.
- **Safety Note**: GPS does not provide exact positioning. SURDAS announcements are assistive guidance only. ALWAYS check traffic manually before crossing streets or making navigation decisions.

---

## How to Run

### Prerequisites
```bash
# Install dependencies
pip install -r requirements.txt

# (Optional) Download offline models once while online
python setup_offline_models.py

# (Optional) Set up offline maps for your area
python setup_offline_maps.py --place "Your City, Country"
```

### Running SURDAS

1. (Optional) Start Ollama for conversational AI:
```bash
ollama serve
ollama run llama3.2
```

2. Run SURDAS:
```bash
cd /path/to/your/suradas
python3 surdas_brain.py
```

**Keyboard Fallbacks**: `[N]` Navigation Mode, `[T]` Read Text, `[L]` Toggle Flashlight, `[Q]` Quit

---

## Testing

Run the test suite:
```bash
# Run all tests
python -m pytest tests/ -v

# Run with coverage
python -m pytest tests/ --cov=. --cov-report=html

# Run specific test file
python -m pytest tests/test_location.py -v
```

---

## Configuration

See `config.py` for all configurable parameters. Key settings can be overridden via environment variables (prefix with `SURDAS_`).

Example `.env` file:
```bash
SURDAS_GPS_ENABLED=true
SURDAS_GPS_PORT=/dev/ttyUSB0
SURDAS_ESP32_IP=192.168.4.1
SURDAS_LOG_LEVEL=INFO
SURDAS_DEPTH_VERY_CLOSE=1200
SURDAS_DEPTH_CLOSE=650
```

---

## Technical Details

### Depth Perception (MiDaS)
MiDaS provides **relative depth estimation**, not metric distance. The system classifies depth into proximity categories:
- **VERY_CLOSE**: Immediate proximity (potential collision risk)
- **CLOSE**: Nearby objects within reach
- **MEDIUM**: Objects at moderate distance
- **FAR**: Distant objects

These categories are based on empirical thresholds and may need tuning for different cameras/lighting conditions.

### Currency Detection
The currency detector combines OCR and color analysis with heuristic confidence categories:
- **HIGH**: Both OCR and color agree on denomination
- **MEDIUM**: OCR detected, or weak agreement
- **LOW**: Color analysis only

Confidence is heuristic, not statistically calibrated probability.

### Safety & Concurrency
Vision processing (YOLO + MiDaS) runs continuously, even during voice commands. Safety-critical warnings can interrupt voice processing. Only routine announcements are suppressed during user interaction.

---

## License

[Add your license here]

## Contributors

[Add contributors here]

## Acknowledgments

- YOLOv8: Ultralytics
- MiDaS: Intel ISL
- EasyOCR: JaidedAI
- OpenStreetMap: OSM Contributors
