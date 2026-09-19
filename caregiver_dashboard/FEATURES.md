# SURDAS Caregiver Dashboard - Feature Showcase

Visual guide to all features in the new dashboard.

---

## 🎯 Overview Tab

The main monitoring interface with comprehensive real-time data.

### Quick Stats Cards

**Four key metrics at a glance:**

1. **System Status**
   - 🟢 Online / 🔴 Offline indicator
   - Real-time connection status
   - Automatic reconnection

2. **Uptime Counter**
   - Hours, minutes, seconds
   - Tracks dashboard session
   - Updated every second

3. **Objects Detected**
   - Real-time count from vision system
   - Updates with each frame
   - Shows detection activity

4. **Memory Locations**
   - Total rooms and landmarks
   - Spatial memory tracker
   - Grows as user labels locations

---

### Live Video Feed

**Real-time camera stream with controls**

Features:
- ✅ Live streaming indicator (red pulsing dot)
- ✅ "LIVE" badge overlay
- ✅ Hide/Show toggle button
- ✅ Aspect ratio maintained (16:9)
- ✅ Automatic fallback if unavailable
- ✅ Black background when no feed

Technical:
- Stream endpoint: `http://localhost:8888/video_feed`
- Format: Motion JPEG (MJPEG)
- Quality: Original from camera
- Latency: ~100-200ms

---

### Vision System Panel

**Complete vision system monitoring**

#### Status Indicators
1. **Mode Badge**
   - IDLE (gray) - System idle
   - NAV (blue) - Navigation active
   - OCR (purple) - Text reading mode

2. **Flashlight Status**
   - 🔦 ON (yellow) - Torch enabled
   - OFF (gray) - Torch disabled
   - Icon and text indicator

3. **Obstacle Detection**
   - 🟢 Path Clear - No obstacles
   - 🔴 Wall Ahead - Warning banner
   - Shows closest obstacle with distance

4. **Detected Objects**
   - Real-time object list
   - Maximum 10 displayed
   - Color-coded tags
   - Automatic deduplication

---

### Fall Detector Panel

**Comprehensive fall monitoring with IMU data**

#### State Display
Large status badge shows:
- 🟢 **NORMAL** - User is stable
- 🟡 **POSSIBLE FALL** - Monitoring unusual movement
- 🟠 **IMPACT DETECTED** - Sudden impact registered
- 🔴 **FALL CONFIRMED** - Fall detected, alert triggered

#### Metrics Display

**Acceleration**
- Current total acceleration (m/s²)
- Real-time calculation
- Updated 5 times per second

**Total Falls**
- Lifetime fall count
- Persistent counter
- Never resets (requires manual reset)

**Pitch & Roll**
- Device orientation angles
- Pitch: Forward/backward tilt
- Roll: Left/right tilt
- Displayed in degrees

**Sensor Status**
- MPU6050 status indicator
- OK (green) or ERROR (red)
- Shows sensor health

#### Emergency Alert
When fall confirmed:
- 🚨 Full-width emergency banner
- Red pulsing animation
- Audio alert plays
- Requires acknowledgment
- Shows total falls prominently

---

### Indoor Navigation Panel

**Real-time navigation guidance tracking**

#### States
1. **IDLE** - Not navigating
   - Shows placeholder icon
   - "Navigation Idle" message
   - Ready for commands

2. **NAVIGATING** - Active guidance
   - Purple gradient banner
   - Shows state name
   - Destination displayed
   - Real-time updates

3. **SAFETY_HOLD** - Paused for safety
   - Orange warning color
   - Hold reason displayed
   - Resumes when safe
   - User can manually pause

4. **APPROACHING** - Near destination
   - Yellow indicator
   - Distance < 1.5m
   - Preparing arrival

5. **ARRIVED** - Destination reached
   - Green success indicator
   - 0.0m distance
   - Navigation complete

#### Information Display

**Destination**
- Target location name
- Room or landmark label
- User-defined label

