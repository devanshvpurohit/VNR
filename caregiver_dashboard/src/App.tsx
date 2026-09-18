import { useState, useEffect, useRef } from 'react';
import './index.css';

interface VisionContext {
  mode: string;
  torch_on: boolean;
  detected_objects: string[];
  closest_obstacle: string | null;
  wall_ahead: boolean;
}

interface IndoorNavigation {
  state: string;
  destination: string | null;
  confidence: string;
  distance_remaining: number | null;
  safe_directions: number;
  hold_reason: string | null;
}

interface SpatialMemory {
  name: string;
  room_id?: number;
  landmark_id?: number;
}

interface LogEntry {
  id: number;
  time: string;
  type: 'speech' | 'alert' | 'system' | 'navigation' | 'fall';
  message: string;
}

interface Location {
  lat: number;
  lng: number;
  city: string;
  region: string;
  country: string;
}

interface FallDetectorData {
  ax: number;
  ay: number;
  az: number;
  acceleration: number;
  pitch: number;
  roll: number;
  falls: number;
  state: 'NORMAL' | 'POSSIBLE_FALL' | 'IMPACT_DETECTED' | 'FALL_CONFIRMED';
  mpu: 'OK' | 'ERROR';
}

interface ControllerStatus {
  device: string;
  ip: string;
  wifi: string;
  mpu: string;
  falls: number;
}

// ──────────── SVG Icons ────────────
const MapPinIcon = () => (
  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <path d="M21 10c0 7-9 13-9 13s-9-6-9-13a9 9 0 0 1 18 0z" />
    <circle cx="12" cy="10" r="3" />
  </svg>
);
const EyeIcon = () => (
  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z" />
    <circle cx="12" cy="12" r="3" />
  </svg>
);
const NavigationIcon = () => (
  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <polygon points="3 11 22 2 13 21 11 13 3 11" />
  </svg>
);
const BrainIcon = () => (
  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <path d="M9.5 2A2.5 2.5 0 0 1 12 4.5v15a2.5 2.5 0 0 1-4.96.44 2.5 2.5 0 0 1-2.96-3.08 3 3 0 0 1-.34-5.58 2.5 2.5 0 0 1 1.32-4.24 2.5 2.5 0 0 1 1.98-3A2.5 2.5 0 0 1 9.5 2Z" />
    <path d="M14.5 2A2.5 2.5 0 0 0 12 4.5v15a2.5 2.5 0 0 0 4.96.44 2.5 2.5 0 0 0 2.96-3.08 3 3 0 0 0 .34-5.58 2.5 2.5 0 0 0-1.32-4.24 2.5 2.5 0 0 0-1.98-3A2.5 2.5 0 0 0 14.5 2Z" />
  </svg>
);
const VolumeIcon = ({ color = 'currentColor' }: { color?: string }) => (
  <svg viewBox="0 0 24 24" fill="none" stroke={color} strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <polygon points="11 5 6 9 2 9 2 15 6 15 11 19 11 5" />
    <path d="M19.07 4.93a10 10 0 0 1 0 14.14" />
    <path d="M15.54 8.46a5 5 0 0 1 0 7.07" />
  </svg>
);
const AlertIcon = () => (
  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z" />
    <line x1="12" y1="9" x2="12" y2="13" />
    <line x1="12" y1="17" x2="12.01" y2="17" />
  </svg>
);
const InfoIcon = () => (
  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <circle cx="12" cy="12" r="10" />
    <line x1="12" y1="8" x2="12" y2="12" />
    <line x1="12" y1="16" x2="12.01" y2="16" />
  </svg>
);
const ListIcon = () => (
  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <line x1="8" y1="6" x2="21" y2="6" /><line x1="8" y1="12" x2="21" y2="12" />
    <line x1="8" y1="18" x2="21" y2="18" /><line x1="3" y1="6" x2="3.01" y2="6" />
    <line x1="3" y1="12" x2="3.01" y2="12" /><line x1="3" y1="18" x2="3.01" y2="18" />
  </svg>
);
const ShieldIcon = () => (
  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" />
  </svg>
);
const TargetIcon = () => (
  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <circle cx="12" cy="12" r="10" />
    <circle cx="12" cy="12" r="6" />
    <circle cx="12" cy="12" r="2" />
  </svg>
);
const AlertTriangleIcon = () => (
  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <path d="m21.73 18-8-14a2 2 0 0 0-3.48 0l-8 14A2 2 0 0 0 4 21h16a2 2 0 0 0 1.73-3Z"/>
    <line x1="12" y1="9" x2="12" y2="13"/>
    <line x1="12" y1="17" x2="12.01" y2="17"/>
  </svg>
);
const ActivityIcon = () => (
  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <polyline points="22 12 18 12 15 21 9 3 6 12 2 12"/>
  </svg>
);

