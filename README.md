# SURDAS - Real-Time Assistive Vision and Local Voice Assistant with Indoor Navigation

SURDAS is an AI-assisted perception and voice assistant for low-cost visually-impaired use-cases. It combines real-time computer vision (YOLOv8 object detection, MiDaS relative depth estimation, Indian banknote recognition, and EasyOCR text reading) with a fully offline/self-hosted voice assistant system (Silero VAD, Wake Word Detection, Whisper STT, Command Router, Local LLM via Ollama, and TTS).

**NEW: Indoor Navigation & Spatial Memory** — SURDAS now supports blindfold navigation in indoor environments with spatial memory for room/object labeling, deterministic safety-first navigation, and same-utterance wake-word detection ("Surdas, guide me to the door").

**⚠️ IMPORTANT LIMITATIONS:**
- **MiDaS provides RELATIVE depth/proximity estimation, NOT metric distance.** Announcements like "nearby" or "very close" are based on relative depth values, not calibrated measurements in meters.
- **Indoor navigation is approximate without IMU/odometry.** Position tracking relies on perception and memory, not precise measurements.
- **Real-world outdoor navigation requires GPS hardware.** Without GPS, navigation uses manual test coordinates only.
- **Safety features are assistive tools, not collision avoidance systems.** Always exercise caution and manual awareness.

---

## 🖥️ User Interfaces

SURDAS offers two modern interfaces for different use cases:

### 1. Tkinter Desktop GUI (New!)
**Modern native desktop application with real-time monitoring**

```bash
# Quick launch with GUI
./launch_gui.sh

# Or launch directly from surdas_brain.py
python3 surdas_brain.py --gui

# Or from test pipeline
python3 test_ai_pipeline.py --gui

# With custom model and audio settings
python3 surdas_brain.py --gui --model gemma3:1b --mic airpods --mic-gain 2.0
```

**Features**:
- 🎨 Modern gradient-based UI with three-column layout
- 📹 Live camera feed display (20 FPS)
- 🎛️ System controls (Start/Stop, Mode selection, Flashlight)
- 🧭 Indoor navigation monitoring (state, confidence, destination)
- 📊 Real-time statistics (FPS, object count, uptime)
- 🧠 Spatial memory display (rooms & landmarks)
- 📜 Color-coded activity logs with timestamps
- 🖱️ Native desktop experience with tkinter (built-in Python)

**Requirements**: `Pillow>=10.0.0` (for image display; tkinter is built into Python)

### CLI Arguments

Both `surdas_brain.py` and `test_ai_pipeline.py` support the following arguments:

```bash
# Launch with GUI
python3 surdas_brain.py --gui

# Specify LLM model
python3 surdas_brain.py --model gemma3:1b

# Specify microphone device
python3 surdas_brain.py --mic airpods
python3 surdas_brain.py --mic boat
python3 surdas_brain.py --mic 0  # Device index

# Adjust microphone gain
python3 surdas_brain.py --mic-gain 2.0

# Combine arguments
python3 surdas_brain.py --gui --model gemma3:1b --mic airpods --mic-gain 2.0
python3 test_ai_pipeline.py --gui --mic boat --mic-gain 1.5
```

**Terminal Mode (Default)**:
```bash
python3 surdas_brain.py              # OpenCV window
python3 test_ai_pipeline.py          # OpenCV window
```

**GUI Mode (Tkinter)**:
```bash
python3 surdas_brain.py --gui        # Tkinter GUI
python3 test_ai_pipeline.py --gui    # Tkinter GUI
./launch_gui.sh                      # Convenience script
```

### 2. Web-Based Caregiver Dashboard
**React + TypeScript dashboard for remote monitoring**

```bash
# Terminal 1: Start SURDAS backend
python3 surdas_brain.py

# Terminal 2: Start dashboard
cd caregiver_dashboard
npm install
npm run dev
```

**Features**:
- 🌐 Web-based interface accessible from any device
- 📱 Responsive design (desktop, tablet, mobile)
- 🔄 WebSocket real-time updates
- 🗺️ Interactive OpenStreetMap integration
- 📊 Event timeline with filtering
- 💬 Speech command history
- 🎨 Modern Tailwind CSS design
- 🚨 **Fall Detection Integration** (NEW!)
  - Real-time IMU data from ESP32 (`http://192.168.4.2/imu`)
  - Automatic emergency alerts on fall confirmation
  - Live acceleration, pitch, and roll monitoring
  - Fall counter with state tracking (NORMAL/POSSIBLE_FALL/IMPACT_DETECTED/FALL_CONFIRMED)
  - Color-coded visual indicators

