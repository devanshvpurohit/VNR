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

const API = 'http://localhost:8000';
const WS  = 'ws://localhost:8000/ws';
const CONTROLLER_IP = '192.168.4.2';

// ──────────── Icons ────────────
const icons = {
  shield: () => (
    <svg className="w-full h-full" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" />
    </svg>
  ),
  eye: () => (
    <svg className="w-full h-full" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z" />
      <circle cx="12" cy="12" r="3" />
    </svg>
  ),
  navigation: () => (
    <svg className="w-full h-full" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <polygon points="3 11 22 2 13 21 11 13 3 11" />
    </svg>
  ),
  heart: () => (
    <svg className="w-full h-full" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <path d="M20.84 4.61a5.5 5.5 0 0 0-7.78 0L12 5.67l-1.06-1.06a5.5 5.5 0 0 0-7.78 7.78l1.06 1.06L12 21.23l7.78-7.78 1.06-1.06a5.5 5.5 0 0 0 0-7.78z" />
    </svg>
  ),
  activity: () => (
    <svg className="w-full h-full" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <polyline points="22 12 18 12 15 21 9 3 6 12 2 12"/>
    </svg>
  ),
  alert: () => (
    <svg className="w-full h-full" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <path d="m21.73 18-8-14a2 2 0 0 0-3.48 0l-8 14A2 2 0 0 0 4 21h16a2 2 0 0 0 1.73-3Z"/>
      <line x1="12" y1="9" x2="12" y2="13"/>
      <line x1="12" y1="17" x2="12.01" y2="17"/>
    </svg>
  ),
  brain: () => (
    <svg className="w-full h-full" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <path d="M9.5 2A2.5 2.5 0 0 1 12 4.5v15a2.5 2.5 0 0 1-4.96.44 2.5 2.5 0 0 1-2.96-3.08 3 3 0 0 1-.34-5.58 2.5 2.5 0 0 1 1.32-4.24 2.5 2.5 0 0 1 1.98-3A2.5 2.5 0 0 1 9.5 2Z" />
      <path d="M14.5 2A2.5 2.5 0 0 0 12 4.5v15a2.5 2.5 0 0 0 4.96.44 2.5 2.5 0 0 0 2.96-3.08 3 3 0 0 0 .34-5.58 2.5 2.5 0 0 0-1.32-4.24 2.5 2.5 0 0 0-1.98-3A2.5 2.5 0 0 0 14.5 2Z" />
    </svg>
  ),
  map: () => (
    <svg className="w-full h-full" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <path d="M21 10c0 7-9 13-9 13s-9-6-9-13a9 9 0 0 1 18 0z" />
      <circle cx="12" cy="10" r="3" />
    </svg>
  ),
};

