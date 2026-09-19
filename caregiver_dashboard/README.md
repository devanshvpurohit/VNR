# SURDAS Caregiver Dashboard v2.0

A modern, comprehensive web-based dashboard for monitoring and managing the SURDAS assistive vision system. Built with React, TypeScript, and Tailwind CSS.

## ✨ Features

### 🎯 Core Monitoring
- **Real-time Video Feed** - Live camera stream from SURDAS system
- **Vision System Status** - Object detection, depth analysis, and obstacle warnings
- **Fall Detection** - Real-time monitoring with MPU6050 IMU sensor
- **Indoor Navigation** - Path guidance with spatial memory
- **Activity Logs** - Comprehensive event tracking with filtering

### 🧭 Navigation
- **Indoor Navigation Status** - Real-time destination tracking
- **Confidence Levels** - HIGH/MEDIUM/LOW safety indicators
- **Spatial Memory** - Room and landmark tracking
- **Safety Holds** - Automatic pause on obstacles or low confidence

### 📊 Analytics
- **System Uptime** - Real-time monitoring
- **Event History** - Searchable and filterable logs
- **Fall Statistics** - Track incidents over time
- **System Health** - Performance metrics

### 🎨 Modern UI/UX
- **Multi-tab Interface** - Overview, Navigation, Analytics, Settings
- **Glass Morphism Design** - Modern backdrop blur effects
- **Responsive Layout** - Desktop, tablet, and mobile support
- **Real-time Updates** - WebSocket-based live data
- **Emergency Alerts** - Critical event notifications
- **Custom Scrollbars** - Enhanced visual experience

## 🚀 Quick Start

### Prerequisites
- Node.js 18+ and npm
- Running SURDAS backend (`python3 surdas_brain.py`)
- ESP32 fall detector (optional, but recommended)

### Installation

```bash
cd caregiver_dashboard
npm install
```

### Development

```bash
npm run dev
```

The dashboard will be available at `http://localhost:5173`

### Production Build

```bash
npm run build
npm run preview
```

## 🔧 Configuration

### API Endpoints

Edit the constants in `src/App.tsx`:

```typescript
const API = 'http://localhost:8000';           // Backend API
const WS  = 'ws://localhost:8000/ws';          // WebSocket
const CONTROLLER_IP = '192.168.4.2';           // ESP32 Controller
const VIDEO_FEED = 'http://localhost:8888/video_feed';  // Camera feed
```

### Backend Setup

Ensure the SURDAS backend is running with telemetry enabled:

```bash
# Terminal 1: Start SURDAS
cd /path/to/suradas
python3 surdas_brain.py

# The telemetry server should start automatically on port 8000
```

### Fall Detector Setup

The ESP32-based fall detector should be accessible at `192.168.4.2` and expose:
- `GET /imu` - Returns IMU data and fall status

## 📱 Dashboard Tabs

### 1. Overview Tab
- **Quick Stats Cards**
  - System status (Online/Offline)
  - System uptime
  - Objects detected count
  - Spatial memory locations
  
- **Live Video Feed**
  - Real-time camera stream
  - LIVE indicator
  - Hide/show toggle
  
- **Vision System Panel**
  - Current mode (IDLE/NAV/OCR)
  - Flashlight status
  - Obstacle detection
  - Detected objects list
  
- **Fall Detector Panel**
  - Current state (NORMAL/POSSIBLE_FALL/IMPACT_DETECTED/FALL_CONFIRMED)
  - Acceleration metrics
  - Pitch and roll angles
  - Total falls counter
  - MPU sensor status
  
- **Indoor Navigation Panel**
  - Navigation state
  - Current destination
  - Confidence level
  - Safe paths available
  - Distance remaining
  
- **Spatial Memory Panel**
  - Stored rooms and landmarks
  - Room/landmark indicators
  - Scrollable list
  
- **Activity Logs**
  - Real-time event stream
  - Type filtering (All/Speech/Navigation/Falls/Alerts/System)
  - Color-coded by priority
  - Timestamps
  - Clear all option

### 2. Navigation Tab
- Navigation map visualization
- Route history
- Location information
- Turn-by-turn guidance history

### 3. Analytics Tab
- Daily activity charts
- System health metrics
- Event statistics
- Fall incident tracking
- Uptime monitoring

### 4. Settings Tab
- Video feed toggle
- Alert sounds on/off
- Connection settings display
- API endpoint configuration

## 🎯 Event Types & Priority Levels

### Event Types
- `speech` - Voice commands and responses
- `alert` - System warnings
- `system` - System status changes
- `navigation` - Navigation events
- `fall` - Fall detection events
- `emergency` - Critical emergencies

### Priority Levels
- `low` - Informational (green/blue)
- `medium` - Notable events (purple)
- `high` - Warnings (orange)
- `critical` - Emergencies (red)

## 🔔 Alert System

### Critical Alerts
When a fall is confirmed or critical event occurs:
- 🚨 Emergency banner appears
- Audio alert plays (if enabled)
- Red pulsing notification
- Requires acknowledgment

