# Fall Detection - Quick Start Guide

## 🚀 Get Started in 3 Steps

### 1. Verify ESP32 is Working

```bash
# Test the IMU endpoint
curl http://192.168.4.2/imu
```

**Expected output:**
```json
{
  "ax": 0.12,
  "ay": 0.05,
  "az": 9.81,
  "acceleration": 9.82,
  "pitch": 2.3,
  "roll": -1.8,
  "falls": 0,
  "state": "NORMAL",
  "mpu": "OK"
}
```

**If it fails:**
- Check ESP32 is powered on: `ping 192.168.4.2`
- Verify WiFi connection
- Check MPU6050 sensor wiring

### 2. Start the Dashboard

```bash
cd caregiver_dashboard
npm install  # First time only
npm run dev
```

**Open browser:** http://localhost:5173

### 3. View Fall Detection

Navigate to **"Live Safety"** tab in the dashboard sidebar.

You should see:
- **Fall Detector Card** with:
  - Current state (color-coded)
  - Acceleration value
  - Total fall count
  - Real-time updates every 200ms

## 📊 Dashboard Views

### Overview Page
- Quick stat card showing total falls
- Located in top-right stats section

### Live Safety Page
- Full fall detector card
- Real-time IMU data
- Color-coded state indicators:
  - 🟢 **NORMAL** - All good
  - 🟡 **POSSIBLE_FALL** - Suspicious movement
  - 🟠 **IMPACT_DETECTED** - Impact detected
  - 🔴 **FALL_CONFIRMED** - Emergency!

### Emergency Mode
When a fall is confirmed (`FALL_CONFIRMED`), the dashboard automatically:
- Switches to full-screen red alert
- Shows giant fall count
- Displays animated warning icon
- Provides "Acknowledge & Return" button

## 🧪 Test the System

### Option 1: Run Automated Tests

```bash
python3 test_imu_endpoint.py
```

This will:
- ✓ Test ESP32 connectivity
- ✓ Validate JSON data format
- ✓ Check state values
- ✓ Verify MPU sensor status
- ✓ Test acceleration ranges
- ✓ Run continuous monitoring (optional)

### Option 2: Manual Testing

```bash
# Watch live IMU data (refreshes every 0.2s)
watch -n 0.2 "curl -s http://192.168.4.2/imu | jq"
```

### Option 3: Simulate Fall (if supported)

Gently shake or tilt the ESP32 device to trigger state changes:
- Small tilt → `POSSIBLE_FALL`
- Sharp movement → `IMPACT_DETECTED`
- Hard drop/shake → `FALL_CONFIRMED` (emergency)

## 🎯 What You Should See

### Normal Operation
```
State: NORMAL
Acceleration: ~9.8 m/s² (gravity)
Pitch: 0° to ±10°
Roll: 0° to ±10°
Falls: 0
```

### During Movement
```
State: POSSIBLE_FALL
Acceleration: 10-15 m/s²
Pitch: ±20° to ±45°
Roll: ±20° to ±45°
Falls: 0
```

### Fall Detected
```
State: FALL_CONFIRMED
Acceleration: >20 m/s²
Pitch: >±60°
Roll: >±60°
Falls: 1+ (increments)
```

## ⚙️ Configuration

### Change Polling Rate

Edit `caregiver_dashboard/src/App.tsx`:

```typescript
// Current: 200ms (5 Hz)
fallPollInterval.current = setInterval(fetchFallData, 200);

// Faster: 100ms (10 Hz)
fallPollInterval.current = setInterval(fetchFallData, 100);

// Slower: 500ms (2 Hz)
fallPollInterval.current = setInterval(fetchFallData, 500);
```

### Change Controller IP

Edit `caregiver_dashboard/src/App.tsx`:

```typescript
const CONTROLLER_IP = '192.168.4.2';  // Change this
```

## 🔧 Troubleshooting

### Problem: Fall card doesn't appear

**Check:**
1. ESP32 powered on: `ping 192.168.4.2`
2. IMU endpoint works: `curl http://192.168.4.2/imu`
3. Browser console for errors (F12)

### Problem: "MPU: ERROR" displayed

**Check:**
1. MPU6050 sensor wiring (SDA, SCL, VCC, GND)
2. I2C address (0x68 or 0x69)
3. Power supply to sensor (3.3V or 5V)

### Problem: False fall detections

**Solutions:**
1. Adjust thresholds on ESP32 firmware
2. Increase acceleration threshold
3. Add minimum duration checks

### Problem: Missed real falls

**Solutions:**
1. Lower acceleration threshold
2. Increase polling rate
3. Add multiple detection algorithms

## 📱 Mobile Access

The dashboard is responsive and works on mobile:

```bash
# Find your computer's local IP
ifconfig | grep inet  # macOS/Linux
ipconfig              # Windows

# Access from phone on same WiFi
http://YOUR_COMPUTER_IP:5173
```

Example: `http://192.168.1.100:5173`

## 🔔 Future Enhancements

The system is ready to extend with:
- SMS/email alerts on fall detection
- Historical fall data logging
- Video recording on fall events
- Machine learning classification
- Multi-user notifications

## 📚 Documentation

- **This file** - Quick start
- **FALL_DETECTION_SUMMARY.md** - Feature overview
- **FALL_DETECTION_INTEGRATION.md** - Complete technical docs
- **test_imu_endpoint.py** - Automated testing

## ✅ Success Checklist

- [ ] ESP32 responds to `curl http://192.168.4.2/imu`
- [ ] Dashboard starts successfully
- [ ] Fall detector card appears in "Live Safety" view
- [ ] State shows "NORMAL" with green background
- [ ] Acceleration shows ~9.8 m/s²
- [ ] Moving ESP32 changes state to "POSSIBLE_FALL"
- [ ] Connection indicator shows "Controller Connected"

## 🆘 Need Help?

1. Run diagnostics: `python3 test_imu_endpoint.py`
2. Check browser console (F12) for errors
3. Verify network: `ping 192.168.4.2`
4. Test endpoint: `curl http://192.168.4.2/imu`

---

**Status**: ✅ Production Ready  
**Last Updated**: 2026-09-19

Everything is set up and ready to use! 🎉