**Recommended for**: Caregivers monitoring from another room/device

**Fall Detection Docs**: See [FALL_DETECTION_SUMMARY.md](FALL_DETECTION_SUMMARY.md) for complete guide

---

##  System Architecture
```
SURDAS
|
+--------------+--------------+
|               |               |
v               v               v
Vision System   Voice System    Spatial Memory
|               |               |
ESP32-CAM       Microphone      SQLite DB
|               |               |
OpenCV/YOLO     VAD (Silero)    Rooms/Objects
|               |               |
Depth (MiDaS)   Speech-to-Text  Landmarks
|            (faster-whisper)  |
Object Detection    |               |
|               |               |
+-------------+---------------+---------------+
|
v
Indoor Perception & Navigation
|
+-----------------+------------------+
|                 |                  |
v                 v                  v
Free-Space    Command Router   Safety Controller
Detection     |                  |
|             +-------+----------+-------+
|             |       |       |       |
|             v       v       v       v
|         Nav Mode  OCR  Torch  Room Label
|             |       |       |       |
+-------------+-------+-------+-------+--------+
|
v
Vision Context → Local LLM (Ollama) → TTS → Speaker
```
---

## 📁 Package Structure
```
surdas/
├── voice/
│  ├── __init__.py
│  ├── vad.py           # Voice Activity Detection (Silero VAD + Energy Fallback)
│  ├── wakeword.py        # Wake Word Detection (same-utterance support)
│  ├── stt.py           # Speech to Text (faster-whisper / Whisper)
│  ├── tts.py           # Unified Text-to-Speech (Piper + pyttsx3)
│  ├── llm.py           # Local LLM integration (Ollama with live Vision Context)
│  ├── command_router.py     # Deterministic Command Router with indoor nav support
│  ├── assistant.py        # Non-blocking audio capture & background listener
│  └── i18n_phrases.py      # Bilingual (EN/HI) command phrase dictionary
├── navigation/
│  ├── __init__.py
│  ├── map_manager.py       # Offline OpenStreetMap management
│  ├── router.py          # Pedestrian routing (Dijkstra on OSM graph)
│  ├── navigator.py        # Turn-by-turn outdoor navigation
│  ├── geocoder.py         # Offline place search
│  ├── location.py         # GPS provider abstraction
│  └── voice_guidance.py     # Navigation instruction generation
├── spatial_memory.py       # **NEW** Persistent room/object/landmark memory (SQLite)
├── indoor_perception.py     # **NEW** Free-space detection, occupancy grid, safe directions
├── indoor_navigator.py      # **NEW** Safety-first indoor navigation controller
├── surdas_brain.py        # Main Unified Vision & Voice System
├── currency_detector.py     # Indian Banknote Recognition (Rs. 10 - Rs. 500)
├── config.py           # Centralized configuration (thresholds, GPS, paths)
├── logger.py           # Subsystem logging (VISION, GPS, NAV, VOICE)
├── telemetry.py          # Caregiver dashboard broadcast
├── test_indoor_navigation.py # **NEW** Test suite for blindfold scenarios
├── surdas_esp32_cam/
│  └── surdas_esp32_cam.ino  # ESP32-CAM Firmware
├── requirements.txt
└── README.md
```
---

##  Core Features

### ✅ WORKING FEATURES
- **Object Detection**: YOLOv8n real-time detection with relative proximity estimation
- **Relative Depth Perception**: MiDaS provides proximity categories (very close, nearby, medium distance, far)
- **Wall & Barrier Detection**: Dense depth analysis for continuous surfaces
- **Indoor Navigation**: Waypoint-free reactive navigation with spatial memory
- **Spatial Memory**: Persistent room/object/landmark labeling and recall (SQLite)
- **Safety-First Navigation**: Automatic safety-hold on camera failure, obstacles, or low confidence
- **Same-Utterance Wake**: "Surdas, command" works in single phrase (no "Hey" required)
- **Indian Currency Recognition**: OCR + color-based denomination detection with confidence categories
- **Text Reading (OCR)**: EasyOCR for English and Hindi text
- **Offline Voice Assistant**: Wake word detection, Whisper STT, command routing, Ollama LLM integration
- **Offline Pedestrian Navigation**: Uses pre-downloaded OpenStreetMap data (requires online setup once)
- **Fall Detection Dashboard**: Real-time IMU monitoring from ESP32 with automatic emergency alerts (see [FALL_DETECTION_SUMMARY.md](FALL_DETECTION_SUMMARY.md))

