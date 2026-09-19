# Quick Start Guide - SURDAS Caregiver Dashboard v2.0

Get up and running in 5 minutes!

## 🚀 Step-by-Step Setup

### Step 1: Install Dependencies (One-time)

```bash
cd caregiver_dashboard
npm install
```

This will install all required packages including React, TypeScript, Tailwind CSS, and Lucide icons.

### Step 2: Start SURDAS Backend

In a **first terminal**:

```bash
cd /path/to/suradas
python3 surdas_brain.py
```

✅ Wait for these messages:
```
[TELEMETRY] Dashboard server starting on http://0.0.0.0:8000
[TELEMETRY] Dashboard server ready — ws://localhost:8000/ws
```

### Step 3: Start Dashboard

In a **second terminal**:

```bash
cd /path/to/suradas/caregiver_dashboard
npm run dev
```

✅ You should see:
```
  VITE v8.x.x  ready in xxx ms

  ➜  Local:   http://localhost:5173/
  ➜  Network: http://192.168.x.x:5173/
```

### Step 4: Open Dashboard

Open your browser and navigate to:
```
http://localhost:5173
```

### Step 5: Verify Connection

Look at the header - you should see:
- 🟢 **"System Online"** (green dot)
- 📍 **Location** indicator
- 🔔 **Notification** bell icon

Check the Activity Logs section for:
```
✅ Dashboard connected to SURDAS
📍 Location: [Your City], [Your Region]
```

## 🎉 You're Ready!

The dashboard is now monitoring your SURDAS system in real-time.

## 🔍 What You'll See

### Overview Tab (Default)
- **Quick Stats** - System status, uptime, object count, memory locations
- **Live Video Feed** - Real-time camera stream (if available)
- **Vision System** - Current mode, flashlight, obstacles, detected objects
- **Fall Detector** - Real-time IMU data and fall status (if ESP32 connected)
- **Indoor Navigation** - Current navigation state and destination
- **Spatial Memory** - Stored rooms and landmarks
- **Activity Logs** - Live event stream

### Testing the Dashboard

Try these voice commands with SURDAS:

```
"Surdas, this is the bedroom"          # Should appear in Spatial Memory
"Surdas, what do you see?"             # Should log speech event
"Surdas, guide me to the door"         # Should update Navigation panel
```

## 🎛️ Dashboard Features

### Video Feed
- Toggle visibility with **Hide/Show** button
- Shows "LIVE" indicator when streaming
- Falls back gracefully if camera unavailable

### Activity Logs
- Filter by type: All, Speech, Navigation, Falls, Alerts, System
- Color-coded by priority: 🟢 Low, 🟣 Medium, 🟠 High, 🔴 Critical
- **Clear All** button to reset

### Fall Detection
- Requires ESP32 controller at `192.168.4.2`
- Shows real-time acceleration, pitch, roll
- Automatic alert on fall detection
- Status indicator: NORMAL, POSSIBLE_FALL, IMPACT_DETECTED, FALL_CONFIRMED

### Navigation
- Shows current destination and distance
- Confidence level: HIGH (green), MEDIUM (yellow), LOW (red)
- Safe paths indicator
- Safety hold reasons

### Settings Tab
- Toggle video feed visibility
- Enable/disable alert sounds
- View connection endpoints

## 🔧 Common Issues

### "Dashboard Offline" / Red Dot

**Problem**: Dashboard can't connect to backend

**Solutions**:
1. Verify SURDAS backend is running:
   ```bash
   curl http://localhost:8000/health
   # Should return: {"status":"ok","clients":1}
   ```

2. Check telemetry server started:
   - Look for `[TELEMETRY] Dashboard server starting` in backend logs

3. Restart backend if needed

### No Video Feed

**Problem**: Black box or "Camera feed unavailable"

**Solutions**:
1. Verify Flask app is running (usually started with `app.py`)
2. Test video endpoint:
   ```bash
   curl -I http://localhost:8888/video_feed
   ```
3. Check camera is connected to SURDAS system
4. Video feed is **optional** - dashboard works without it

### Fall Detector Showing "Connecting..."

**Problem**: ESP32 controller not reachable

**Solutions**:
1. Check ESP32 is powered on
2. Verify it's connected to same network
3. Test endpoint:
   ```bash
   curl http://192.168.4.2/imu
   ```
4. Update IP in `src/App.tsx` if different:
   ```typescript
   const CONTROLLER_IP = '192.168.x.x';  // Your ESP32 IP
   ```
5. Fall detector is **optional** - dashboard works without it

### No Events in Activity Logs

**Problem**: Logs are empty

**Solutions**:
1. Check WebSocket connection (should be green dot in header)
2. Try a voice command to generate activity
3. Check browser console for errors (F12)
4. Verify telemetry is broadcasting:
   ```python
   from telemetry import broadcast_event
   broadcast_event('test', {'message': 'Hello dashboard!'})
   ```

## 🎯 Next Steps

1. **Explore Tabs** - Navigation, Analytics, Settings
2. **Test Voice Commands** - Generate different event types
3. **Label Rooms** - Build spatial memory
4. **Set Up Fall Detector** - For complete monitoring
5. **Customize Settings** - Adjust to your preferences

## 📱 Mobile Access

Access from other devices on your network:

```
http://[your-computer-ip]:5173
```

Find your IP:
- **macOS**: `ifconfig | grep "inet " | grep -v 127.0.0.1`
- **Linux**: `hostname -I`
- **Windows**: `ipconfig`

## 🆘 Need Help?

1. Check the full [README.md](./README.md) for detailed docs
2. Review browser console (F12) for errors
3. Check SURDAS backend logs
4. Verify network connectivity between components

## 🎊 Success!

You now have a fully functional caregiver dashboard monitoring your SURDAS system!

The dashboard will:
- ✅ Automatically reconnect if connection drops
- ✅ Show real-time updates from SURDAS
- ✅ Alert on critical events (falls, obstacles)
- ✅ Track spatial memory and navigation
- ✅ Log all system activity

**Happy monitoring! 🚀**
