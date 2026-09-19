"""
safety_engine.py — Deterministic Obstacle Safety, Tracking & Collision Engine.

Responsibilities:
  • Multi-frame persistent object tracking with stable IDs (Requirement 20)
  • Temporal filtering to prevent single-frame flickering/false alarms (Requirement 19)
  • Categorization into Static, Dynamic, and Temporary objects (Requirement 21)
  • Metric/Relative coordinate transformation in Local Room Frame (Requirement 23)
  • Deterministic safety evaluation: CLEAR → CAUTION → BLOCKED → CRITICAL (Requirement 18)
  • Collision prediction / closing velocity estimation (Requirement 29)
  • Structured spatial fact generator for deterministic voice replies (Requirement 32)
"""
from __future__ import annotations

import time
import math
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple, Any
import numpy as np

from system_state import SafetyLevel


# ── Object Categorization (Requirement 21) ───────────────────────────────────

STATIC_OBJECTS = {
    "chair", "couch", "sofa", "bed", "dining table", "table", "desk",
    "toilet", "door", "wall", "refrigerator", "oven", "sink", "bookcase",
    "cabinet", "cupboard", "tv", "wardrobe"
}

DYNAMIC_OBJECTS = {
    "person", "bicycle", "car", "motorcycle", "bus", "truck",
    "dog", "cat", "horse", "sheep", "cow", "bird"
}

TEMPORARY_OBJECTS = {
    "backpack", "umbrella", "handbag", "suitcase", "sports ball",
    "bottle", "cup", "bowl", "box", "package"
}


def categorize_object(label: str) -> str:
    """Classify an object label into STATIC, DYNAMIC, or TEMPORARY."""
    l = label.lower()
    if l in STATIC_OBJECTS:
        return "STATIC"
    elif l in DYNAMIC_OBJECTS:
        return "DYNAMIC"
    elif l in TEMPORARY_OBJECTS:
        return "TEMPORARY"
    return "STATIC"  # Default assumption for indoor objects


# ── Tracked Object Representation (Requirement 20) ───────────────────────────

@dataclass
class TrackedObject:
    """Persistent representation of a tracked object across video frames."""
    id: int
    label: str
    category: str              # STATIC, DYNAMIC, TEMPORARY
    bbox: List[int]            # [x1, y1, x2, y2]
    center: Tuple[float, float]# (cx, cy)
    relative_depth: float      # Raw MiDaS relative depth (higher = closer)
    proximity: str             # "VERY_CLOSE", "CLOSE", "MEDIUM", "FAR"
    confidence: float          # Detection confidence [0..1]
    velocity: Tuple[float, float] = (0.0, 0.0)  # (vx, vy) in pixels/second
    closing_rate: float = 0.0  # rate of change in relative depth (units/sec)
    first_seen: float = field(default_factory=time.time)
    last_seen: float = field(default_factory=time.time)
    frame_hits: int = 1
    consecutive_misses: int = 0
    confirmed: bool = False
    
    # Local coordinate frame relative to user:
    # X = Left (-X) to Right (+X), Y = Forward (+Y), Z = Vertical (+Z)
    local_coords: Tuple[float, float, float] = (0.0, 0.0, 0.0)

    def to_dict(self) -> Dict[str, Any]:
        cx, cy = self.center
        return {
            "id": self.id,
            "class": self.label,
            "category": self.category,
            "bbox": list(self.bbox),
            "center": [round(cx, 1), round(cy, 1)],
            "relative_depth": round(self.relative_depth, 1),
            "proximity": self.proximity,
            "confidence": round(self.confidence, 2),
            "velocity": [round(self.velocity[0], 1), round(self.velocity[1], 1)],
            "closing_rate": round(self.closing_rate, 2),
            "confirmed": self.confirmed,
            "first_seen": self.first_seen,
            "last_seen": self.last_seen,
            "local_coords": [round(c, 2) for c in self.local_coords]
        }


# ── Persistent Object Tracker (Requirement 19 & 20) ──────────────────────────