### 🔧 REQUIRES HARDWARE
- **GPS Navigation**: Real-world dynamic outdoor navigation requires a GPS module (USB/Bluetooth serial GPS)
- **ESP32-CAM**: Optional wireless camera (can use local webcam for testing)
- **ESP32 with IMU**: Optional fall detection (MPU6050/MPU9250) at `http://192.168.4.2/imu`

### 🧪 EXPERIMENTAL / OPTIONAL
- **Ollama LLM Integration**: Conversational AI for visual Q&A (requires Ollama server)
- **Caregiver Dashboard**: Real-time telemetry web interface

---

## 🏠 Indoor Navigation & Blindfold Usage

### Overview
SURDAS now supports **indoor navigation for blindfold scenarios** with:
- **Spatial Memory**: Remember rooms, objects, and landmarks
- **Deterministic Navigation**: Safety-first reactive guidance (never LLM-controlled)
- **Free-Space Detection**: Real-time occupancy mapping from YOLO + MiDaS
- **Navigation Confidence**: HIGH/MEDIUM/LOW/INVALID scoring
- **Safety-Hold State**: Automatic pause on camera failure or obstacles
- **Bilingual Commands**: English and Hindi support

### Key Commands

#### Room & Object Labeling
```
"Surdas, this is the bedroom"              # Label current room
"Surdas, label this as kitchen entrance"   # Save landmark
"Surdas, this is a chair"                  # Label detected object
```

#### Spatial Queries
```
"Surdas, where is the chair?"              # Find remembered object
"Surdas, what room is this?"               # Identify current room
"Surdas, describe surroundings"            # List nearby objects
"Surdas, list rooms"                       # List all remembered rooms
```

#### Indoor Navigation
```
"Surdas, guide me to the door"             # Navigate to object
"Surdas, take me to kitchen entrance"      # Navigate to landmark
"Surdas, pause navigation"                 # Pause guidance
"Surdas, resume navigation"                # Resume guidance
"Surdas, stop navigation"                  # Cancel navigation
```

### Navigation States

1. **IDLE**: Not navigating, spatial queries only
2. **NAVIGATING**: Active guidance toward destination
3. **SAFETY_HOLD**: Paused due to:
   - Camera failure (no depth data)
   - Stale perception (>2s old)
   - Low confidence (obstacles blocking view)
   - Obstacle too close (<0.8m)
   - User requested pause
4. **APPROACHING**: Close to destination (<1.5m)
5. **ARRIVED**: Destination reached

### Safety Features

**Automatic Safety-Hold Triggers:**
- Camera failure or invalid depth data → "camera not working, please check"
- Obstacles very close (>0.9 relative depth) → "Stop! Obstacle very close"
- Low navigation confidence → "Pausing: limited visibility"
- Stale perception (>2 seconds) → "Lost camera view, reconnecting"

**Movement Commands Only When:**
- Navigation confidence >= MEDIUM
- Perception data < 2 seconds old
- No critical obstacles detected
- Camera functioning normally

### Blindfold Testing Protocol

1. **Setup Phase**
   ```bash
   python surdas_brain.py  # Start system
   # Put on blindfold, ensure camera is working
   ```

2. **Exploration Phase**
   ```
   "Surdas, this is the living room"       # Label room
   # Walk around, let camera detect objects
   "Surdas, describe surroundings"         # Hear what's detected
   "Surdas, remember this as sofa"         # Label object
   ```

3. **Navigation Phase**
   ```
   "Surdas, guide me to the sofa"          # Start navigation
   # Follow voice guidance:
   # "Move forward. Path is clear for 3 metres."
   # "Turn left about 30 degrees, then move forward."
   # "Almost there. Sofa is very close."
   # "Arrived! Sofa should be right in front of you."
   ```

4. **Safety Testing**
   ```
   # Cover camera → automatic safety-hold
   # Place obstacle in path → system detects and warns
   # Low light conditions → system reports low confidence
   ```

### Testing the System

Run comprehensive test suite:
```bash
# All tests
python test_indoor_navigation.py --test all

# Individual tests
python test_indoor_navigation.py --test spatial_memory
python test_indoor_navigation.py --test perception
python test_indoor_navigation.py --test navigation
python test_indoor_navigation.py --test wakeword
python test_indoor_navigation.py --test blindfold_simulation
```