function App() {
  const [vision, setVision] = useState<VisionContext | null>(null);
  const [indoorNav, setIndoorNav] = useState<IndoorNavigation | null>(null);
  const [spatialMemory, setSpatialMemory] = useState<SpatialMemory[]>([]);
  const [fallData, setFallData] = useState<FallDetectorData | null>(null);
  const [logs, setLogs] = useState<LogEntry[]>([]);
  const [location, setLocation] = useState<Location | null>(null);
  const [wsState, setWsState] = useState<'connecting' | 'connected' | 'disconnected'>('connecting');
  const [controllerConnected, setControllerConnected] = useState(false);
  
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const fallPollInterval = useRef<ReturnType<typeof setInterval> | null>(null);

  const addLog = (type: LogEntry['type'], message: string) => {
    setLogs(prev => [
      { id: Date.now() + Math.random(), time: new Date().toLocaleTimeString(), type, message },
      ...prev,
    ].slice(0, 100));
  };

  const fetchFallData = async () => {
    try {
      const response = await fetch(`http://${CONTROLLER_IP}/imu`, { 
        signal: AbortSignal.timeout(2000) 
      });
      const data = await response.json();
      
      const prevState = fallData?.state;
      setFallData(data);
      setControllerConnected(true);
      
      if (data.state === 'FALL_CONFIRMED' && prevState !== 'FALL_CONFIRMED') {
        addLog('fall', `🚨 FALL DETECTED! Total falls: ${data.falls}`);
      } else if (data.state === 'POSSIBLE_FALL' && prevState !== 'POSSIBLE_FALL') {
        addLog('fall', '⚠️ Possible fall detected - monitoring...');
      }
    } catch {
      if (controllerConnected) {
        setControllerConnected(false);
      }
      setFallData(null);
    }
  };

  const fetchLocation = () => {
    fetch(`${API}/location`)
      .then(r => r.json())
      .then(setLocation)
      .catch(() => {});
  };

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

    ws.onerror = () => ws.close();

    ws.onmessage = (event) => {
      try {
        const parsed = JSON.parse(event.data);
        if (parsed.type === 'vision') {
          setVision(parsed.data as VisionContext);
        } else if (parsed.type === 'speech') {
          addLog('speech', parsed.data.text);
        } else if (parsed.type === 'indoor_navigation') {
          setIndoorNav(parsed.data as IndoorNavigation);
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
    fetchFallData();
    fallPollInterval.current = setInterval(fetchFallData, 200);
    
    return () => {
      if (reconnectTimer.current) clearTimeout(reconnectTimer.current);
      if (fallPollInterval.current) clearInterval(fallPollInterval.current);
      if (wsRef.current) { wsRef.current.onclose = null; wsRef.current.close(); }
    };
  }, []);

  const getStatusColor = () => {
    if (wsState === 'connected') return 'bg-emerald-500';
    if (wsState === 'connecting') return 'bg-amber-500';
    return 'bg-red-500';
  };

  const getFallStateColor = (state: string) => {
    const colors = {
      'NORMAL': 'bg-emerald-500',
      'POSSIBLE_FALL': 'bg-amber-500',
      'IMPACT_DETECTED': 'bg-orange-500',
      'FALL_CONFIRMED': 'bg-red-600'
    };
    return colors[state as keyof typeof colors] || 'bg-gray-500';
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-900 via-purple-900 to-slate-900">
      
      {/* Animated Background */}
      <div className="fixed inset-0 overflow-hidden pointer-events-none">
        <div className="absolute top-1/4 left-1/4 w-96 h-96 bg-purple-500/10 rounded-full blur-3xl animate-pulse" />
        <div className="absolute bottom-1/4 right-1/4 w-96 h-96 bg-blue-500/10 rounded-full blur-3xl animate-pulse" style={{ animationDelay: '1s' }} />
      </div>

      {/* Header */}
      <header className="relative bg-black/20 backdrop-blur-xl border-b border-white/10">
        <div className="max-w-[1800px] mx-auto px-6 py-6">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-4">
              <div className="w-14 h-14 rounded-2xl bg-gradient-to-br from-blue-500 to-purple-600 flex items-center justify-center shadow-lg shadow-purple-500/50">
                {icons.shield()}
              </div>
              <div>
                <h1 className="text-3xl font-bold text-white">SURDAS</h1>
                <p className="text-sm text-purple-200">Advanced Caregiver Dashboard</p>
              </div>
            </div>
            
            <div className="flex items-center gap-4">
              {/* System Status */}
              <div className="flex items-center gap-2 px-4 py-2 bg-white/10 backdrop-blur-md rounded-full">
                <div className={`w-3 h-3 rounded-full ${getStatusColor()} animate-pulse`} />
                <span className="text-white font-medium text-sm">
                  {wsState === 'connected' ? 'System Online' : wsState === 'connecting' ? 'Connecting...' : 'Offline'}
                </span>
              </div>
              
              {/* Fall Detector Status */}
              {controllerConnected && (
                <div className="flex items-center gap-2 px-4 py-2 bg-white/10 backdrop-blur-md rounded-full">
                  <div className="w-3 h-3 rounded-full bg-green-500 animate-pulse" />
                  <span className="text-white font-medium text-sm">Fall Detector</span>
                </div>
              )}
            </div>
          </div>
        </div>
      </header>

      {/* Main Dashboard */}
      <div className="relative max-w-[1800px] mx-auto px-6 py-8">
        
        {/* Fall Alert Banner */}
        {fallData?.state === 'FALL_CONFIRMED' && (
          <div className="mb-6 bg-red-600 border-2 border-red-400 rounded-2xl p-6 shadow-2xl shadow-red-500/50 animate-pulse">
            <div className="flex items-center gap-4">
              <div className="w-16 h-16 bg-white rounded-full flex items-center justify-center">
                {icons.alert()}
              </div>
              <div className="flex-1">
                <h2 className="text-2xl font-bold text-white mb-1">🚨 FALL DETECTED</h2>
                <p className="text-red-100">Immediate attention required! Total falls: {fallData.falls}</p>
              </div>
              <div className="text-right">
                <div className="text-4xl font-bold text-white">{fallData.falls}</div>
                <div className="text-sm text-red-100">Total Falls</div>
              </div>
            </div>
          </div>
        )}

        {/* Grid Layout */}
        <div className="grid grid-cols-1 lg:grid-cols-2 xl:grid-cols-4 gap-6">
          
          {/* Card 1: Vision System */}
          <div className="bg-white/10 backdrop-blur-xl border border-white/20 rounded-3xl p-6 shadow-2xl hover:shadow-purple-500/20 transition-all">
            <div className="flex items-center gap-3 mb-6">
              <div className="w-10 h-10 bg-gradient-to-br from-blue-500 to-cyan-500 rounded-xl flex items-center justify-center">
                {icons.eye()}
              </div>
              <div>
                <h3 className="text-lg font-bold text-white">Vision System</h3>
                <p className="text-xs text-purple-200">Real-time monitoring</p>
              </div>
            </div>
            
            <div className="space-y-4">
              <div className="flex justify-between items-center p-3 bg-white/5 rounded-xl">
                <span className="text-purple-200 text-sm">Mode</span>
                <span className="text-white font-bold text-sm px-3 py-1 bg-blue-500/30 rounded-lg">
                  {vision?.mode || 'IDLE'}
                </span>
              </div>
              
              <div className="flex justify-between items-center p-3 bg-white/5 rounded-xl">
                <span className="text-purple-200 text-sm">Flashlight</span>
                <span className={`text-white font-bold text-sm px-3 py-1 rounded-lg ${vision?.torch_on ? 'bg-yellow-500/30' : 'bg-gray-500/30'}`}>
                  {vision?.torch_on ? '🔦 ON' : 'OFF'}
                </span>
              </div>
              
              <div className="p-4 bg-white/5 rounded-xl">
                <span className="text-purple-200 text-sm block mb-2">Closest Obstacle</span>
                <span className="text-white font-medium text-sm">
                  {vision?.closest_obstacle || '✅ Path is clear'}
                </span>
              </div>
              
              <div className={`p-3 rounded-xl ${vision?.wall_ahead ? 'bg-red-500/30 border border-red-400/50' : 'bg-green-500/30 border border-green-400/50'}`}>
                <div className="flex items-center justify-between">
                  <span className="text-white font-medium text-sm">Wall Detection</span>
                  <span className="text-white font-bold">
                    {vision?.wall_ahead ? '🧱 WARNING' : '✅ CLEAR'}
                  </span>
                </div>
              </div>
              
              {vision && vision.detected_objects.length > 0 && (
                <div className="p-3 bg-white/5 rounded-xl">
                  <span className="text-purple-200 text-sm block mb-2">Detected Objects</span>
                  <div className="flex flex-wrap gap-2">
                    {[...new Set(vision.detected_objects)].slice(0, 5).map((obj, i) => (
                      <span key={i} className="px-2 py-1 bg-indigo-500/30 text-white text-xs rounded-lg font-medium">
                        {obj}
                      </span>
                    ))}
                  </div>
                </div>
              )}
            </div>
          </div>

          {/* Card 2: Fall Detector */}
          <div className="bg-white/10 backdrop-blur-xl border border-white/20 rounded-3xl p-6 shadow-2xl hover:shadow-red-500/20 transition-all">
            <div className="flex items-center gap-3 mb-6">
              <div className="w-10 h-10 bg-gradient-to-br from-red-500 to-pink-500 rounded-xl flex items-center justify-center">
                {icons.heart()}
              </div>
              <div>
                <h3 className="text-lg font-bold text-white">Fall Detector</h3>
                <p className="text-xs text-purple-200">
                  {controllerConnected ? 'Active monitoring' : 'Disconnected'}
                </p>
              </div>
            </div>
            
            {controllerConnected && fallData ? (
              <div className="space-y-4">
                <div className={`p-4 rounded-xl ${getFallStateColor(fallData.state)} border-2 border-white/20`}>
                  <div className="text-center">
                    <div className="text-2xl font-bold text-white mb-1">
                      {fallData.state.replace('_', ' ')}
                    </div>
                    <div className="text-white/80 text-sm">Current Status</div>
                  </div>
                </div>
                
                <div className="grid grid-cols-2 gap-3">
                  <div className="p-3 bg-white/5 rounded-xl text-center">
                    <div className="text-2xl font-bold text-white">{fallData.acceleration.toFixed(1)}</div>
                    <div className="text-xs text-purple-200 mt-1">Acceleration m/s²</div>
                  </div>
                  <div className="p-3 bg-white/5 rounded-xl text-center">
                    <div className="text-2xl font-bold text-white">{fallData.falls}</div>
                    <div className="text-xs text-purple-200 mt-1">Total Falls</div>
                  </div>
                </div>
                
                <div className="grid grid-cols-2 gap-3">
                  <div className="p-3 bg-white/5 rounded-xl">
                    <div className="text-sm text-purple-200 mb-1">Pitch</div>
                    <div className="text-lg font-bold text-white">{fallData.pitch.toFixed(1)}°</div>
                  </div>
                  <div className="p-3 bg-white/5 rounded-xl">
                    <div className="text-sm text-purple-200 mb-1">Roll</div>
                    <div className="text-lg font-bold text-white">{fallData.roll.toFixed(1)}°</div>
                  </div>
                </div>
                
                <div className="p-3 bg-white/5 rounded-xl flex items-center justify-between">
                  <span className="text-purple-200 text-sm">MPU6050 Sensor</span>
                  <span className={`px-3 py-1 rounded-lg font-bold text-sm ${fallData.mpu === 'OK' ? 'bg-green-500/30 text-green-200' : 'bg-red-500/30 text-red-200'}`}>
                    {fallData.mpu}
                  </span>
                </div>
              </div>
            ) : (
              <div className="flex flex-col items-center justify-center h-64 text-center">
                <div className="w-16 h-16 border-4 border-purple-500/30 border-t-purple-500 rounded-full animate-spin mb-4" />
                <p className="text-purple-200">Connecting to fall detector...</p>
                <p className="text-xs text-purple-300 mt-2">Check ESP32 controller at {CONTROLLER_IP}</p>
              </div>
            )}
          </div>

          {/* Card 3: Indoor Navigation */}
          <div className="bg-white/10 backdrop-blur-xl border border-white/20 rounded-3xl p-6 shadow-2xl hover:shadow-purple-500/20 transition-all">
            <div className="flex items-center gap-3 mb-6">
              <div className="w-10 h-10 bg-gradient-to-br from-purple-500 to-pink-500 rounded-xl flex items-center justify-center">
                {icons.navigation()}
              </div>
              <div>
                <h3 className="text-lg font-bold text-white">Indoor Navigation</h3>
                <p className="text-xs text-purple-200">Path guidance</p>
              </div>
            </div>
            
            {indoorNav && indoorNav.state !== 'IDLE' ? (
              <div className="space-y-4">
                <div className="p-4 bg-gradient-to-r from-purple-500/30 to-pink-500/30 rounded-xl border border-purple-400/50">
                  <div className="text-center">
                    <div className="text-xl font-bold text-white mb-1">{indoorNav.state}</div>
                    <div className="text-purple-200 text-sm">Navigation Status</div>
                  </div>
                </div>
                
                {indoorNav.destination && (
                  <div className="p-4 bg-white/5 rounded-xl">
                    <div className="text-purple-200 text-sm mb-2">Destination</div>
                    <div className="text-white font-bold text-lg">{indoorNav.destination}</div>
                  </div>
                )}
                
                <div className="grid grid-cols-2 gap-3">
                  <div className="p-3 bg-white/5 rounded-xl text-center">
                    <div className="text-lg font-bold text-white">{indoorNav.confidence}</div>
                    <div className="text-xs text-purple-200 mt-1">Confidence</div>
                  </div>
                  <div className="p-3 bg-white/5 rounded-xl text-center">
                    <div className="text-lg font-bold text-white">{indoorNav.safe_directions}</div>
                    <div className="text-xs text-purple-200 mt-1">Safe Paths</div>
                  </div>
                </div>
                
                {indoorNav.distance_remaining && (
                  <div className="p-3 bg-blue-500/30 rounded-xl border border-blue-400/50">
                    <div className="text-center">
                      <div className="text-2xl font-bold text-white">{indoorNav.distance_remaining.toFixed(1)}m</div>
                      <div className="text-blue-200 text-sm">Distance Remaining</div>
                    </div>
                  </div>
                )}
              </div>
            ) : (
              <div className="flex flex-col items-center justify-center h-64 text-center">
                <div className="w-16 h-16 bg-purple-500/20 rounded-full flex items-center justify-center mb-4">
                  {icons.navigation()}
                </div>
                <p className="text-purple-200">Navigation Idle</p>
                <p className="text-xs text-purple-300 mt-2">Awaiting destination command</p>
              </div>
            )}
          </div>

          {/* Card 4: Spatial Memory */}
          <div className="bg-white/10 backdrop-blur-xl border border-white/20 rounded-3xl p-6 shadow-2xl hover:shadow-blue-500/20 transition-all">
            <div className="flex items-center gap-3 mb-6">
              <div className="w-10 h-10 bg-gradient-to-br from-violet-500 to-purple-500 rounded-xl flex items-center justify-center">
                {icons.brain()}
              </div>
              <div>
                <h3 className="text-lg font-bold text-white">Spatial Memory</h3>
                <p className="text-xs text-purple-200">{spatialMemory.length} locations stored</p>
              </div>
            </div>
            
            {spatialMemory.length > 0 ? (
              <div className="space-y-2 max-h-64 overflow-y-auto custom-scrollbar">
                {spatialMemory.slice(0, 10).map((item, i) => (
                  <div key={i} className="p-3 bg-white/5 rounded-xl flex items-center justify-between hover:bg-white/10 transition-colors">
                    <span className="text-white font-medium text-sm">{item.name}</span>
                    <span className="text-xs px-2 py-1 bg-violet-500/30 text-violet-200 rounded-lg">
                      {item.room_id ? '🏠 Room' : '📍 Landmark'}
                    </span>
                  </div>
                ))}
              </div>
            ) : (
              <div className="flex flex-col items-center justify-center h-64 text-center">
                <div className="w-16 h-16 bg-purple-500/20 rounded-full flex items-center justify-center mb-4">
                  {icons.brain()}
                </div>
                <p className="text-purple-200">No spatial data yet</p>
                <p className="text-xs text-purple-300 mt-2">Start labeling rooms and objects</p>
              </div>
            )}
          </div>
        </div>

        {/* Activity Logs */}
        <div className="mt-6 bg-white/10 backdrop-blur-xl border border-white/20 rounded-3xl p-6 shadow-2xl">
          <div className="flex items-center justify-between mb-6">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 bg-gradient-to-br from-gray-500 to-slate-500 rounded-xl flex items-center justify-center">
                {icons.activity()}
              </div>
              <div>
                <h3 className="text-lg font-bold text-white">Activity Logs</h3>
                <p className="text-xs text-purple-200">{logs.length} events tracked</p>
              </div>
            </div>
            {logs.length > 0 && (
              <button
                onClick={() => setLogs([])}
                className="px-4 py-2 bg-white/10 hover:bg-white/20 text-white rounded-xl font-medium text-sm transition-colors"
              >
                Clear All
              </button>
            )}
          </div>
          
          <div className="space-y-2 max-h-96 overflow-y-auto custom-scrollbar">
            {logs.length === 0 ? (
              <div className="text-center py-12">
                <p className="text-purple-200">No activity yet</p>
                <p className="text-xs text-purple-300 mt-2">Events will appear here in real-time</p>
              </div>
            ) : (
              logs.map(log => (
                <div
                  key={log.id}
                  className={`p-4 rounded-xl border transition-all hover:scale-[1.01] ${
                    log.type === 'fall' ? 'bg-red-500/20 border-red-400/50' :
                    log.type === 'alert' ? 'bg-orange-500/20 border-orange-400/50' :
                    log.type === 'navigation' ? 'bg-blue-500/20 border-blue-400/50' :
                    log.type === 'speech' ? 'bg-purple-500/20 border-purple-400/50' :
                    'bg-white/5 border-white/10'
                  }`}
                >
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-xs text-purple-300 font-mono">{log.time}</span>
                    <span className={`text-xs px-2 py-1 rounded-lg font-bold ${
                      log.type === 'fall' ? 'bg-red-500/50 text-white' :
                      log.type === 'alert' ? 'bg-orange-500/50 text-white' :
                      log.type === 'navigation' ? 'bg-blue-500/50 text-white' :
                      log.type === 'speech' ? 'bg-purple-500/50 text-white' :
                      'bg-gray-500/50 text-white'
                    }`}>
                      {log.type.toUpperCase()}
                    </span>
                  </div>
                  <p className="text-white text-sm font-medium">{log.message}</p>
                </div>
              ))
            )}
          </div>
        </div>
      </div>

      {/* Footer */}
      <footer className="relative mt-8 py-6 text-center border-t border-white/10">
        <p className="text-purple-200 text-sm">SURDAS Assistive Vision System &copy; 2024</p>
        <p className="text-purple-300 text-xs mt-1">Real-time monitoring • Fall detection • Indoor navigation</p>
      </footer>
    </div>
  );
}

export default App;