class ObjectTracker:
    """
    Centroid + IoU multi-object tracker with temporal confirmation and decay.
    """

    def __init__(self, min_hits: int = 2, max_misses: int = 4, max_distance_px: float = 120.0):
        self._next_id = 1
        self._tracks: Dict[int, TrackedObject] = {}
        self._min_hits = min_hits
        self._max_misses = max_misses
        self._max_distance_px = max_distance_px
        self._last_update_time = time.time()

    def update(
        self,
        detections: List[Dict[str, Any]],
        raw_depth: np.ndarray,
        frame_width: int,
        frame_height: int
    ) -> List[TrackedObject]:
        """
        Update tracked objects with new YOLO detections and depth.
        """
        now = time.time()
        dt = max(0.001, now - self._last_update_time)
        self._last_update_time = now

        # Convert raw detections into candidate records
        candidates = []
        for det in detections:
            x1, y1, x2, y2 = det["bbox"]
            cx = (x1 + x2) / 2.0
            cy = (y1 + y2) / 2.0
            
            # Sample depth inside bounding box
            crop_d = raw_depth[max(0, y1):min(frame_height, y2), max(0, x1):min(frame_width, x2)]
            med_depth = float(np.median(crop_d)) if crop_d.size > 0 else 0.0
            
            # Relative proximity
            from config import classify_depth_proximity_adaptive, classify_depth_proximity, DEPTH_ADAPTIVE_NORMALIZATION
            if DEPTH_ADAPTIVE_NORMALIZATION and raw_depth.size > 0:
                prox = classify_depth_proximity_adaptive(med_depth, raw_depth)
            else:
                prox = classify_depth_proximity(med_depth)

            # Camera-to-local coordinate approximation
            # Norm X: -1.0 (left edge) to +1.0 (right edge)
            norm_x = (cx - (frame_width / 2.0)) / (frame_width / 2.0)
            # Relative forward estimate based on depth
            est_forward = max(0.5, 600.0 / max(med_depth, 50.0))
            est_lateral = norm_x * est_forward * 0.6
            local_coords = (round(est_lateral, 2), round(est_forward, 2), 0.0)

            candidates.append({
                "label": det["class"],
                "category": categorize_object(det["class"]),
                "bbox": [x1, y1, x2, y2],
                "center": (cx, cy),
                "relative_depth": med_depth,
                "proximity": prox,
                "confidence": float(det.get("confidence", 0.5)),
                "local_coords": local_coords
            })

        # Match existing tracks with candidates using greedy assignment
        unmatched_candidates = list(range(len(candidates)))
        matched_tracks = set()

        for track_id, track in list(self._tracks.items()):
            best_idx = None
            best_dist = float("inf")

            for c_idx in unmatched_candidates:
                cand = candidates[c_idx]
                if cand["label"] != track.label:
                    continue  # Only match same class

                # Euclidean distance between centers
                dist = math.hypot(cand["center"][0] - track.center[0], cand["center"][1] - track.center[1])
                if dist < best_dist and dist < self._max_distance_px:
                    best_dist = dist
                    best_idx = c_idx

            if best_idx is not None:
                cand = candidates[best_idx]
                unmatched_candidates.remove(best_idx)
                matched_tracks.add(track_id)

                # Compute velocity & closing rate
                vx = (cand["center"][0] - track.center[0]) / dt
                vy = (cand["center"][1] - track.center[1]) / dt
                closing_rate = (cand["relative_depth"] - track.relative_depth) / dt

                # Update track with exponential smoothing on depth
                smooth_depth = 0.7 * cand["relative_depth"] + 0.3 * track.relative_depth
                track.bbox = cand["bbox"]
                track.center = cand["center"]
                track.relative_depth = smooth_depth
                track.proximity = cand["proximity"]
                track.confidence = cand["confidence"]
                track.velocity = (vx, vy)
                track.closing_rate = closing_rate
                track.last_seen = now
                track.frame_hits += 1
                track.consecutive_misses = 0
                track.local_coords = cand["local_coords"]

                if track.frame_hits >= self._min_hits:
                    track.confirmed = True
            else:
                # Track missed in this frame
                track.consecutive_misses += 1
                # Velocity decays
                track.velocity = (track.velocity[0] * 0.5, track.velocity[1] * 0.5)

        # Remove dead tracks that exceeded max_misses
        dead_ids = [tid for tid, t in self._tracks.items() if t.consecutive_misses > self._max_misses]
        for tid in dead_ids:
            del self._tracks[tid]

        # Create new tracks for unmatched candidates
        for c_idx in unmatched_candidates:
            cand = candidates[c_idx]
            new_id = self._next_id
            self._next_id += 1

            self._tracks[new_id] = TrackedObject(
                id=new_id,
                label=cand["label"],
                category=cand["category"],
                bbox=cand["bbox"],
                center=cand["center"],
                relative_depth=cand["relative_depth"],
                proximity=cand["proximity"],
                confidence=cand["confidence"],
                first_seen=now,
                last_seen=now,
                frame_hits=1,
                consecutive_misses=0,
                confirmed=(self._min_hits <= 1),
                local_coords=cand["local_coords"]
            )

        return list(self._tracks.values())

    def get_confirmed_tracks(self) -> List[TrackedObject]:
        """Return only tracks confirmed by temporal filtering."""
        return [t for t in self._tracks.values() if t.confirmed]


