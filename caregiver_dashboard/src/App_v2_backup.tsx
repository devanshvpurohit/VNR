import { useState, useEffect, useRef } from 'react';
import './index.css';
import { 
  Eye, Heart, Navigation, Brain, Activity, MapPin, AlertTriangle, 
  Zap, Clock, Shield, Video, Settings, Bell, TrendingUp, Users,
  Power, Camera, Flashlight, Volume2, Play, Pause, Circle, Maximize2,
  Minimize2, Radio, Wifi, Battery, Cpu, HardDrive, Thermometer
} from 'lucide-react';

// ==================== INTERFACES ====================
interface VisionContext {
  mode: string;
  torch_on: boolean;
  detected_objects: string[];
  closest_obstacle: string | null;
  wall_ahead: boolean;
  fps?: number;
  frame_count?: number;
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
  timestamp?: string;
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
  type: 'speech' | 'alert' | 'system' | 'navigation' | 'fall' | 'emergency';
  message: string;
  priority?: 'low' | 'medium' | 'high' | 'critical';
}

interface Location {
  lat: number;
  lng: number;
  city: string;
  region: string;
  country: string;
}

interface SystemMetrics {
  uptime: number;
  cpu_usage?: number;
  memory_usage?: number;
  temperature?: number;
}

// ==================== CONSTANTS ====================
const API = 'http://localhost:8000';
const WS  = 'ws://localhost:8000/ws';
const CONTROLLER_IP = '192.168.4.2';
const VIDEO_FEED = 'http://localhost:8888/video_feed';