Expected output:
```
✅ SPATIAL MEMORY: ALL TESTS PASSED
✅ INDOOR PERCEPTION: ALL TESTS PASSED
✅ INDOOR NAVIGATION CONTROLLER: ALL TESTS PASSED
✅ WAKE-WORD DETECTION: ALL TESTS PASSED
✅ BLINDFOLD SCENARIO SIMULATION: ALL TESTS PASSED

🎉 ALL TESTS PASSED - INDOOR NAVIGATION READY FOR BLINDFOLD USE
```

### Spatial Memory Database

Location: `spatial_memory.db` (SQLite)

**Schema:**
- `rooms`: Room definitions with boundaries
- `objects`: Detected objects with positions, confidence, timestamps
- `landmarks`: User-labeled navigation points
- `spatial_relations`: Object relationships

**Maintenance:**
```python
from spatial_memory import SpatialMemory

memory = SpatialMemory()

# View statistics
stats = memory.get_stats()
print(f"Rooms: {stats['rooms']}, Objects: {stats['objects']}")

# Clear stale objects (not seen in >1 hour)
memory.clear_stale_objects(max_age_seconds=3600)

# Export to JSON
json_data = memory.export_to_json()
```

### Hindi Commands

All indoor navigation commands work in Hindi:
```
"सुरदास, यह बेडरूम है"                    # This is the bedroom
"सुरदास, कुर्सी कहाँ है?"                 # Where is the chair?
"सुरदास, मुझे दरवाजे तक ले चलो"          # Guide me to the door
"सुरदास, आसपास बताओ"                     # Describe surroundings
"सुरदास, नेविगेशन रोको"                   # Stop navigation
```

### Configuration

Edit `config.py` for thresholds:
```python
# Indoor Navigation
PERCEPTION_MAX_AGE_S = 2.0          # Max perception staleness
ARRIVAL_THRESHOLD_M = 0.5           # Distance to consider "arrived"
OBSTACLE_CRITICAL_M = 0.8           # Trigger safety-hold distance
MIN_CONFIDENCE_TO_MOVE = "MEDIUM"   # Minimum confidence for movement

# Depth Classification
DEPTH_VERY_CLOSE_THRESHOLD = 0.8    # Relative depth (higher = closer)
DEPTH_CLOSE_THRESHOLD = 0.6
DEPTH_MEDIUM_THRESHOLD = 0.4
```

---

The assistant wakes up on either "Hey Surdas" or "Surdas":

### Voice System Features

**🎙️ XTTS-v2 Voice Cloning (NEW!)**
- Natural voice cloning using your reference voice
- Any language supported by XTTS-v2
- In-memory audio generation (no temporary files)
- Preserves all priority and barge-in features
- Graceful fallback to system TTS
- See [XTTS_QUICKSTART.md](XTTS_QUICKSTART.md) for setup

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

**Keyboard Fallbacks**: 
- `[N]` Navigation Mode
- `[T]` Read Text
- `[L]` Toggle Flashlight
- `[A]` AI Voice Mode (NEW!)
- `[Q]` Quit

---

## 🎙️ AI Voice Mode

**NEW: Interactive AI Assistant with Vision Pause**

Press the `[A]` key to activate AI Voice Mode for quick conversational questions without vision interruptions.

### Features
- ✓ **Single-Key Activation**: Press 'A' to instantly activate
- ✓ **Vision Pause**: All vision and safety workers pause during AI mode
- ✓ **Single Question Mode**: System answers ONE question then auto-exits
- ✓ **Auto-Resume**: Vision and safety automatically resume after exit
- ✓ **Echo Cancellation**: Triple-layer protection prevents feedback loops
- ✓ **Ollama Integration**: Uses local Llama 3.2 model

### Quick Start
```bash
# Start SURDAS
python3 surdas_brain.py

# Press 'A' key → Ask question → System auto-exits
```

### Example Questions
- "What's the weather today?"
- "Tell me a joke"
- "How does SURDAS work?"
- "Calculate 25 times 37"

### Safety Note
⚠️ AI mode pauses obstacle detection. Use only when stationary in a safe location.

### Documentation
- **Complete Guide**: [AI_VOICE_MODE_GUIDE.md](AI_VOICE_MODE_GUIDE.md)
- **Quick Reference**: [AI_MODE_QUICK_REF.md](AI_MODE_QUICK_REF.md)
- **Testing**: Run `python3 test_ai_mode.py`

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