# ── Deterministic Safety Engine (Requirements 18 & 29) ───────────────────────

@dataclass
class SafetyEvaluation:
    """Output of SafetyEngine evaluation."""
    level: SafetyLevel
    immediate_danger_text: Optional[str]
    guidance_text: Optional[str]
    corridor_state: str  # "LEFT_OPEN", "CENTER_OPEN", "RIGHT_OPEN", "BLOCKED"
    time_to_collision_s: Optional[float]
    wall_detected: bool
    nearest_obstacle: Optional[Dict[str, Any]]
    detected_count: int


class SafetyEngine:
    """
    Deterministic real-time safety evaluation engine.
    Calculates collision risk and corridor status without relying on any LLM.
    """

    def __init__(self):
        self.tracker = ObjectTracker(min_hits=2, max_misses=3)
        self.last_speech_time = 0.0
        self.last_spoken = ""

    def evaluate(
        self,
        detections: List[Dict[str, Any]],
        raw_depth: np.ndarray,
        frame_width: int,
        frame_height: int
    ) -> SafetyEvaluation:
        """
        Evaluate current frame for collision risk, corridor clearance, and walls.
        """
        # 1. Update temporal object tracker
        tracks = self.tracker.update(detections, raw_depth, frame_width, frame_height)
        confirmed_tracks = [t for t in tracks if t.confirmed]

        # 2. Divide frame into spatial corridors: Left (0..1/3), Center (1/3..2/3), Right (2/3..1)
        third_w = frame_width // 3
        center_depth_crop = raw_depth[:, third_w : 2 * third_w]
        left_depth_crop = raw_depth[:, :third_w]
        right_depth_crop = raw_depth[:, 2 * third_w:]

        center_med = float(np.median(center_depth_crop)) if center_depth_crop.size > 0 else 0.0
        left_med = float(np.median(left_depth_crop)) if left_depth_crop.size > 0 else 0.0
        right_med = float(np.median(right_depth_crop)) if right_depth_crop.size > 0 else 0.0

        # Import wall thresholds from config
        from config import (
            DEPTH_WALL_DENSE_THRESHOLD,
            DEPTH_WALL_CENTER_RATIO,
            DEPTH_WALL_IMMEDIATE_THRESHOLD,
        )

        center_close_ratio = float(np.mean(center_depth_crop > DEPTH_WALL_DENSE_THRESHOLD)) if center_depth_crop.size > 0 else 0.0
        
        # 3. Check for wall / continuous obstacle
        wall_detected = False
        immediate_danger = None
        guidance_text = None
        
        # Check if objects explain the central depth
        center_has_object = any(t.bbox[0] < 2 * third_w and t.bbox[2] > third_w for t in confirmed_tracks)

        if center_close_ratio > DEPTH_WALL_CENTER_RATIO and not center_has_object:
            wall_detected = True
            if center_med > DEPTH_WALL_IMMEDIATE_THRESHOLD:
                immediate_danger = "Stop! Wall directly in front of you."
            else:
                immediate_danger = "Caution! Wall ahead."

            if left_med < center_med - 100 and left_med < right_med:
                guidance_text = "Wall ahead. Path is clear on your left."
            elif right_med < center_med - 100:
                guidance_text = "Wall ahead. Path is clear on your right."

        # 4. Check for close confirmed objects in central corridor
        nearest_obs_dict = None
        min_forward = float("inf")
        time_to_collision = None

        for t in confirmed_tracks:
            cx = t.center[0]
            # Spatial position
            if cx < third_w:
                pos = "on your left"
            elif cx > 2 * third_w:
                pos = "on your right"
            else:
                pos = "ahead"

            # Check collision hazard
            if pos == "ahead" and t.proximity == "VERY_CLOSE":
                if not immediate_danger:
                    immediate_danger = f"Stop! {t.label} directly ahead."
                    
            elif pos == "ahead" and t.proximity == "CLOSE":
                if not immediate_danger:
                    immediate_danger = f"Caution! {t.label} ahead."

            # Calculate time to collision if closing in
            if t.closing_rate > 15.0 and t.proximity in ("VERY_CLOSE", "CLOSE"):
                # Approximate time before collision
                ttc = max(0.5, 100.0 / max(t.closing_rate, 1.0))
                if time_to_collision is None or ttc < time_to_collision:
                    time_to_collision = round(ttc, 1)

            # Track nearest obstacle
            if t.local_coords[1] < min_forward:
                min_forward = t.local_coords[1]
                nearest_obs_dict = {
                    "id": t.id,
                    "class": t.label,
                    "position": pos,
                    "proximity": t.proximity,
                    "confidence": t.confidence,
                    "relative_depth": t.relative_depth
                }

        # 5. Determine Corridor State
        left_clear = left_med < DEPTH_WALL_DENSE_THRESHOLD and not any(t.center[0] < third_w and t.proximity == "VERY_CLOSE" for t in confirmed_tracks)
        center_clear = center_med < DEPTH_WALL_DENSE_THRESHOLD and not any(third_w <= t.center[0] <= 2 * third_w and t.proximity in ("VERY_CLOSE", "CLOSE") for t in confirmed_tracks)
        right_clear = right_med < DEPTH_WALL_DENSE_THRESHOLD and not any(t.center[0] > 2 * third_w and t.proximity == "VERY_CLOSE" for t in confirmed_tracks)

        if center_clear:
            corridor_state = "CENTER_OPEN"
        elif left_clear and not right_clear:
            corridor_state = "LEFT_OPEN"
        elif right_clear and not left_clear:
            corridor_state = "RIGHT_OPEN"
        elif left_clear and right_clear:
            corridor_state = "LEFT_OPEN" if left_med < right_med else "RIGHT_OPEN"
        else:
            corridor_state = "BLOCKED"

        # 6. Assign Safety Level
        if immediate_danger and ("Stop!" in immediate_danger or wall_detected and center_med > DEPTH_WALL_IMMEDIATE_THRESHOLD):
            safety_lvl = SafetyLevel.CRITICAL
        elif immediate_danger or corridor_state == "BLOCKED":
            safety_lvl = SafetyLevel.BLOCKED
        elif corridor_state in ("LEFT_OPEN", "RIGHT_OPEN"):
            safety_lvl = SafetyLevel.CAUTION
        else:
            safety_lvl = SafetyLevel.CLEAR

        return SafetyEvaluation(
            level=safety_lvl,
            immediate_danger_text=immediate_danger,
            guidance_text=guidance_text,
            corridor_state=corridor_state,
            time_to_collision_s=time_to_collision,
            wall_detected=wall_detected,
            nearest_obstacle=nearest_obs_dict,
            detected_count=len(confirmed_tracks)
        )

    # ── Deterministic Spatial Fact Generator (Requirement 32) ─────────────────

    @staticmethod
    def generate_spatial_facts(tracks: List[TrackedObject], safety: SafetyEvaluation, lang: str = "en") -> str:
        """
        Generate natural spoken description of spatial surroundings directly
        from tracking facts without calling any LLM.
        """
        if safety.wall_detected:
            if lang == "hi":
                return "आगे एक दीवार है। रास्ता अवरुद्ध है।"
            return "There is a wall directly ahead. Path is blocked."

        if not tracks:
            if lang == "hi":
                return "रास्ता बिल्कुल साफ है। कोई रुकावट नहीं है।"
            return "Path is clear ahead. No obstacles in view."

        # Group tracks by corridor
        ahead = [t for t in tracks if t.confirmed and t.center[0] >= 100 and t.center[0] <= 500]  # center
        left = [t for t in tracks if t.confirmed and t.center[0] < 100]
        right = [t for t in tracks if t.confirmed and t.center[0] > 500]

        parts = []
        if lang == "hi":
            if ahead:
                top = ahead[0]
                parts.append(f"सामने {top.label} है")
            else:
                parts.append("सामने का रास्ता साफ है")

            if left:
                parts.append(f"बाईं ओर {left[0].label}")
            if right:
                parts.append(f"दाईं ओर {right[0].label}")

            return "। ".join(parts) + "।"
        else:
            if ahead:
                top = ahead[0]
                prox_word = "close" if top.proximity in ("VERY_CLOSE", "CLOSE") else "further ahead"
                parts.append(f"Directly ahead: {top.label}, {prox_word}")
            else:
                parts.append("Directly ahead: path is clear")

            if left:
                parts.append(f"to your left: {left[0].label}")
            if right:
                parts.append(f"to your right: {right[0].label}")

            return ". ".join(parts) + "."