// ==================== COMPONENT ====================
function App() {
  // State Management
  const [activeTab, setActiveTab] = useState<'overview' | 'navigation' | 'analytics' | 'settings'>('overview');
  const [vision, setVision] = useState<VisionContext | null>(null);
  const [indoorNav, setIndoorNav] = useState<IndoorNavigation | null>(null);
  const [spatialMemory, setSpatialMemory] = useState<SpatialMemory[]>([]);
  const [fallData, setFallData] = useState<FallDetectorData | null>(null);
  const [logs, setLogs] = useState<LogEntry[]>([]);
  const [location, setLocation] = useState<Location | null>(null);
  const [wsState, setWsState] = useState<'connecting' | 'connected' | 'disconnected'>('connecting');
  const [controllerConnected, setControllerConnected] = useState(false);
  const [systemMetrics, setSystemMetrics] = useState<SystemMetrics>({ uptime: 0 });
  const [emergencyMode, setEmergencyMode] = useState(false);
  const [showVideo, setShowVideo] = useState(true);
  const [alertsEnabled, setAlertsEnabled] = useState(true);
  const [logFilter, setLogFilter] = useState<string>('all');
  
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const fallPollInterval = useRef<ReturnType<typeof setInterval> | null>(null);
  const uptimeInterval = useRef<ReturnType<typeof setInterval> | null>(null);
  const startTime = useRef(Date.now());

  // ==================== HELPER FUNCTIONS ====================
  const addLog = (type: LogEntry['type'], message: string, priority: LogEntry['priority'] = 'medium') => {
    const newLog: LogEntry = {
      id: Date.now() + Math.random(),
      time: new Date().toLocaleTimeString(),
      type,
      message,
      priority
    };
    
    setLogs(prev => [newLog, ...prev].slice(0, 500));
    
    // Play alert sound for critical events
    if (alertsEnabled && (priority === 'critical' || type === 'fall')) {
      playAlertSound();
    }
  };

  const playAlertSound = () => {
    // Browser notification sound
    const audio = new Audio('data:audio/wav;base64,UklGRnoGAABXQVZFZm10IBAAAAABAAEAQB8AAEAfAAABAAgAZGF0YQoGAACBhYqFbF1fdJivrJBhNjVgodDbq2EcBj+a2/LDciUFLIHO8tiJNwgZaLvt559NEAxQp+PwtmMcBjiR1/LMeSwFJHfH8N2QQAoUXrTp66hVFApGn+DyvmwhBjGH0fPTgjMGHGq670+eNUgQUKjo8bllHAU2jdT0yoQzBhphtu+kbCQJL3/L8duCMQYZaLjv0IsuCQlGn+PztGMcBj+a2/LDciUFLIHO8tiJNwgZaLvt559NEAxQp+PwtmMcBjiR1/LMeSwFJHfH8N2QQAoUXrTp66hVFApGn+DyvmwhBjGH0fPTgjMGHGq670+eNUgQUKjo8bllHAU2jdT0yoQzBhphtu+kbCQJL3/L8duCMQYZaLjv0IsuCQlGn+PztGMcBj+a2/LDciUFLIHO8tiJNwgZaLvt559NEAxQp+PwtmMcBjiR1/LMeSwFJHfH8N2QQAoUXrTp66hVFApGn+DyvmwhBjGH0fPTgjMGHGq670+eNUgQUKjo8bllHAU2jdT0yoQzBhphtu+kbCQJL3/L8duCMQYZaLjv0IsuCQ==');
    audio.play().catch(() => {});
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
      
      // Log state changes
      if (data.state === 'FALL_CONFIRMED' && prevState !== 'FALL_CONFIRMED') {
        addLog('fall', `🚨 FALL DETECTED! Total falls: ${data.falls}`, 'critical');
        setEmergencyMode(true);
      } else if (data.state === 'POSSIBLE_FALL' && prevState !== 'POSSIBLE_FALL') {
        addLog('fall', '⚠️ Possible fall detected - monitoring...', 'high');
      } else if (data.state === 'NORMAL' && prevState === 'POSSIBLE_FALL') {
        addLog('system', '✅ False alarm - user stable', 'low');
      }
    } catch {
      if (controllerConnected) {
        setControllerConnected(false);
        addLog('system', '⚠️ Fall detector disconnected', 'medium');
      }
      setFallData(null);
    }
  };

  const fetchLocation = () => {
    fetch(`${API}/location`)
      .then(r => r.json())
      .then(loc => {
        setLocation(loc);
        addLog('system', `📍 Location: ${loc.city}, ${loc.region}`, 'low');
      })
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
      addLog('system', '✅ Dashboard connected to SURDAS', 'low');
      fetchLocation();
    };

    ws.onclose = () => {
      setWsState('disconnected');
      addLog('system', '❌ Connection lost - reconnecting...', 'medium');
      reconnectTimer.current = setTimeout(connect, 3000);
    };

    ws.onerror = () => ws.close();

    ws.onmessage = (event) => {
      try {
        const parsed = JSON.parse(event.data);
        
        if (parsed.type === 'vision') {
          setVision(parsed.data as VisionContext);
        } else if (parsed.type === 'speech') {
          addLog('speech', `🗣️ ${parsed.data.text}`, 'low');
        } else if (parsed.type === 'indoor_navigation') {
          const navData = parsed.data as IndoorNavigation;
          setIndoorNav(navData);
          
          if (navData.state === 'SAFETY_HOLD' && navData.hold_reason) {
            addLog('navigation', `⚠️ Safety hold: ${navData.hold_reason}`, 'high');
          } else if (navData.state === 'ARRIVED') {
            addLog('navigation', `✅ Destination reached: ${navData.destination}`, 'medium');
          }
        } else if (parsed.type === 'room_labeled') {
          addLog('system', `🏠 Room labeled: ${parsed.data.name}`, 'low');
          setSpatialMemory(prev => [...prev, { ...parsed.data, timestamp: new Date().toISOString() }]);
        } else if (parsed.type === 'landmark_labeled') {
          addLog('system', `📍 Landmark saved: ${parsed.data.name}`, 'low');
          setSpatialMemory(prev => [...prev, { ...parsed.data, timestamp: new Date().toISOString() }]);
        } else if (parsed.type === 'alert') {
          addLog('alert', parsed.data.message, parsed.data.priority || 'medium');
        } else if (parsed.type === 'metrics') {
          setSystemMetrics(parsed.data);
        }
      } catch (e) {
        console.error('WS message parse error:', e);
      }
    };
  };

  // ==================== EFFECTS ====================
  useEffect(() => {
    connect();
    fetchFallData();
    fallPollInterval.current = setInterval(fetchFallData, 200);
    uptimeInterval.current = setInterval(() => {
      setSystemMetrics(prev => ({
        ...prev,
        uptime: Math.floor((Date.now() - startTime.current) / 1000)
      }));
    }, 1000);
    
    return () => {
      if (reconnectTimer.current) clearTimeout(reconnectTimer.current);
      if (fallPollInterval.current) clearInterval(fallPollInterval.current);
      if (uptimeInterval.current) clearInterval(uptimeInterval.current);
      if (wsRef.current) { 
        wsRef.current.onclose = null; 
        wsRef.current.close(); 
      }
    };
  }, []);

  // ==================== UI HELPERS ====================
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

  const formatUptime = (seconds: number) => {
    const h = Math.floor(seconds / 3600);
    const m = Math.floor((seconds % 3600) / 60);
    const s = seconds % 60;
    return `${h}h ${m}m ${s}s`;
  };

  const getConfidenceColor = (confidence: string) => {
    if (confidence === 'HIGH') return 'text-emerald-400';
    if (confidence === 'MEDIUM') return 'text-amber-400';
    return 'text-red-400';
  };

  const filteredLogs = logs.filter(log => {
    if (logFilter === 'all') return true;
    return log.type === logFilter;
  });

  // ==================== EMERGENCY BANNER ====================
  const renderEmergencyBanner = () => {
    if (!emergencyMode && fallData?.state !== 'FALL_CONFIRMED') return null;

    return (
      <div className="mb-6 bg-gradient-to-r from-red-600 via-red-500 to-red-600 border-2 border-red-300 rounded-2xl p-6 shadow-2xl shadow-red-500/50 animate-pulse">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-4">
            <div className="w-16 h-16 bg-white rounded-full flex items-center justify-center animate-bounce">
              <AlertTriangle className="w-10 h-10 text-red-600" />
            </div>
            <div className="flex-1">
              <h2 className="text-2xl font-bold text-white mb-1">🚨 EMERGENCY: FALL DETECTED</h2>
              <p className="text-red-100">Immediate attention required! User may need assistance.</p>
            </div>
          </div>
          <div className="text-right">
            <div className="text-5xl font-bold text-white mb-1">{fallData?.falls || 0}</div>
            <div className="text-sm text-red-100">Total Falls</div>
            <button
              onClick={() => setEmergencyMode(false)}
              className="mt-3 px-4 py-2 bg-white/20 hover:bg-white/30 text-white rounded-lg font-medium text-sm transition-all"
            >
              Acknowledge
            </button>
          </div>
        </div>
      </div>
    );
  };

  // ==================== NAVIGATION TABS ====================
  const renderTabs = () => (
    <div className="flex gap-2 mb-6 bg-white/5 backdrop-blur-xl rounded-2xl p-2 border border-white/10">
      {[
        { id: 'overview', label: 'Overview', icon: Activity },
        { id: 'navigation', label: 'Navigation', icon: Navigation },
        { id: 'analytics', label: 'Analytics', icon: TrendingUp },
        { id: 'settings', label: 'Settings', icon: Settings },
      ].map(tab => (
        <button
          key={tab.id}
          onClick={() => setActiveTab(tab.id as any)}
          className={`flex-1 flex items-center justify-center gap-2 px-6 py-3 rounded-xl font-medium transition-all ${
            activeTab === tab.id
              ? 'bg-gradient-to-r from-purple-500 to-pink-500 text-white shadow-lg'
              : 'text-purple-200 hover:bg-white/10'
          }`}
        >
          <tab.icon className="w-5 h-5" />
          {tab.label}
        </button>
      ))}
    </div>
  );

  // ==================== OVERVIEW TAB ====================
  const renderOverview = () => (
    <>
      {/* Quick Stats */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
        {/* System Status */}
        <div className="bg-gradient-to-br from-blue-500/20 to-cyan-500/20 backdrop-blur-xl border border-blue-400/30 rounded-2xl p-6">
          <div className="flex items-center justify-between mb-4">
            <div className="w-12 h-12 bg-blue-500/30 rounded-xl flex items-center justify-center">
              <Power className="w-6 h-6 text-blue-300" />
            </div>
            <div className={`w-3 h-3 rounded-full ${getStatusColor()} animate-pulse`} />
          </div>
          <div className="text-2xl font-bold text-white mb-1">
            {wsState === 'connected' ? 'Online' : 'Offline'}
          </div>
          <div className="text-sm text-blue-200">System Status</div>
        </div>

        {/* Uptime */}
        <div className="bg-gradient-to-br from-purple-500/20 to-pink-500/20 backdrop-blur-xl border border-purple-400/30 rounded-2xl p-6">
          <div className="flex items-center justify-between mb-4">
            <div className="w-12 h-12 bg-purple-500/30 rounded-xl flex items-center justify-center">
              <Clock className="w-6 h-6 text-purple-300" />
            </div>
          </div>
          <div className="text-2xl font-bold text-white mb-1">
            {formatUptime(systemMetrics.uptime).split(' ')[0]}
          </div>
          <div className="text-sm text-purple-200">System Uptime</div>
        </div>

        {/* Objects Detected */}
        <div className="bg-gradient-to-br from-emerald-500/20 to-green-500/20 backdrop-blur-xl border border-emerald-400/30 rounded-2xl p-6">
          <div className="flex items-center justify-between mb-4">
            <div className="w-12 h-12 bg-emerald-500/30 rounded-xl flex items-center justify-center">
              <Eye className="w-6 h-6 text-emerald-300" />
            </div>
          </div>
          <div className="text-2xl font-bold text-white mb-1">
            {vision?.detected_objects?.length || 0}
          </div>
          <div className="text-sm text-emerald-200">Objects Detected</div>
        </div>

        {/* Memory Locations */}
        <div className="bg-gradient-to-br from-violet-500/20 to-purple-500/20 backdrop-blur-xl border border-violet-400/30 rounded-2xl p-6">
          <div className="flex items-center justify-between mb-4">
            <div className="w-12 h-12 bg-violet-500/30 rounded-xl flex items-center justify-center">
              <Brain className="w-6 h-6 text-violet-300" />
            </div>
          </div>
          <div className="text-2xl font-bold text-white mb-1">
            {spatialMemory.length}
          </div>
          <div className="text-sm text-violet-200">Memory Locations</div>
        </div>
      </div>

      {/* Main Content Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left Column - Video Feed */}
        <div className="lg:col-span-2 space-y-6">
          {/* Live Video Feed */}
          {showVideo && (
            <div className="bg-white/10 backdrop-blur-xl border border-white/20 rounded-3xl p-6 shadow-2xl">
              <div className="flex items-center justify-between mb-4">
                <div className="flex items-center gap-3">
                  <div className="w-10 h-10 bg-gradient-to-br from-red-500 to-pink-500 rounded-xl flex items-center justify-center">
                    <Video className="w-5 h-5 text-white" />
                  </div>
                  <div>
                    <h3 className="text-lg font-bold text-white">Live Camera Feed</h3>
                    <p className="text-xs text-purple-200">Real-time vision system</p>
                  </div>
                </div>
                <button
                  onClick={() => setShowVideo(!showVideo)}
                  className="px-3 py-1.5 bg-white/10 hover:bg-white/20 text-white rounded-lg text-sm transition-all"
                >
                  Hide
                </button>
              </div>
              <div className="relative bg-black/50 rounded-2xl overflow-hidden aspect-video">
                <img
                  src={VIDEO_FEED}
                  alt="Live camera feed"
                  className="w-full h-full object-contain"
                  onError={(e) => {
                    e.currentTarget.src = '';
                    e.currentTarget.alt = 'Camera feed unavailable';
                  }}
                />
                <div className="absolute top-4 right-4 flex items-center gap-2 bg-black/50 backdrop-blur-sm px-3 py-1.5 rounded-lg">
                  <Circle className="w-2 h-2 text-red-500 fill-red-500 animate-pulse" />
                  <span className="text-white text-sm font-medium">LIVE</span>
                </div>
              </div>
            </div>
          )}

          {/* Vision System Details */}
          <div className="bg-white/10 backdrop-blur-xl border border-white/20 rounded-3xl p-6 shadow-2xl">
            <div className="flex items-center gap-3 mb-6">
              <div className="w-10 h-10 bg-gradient-to-br from-blue-500 to-cyan-500 rounded-xl flex items-center justify-center">
                <Eye className="w-5 h-5 text-white" />
              </div>
              <div>
                <h3 className="text-lg font-bold text-white">Vision System</h3>
                <p className="text-xs text-purple-200">Object detection & depth analysis</p>
              </div>
            </div>
            
            <div className="grid grid-cols-2 gap-4">
              <div className="p-4 bg-white/5 rounded-xl">
                <div className="text-purple-200 text-sm mb-2">Mode</div>
                <div className="text-white font-bold text-lg">{vision?.mode || 'IDLE'}</div>
              </div>
              
              <div className="p-4 bg-white/5 rounded-xl">
                <div className="text-purple-200 text-sm mb-2">Flashlight</div>
                <div className="flex items-center gap-2">
                  <Flashlight className={`w-5 h-5 ${vision?.torch_on ? 'text-yellow-400' : 'text-gray-400'}`} />
                  <span className="text-white font-bold">{vision?.torch_on ? 'ON' : 'OFF'}</span>
                </div>
              </div>
              
              <div className={`col-span-2 p-4 rounded-xl border ${vision?.wall_ahead ? 'bg-red-500/20 border-red-400/50' : 'bg-green-500/20 border-green-400/50'}`}>
                <div className="text-white font-medium text-sm mb-1">Obstacle Detection</div>
                <div className="text-white text-lg font-bold">
                  {vision?.wall_ahead ? '🧱 Wall Ahead' : '✅ Path Clear'}
                </div>
                {vision?.closest_obstacle && (
                  <div className="text-white/80 text-sm mt-2">
                    Closest: {vision.closest_obstacle}
                  </div>
                )}
              </div>
              
              {vision && vision.detected_objects.length > 0 && (
                <div className="col-span-2 p-4 bg-white/5 rounded-xl">
                  <div className="text-purple-200 text-sm mb-3">Detected Objects</div>
                  <div className="flex flex-wrap gap-2">
                    {[...new Set(vision.detected_objects)].slice(0, 10).map((obj, i) => (
                      <span key={i} className="px-3 py-1.5 bg-indigo-500/30 text-white text-sm rounded-lg font-medium">
                        {obj}
                      </span>
                    ))}
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>

        {/* Right Column */}
        <div className="space-y-6">
          {/* Fall Detector */}
          <div className="bg-white/10 backdrop-blur-xl border border-white/20 rounded-3xl p-6 shadow-2xl">
            <div className="flex items-center gap-3 mb-6">
              <div className="w-10 h-10 bg-gradient-to-br from-red-500 to-pink-500 rounded-xl flex items-center justify-center">
                <Heart className="w-5 h-5 text-white" />
              </div>
              <div>
                <h3 className="text-lg font-bold text-white">Fall Detector</h3>
                <p className="text-xs text-purple-200">
                  {controllerConnected ? 'Active' : 'Disconnected'}
                </p>
              </div>
            </div>
            
            {controllerConnected && fallData ? (
              <div className="space-y-4">
                <div className={`p-4 rounded-xl ${getFallStateColor(fallData.state)} border-2 border-white/20`}>
                  <div className="text-center">
                    <div className="text-xl font-bold text-white mb-1">
                      {fallData.state.replace('_', ' ')}
                    </div>
                    <div className="text-white/80 text-sm">Current Status</div>
                  </div>
                </div>
                
                <div className="grid grid-cols-2 gap-3">
                  <div className="p-3 bg-white/5 rounded-xl text-center">
                    <div className="text-xl font-bold text-white">{fallData.acceleration.toFixed(1)}</div>
                    <div className="text-xs text-purple-200 mt-1">Acceleration</div>
                  </div>
                  <div className="p-3 bg-white/5 rounded-xl text-center">
                    <div className="text-xl font-bold text-white">{fallData.falls}</div>
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
              </div>
            ) : (
              <div className="flex flex-col items-center justify-center h-48 text-center">
                <div className="w-12 h-12 border-4 border-purple-500/30 border-t-purple-500 rounded-full animate-spin mb-3" />
                <p className="text-purple-200 text-sm">Connecting...</p>
              </div>
            )}
          </div>

          {/* Indoor Navigation */}
          <div className="bg-white/10 backdrop-blur-xl border border-white/20 rounded-3xl p-6 shadow-2xl">
            <div className="flex items-center gap-3 mb-6">
              <div className="w-10 h-10 bg-gradient-to-br from-purple-500 to-pink-500 rounded-xl flex items-center justify-center">
                <Navigation className="w-5 h-5 text-white" />
              </div>
              <div>
                <h3 className="text-lg font-bold text-white">Navigation</h3>
                <p className="text-xs text-purple-200">Indoor guidance</p>
              </div>
            </div>
            
            {indoorNav && indoorNav.state !== 'IDLE' ? (
              <div className="space-y-4">
                <div className="p-4 bg-gradient-to-r from-purple-500/30 to-pink-500/30 rounded-xl border border-purple-400/50">
                  <div className="text-center">
                    <div className="text-lg font-bold text-white mb-1">{indoorNav.state}</div>
                    <div className="text-purple-200 text-sm">Status</div>
                  </div>
                </div>
                
                {indoorNav.destination && (
                  <div className="p-4 bg-white/5 rounded-xl">
                    <div className="text-purple-200 text-sm mb-2">Destination</div>
                    <div className="text-white font-bold">{indoorNav.destination}</div>
                  </div>
                )}
                
                <div className="grid grid-cols-2 gap-3">
                  <div className="p-3 bg-white/5 rounded-xl text-center">
                    <div className={`text-lg font-bold ${getConfidenceColor(indoorNav.confidence)}`}>
                      {indoorNav.confidence}
                    </div>
                    <div className="text-xs text-purple-200 mt-1">Confidence</div>
                  </div>
                  <div className="p-3 bg-white/5 rounded-xl text-center">
                    <div className="text-lg font-bold text-white">{indoorNav.safe_directions}</div>
                    <div className="text-xs text-purple-200 mt-1">Safe Paths</div>
                  </div>
                </div>
                
                {indoorNav.distance_remaining !== null && (
                  <div className="p-3 bg-blue-500/30 rounded-xl border border-blue-400/50 text-center">
                    <div className="text-2xl font-bold text-white">{indoorNav.distance_remaining.toFixed(1)}m</div>
                    <div className="text-blue-200 text-sm">Remaining</div>
                  </div>
                )}
              </div>
            ) : (
              <div className="flex flex-col items-center justify-center h-48 text-center">
                <Navigation className="w-12 h-12 text-purple-400/50 mb-3" />
                <p className="text-purple-200 text-sm">Navigation Idle</p>
              </div>
            )}
          </div>

          {/* Spatial Memory */}
          <div className="bg-white/10 backdrop-blur-xl border border-white/20 rounded-3xl p-6 shadow-2xl">
            <div className="flex items-center gap-3 mb-4">
              <div className="w-10 h-10 bg-gradient-to-br from-violet-500 to-purple-500 rounded-xl flex items-center justify-center">
                <Brain className="w-5 h-5 text-white" />
              </div>
              <div>
                <h3 className="text-lg font-bold text-white">Spatial Memory</h3>
                <p className="text-xs text-purple-200">{spatialMemory.length} locations</p>
              </div>
            </div>
            
            {spatialMemory.length > 0 ? (
              <div className="space-y-2 max-h-64 overflow-y-auto custom-scrollbar">
                {spatialMemory.slice(0, 10).map((item, i) => (
                  <div key={i} className="p-3 bg-white/5 rounded-xl flex items-center justify-between hover:bg-white/10 transition-colors">
                    <span className="text-white font-medium text-sm">{item.name}</span>
                    <span className="text-xs px-2 py-1 bg-violet-500/30 text-violet-200 rounded-lg">
                      {item.room_id ? '🏠' : '📍'}
                    </span>
                  </div>
                ))}
              </div>
            ) : (
              <div className="flex flex-col items-center justify-center h-32 text-center">
                <Brain className="w-12 h-12 text-purple-400/50 mb-3" />
                <p className="text-purple-200 text-sm">No locations stored</p>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Activity Logs */}
      <div className="mt-6 bg-white/10 backdrop-blur-xl border border-white/20 rounded-3xl p-6 shadow-2xl">
        <div className="flex items-center justify-between mb-6">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 bg-gradient-to-br from-gray-500 to-slate-500 rounded-xl flex items-center justify-center">
              <Activity className="w-5 h-5 text-white" />
            </div>
            <div>
              <h3 className="text-lg font-bold text-white">Activity Logs</h3>
              <p className="text-xs text-purple-200">{filteredLogs.length} events</p>
            </div>
          </div>
          <div className="flex items-center gap-3">
            <select
              value={logFilter}
              onChange={(e) => setLogFilter(e.target.value)}
              className="px-4 py-2 bg-white/10 border border-white/20 text-white rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-purple-500"
            >
              <option value="all">All Events</option>
              <option value="speech">Speech</option>
              <option value="navigation">Navigation</option>
              <option value="fall">Falls</option>
              <option value="alert">Alerts</option>
              <option value="system">System</option>
            </select>
            {logs.length > 0 && (
              <button
                onClick={() => setLogs([])}
                className="px-4 py-2 bg-white/10 hover:bg-white/20 text-white rounded-xl font-medium text-sm transition-colors"
              >
                Clear All
              </button>
            )}
          </div>
        </div>
        
        <div className="space-y-2 max-h-96 overflow-y-auto custom-scrollbar">
          {filteredLogs.length === 0 ? (
            <div className="text-center py-12">
              <Activity className="w-12 h-12 text-purple-400/50 mx-auto mb-3" />
              <p className="text-purple-200">No activity yet</p>
            </div>
          ) : (
            filteredLogs.map(log => (
              <div
                key={log.id}
                className={`p-4 rounded-xl border transition-all hover:scale-[1.01] ${
                  log.priority === 'critical' || log.type === 'fall' ? 'bg-red-500/20 border-red-400/50' :
                  log.priority === 'high' || log.type === 'alert' ? 'bg-orange-500/20 border-orange-400/50' :
                  log.type === 'navigation' ? 'bg-blue-500/20 border-blue-400/50' :
                  log.type === 'speech' ? 'bg-purple-500/20 border-purple-400/50' :
                  'bg-white/5 border-white/10'
                }`}
              >
                <div className="flex items-center justify-between mb-2">
                  <span className="text-xs text-purple-300 font-mono">{log.time}</span>
                  <span className={`text-xs px-2 py-1 rounded-lg font-bold ${
                    log.priority === 'critical' || log.type === 'fall' ? 'bg-red-500/50 text-white' :
                    log.priority === 'high' || log.type === 'alert' ? 'bg-orange-500/50 text-white' :
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
    </>
  );

  // ==================== NAVIGATION TAB ====================
  const renderNavigationTab = () => (
    <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
      <div className="bg-white/10 backdrop-blur-xl border border-white/20 rounded-3xl p-6 shadow-2xl">
        <h3 className="text-xl font-bold text-white mb-4">Navigation Map</h3>
        <div className="bg-slate-800 rounded-2xl h-96 flex items-center justify-center">
          <div className="text-center">
            <MapPin className="w-16 h-16 text-purple-400 mx-auto mb-4" />
            <p className="text-purple-200">Map visualization</p>
            <p className="text-sm text-purple-300 mt-2">
              {location ? `${location.city}, ${location.region}` : 'Loading location...'}
            </p>
          </div>
        </div>
      </div>
      
      <div className="bg-white/10 backdrop-blur-xl border border-white/20 rounded-3xl p-6 shadow-2xl">
        <h3 className="text-xl font-bold text-white mb-4">Route History</h3>
        <div className="space-y-3">
          <p className="text-purple-200 text-sm">Recent navigation sessions will appear here</p>
        </div>
      </div>
    </div>
  );

  // ==================== ANALYTICS TAB ====================
  const renderAnalyticsTab = () => (
    <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
      <div className="bg-white/10 backdrop-blur-xl border border-white/20 rounded-3xl p-6 shadow-2xl">
        <h3 className="text-xl font-bold text-white mb-4">Daily Activity</h3>
        <div className="text-purple-200 text-sm">Analytics charts will appear here</div>
      </div>
      
      <div className="bg-white/10 backdrop-blur-xl border border-white/20 rounded-3xl p-6 shadow-2xl">
        <h3 className="text-xl font-bold text-white mb-4">System Health</h3>
        <div className="space-y-4">
          <div className="p-4 bg-white/5 rounded-xl">
            <div className="flex justify-between items-center">
              <span className="text-purple-200">Uptime</span>
              <span className="text-white font-bold">{formatUptime(systemMetrics.uptime)}</span>
            </div>
          </div>
          <div className="p-4 bg-white/5 rounded-xl">
            <div className="flex justify-between items-center">
              <span className="text-purple-200">Total Events</span>
              <span className="text-white font-bold">{logs.length}</span>
            </div>
          </div>
          <div className="p-4 bg-white/5 rounded-xl">
            <div className="flex justify-between items-center">
              <span className="text-purple-200">Fall Incidents</span>
              <span className="text-white font-bold">{fallData?.falls || 0}</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );

  // ==================== SETTINGS TAB ====================
  const renderSettingsTab = () => (
    <div className="max-w-2xl mx-auto">
      <div className="bg-white/10 backdrop-blur-xl border border-white/20 rounded-3xl p-6 shadow-2xl">
        <h3 className="text-xl font-bold text-white mb-6">Dashboard Settings</h3>
        
        <div className="space-y-4">
          <div className="flex items-center justify-between p-4 bg-white/5 rounded-xl">
            <div>
              <div className="text-white font-medium">Show Video Feed</div>
              <div className="text-sm text-purple-200">Display live camera stream</div>
            </div>
            <button
              onClick={() => setShowVideo(!showVideo)}
              className={`w-14 h-7 rounded-full transition-colors ${showVideo ? 'bg-green-500' : 'bg-gray-600'}`}
            >
              <div className={`w-5 h-5 bg-white rounded-full transition-transform ${showVideo ? 'translate-x-8' : 'translate-x-1'}`} />
            </button>
          </div>
          
          <div className="flex items-center justify-between p-4 bg-white/5 rounded-xl">
            <div>
              <div className="text-white font-medium">Alert Sounds</div>
              <div className="text-sm text-purple-200">Play audio for critical events</div>
            </div>
            <button
              onClick={() => setAlertsEnabled(!alertsEnabled)}
              className={`w-14 h-7 rounded-full transition-colors ${alertsEnabled ? 'bg-green-500' : 'bg-gray-600'}`}
            >
              <div className={`w-5 h-5 bg-white rounded-full transition-transform ${alertsEnabled ? 'translate-x-8' : 'translate-x-1'}`} />
            </button>
          </div>
          
          <div className="p-4 bg-white/5 rounded-xl">
            <div className="text-white font-medium mb-3">Connection Settings</div>
            <div className="space-y-2 text-sm">
              <div className="flex justify-between">
                <span className="text-purple-200">API Server:</span>
                <span className="text-white font-mono">{API}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-purple-200">WebSocket:</span>
                <span className="text-white font-mono">{WS}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-purple-200">Controller:</span>
                <span className="text-white font-mono">{CONTROLLER_IP}</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );

  // ==================== MAIN RENDER ====================
  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-900 via-purple-900 to-slate-900">
      {/* Animated Background */}
      <div className="fixed inset-0 overflow-hidden pointer-events-none">
        <div className="absolute top-1/4 left-1/4 w-96 h-96 bg-purple-500/10 rounded-full blur-3xl animate-pulse" />
        <div className="absolute bottom-1/4 right-1/4 w-96 h-96 bg-blue-500/10 rounded-full blur-3xl animate-pulse" style={{ animationDelay: '1s' }} />
      </div>

      {/* Header */}
      <header className="relative bg-black/20 backdrop-blur-xl border-b border-white/10 sticky top-0 z-50">
        <div className="max-w-[1920px] mx-auto px-6 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-4">
              <div className="w-14 h-14 rounded-2xl bg-gradient-to-br from-blue-500 to-purple-600 flex items-center justify-center shadow-lg shadow-purple-500/50">
                <Shield className="w-8 h-8 text-white" />
              </div>
              <div>
                <h1 className="text-3xl font-bold text-white">SURDAS</h1>
                <p className="text-sm text-purple-200">Advanced Caregiver Dashboard v2.0</p>
              </div>
            </div>
            
            <div className="flex items-center gap-4">
              {/* System Status */}
              <div className="flex items-center gap-2 px-4 py-2 bg-white/10 backdrop-blur-md rounded-full">
                <div className={`w-3 h-3 rounded-full ${getStatusColor()} animate-pulse`} />
                <span className="text-white font-medium text-sm">
                  {wsState === 'connected' ? 'Online' : wsState === 'connecting' ? 'Connecting...' : 'Offline'}
                </span>
              </div>
              
              {/* Fall Detector Status */}
              {controllerConnected && (
                <div className="flex items-center gap-2 px-4 py-2 bg-white/10 backdrop-blur-md rounded-full">
                  <Heart className="w-4 h-4 text-red-400" />
                  <span className="text-white font-medium text-sm">Fall Detector</span>
                </div>
              )}
              
              {/* Location */}
              {location && (
                <div className="flex items-center gap-2 px-4 py-2 bg-white/10 backdrop-blur-md rounded-full">
                  <MapPin className="w-4 h-4 text-blue-400" />
                  <span className="text-white font-medium text-sm">{location.city}</span>
                </div>
              )}
              
              {/* Notifications */}
              <button className="relative p-2 bg-white/10 backdrop-blur-md rounded-full hover:bg-white/20 transition-colors">
                <Bell className="w-5 h-5 text-white" />
                {logs.filter(l => l.priority === 'critical' || l.priority === 'high').length > 0 && (
                  <div className="absolute top-0 right-0 w-3 h-3 bg-red-500 rounded-full animate-pulse" />
                )}
              </button>
            </div>
          </div>
        </div>
      </header>

      {/* Main Dashboard */}
      <div className="relative max-w-[1920px] mx-auto px-6 py-8">
        {renderEmergencyBanner()}
        {renderTabs()}
        
        {activeTab === 'overview' && renderOverview()}
        {activeTab === 'navigation' && renderNavigationTab()}
        {activeTab === 'analytics' && renderAnalyticsTab()}
        {activeTab === 'settings' && renderSettingsTab()}
      </div>

      {/* Footer */}
      <footer className="relative mt-8 py-6 text-center border-t border-white/10">
        <p className="text-purple-200 text-sm">SURDAS Assistive Vision System &copy; 2024</p>
        <p className="text-purple-300 text-xs mt-1">
          Real-time monitoring • Fall detection • Indoor navigation • Spatial awareness
        </p>
      </footer>
    </div>
  );
}

export default App;