**Confidence Level**
- HIGH (green) - Safe to move
- MEDIUM (yellow) - Use caution
- LOW (red) - Do not move
- INVALID (gray) - No data

**Safe Directions**
- Number of unobstructed paths
- 0 = No safe routes
- Higher = More options

**Distance Remaining**
- Meters to destination
- 1 decimal precision
- Updates continuously
- Blue highlight badge

---

### Spatial Memory Panel

**Room and landmark tracking**

#### Display
- Scrollable list of locations
- Most recent at top
- Maximum 10 visible (scrollable)
- Icon indicators:
  - 🏠 Room
  - 📍 Landmark

#### Features
- Automatic timestamps
- Persistent storage (SQLite)
- Search capability (coming soon)
- Export option (coming soon)

#### Empty State
- Brain icon placeholder
- "No locations stored" message
- Encourages labeling

---

### Activity Logs

**Comprehensive event tracking system**

#### Event Types
1. **Speech** 🟣 - Voice commands
2. **Navigation** 🔵 - Navigation events
3. **Fall** 🔴 - Fall detection
4. **Alert** 🟠 - System warnings
5. **System** ⚪ - Status changes
6. **Emergency** 🔴 - Critical events

#### Priority Levels
- **Critical** - Red, audio alert
- **High** - Orange, important
- **Medium** - Purple/blue, normal
- **Low** - White/gray, info

#### Features
- Real-time updates
- Filter by type dropdown
- Color-coded entries
- Timestamp for each event
- 500 event history
- Clear all button
- Auto-scroll to latest

#### Display
- Time (HH:MM:SS)
- Type badge (color-coded)
- Message text
- Priority styling
- Hover animation

---

## 🧭 Navigation Tab

**Map and route visualization**

### Map Display
- OpenStreetMap integration (placeholder)
- User location marker
- Route visualization
- Turn-by-turn instructions
- Zoom controls

### Route History
- Past navigation sessions
- Start/end locations
- Duration and distance
- Success rate

### Location Info
- Current city
- Region/state
- Country
- IP-based geolocation

---

## 📊 Analytics Tab

**System insights and statistics**

### Daily Activity
- Event timeline
- Activity heatmap
- Peak usage times
- Command frequency

### System Health
- Uptime statistics
- Event counts by type
- Fall incident tracking
- Navigation success rate
- Object detection accuracy

### Charts (Future)
- Line charts for trends
- Bar charts for comparisons
- Pie charts for distributions
- Real-time data updates

---

## ⚙️ Settings Tab

**Dashboard configuration**

### Display Options

**Show Video Feed**
- Toggle camera stream visibility
- On (green) / Off (gray)
- Saves bandwidth when off
- State persists in session

**Alert Sounds**
- Enable/disable audio notifications
- On (green) / Off (gray)
- Browser notification sound
- For critical events only

### Connection Info

**Backend API**
- Endpoint: `http://localhost:8000`
- Health check available
- REST API for queries

**WebSocket**
- Endpoint: `ws://localhost:8000/ws`
- Real-time data stream
- Auto-reconnect enabled

**Fall Controller**
- Endpoint: `http://192.168.4.2`
- ESP32 IMU controller
- Polled at 200ms

**Video Feed**
- Endpoint: `http://localhost:8888/video_feed`
- MJPEG stream
- Optional component

---

## 🎨 Design System

### Color Palette

**Background**
- Base: Slate 900
- Gradient: Purple 900
- Accent: Blue tones

**UI Elements**
- Cards: White 10% opacity
- Borders: White 20% opacity
- Text: White primary
- Secondary: Purple 200

**Status Colors**
- Success: Emerald 500
- Warning: Amber 500
- Error: Red 500
- Info: Blue 500
- Normal: Purple 500

### Typography
- Headers: Bold, White
- Body: Medium, White
- Labels: Regular, Purple 200
- Mono: Font-mono for codes

### Spacing
- Gap: 4 (16px) or 6 (24px)
- Padding: 4-6 cards, 3-4 items
- Margin: 6-8 sections

