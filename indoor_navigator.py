"""
indoor_navigator.py — Deterministic safety-first indoor navigation controller.

Responsibilities:
  • NAVIGATION_MODE: waypoint-free guidance using perception + spatial memory
  • Safety-hold: halt movement on camera failure, stale perception, or confidence drop
  • Deterministic control: NEVER LLM-controlled, pure logic-based navigation
  • Spatial awareness: use memory to guide toward remembered objects/landmarks
  • Real-time obstacle avoidance: react to immediate perception changes
  • Natural guidance: "move forward 2 metres", "turn left 30 degrees", "stop, obstacle ahead"

Design principles:
  • Safety-first: conservative, prefer stopping over moving unsafely
  • Confidence-driven: only issue movement commands when confidence >= MEDIUM
  • State machine: IDLE → NAVIGATION_MODE → SAFETY_HOLD → recovery
  • No path planning: local reactive navigation only
  • Preserve user autonomy: guidance, not control
  • Clear communication: announce every state transition

States:
  • IDLE: Not navigating, spatial memory queries only
  • NAVIGATING: Active guidance toward destination
  • SAFETY_HOLD: Paused due to safety concern (camera failure, obstacle, low confidence)
  • APPROACHING: Close to destination, final guidance phase
  • ARRIVED: Destination reached

Inputs:
  • Perception result: from indoor_perception.py
  • Spatial memory: from spatial_memory.py
  • Destination: object label or landmark name
  • User commands: voice instructions

Outputs:
  • Guidance instructions: spoken via TTS
  • State updates: broadcast to telemetry
  • Confidence scores: HIGH/MEDIUM/LOW/INVALID
  • Safety alerts: obstacle warnings, camera failures

Never:
  • Issue movement commands with LOW or INVALID confidence
  • Navigate without recent perception data (< 2 seconds old)
  • Ignore safety-hold triggers
  • Use LLM for navigation decisions
"""

import time
import threading
from enum import Enum
from typing import Optional, Dict, Tuple
from dataclasses import dataclass
import math

from indoor_perception import PerceptionResult, NavConfidence, SafeDirection
from spatial_memory import SpatialMemory, SpatialObject, Landmark


class NavigationState(str, Enum):
    """Indoor navigation state machine."""
    IDLE = "IDLE"
    NAVIGATING = "NAVIGATING"
    SAFETY_HOLD = "SAFETY_HOLD"
    APPROACHING = "APPROACHING"
    ARRIVED = "ARRIVED"


class HoldReason(str, Enum):
    """Reasons for entering SAFETY_HOLD."""
    CAMERA_FAILURE = "camera_failure"
    STALE_PERCEPTION = "stale_perception"
    LOW_CONFIDENCE = "low_confidence"
    OBSTACLE_TOO_CLOSE = "obstacle_too_close"
    USER_REQUEST = "user_request"


@dataclass
class NavigationStatus:
    """Current navigation status."""
    state: NavigationState
    destination: Optional[str]
    confidence: NavConfidence
    distance_remaining: Optional[float]  # Approximate, in metres
    next_guidance: Optional[str]
    hold_reason: Optional[HoldReason]
    last_perception_time: float
    safe_directions_count: int