const API = 'http://localhost:8000';
const WS  = 'ws://localhost:8000/ws';
const CONTROLLER_IP = '192.168.4.2';  // ESP32 Controller

// ──────────── Main App ────────────
function App() {
  const [vision, setVision] = useState<VisionContext | null>(null);
  const [indoorNav, setIndoorNav] = useState<IndoorNavigation | null>(null);
  const [spatialMemory, setSpatialMemory] = useState<SpatialMemory[]>([]);
  const [logs, setLogs] = useState<LogEntry[]>([]);
  const [location, setLocation] = useState<Location | null>(null);
  const [wsState, setWsState] = useState<'connecting' | 'connected' | 'disconnected'>('connecting');
  
  // Fall detector state
  const [fallData, setFallData] = useState<FallDetectorData | null>(null);
  const [controllerStatus, setControllerStatus] = useState<ControllerStatus | null>(null);
  const [controllerConnected, setControllerConnected] = useState(false);
  
  const wsRef = useRef<WebSocket | null>(null);
  const prevWallRef = useRef(false);
  const reconnectTimer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const fallPollInterval = useRef<ReturnType<typeof setInterval> | null>(null);

  const addLog = (type: LogEntry['type'], message: string) => {
    setLogs(prev => [
      { id: Date.now() + Math.random(), time: new Date().toLocaleTimeString(), type, message },
      ...prev,
    ].slice(0, 100));
  };

  // Fetch fall detector data
  const fetchFallData = async () => {
    try {
      const response = await fetch(`http://${CONTROLLER_IP}/imu`, { 
        signal: AbortSignal.timeout(2000) 
      });
      const data = await response.json();
      
      setFallData(data);
      setControllerConnected(true);
      
      // Alert on fall detection
      if (data.state === 'FALL_CONFIRMED' && (!fallData || fallData.state !== 'FALL_CONFIRMED')) {
        addLog('fall', `🚨 FALL DETECTED! Total falls: ${data.falls}`);
      } else if (data.state === 'POSSIBLE_FALL') {
        addLog('fall', '⚠️ Possible fall detected - monitoring...');
      } else if (data.state === 'IMPACT_DETECTED') {
        addLog('fall', '💥 Impact detected - analyzing orientation...');
      }
    } catch (error) {
      if (controllerConnected) {
        setControllerConnected(false);
        addLog('system', 'Fall detector disconnected');
      }
      setFallData(null);
    }
  };

  // Fetch controller status
  const fetchControllerStatus = async () => {
    try {
      const response = await fetch(`http://${CONTROLLER_IP}/status`, {
        signal: AbortSignal.timeout(2000)
      });
      const data = await response.json();
      setControllerStatus(data);
    } catch (error) {
      setControllerStatus(null);
    }
  };

  // Fetch location once
  const fetchLocation = () => {
    fetch(`${API}/location`)
      .then(r => r.json())
      .then(setLocation)
      .catch(() => {});
  };

  // WebSocket with auto-reconnect
  const connect = () => {
    if (wsRef.current) {
      wsRef.current.onclose = null;
      wsRef.current.close();
    }
    setWsState('connecting');
    const ws = new WebSocket(WS);
    wsRef.current = ws;

    ws.onopen = () => {
      setWsState('connected');
      addLog('system', '✅ Dashboard connected to SURDAS');
      fetchLocation();
    };

    ws.onclose = () => {
      setWsState('disconnected');
      reconnectTimer.current = setTimeout(connect, 3000);
    };

    ws.onerror = () => {
      ws.close();
    };

    ws.onmessage = (event) => {
      try {
        const parsed = JSON.parse(event.data);
        if (parsed.type === 'vision') {
          setVision(parsed.data as VisionContext);
        } else if (parsed.type === 'speech') {
          addLog('speech', parsed.data.text);
        } else if (parsed.type === 'indoor_navigation') {
          setIndoorNav(parsed.data as IndoorNavigation);
          if (parsed.data.state === 'NAVIGATING') {
            addLog('navigation', `🧭 Navigating to ${parsed.data.destination}`);
          } else if (parsed.data.state === 'SAFETY_HOLD') {
            addLog('alert', `⚠️ Safety hold: ${parsed.data.hold_reason}`);
          }
        } else if (parsed.type === 'room_labeled') {
          addLog('system', `🏠 Room labeled: ${parsed.data.name}`);
          setSpatialMemory(prev => [...prev, parsed.data]);
        } else if (parsed.type === 'landmark_labeled') {
          addLog('system', `📍 Landmark saved: ${parsed.data.name}`);
          setSpatialMemory(prev => [...prev, parsed.data]);
        }
      } catch (_) {}
    };
  };

  useEffect(() => {
    connect();
    
    // Start fall detector polling
    fetchFallData();
    fetchControllerStatus();
    fallPollInterval.current = setInterval(() => {
      fetchFallData();
      if (Math.random() < 0.1) { // Status every ~2 seconds
        fetchControllerStatus();
      }
    }, 200);
    
    return () => {
      if (reconnectTimer.current) clearTimeout(reconnectTimer.current);
      if (fallPollInterval.current) clearInterval(fallPollInterval.current);
      if (wsRef.current) { wsRef.current.onclose = null; wsRef.current.close(); }
    };
  }, []);

  // Log wall detection transitions
  useEffect(() => {
    if (vision?.wall_ahead && !prevWallRef.current) {
      addLog('alert', '🧱 Wall or barrier detected ahead!');
    }
    prevWallRef.current = vision?.wall_ahead ?? false;
  }, [vision?.wall_ahead]);

  const getStatusBadge = () => {
    if (wsState === 'connected') {
      return { bg: 'bg-emerald-50', text: 'text-emerald-700', dot: 'bg-emerald-500', label: '🟢 System Online' };
    } else if (wsState === 'connecting') {
      return { bg: 'bg-amber-50', text: 'text-amber-700', dot: 'bg-amber-500', label: '🟡 Connecting…' };
    } else {
      return { bg: 'bg-red-50', text: 'text-red-700', dot: 'bg-red-500', label: '🔴 Offline' };
    }
  };

  const status = getStatusBadge();

  const getNavStateColor = (state: string) => {
    const colors = {
      'NAVIGATING': 'text-blue-600 bg-blue-50',
      'SAFETY_HOLD': 'text-red-600 bg-red-50',
      'APPROACHING': 'text-green-600 bg-green-50',
      'ARRIVED': 'text-emerald-600 bg-emerald-50',
      'IDLE': 'text-gray-600 bg-gray-50'
    };
    return colors[state as keyof typeof colors] || 'text-gray-600 bg-gray-50';
  };

  const getConfidenceColor = (conf: string) => {
    const colors = {
      'HIGH': 'text-green-600',
      'MEDIUM': 'text-yellow-600',
      'LOW': 'text-orange-600',
      'INVALID': 'text-red-600'
    };
    return colors[conf as keyof typeof colors] || 'text-gray-600';
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 via-blue-50 to-indigo-50">
      {/* ── Header ── */}
      <header className="bg-white/80 backdrop-blur-md border-b border-gray-200/50 sticky top-0 z-50 shadow-sm">
        <div className="max-w-[1600px] mx-auto px-6 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-blue-500 to-indigo-600 flex items-center justify-center shadow-lg">
                <ShieldIcon />
              </div>
              <div>
                <h1 className="text-2xl font-bold bg-gradient-to-r from-blue-600 to-indigo-600 bg-clip-text text-transparent">
                  SURDAS
                </h1>
                <p className="text-sm text-gray-600">Caregiver Dashboard</p>
              </div>
            </div>
            <div className={`px-4 py-2 rounded-full ${status.bg} ${status.text} flex items-center gap-2 font-medium shadow-sm`}>
              <span className={`w-2 h-2 rounded-full ${status.dot} animate-pulse`} />
              {status.label}
            </div>
          </div>
        </div>
      </header>

      {wsState !== 'connected' && (
        <div className="max-w-[1600px] mx-auto px-6 mt-4">
          <div className="bg-blue-50 border border-blue-200 rounded-xl p-4 flex items-center gap-3">
            <InfoIcon />
            <span className="text-blue-800">
              Start <code className="px-2 py-1 bg-blue-100 rounded font-mono text-sm">python3 surdas_brain.py</code> — the dashboard will connect automatically.
            </span>
          </div>
        </div>
      )}

      {/* ── Main Grid ── */}
      <div className="max-w-[1600px] mx-auto px-6 py-6 grid grid-cols-1 lg:grid-cols-3 gap-6">

        {/* ── Column 1: Vision & Status ── */}
        <div className="space-y-6">
          {/* Vision State */}
          <div className="bg-white rounded-2xl shadow-lg border border-gray-100 overflow-hidden">
            <div className="bg-gradient-to-r from-blue-500 to-indigo-600 px-6 py-4 flex items-center gap-3 text-white">
              <EyeIcon />
              <h2 className="text-lg font-semibold">Vision State</h2>
            </div>
            <div className="p-6 space-y-4">
              <div className="flex items-center justify-between pb-3 border-b border-gray-100">
                <span className="text-gray-600 font-medium">Mode</span>
                <span className="px-3 py-1 bg-blue-50 text-blue-700 rounded-lg font-semibold">
                  {vision?.mode ?? 'IDLE'}
                </span>
              </div>
              <div className="flex items-center justify-between pb-3 border-b border-gray-100">
                <span className="text-gray-600 font-medium">Flashlight</span>
                <span className={`px-3 py-1 rounded-lg font-semibold ${vision?.torch_on ? 'bg-yellow-50 text-yellow-700' : 'bg-gray-50 text-gray-500'}`}>
                  {vision ? (vision.torch_on ? '🔦 ON' : 'OFF') : '—'}
                </span>
              </div>
              <div>
                <span className="text-gray-600 font-medium block mb-2">Closest Obstacle</span>
                <div className="px-4 py-3 bg-gray-50 rounded-lg">
                  <p className="text-gray-800 font-medium">
                    {vision?.closest_obstacle ?? '✅ Path is clear'}
                  </p>
                </div>
              </div>
              <div className={`px-4 py-3 rounded-lg ${vision?.wall_ahead ? 'bg-red-50 border border-red-200' : 'bg-green-50 border border-green-200'}`}>
                <div className="flex items-center justify-between">
                  <span className="font-medium text-gray-700">Wall Detection</span>
                  <span className={`font-bold ${vision?.wall_ahead ? 'text-red-600' : 'text-green-600'}`}>
                    {vision?.wall_ahead ? '🧱 WARNING' : '✅ CLEAR'}
                  </span>
                </div>
              </div>
              
              {vision && vision.detected_objects.length > 0 && (
                <div>
                  <span className="text-gray-600 font-medium block mb-3">Detected Objects</span>
                  <div className="flex flex-wrap gap-2">
                    {[...new Set(vision.detected_objects)].map((obj, i) => (
                      <span key={i} className="px-3 py-1.5 bg-indigo-50 text-indigo-700 rounded-lg text-sm font-medium">
                        {obj}
                      </span>
                    ))}
                  </div>
                </div>
              )}
            </div>
          </div>

          {/* Indoor Navigation */}
          {indoorNav && indoorNav.state !== 'IDLE' && (
            <div className="bg-white rounded-2xl shadow-lg border border-gray-100 overflow-hidden">
              <div className="bg-gradient-to-r from-purple-500 to-pink-600 px-6 py-4 flex items-center gap-3 text-white">
                <NavigationIcon />
                <h2 className="text-lg font-semibold">Indoor Navigation</h2>
              </div>
              <div className="p-6 space-y-4">
                <div className="flex items-center justify-between">
                  <span className="text-gray-600 font-medium">Status</span>
                  <span className={`px-3 py-1.5 rounded-lg font-semibold ${getNavStateColor(indoorNav.state)}`}>
                    {indoorNav.state}
                  </span>
                </div>
                {indoorNav.destination && (
                  <div className="flex items-center gap-2 px-4 py-3 bg-purple-50 rounded-lg">
                    <TargetIcon />
                    <div>
                      <p className="text-sm text-purple-600 font-medium">Destination</p>
                      <p className="text-purple-900 font-semibold">{indoorNav.destination}</p>
                    </div>
                  </div>
                )}
                <div className="grid grid-cols-2 gap-3">
                  <div className="px-4 py-3 bg-gray-50 rounded-lg">
                    <p className="text-xs text-gray-600 mb-1">Confidence</p>
                    <p className={`font-bold ${getConfidenceColor(indoorNav.confidence)}`}>
                      {indoorNav.confidence}
                    </p>
                  </div>
                  <div className="px-4 py-3 bg-gray-50 rounded-lg">
                    <p className="text-xs text-gray-600 mb-1">Safe Paths</p>
                    <p className="font-bold text-gray-800">{indoorNav.safe_directions}</p>
                  </div>
                </div>
                {indoorNav.distance_remaining !== null && (
                  <div className="px-4 py-3 bg-blue-50 rounded-lg">
                    <p className="text-sm text-blue-600 font-medium mb-1">Distance Remaining</p>
                    <p className="text-2xl font-bold text-blue-900">{indoorNav.distance_remaining.toFixed(1)}m</p>
                  </div>
                )}
                {indoorNav.hold_reason && (
                  <div className="px-4 py-3 bg-red-50 border border-red-200 rounded-lg flex items-start gap-2">
                    <AlertIcon />
                    <div>
                      <p className="text-sm text-red-600 font-medium">Hold Reason</p>
                      <p className="text-red-800 font-semibold">{indoorNav.hold_reason}</p>
                    </div>
                  </div>
                )}
              </div>
            </div>
          )}
        </div>

        {/* ── Column 2: Location & Memory ── */}
        <div className="space-y-6">
          {/* Location */}
          <div className="bg-white rounded-2xl shadow-lg border border-gray-100 overflow-hidden">
            <div className="bg-gradient-to-r from-green-500 to-emerald-600 px-6 py-4 flex items-center gap-3 text-white">
              <MapPinIcon />
              <h2 className="text-lg font-semibold">Live Location</h2>
            </div>
            <div className="p-6">
              {location ? (
                <>
                  <div className="mb-4">
                    <div className="text-2xl font-bold text-gray-800 mb-1">
                      📍 {location.city}{location.region ? `, ${location.region}` : ''}
                    </div>
                    <div className="text-sm text-gray-600">
                      {location.country && <span className="mr-2">🌐 {location.country}</span>}
                      <span className="font-mono">
                        {location.lat.toFixed(4)}, {location.lng.toFixed(4)}
                      </span>
                    </div>
                  </div>
                  {location.lat !== 0 && (
                    <iframe
                      className="w-full h-64 rounded-xl border border-gray-200"
                      title="User location map"
                      src={`https://www.openstreetmap.org/export/embed.html?bbox=${location.lng - 0.012}%2C${location.lat - 0.012}%2C${location.lng + 0.012}%2C${location.lat + 0.012}&layer=mapnik&marker=${location.lat}%2C${location.lng}`}
                    />
                  )}
                </>
              ) : (
                <p className="text-gray-500 text-center py-8">
                  {wsState === 'connected' ? 'Fetching location…' : 'Connect SURDAS to load location'}
                </p>
              )}
            </div>
          </div>

          {/* Spatial Memory */}
          {spatialMemory.length > 0 && (
            <div className="bg-white rounded-2xl shadow-lg border border-gray-100 overflow-hidden">
              <div className="bg-gradient-to-r from-violet-500 to-purple-600 px-6 py-4 flex items-center gap-3 text-white">
                <BrainIcon />
                <h2 className="text-lg font-semibold">Spatial Memory</h2>
              </div>
              <div className="p-6">
                <div className="space-y-2">
                  {spatialMemory.slice(0, 10).map((item, i) => (
                    <div key={i} className="px-4 py-3 bg-violet-50 rounded-lg flex items-center justify-between">
                      <span className="font-medium text-violet-900">{item.name}</span>
                      <span className="text-xs text-violet-600 px-2 py-1 bg-violet-100 rounded">
                        {item.room_id ? '🏠 Room' : '📍 Landmark'}
                      </span>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          )}
        </div>

        {/* ── Column 3: Activity Logs ── */}
        <div className="lg:col-span-1">
          <div className="bg-white rounded-2xl shadow-lg border border-gray-100 overflow-hidden h-full flex flex-col">
            <div className="bg-gradient-to-r from-gray-700 to-gray-900 px-6 py-4 flex items-center justify-between text-white">
              <div className="flex items-center gap-3">
                <ListIcon />
                <h2 className="text-lg font-semibold">Activity Logs</h2>
              </div>
              {logs.length > 0 && (
                <button
                  onClick={() => setLogs([])}
                  className="px-3 py-1 bg-white/20 hover:bg-white/30 rounded-lg text-sm font-medium transition-colors"
                >
                  Clear
                </button>
              )}
            </div>

            <div className="flex-1 overflow-y-auto p-4 space-y-3 max-h-[calc(100vh-16rem)]">
              {logs.length === 0 ? (
                <p className="text-gray-500 text-center py-12">
                  No activity yet — start SURDAS to see events here.
                </p>
              ) : (
                logs.map(log => (
                  <div
                    key={log.id}
                    className={`p-4 rounded-lg border ${
                      log.type === 'alert' ? 'bg-red-50 border-red-200' :
                      log.type === 'navigation' ? 'bg-blue-50 border-blue-200' :
                      log.type === 'speech' ? 'bg-purple-50 border-purple-200' :
                      'bg-gray-50 border-gray-200'
                    }`}
                  >
                    <div className="flex items-center gap-2 mb-2">
                      <div className="w-5 h-5">
                        {log.type === 'speech' && <VolumeIcon color="#9333ea" />}
                        {log.type === 'alert' && <AlertIcon />}
                        {log.type === 'navigation' && <NavigationIcon />}
                        {log.type === 'system' && <InfoIcon />}
                      </div>
                      <span className="text-xs text-gray-500 font-mono">{log.time}</span>
                    </div>
                    <p className={`text-sm font-medium ${
                      log.type === 'alert' ? 'text-red-800' :
                      log.type === 'navigation' ? 'text-blue-800' :
                      log.type === 'speech' ? 'text-purple-800' :
                      'text-gray-800'
                    }`}>
                      {log.message}
                    </p>
                  </div>
                ))
              )}
            </div>
          </div>
        </div>

      </div>
    </div>
  );
}

export default App;