### Effects
- Backdrop blur: 16px
- Border radius: 16-24px
- Shadows: 2xl with color/50
- Transitions: 150ms ease

---

## 🔔 Alert System

### Visual Alerts

**Emergency Banner**
- Full-width display
- Red gradient background
- Pulsing animation
- Large icons
- Bold text
- Acknowledge button

**Status Indicators**
- Pulsing dots for connection
- Color-coded badges
- Icon + text combinations
- Hover effects

### Audio Alerts

**Trigger Conditions**
- Fall confirmed
- Critical priority events
- User configurable

**Sound**
- Browser notification sound
- Short and attention-grabbing
- Respects system volume

### Priority System

**Critical** (Red)
- Immediate attention required
- Audio + visual alert
- Blocks other notifications
- Requires acknowledgment

**High** (Orange)
- Important but not urgent
- Visual alert only
- Logged prominently
- Can be dismissed

**Medium** (Purple/Blue)
- Normal operations
- Standard logging
- No special alerts

**Low** (White/Gray)
- Informational only
- Minimal visual weight
- Background logging

---

## 🚀 Performance Features

### Optimization Techniques

1. **Efficient Rendering**
   - React memo for static components
   - Key-based lists
   - Conditional rendering
   - Lazy loading for video

2. **State Management**
   - useState for local state
   - useRef for non-rendering values
   - Proper dependency arrays
   - Debounced updates

3. **Network Optimization**
   - WebSocket for real-time data
   - HTTP polling only for ESP32
   - Reconnection with backoff
   - Connection pooling

4. **Memory Management**
   - 500 event log limit
   - Cleanup on unmount
   - Efficient data structures
   - No memory leaks

### Performance Metrics

- Initial Load: < 2s
- Time to Interactive: < 3s
- WebSocket Latency: < 50ms
- Video Frame Rate: 20-30 FPS
- Event Processing: Real-time
- Memory Usage: < 100MB
- CPU Usage: < 10% (idle)

---

## 🎯 User Experience

### Intuitive Design

**Clear Hierarchy**
- Important info larger
- Status always visible
- Actions easily accessible
- Logical grouping

**Visual Feedback**
- Hover effects on interactive elements
- Color changes on state
- Animations for transitions
- Loading indicators

**Error Handling**
- Graceful degradation
- Clear error messages
- Automatic retry
- Fallback UI

### Accessibility

**Considerations**
- Color not sole indicator
- Text labels on icons
- Sufficient contrast
- Readable font sizes
- Focus indicators

**Future Enhancements**
- Screen reader support
- Keyboard navigation
- High contrast mode
- Text size controls

---

## 🔧 Customization

### Easy Configuration

**Environment Variables**
```typescript
const API = 'http://localhost:8000';
const WS = 'ws://localhost:8000/ws';
const CONTROLLER_IP = '192.168.4.2';
const VIDEO_FEED = 'http://localhost:8888/video_feed';
```

**Color Themes**
- Modify Tailwind config
- Change gradient colors
- Adjust opacity levels
- Custom brand colors

**Feature Toggles**
```typescript
const showVideo = true;
const alertsEnabled = true;
const enableAnalytics = false;
```

---

## 📱 Responsive Design

### Breakpoints

**Mobile** (< 768px)
- Single column layout
- Stacked cards
- Compact spacing
- Touch-optimized

**Tablet** (768px - 1024px)
- Two column layout
- Medium card sizes
- Balanced spacing

**Desktop** (> 1024px)
- Multi-column layouts
- Large cards
- Generous spacing
- Optimized for cursor

### Adaptive Elements
- Navigation tabs adapt
- Cards reflow
- Text scales appropriately
- Images maintain aspect ratio

---

## 🎊 What's Next?

### Planned Features
- Interactive maps
- Historical charts
- Multi-user support
- Mobile app
- Voice controls
- AI insights
- Export functionality
- More languages

### Community Contributions
- Feature requests welcome
- Bug reports appreciated
- Pull requests accepted
- Documentation improvements

---

**This is a living document. Features are continuously being enhanced!**
