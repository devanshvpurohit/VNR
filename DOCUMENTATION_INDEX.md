# SURDAS Documentation Index

## 📚 Complete Documentation Guide

This index helps you find the right documentation for your needs.

---

## 🚀 Getting Started

### New Users - Start Here
1. **[README.md](README.md)** - Main project overview
2. **[FALL_DETECTION_QUICKSTART.md](FALL_DETECTION_QUICKSTART.md)** - 3-step quick start for fall detection
3. **[AI_MODE_QUICK_REF.md](AI_MODE_QUICK_REF.md)** - Quick reference for AI Voice Mode

---

## 🔴 Fall Detection

### Quick Start
- **[FALL_DETECTION_QUICKSTART.md](FALL_DETECTION_QUICKSTART.md)**
  - 3-step setup guide
  - Basic testing
  - Troubleshooting

### Overview
- **[FALL_DETECTION_SUMMARY.md](FALL_DETECTION_SUMMARY.md)**
  - Feature summary
  - What's working
  - Quick test commands

### Technical Documentation
- **[FALL_DETECTION_INTEGRATION.md](FALL_DETECTION_INTEGRATION.md)**
  - Complete technical guide
  - API documentation
  - Configuration options
  - Advanced features
  - Security considerations

### Dashboard Specific
- **[caregiver_dashboard/FALL_DETECTION.md](caregiver_dashboard/FALL_DETECTION.md)**
  - Dashboard implementation
  - UI components
  - Code structure
  - Performance metrics

### Testing
- **[test_imu_endpoint.py](test_imu_endpoint.py)**
  - Automated test suite
  - Connectivity tests
  - Data validation
  - Continuous monitoring

---

## 🎙️ AI Voice Mode

### Quick Reference
- **[AI_MODE_QUICK_REF.md](AI_MODE_QUICK_REF.md)**
  - Quick commands
  - Key bindings
  - Troubleshooting

### Complete Guide
- **[AI_VOICE_MODE_GUIDE.md](AI_VOICE_MODE_GUIDE.md)**
  - Full documentation
  - Architecture
  - Configuration
  - Advanced features

### Quick Start
- **[QUICK_START_AI_VOICE.md](QUICK_START_AI_VOICE.md)**
  - Setup instructions
  - First use
  - Testing

### Testing
- **[test_ai_mode.py](test_ai_mode.py)**
  - Automated tests
  - Worker validation
  - Integration checks

### Validation
- **[validate_ai_mode.sh](validate_ai_mode.sh)**
  - Pre-flight checks
  - Dependency validation
  - System readiness

---

## 🧭 Indoor Navigation

### Main Documentation
- **README.md** (Indoor Navigation section)
  - Spatial memory
  - Navigation commands
  - Safety features
  - Blindfold testing

### Testing
- **[test_indoor_navigation.py](test_indoor_navigation.py)**
  - Navigation tests
  - Spatial memory validation
  - Blindfold simulation

---

## 🖥️ User Interfaces

### Tkinter GUI
- **README.md** (User Interfaces section)
  - Launch commands
  - Features
  - CLI arguments

### Web Dashboard
- **README.md** (Caregiver Dashboard section)
  - Setup instructions
  - Features
  - WebSocket integration

### Launch Scripts
- **[launch_gui.sh](launch_gui.sh)**
  - GUI launcher
- **[START_VOICE_CHAT.sh](START_VOICE_CHAT.sh)**
  - Voice chat launcher

---

## 🎤 Voice System

### Voice Assistant
- **[voice/assistant.py](voice/assistant.py)**
  - Main assistant implementation
  - Wake-word detection
  - Audio capture

### Simple Voice Chat
- **[simple_voice_assistant.py](simple_voice_assistant.py)**
  - Standalone voice chat
  - No wake-word required
  - Echo cancellation

### Voice Commands
- **[voice/command_router.py](voice/command_router.py)**
  - Command routing
  - Indoor navigation integration
  - Bilingual support

---

## 🔧 Configuration

### Main Config
- **[config.py](config.py)**
  - All system settings
  - Thresholds
  - Hardware configuration

### Environment Variables
- **README.md** (Configuration section)
  - Environment setup
  - GPS configuration
  - Model paths

---

## 🧪 Testing

### Test Files
- **[test_imu_endpoint.py](test_imu_endpoint.py)** - Fall detection endpoint
- **[test_ai_mode.py](test_ai_mode.py)** - AI Voice Mode
- **[test_indoor_navigation.py](test_indoor_navigation.py)** - Navigation system
- **[test_basic_voice.py](test_basic_voice.py)** - Voice components
- **[test_voice_wake_word.py](test_voice_wake_word.py)** - Wake-word detection
- **[quick_test.py](quick_test.py)** - Audio array handling

### Validation Scripts
- **[validate_ai_mode.sh](validate_ai_mode.sh)** - AI mode validation
- **[navigation/offline_test.py](navigation/offline_test.py)** - Offline maps

---

## 📦 Setup & Installation

### System Setup
- **[setup_offline_models.py](setup_offline_models.py)**
  - Download AI models
  - Offline setup

- **[setup_offline_maps.py](setup_offline_maps.py)**
  - Download map data
  - Navigation setup

- **[download_models.py](download_models.py)**
  - Model download script

### Requirements
- **[requirements.txt](requirements.txt)**
  - Python dependencies

- **[caregiver_dashboard/package.json](caregiver_dashboard/package.json)**
  - Node.js dependencies

---

## 🏗️ Architecture & Development

### Core System
- **[surdas_brain.py](surdas_brain.py)**
  - Main system orchestrator
  - Worker management
  - AI mode integration

