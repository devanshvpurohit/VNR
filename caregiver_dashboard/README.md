# SURDAS Caregiver Dashboard

A modern, real-time monitoring dashboard for caregivers to track SURDAS assistive device status, location, indoor navigation, and activity.

## Features

### 🎨 Modern UI/UX
- **Gradient-based Design**: Beautiful, accessible interface with Tailwind CSS
- **Responsive Layout**: Optimized for desktop and mobile devices
- **Real-time Status**: Live connection indicator with color-coded states
- **Smooth Animations**: Subtle transitions for enhanced user experience

### 👁️ Vision Monitoring
- **Object Detection**: Real-time display of detected objects with confidence scores
- **Obstacle Tracking**: Closest obstacle identification and wall detection
- **Camera Status**: Flashlight state and operating mode visibility

### 🧭 Indoor Navigation
- **Navigation State**: Current state (IDLE, NAVIGATING, SAFETY_HOLD, APPROACHING, ARRIVED)
- **Destination Tracking**: Active destination and distance remaining
- **Confidence Scoring**: HIGH/MEDIUM/LOW/INVALID navigation confidence
- **Safe Direction Count**: Number of available safe paths
- **Safety Alerts**: Hold reasons and real-time warnings

### 🧠 Spatial Memory
- **Room Tracking**: Labeled rooms with persistent memory
- **Landmark Recognition**: Saved landmarks for navigation reference
- **Memory Display**: Visual list of known spaces and objects

### 📍 Location Services
- **Live GPS**: Real-time location with coordinates
- **Interactive Map**: OpenStreetMap integration for visual reference
- **City/Region Display**: Human-readable location information

### 📊 Activity Monitoring
- **Event Logging**: Timestamped activity feed with type classification
- **Speech Recognition**: Voice commands and assistant responses
- **System Events**: Navigation events, spatial memory updates
- **Alert Management**: Safety warnings and error notifications
- **Color-Coded Events**: Visual differentiation (speech, alerts, navigation, system)

## Setup

### Installation
```bash
cd caregiver_dashboard
npm install
```

### Development
```bash
npm run dev
```
Dashboard will be available at `http://localhost:5173`

### Production Build
```bash
npm run build
npm run preview
```

## Backend Connection

The dashboard connects to the SURDAS backend at:
- **HTTP API**: `http://localhost:8000`
- **WebSocket**: `ws://localhost:8000/ws`

### Start SURDAS System
```bash
cd ..
python3 surdas_brain.py
```

The dashboard will automatically connect and start receiving real-time updates.

## Tech Stack

- **React 19** - Modern UI framework with hooks
- **TypeScript** - Type-safe development
- **Vite** - Fast build tool and dev server
- **Tailwind CSS** - Utility-first styling
- **WebSocket** - Real-time bidirectional communication
- **PostCSS & Autoprefixer** - CSS optimization

## Architecture

### Component Structure
```
App.tsx
├── Header (status badge, branding)
├── Column 1: Vision & Navigation
│   ├── Vision State Card
│   └── Indoor Navigation Card
├── Column 2: Location & Memory
│   ├── Location Card
│   └── Spatial Memory Card
└── Column 3: Activity Logs
    └── Logs Card (scrollable)
```

### WebSocket Events
The dashboard listens for these event types:
- `vision`: Vision state updates (objects, obstacles, torch)
- `speech`: Voice command recognition and responses
- `indoor_navigation`: Navigation state, destination, confidence
- `room_labeled`: New room added to spatial memory
- `landmark_labeled`: New landmark saved

### Auto-Reconnection
The dashboard automatically reconnects to the backend if the connection is lost, with a 3-second retry interval.

## Color Scheme

### Status Colors
- 🟢 **Connected**: Green (emerald-500)
- 🟡 **Connecting**: Amber (amber-500)
- 🔴 **Offline**: Red (red-500)

### Navigation States
- **NAVIGATING**: Blue (blue-600)
- **SAFETY_HOLD**: Red (red-600)
- **APPROACHING**: Green (green-600)
- **ARRIVED**: Emerald (emerald-600)
- **IDLE**: Gray (gray-600)

### Confidence Levels
- **HIGH**: Green (green-600)
- **MEDIUM**: Yellow (yellow-600)
- **LOW**: Orange (orange-600)
- **INVALID**: Red (red-600)

### Event Types
- **Speech**: Purple (purple-800)
- **Alert**: Red (red-800)
- **Navigation**: Blue (blue-800)
- **System**: Gray (gray-800)

## Development

### Code Formatting
```bash
npm run lint
```

### Type Checking
```bash
npx tsc --noEmit
```

## Contributing

When adding new features to the dashboard:
1. Follow the existing Tailwind CSS patterns
2. Use the established color scheme for consistency
3. Add TypeScript types for new data structures
4. Update the WebSocket event handlers as needed
5. Test responsive behavior on mobile devices
6. Maintain accessibility standards (ARIA labels, keyboard navigation)

## License

Part of the SURDAS assistive vision system.