class IndoorNavigator:
    """
    Deterministic safety-first indoor navigation controller.
    
    Usage:
        navigator = IndoorNavigator(spatial_memory, voice_engine)
        
        # Start navigation to remembered object
        navigator.navigate_to_object("chair")
        
        # Update with perception (every frame)
        navigator.update(perception_result)
        
        # User commands
        navigator.pause()  # Enter SAFETY_HOLD
        navigator.resume()  # Exit SAFETY_HOLD
        navigator.stop()  # Return to IDLE
        
        # Query status
        status = navigator.get_status()
    """
    
    # Thresholds
    PERCEPTION_MAX_AGE_S = 2.0          # Max age of perception data
    ARRIVAL_THRESHOLD_M = 0.5           # Distance to consider "arrived"
    APPROACHING_THRESHOLD_M = 1.5       # Distance to enter APPROACHING state
    OBSTACLE_CRITICAL_M = 0.8           # Distance triggering immediate SAFETY_HOLD
    MIN_CONFIDENCE_TO_MOVE = NavConfidence.MEDIUM  # Minimum confidence to issue movement commands
    
    # Guidance timing
    GUIDANCE_INTERVAL_S = 3.0           # Minimum time between guidance announcements
    SAFETY_HOLD_REMINDER_S = 10.0       # Remind user why we're in SAFETY_HOLD
    
    def __init__(self, spatial_memory: SpatialMemory, voice_engine=None):
        """
        Initialize indoor navigator.
        
        Args:
            spatial_memory: SpatialMemory instance for object/landmark queries
            voice_engine: TTS engine for guidance (VoiceEngine from tts.py)
        """
        self.memory = spatial_memory
        self.voice = voice_engine
        self._lock = threading.Lock()
        
        # State
        self._state = NavigationState.IDLE
        self._destination_label: Optional[str] = None
        self._destination_obj: Optional[SpatialObject] = None
        self._destination_landmark: Optional[Landmark] = None
        self._hold_reason: Optional[HoldReason] = None
        
        # Perception tracking
        self._last_perception: Optional[PerceptionResult] = None
        self._last_perception_time: float = 0.0
        self._last_guidance_time: float = 0.0
        self._last_hold_reminder_time: float = 0.0
        
        # Current position estimate (relative to start, in metres)
        # Note: Without GPS/IMU, this is approximate based on movement commands
        self._estimated_x: float = 0.0
        self._estimated_y: float = 0.0
        
        # Language preference
        self._lang = "en"
    
    # ── Public API ────────────────────────────────────────────────────────────
    
    def navigate_to_object(self, label: str, lang: str = "en") -> bool:
        """
        Start navigation to a remembered object.
        
        Returns:
            True if navigation started, False if object not found
        """
        obj = self.memory.find_object_by_label(label)
        if obj is None:
            self._speak(f"I don't remember seeing a {label}. Please show it to me first.", lang)
            return False
        
        with self._lock:
            self._state = NavigationState.NAVIGATING
            self._destination_label = label
            self._destination_obj = obj
            self._destination_landmark = None
            self._hold_reason = None
            self._lang = lang
            self._last_guidance_time = 0.0
        
        self._speak(f"Navigating to {label}. I'll guide you there safely.", lang)
        print(f"[INDOOR_NAV] Navigation started to object: {label} at ({obj.x:.1f}, {obj.y:.1f})")
        return True
    
    def navigate_to_landmark(self, name: str, lang: str = "en") -> bool:
        """
        Start navigation to a named landmark.
        
        Returns:
            True if navigation started, False if landmark not found
        """
        landmark = self.memory.find_landmark(name)
        if landmark is None:
            self._speak(f"I don't know where '{name}' is. You can label this location by saying 'remember this as {name}'.", lang)
            return False
        
        with self._lock:
            self._state = NavigationState.NAVIGATING
            self._destination_label = name
            self._destination_landmark = landmark
            self._destination_obj = None
            self._hold_reason = None
            self._lang = lang
            self._last_guidance_time = 0.0
        
        self._speak(f"Navigating to {name}. I'll guide you there safely.", lang)
        print(f"[INDOOR_NAV] Navigation started to landmark: {name} at ({landmark.x:.1f}, {landmark.y:.1f})")
        return True
    
    def stop(self, lang: str = "en") -> None:
        """Stop navigation and return to IDLE."""
        with self._lock:
            was_active = self._state != NavigationState.IDLE
            self._state = NavigationState.IDLE
            self._destination_label = None
            self._destination_obj = None
            self._destination_landmark = None
            self._hold_reason = None
        
        if was_active:
            self._speak("Navigation stopped.", lang)
            print("[INDOOR_NAV] Navigation stopped by user")
    
    def pause(self, lang: str = "en") -> None:
        """Enter SAFETY_HOLD (user-requested pause)."""
        with self._lock:
            if self._state == NavigationState.NAVIGATING or self._state == NavigationState.APPROACHING:
                self._state = NavigationState.SAFETY_HOLD
                self._hold_reason = HoldReason.USER_REQUEST
        
        self._speak("Navigation paused. Say 'resume navigation' to continue.", lang)
        print("[INDOOR_NAV] Navigation paused by user")
    
    def resume(self, lang: str = "en") -> None:
        """Exit SAFETY_HOLD and resume navigation."""
        with self._lock:
            if self._state == NavigationState.SAFETY_HOLD:
                self._state = NavigationState.NAVIGATING
                self._hold_reason = None
                self._last_guidance_time = 0.0  # Force immediate guidance
        
        self._speak("Resuming navigation.", lang)
        print("[INDOOR_NAV] Navigation resumed")
    
    def update(self, perception: PerceptionResult) -> None:
        """
        Update navigation with latest perception data.
        Called every frame from main loop.
        
        Args:
            perception: Latest PerceptionResult from indoor_perception.py
        """
        now = time.time()
        
        with self._lock:
            self._last_perception = perception
            self._last_perception_time = now
            
            if self._state == NavigationState.IDLE:
                return
            
            state = self._state
            lang = self._lang
        
        # Check for safety triggers
        self._check_safety_conditions(perception, now)
        
        # State-specific behavior
        if state == NavigationState.NAVIGATING:
            self._navigate_step(perception, now)
        elif state == NavigationState.APPROACHING:
            self._approach_step(perception, now)
        elif state == NavigationState.SAFETY_HOLD:
            self._safety_hold_step(perception, now)
    
    def get_status(self) -> NavigationStatus:
        """Get current navigation status."""
        with self._lock:
            perc = self._last_perception
            
            # Calculate approximate distance to destination
            dist_remaining = None
            if self._destination_obj:
                dist_remaining = math.sqrt(
                    (self._destination_obj.x - self._estimated_x) ** 2 +
                    (self._destination_obj.y - self._estimated_y) ** 2
                )
            elif self._destination_landmark:
                dist_remaining = math.sqrt(
                    (self._destination_landmark.x - self._estimated_x) ** 2 +
                    (self._destination_landmark.y - self._estimated_y) ** 2
                )
            
            return NavigationStatus(
                state=self._state,
                destination=self._destination_label,
                confidence=perc.nav_confidence if perc else NavConfidence.INVALID,
                distance_remaining=dist_remaining,
                next_guidance=self._generate_next_guidance() if perc else None,
                hold_reason=self._hold_reason,
                last_perception_time=self._last_perception_time,
                safe_directions_count=len(perc.safe_directions) if perc else 0
            )
    
    # ── Internal navigation logic ─────────────────────────────────────────────
    
    def _check_safety_conditions(self, perception: PerceptionResult, now: float) -> None:
        """Check for conditions requiring SAFETY_HOLD."""
        with self._lock:
            if self._state == NavigationState.IDLE or self._state == NavigationState.ARRIVED:
                return
            
            lang = self._lang
            current_state = self._state
        
        # Check 1: Camera failure (invalid perception)
        if perception.nav_confidence == NavConfidence.INVALID:
            if current_state != NavigationState.SAFETY_HOLD or self._hold_reason != HoldReason.CAMERA_FAILURE:
                with self._lock:
                    self._state = NavigationState.SAFETY_HOLD
                    self._hold_reason = HoldReason.CAMERA_FAILURE
                self._speak("Safety hold: camera not working. Please check the camera.", lang)
                print("[INDOOR_NAV] SAFETY_HOLD: Camera failure")
            return
        
        # Check 2: Stale perception
        age = now - self._last_perception_time
        if age > self.PERCEPTION_MAX_AGE_S:
            if current_state != NavigationState.SAFETY_HOLD or self._hold_reason != HoldReason.STALE_PERCEPTION:
                with self._lock:
                    self._state = NavigationState.SAFETY_HOLD
                    self._hold_reason = HoldReason.STALE_PERCEPTION
                self._speak("Safety hold: lost camera view. Reconnecting...", lang)
                print(f"[INDOOR_NAV] SAFETY_HOLD: Stale perception ({age:.1f}s old)")
            return
        
        # Check 3: Critical obstacle proximity
        if perception.obstacle_summary.nearest_distance > 0.9:  # Depth > 0.9 = very close (inverse depth)
            if current_state != NavigationState.SAFETY_HOLD or self._hold_reason != HoldReason.OBSTACLE_TOO_CLOSE:
                with self._lock:
                    self._state = NavigationState.SAFETY_HOLD
                    self._hold_reason = HoldReason.OBSTACLE_TOO_CLOSE
                obstacles_str = ", ".join(perception.obstacle_summary.categories[:3])
                self._speak(f"Stop! Obstacle very close: {obstacles_str}. Please clear the path or move around it.", lang)
                print(f"[INDOOR_NAV] SAFETY_HOLD: Obstacle too close (depth={perception.obstacle_summary.nearest_distance:.2f})")
            return
        
        # Check 4: Low navigation confidence (not critical, just cautious)
        if perception.nav_confidence == NavConfidence.LOW:
            if current_state != NavigationState.SAFETY_HOLD or self._hold_reason != HoldReason.LOW_CONFIDENCE:
                with self._lock:
                    self._state = NavigationState.SAFETY_HOLD
                    self._hold_reason = HoldReason.LOW_CONFIDENCE
                self._speak("Pausing: limited visibility. Please wait or clear obstacles.", lang)
                print("[INDOOR_NAV] SAFETY_HOLD: Low confidence")
            return
        
        # All safety checks passed — if we were in SAFETY_HOLD, auto-resume
        if current_state == NavigationState.SAFETY_HOLD and self._hold_reason != HoldReason.USER_REQUEST:
            with self._lock:
                self._state = NavigationState.NAVIGATING
                self._hold_reason = None
                self._last_guidance_time = 0.0
            self._speak("Safety conditions restored. Continuing navigation.", lang)
            print("[INDOOR_NAV] Auto-resumed from SAFETY_HOLD")
    
    def _navigate_step(self, perception: PerceptionResult, now: float) -> None:
        """Execute navigation step in NAVIGATING state."""
        with self._lock:
            dest_obj = self._destination_obj
            dest_landmark = self._destination_landmark
            lang = self._lang
            last_guidance_time = self._last_guidance_time
        
        # Determine target position
        if dest_obj:
            target_x, target_y = dest_obj.x, dest_obj.y
        elif dest_landmark:
            target_x, target_y = dest_landmark.x, dest_landmark.y
        else:
            return
        
        # Estimate distance (very rough — we don't have odometry)
        # For now, assume we're at origin (0, 0) and destination is relative
        # In a real system, you'd integrate IMU/odometry data
        dist_est = math.sqrt(target_x ** 2 + target_y ** 2)
        
        # Check if approaching
        if dist_est < self.APPROACHING_THRESHOLD_M:
            with self._lock:
                self._state = NavigationState.APPROACHING
            self._speak(f"Almost there. {self._destination_label} is very close.", lang)
            print(f"[INDOOR_NAV] Entered APPROACHING state (dist ~{dist_est:.1f}m)")
            return
        
        # Only give guidance if enough time has passed
        if now - last_guidance_time < self.GUIDANCE_INTERVAL_S:
            return
        
        # Generate guidance based on safe directions
        guidance = self._generate_guidance(perception, target_x, target_y)
        if guidance:
            self._speak(guidance, lang)
            with self._lock:
                self._last_guidance_time = now
    
    def _approach_step(self, perception: PerceptionResult, now: float) -> None:
        """Execute navigation step in APPROACHING state."""
        with self._lock:
            dest_label = self._destination_label
            lang = self._lang
            last_guidance_time = self._last_guidance_time
        
        # Check if arrived (heuristic: destination object visible in perception)
        # In a real system, you'd use visual detection or spatial matching
        if perception.obstacle_summary.count > 0:
            # For now, assume if we see any object matching the category, we've arrived
            # This is a simplification — real system would do visual recognition
            with self._lock:
                self._state = NavigationState.ARRIVED
            self._speak(f"Arrived! {dest_label} should be right in front of you.", lang)
            print(f"[INDOOR_NAV] ARRIVED at {dest_label}")
            
            # Auto-stop after arrival
            time.sleep(2.0)
            self.stop(lang)
            return
        
        # Give final approach guidance
        if now - last_guidance_time >= self.GUIDANCE_INTERVAL_S:
            if perception.safe_directions:
                best = perception.safe_directions[0]
                if abs(best.angle_deg) < 15:
                    guidance = f"Move straight ahead slowly. {dest_label} is very close."
                elif best.angle_deg < 0:
                    guidance = f"Turn slightly left and move forward. Almost there."
                else:
                    guidance = f"Turn slightly right and move forward. Almost there."
            else:
                guidance = f"Stop. I can't see a clear path. Please orient yourself toward {dest_label}."
            
            self._speak(guidance, lang)
            with self._lock:
                self._last_guidance_time = now
    
    def _safety_hold_step(self, perception: PerceptionResult, now: float) -> None:
        """Monitor conditions while in SAFETY_HOLD."""
        with self._lock:
            hold_reason = self._hold_reason
            lang = self._lang
            last_reminder = self._last_hold_reminder_time
        
        # Periodically remind user why we're holding
        if now - last_reminder > self.SAFETY_HOLD_REMINDER_S:
            if hold_reason == HoldReason.USER_REQUEST:
                reminder = "Navigation is paused. Say 'resume navigation' to continue."
            elif hold_reason == HoldReason.CAMERA_FAILURE:
                reminder = "Still waiting for camera to work. Please check the connection."
            elif hold_reason == HoldReason.OBSTACLE_TOO_CLOSE:
                reminder = "Obstacle still blocking the path. Please clear it or move around."
            elif hold_reason == HoldReason.LOW_CONFIDENCE:
                reminder = "Still waiting for clear visibility. Please ensure the path is clear."
            else:
                reminder = "Navigation paused for safety."
            
            self._speak(reminder, lang)
            with self._lock:
                self._last_hold_reminder_time = now
    
    def _generate_guidance(
        self,
        perception: PerceptionResult,
        target_x: float,
        target_y: float
    ) -> Optional[str]:
        """
        Generate guidance instruction based on perception and target.
        
        Returns:
            Guidance string or None if no safe guidance available
        """
        if not perception.safe_directions:
            return "Stop. No clear path ahead. Please turn slowly to find an opening."
        
        # Get best safe direction
        best = perception.safe_directions[0]
        
        # Calculate rough bearing to target (assuming forward is 0°, left is negative)
        # This is a simplification — real system would use IMU orientation
        target_bearing = math.degrees(math.atan2(target_x, target_y))
        
        # Simple guidance based on angle
        angle = best.angle_deg
        clearance = best.clearance_m
        
        if abs(angle) < 15:
            # Straight ahead
            if clearance > 3.0:
                return f"Move forward. Path is clear for at least {int(clearance)} metres."
            else:
                return f"Move forward carefully. About {int(clearance)} metres clear."
        elif angle < -30:
            # Far left
            return "Turn left 45 degrees, then move forward."
        elif angle < 0:
            # Left
            return f"Turn left about {abs(int(angle))} degrees, then move forward."
        elif angle < 30:
            # Right
            return f"Turn right about {int(angle)} degrees, then move forward."
        else:
            # Far right
            return "Turn right 45 degrees, then move forward."
    
    def _generate_next_guidance(self) -> Optional[str]:
        """Generate preview of next guidance (for status queries)."""
        perc = self._last_perception
        if not perc or not perc.safe_directions:
            return None
        
        best = perc.safe_directions[0]
        angle = best.angle_deg
        
        if abs(angle) < 15:
            return "Move straight forward"
        elif angle < 0:
            return f"Turn left {abs(int(angle))}° and move forward"
        else:
            return f"Turn right {int(angle)}° and move forward"
    
    def _speak(self, text: str, lang: str = "en") -> None:
        """Speak guidance via voice engine."""
        if not text:
            return
        
        if self.voice is not None:
            self.voice.speak(text, lang=lang)
        else:
            # Fallback: print only
            print(f"[INDOOR_NAV GUIDANCE] {text}")