### Workers
- **[workers.py](workers.py)**
  - VisionWorker
  - SafetyWorker
  - LLMWorker

### Perception
- **[indoor_perception.py](indoor_perception.py)**
  - Free-space detection
  - Occupancy grid

### Navigation
- **[indoor_navigator.py](indoor_navigator.py)**
  - Indoor navigation controller
- **[navigation/navigator.py](navigation/navigator.py)**
  - Outdoor navigation
- **[navigation/router.py](navigation/router.py)**
  - Route planning

### Spatial Memory
- **[spatial_memory.py](spatial_memory.py)**
  - Room/object storage
  - SQLite database

---

## 🎯 Use Case Guides

### For Visually Impaired Users
1. Start with **README.md** (Overview)
2. Read **Indoor Navigation section**
3. Check **Voice Commands** in README
4. Use **AI Voice Mode** (`A` key)

### For Caregivers
1. Start with **README.md** (Caregiver Dashboard)
2. Read **FALL_DETECTION_QUICKSTART.md**
3. Review **caregiver_dashboard/FALL_DETECTION.md**
4. Test with **test_imu_endpoint.py**

### For Developers
1. Start with **README.md** (System Architecture)
2. Review **workers.py** and **surdas_brain.py**
3. Check **test_*.py** files for examples
4. Read **FALL_DETECTION_INTEGRATION.md** for API details

### For System Administrators
1. Read **README.md** (Configuration section)
2. Check **config.py** for settings
3. Review **setup_offline_*.py** scripts
4. Use **validate_ai_mode.sh** for validation

---

## 🔍 Quick Find

### By Feature

| Feature | Documentation |
|---------|--------------|
| Fall Detection | FALL_DETECTION_QUICKSTART.md |
| AI Voice Mode | AI_VOICE_MODE_GUIDE.md |
| Indoor Navigation | README.md (Indoor Navigation section) |
| Outdoor Navigation | README.md (Offline Navigation section) |
| Spatial Memory | README.md (Spatial Memory section) |
| Voice Commands | README.md (Voice System section) |
| Dashboard | caregiver_dashboard/FALL_DETECTION.md |
| Configuration | config.py |
| Testing | test_*.py files |

### By User Type

| User Type | Start Here |
|-----------|-----------|
| First-time User | README.md |
| Visually Impaired | README.md → Indoor Navigation |
| Caregiver | FALL_DETECTION_QUICKSTART.md |
| Developer | README.md → Architecture section |
| Tester | test_*.py files |
| Administrator | config.py → setup_*.py |

---

## 📝 Document Categories

### 📘 User Documentation
- README.md
- FALL_DETECTION_QUICKSTART.md
- AI_MODE_QUICK_REF.md
- QUICK_START_AI_VOICE.md

### 📙 Technical Documentation
- FALL_DETECTION_INTEGRATION.md
- AI_VOICE_MODE_GUIDE.md
- caregiver_dashboard/FALL_DETECTION.md

### 📗 Developer Documentation
- Code files (.py, .tsx)
- Test files (test_*.py)
- Setup scripts (setup_*.py)

### 📕 Reference Documentation
- FALL_DETECTION_SUMMARY.md
- config.py
- requirements.txt

---

## 🆘 Troubleshooting Index

### Fall Detection Issues
→ **FALL_DETECTION_INTEGRATION.md** (Troubleshooting section)

### AI Voice Issues
→ **AI_VOICE_MODE_GUIDE.md** (Troubleshooting section)

### Navigation Issues
→ **README.md** (Indoor Navigation section)

### Voice System Issues
→ **AI_VOICE_MODE_GUIDE.md** (Troubleshooting section)

### Dashboard Issues
→ **caregiver_dashboard/FALL_DETECTION.md** (Troubleshooting section)

---

## 📊 Diagrams & Visual Aids

### System Architecture
- **README.md** - Overall system architecture
- **FALL_DETECTION_INTEGRATION.md** - Fall detection architecture

### State Machines
- **FALL_DETECTION_INTEGRATION.md** - Fall state transitions
- **indoor_navigator.py** - Navigation states

### Data Flow
- **AI_VOICE_MODE_GUIDE.md** - Voice processing flow
- **FALL_DETECTION_INTEGRATION.md** - IMU data flow

---

## 🔗 External Resources

### Dependencies
- YOLOv8: https://docs.ultralytics.com/
- MiDaS: https://github.com/isl-org/MiDaS
- Whisper: https://github.com/openai/whisper
- Ollama: https://ollama.ai/

### Hardware
- ESP32-CAM: https://randomnerdtutorials.com/esp32-cam-video-streaming-web-server-camera-home-assistant/
- MPU6050: https://invensense.tdk.com/products/motion-tracking/6-axis/mpu-6050/

---

## 📅 Version History

### v1.0 (Current)
- ✅ Complete fall detection integration
- ✅ AI Voice Mode with single-question behavior
- ✅ Indoor navigation with spatial memory
- ✅ Caregiver dashboard with WebSocket
- ✅ Comprehensive documentation

---

## 🤝 Contributing

Before contributing:
1. Read **README.md** (Overview)
2. Review relevant **technical documentation**
3. Run **test_*.py** files
4. Check **config.py** for settings

---

## 📞 Support

For help:
1. Check this index for relevant docs
2. Review troubleshooting sections
3. Run diagnostic scripts (validate_*.sh, test_*.py)
4. Check configuration files (config.py)

---

**Last Updated**: September 19, 2026  
**Total Documents**: 25+ files  
**Status**: ✅ Complete and Up-to-date