### Alert Sounds
Enable/disable in Settings tab. Plays browser notification sound for:
- Fall confirmed
- Critical priority events
- Emergency situations

## 🎨 UI Components

### Color Coding
- **Emerald/Green** - Normal, safe, online
- **Amber/Yellow** - Warning, medium confidence
- **Orange** - High alert, caution
- **Red** - Critical, emergency, danger
- **Blue** - Information, navigation
- **Purple** - Speech, routine events
- **Violet** - Spatial memory

### Status Indicators
- **Pulsing Dots** - Real-time status (online/offline)
- **Gradient Backgrounds** - Visual separation
- **Glass Morphism** - Modern backdrop blur
- **Smooth Transitions** - Professional feel

## 📊 WebSocket Data Format

### Vision Context
```json
{
  "type": "vision",
  "data": {
    "mode": "NAV",
    "torch_on": false,
    "detected_objects": ["person", "chair", "door"],
    "closest_obstacle": "chair (1.5m)",
    "wall_ahead": false,
    "fps": 25
  }
}
```

### Indoor Navigation
```json
{
  "type": "indoor_navigation",
  "data": {
    "state": "NAVIGATING",
    "destination": "kitchen",
    "confidence": "HIGH",
    "distance_remaining": 3.2,
    "safe_directions": 2,
    "hold_reason": null
  }
}
```

### Speech
```json
{
  "type": "speech",
  "data": {
    "text": "Guide me to the door"
  }
}
```

### Room/Landmark Labeled
```json
{
  "type": "room_labeled",
  "data": {
    "name": "bedroom",
    "room_id": 1,
    "timestamp": "2024-01-15T10:30:00Z"
  }
}
```

### Alerts
```json
{
  "type": "alert",
  "data": {
    "message": "Obstacle detected ahead",
    "priority": "high"
  }
}
```

## 🛠️ Development

### Project Structure
```
caregiver_dashboard/
├── src/
│   ├── App.tsx          # Main application component
│   ├── index.css        # Global styles and animations
│   └── main.tsx         # Application entry point
├── public/
│   ├── favicon.svg      # Dashboard icon
│   └── icons.svg        # Icon sprites
├── package.json         # Dependencies
├── vite.config.ts       # Vite configuration
└── tsconfig.json        # TypeScript configuration
```

### Tech Stack
- **React 19** - UI framework
- **TypeScript 6** - Type safety
- **Tailwind CSS 3** - Utility-first styling
- **Vite 8** - Build tool and dev server
- **Lucide React** - Modern icon library
- **WebSocket** - Real-time communication

### Adding New Features

1. **New Event Type**
   ```typescript
   // In App.tsx, add to LogEntry type
   type: 'speech' | 'alert' | 'system' | 'navigation' | 'fall' | 'your_new_type';
   ```

2. **New Status Card**
   ```tsx
   <div className="bg-gradient-to-br from-color-500/20 to-color-500/20 backdrop-blur-xl border border-color-400/30 rounded-2xl p-6">
     {/* Your content */}
   </div>
   ```

3. **New Tab**
   - Add tab button in `renderTabs()`
   - Create render function (e.g., `renderYourTab()`)
   - Add to main render logic

## 🐛 Troubleshooting

### Dashboard Not Connecting
1. Verify SURDAS backend is running: `http://localhost:8000/health`
2. Check WebSocket connection: `ws://localhost:8000/ws`
3. Look for CORS errors in browser console
4. Ensure telemetry server started successfully

### Video Feed Not Showing
1. Verify Flask app is running on port 8888
2. Check `http://localhost:8888/video_feed` directly
3. Ensure camera is connected and accessible
4. Check browser permissions for media

### Fall Detector Offline
1. Verify ESP32 is powered and connected to WiFi
2. Check IP address is correct (default: `192.168.4.2`)
3. Test endpoint: `http://192.168.4.2/imu`
4. Check ESP32 serial monitor for errors

### No Events Appearing
1. Check WebSocket connection status (should be green)
2. Verify SURDAS is broadcasting events
3. Check browser console for JavaScript errors
4. Test with: `python3 -c "from telemetry import broadcast_event; broadcast_event('test', {'message': 'hello'})"`

## 🔒 Security Considerations

- Dashboard is intended for local network use only
- No authentication implemented (add if exposing to internet)
- WebSocket traffic is unencrypted
- Video feed is unencrypted HTTP
- Consider adding SSL/TLS for production deployments

## 📈 Performance

- Optimized for 60fps rendering
- WebSocket reconnection with exponential backoff
- Efficient log management (500 event limit)
- Fall detector polled at 200ms (5Hz)
- Minimal re-renders with proper state management

## 🤝 Contributing

This dashboard is part of the SURDAS project. Contributions welcome!

## 📄 License

[Add your license here]

## 🙏 Acknowledgments

- Icons from Lucide React
- UI inspiration from modern dashboard designs
- Built for assistive technology and accessibility

---

**SURDAS** - Empowering independence through AI-assisted vision
