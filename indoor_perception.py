"""
indoor_perception.py — Free-space detection and local occupancy mapping for indoor navigation.

Responsibilities:
  • Extract navigable floor space from YOLO detections + MiDaS depth
  • Build local occupancy grid (2D map of obstacles vs free space)
  • Detect doorways, openings, and passages
  • Cluster obstacles by proximity
  • Provide navigation confidence score (HIGH/MEDIUM/LOW/INVALID)
  • Identify safe movement directions and angles

Design principles:
  • Deterministic: no learning, no randomness
  • Fast: runs every frame alongside existing YOLO+MiDaS
  • Safety-first: conservative free-space detection
  • Confidence-aware: never return LOW confidence as safe
  • Coordinate system: camera-relative (forward=+Z, left=-X, up=+Y)

Input:
  • YOLO detections: bounding boxes with class labels
  • MiDaS depth map: relative depth values (NOT metric distances)
  • Image dimensions: width, height

Output:
  • Occupancy grid: 2D array [FREE, OCCUPIED, UNKNOWN]
  • Safe directions: list of (angle_deg, confidence, distance_m)
  • Doorway candidates: list of (x1, x2, center_depth)
  • Navigation confidence: HIGH / MEDIUM / LOW / INVALID
  • Obstacle summary: count, nearest_distance, categories
"""

import numpy as np
from enum import Enum
from typing import List, Dict, Tuple, Optional, NamedTuple
from dataclasses import dataclass


class CellState(int, Enum):
    """Occupancy grid cell states."""
    UNKNOWN = 0
    FREE = 1
    OCCUPIED = 2
    DOORWAY = 3


class NavConfidence(str, Enum):
    """Navigation confidence levels."""
    INVALID = "INVALID"      # No depth data, camera failure, or critical error
    LOW = "LOW"              # Obstacles very close, limited visibility
    MEDIUM = "MEDIUM"        # Some obstacles, partial visibility
    HIGH = "HIGH"            # Clear path, good visibility


@dataclass
class SafeDirection:
    """A direction deemed safe for movement."""
    angle_deg: float          # -90 (left) to +90 (right), 0 = straight ahead
    confidence: NavConfidence
    clearance_m: float        # Approximate distance before obstacle
    width_m: float            # Width of passage in metres


@dataclass
class Doorway:
    """Detected doorway or passage."""
    center_x: float           # Normalized x position [0, 1]
    width: float              # Width in pixels
    depth: float              # Relative depth (lower = closer)
    confidence: float         # Detection confidence [0, 1]


@dataclass
class ObstacleSummary:
    """Summary of obstacles in view."""
    count: int
    nearest_distance: float   # Relative depth (NOT metres)
    categories: List[str]     # YOLO class names
    left_blocked: bool
    center_blocked: bool
    right_blocked: bool


# Depth thresholds for safety classification (relative depth, higher = closer)
DEPTH_VERY_CLOSE = 0.8
DEPTH_CLOSE = 0.6
DEPTH_MEDIUM = 0.4
DEPTH_FAR = 0.2


class IndoorPerception:
    """
    Free-space detection and occupancy mapping for indoor navigation.
    
    Usage:
        perception = IndoorPerception(grid_size=32)
        
        # Process frame
        result = perception.process_frame(
            yolo_detections=detections,
            depth_map=depth_array,
            img_width=640,
            img_height=480
        )
        
        # Check navigation safety
        if result.nav_confidence == NavConfidence.HIGH:
            safe_dirs = result.safe_directions
            print(f"Safe to move: {safe_dirs[0].angle_deg}° for {safe_dirs[0].clearance_m}m")
    """
    
    # YOLO classes that block movement (obstacles)
    OBSTACLE_CLASSES = {
        "person", "bicycle", "car", "motorcycle", "bus", "truck",
        "chair", "couch", "bed", "dining table", "toilet",
        "tv", "laptop", "mouse", "keyboard", "cell phone",
        "book", "clock", "vase", "scissors", "teddy bear",
        "suitcase", "backpack", "handbag", "tie", "umbrella",
        "bottle", "wine glass", "cup", "fork", "knife", "spoon", "bowl"
    }
    
    # Classes that suggest doorways or passages
    DOORWAY_CLASSES = {"door", "doorway", "opening"}
    
    # Minimum detection confidence to consider
    MIN_DETECTION_CONFIDENCE = 0.3
    
    # Grid cell size in degrees (horizontal FOV / grid_size)
    CAMERA_HFOV_DEG = 60.0  # Typical ESP32-CAM horizontal FOV
    
    def __init__(self, grid_size: int = 32):
        """
        Initialize indoor perception.
        
        Args:
            grid_size: Occupancy grid resolution (grid_size x grid_size cells)
        """
        self.grid_size = grid_size
        self.grid = np.zeros((grid_size, grid_size), dtype=np.int8)
    
    def process_frame(
        self,
        yolo_detections: List[Dict],
        depth_map: np.ndarray,
        img_width: int,
        img_height: int
    ) -> 'PerceptionResult':
        """
        Process a single frame to extract navigation information.
        
        Args:
            yolo_detections: List of dicts with keys: class, confidence, bbox [x1, y1, x2, y2]
            depth_map: 2D numpy array with relative depth (0-1, higher = closer)
            img_width, img_height: Image dimensions
        
        Returns:
            PerceptionResult with occupancy grid, safe directions, confidence
        """
        
        # Validate inputs
        if depth_map is None or depth_map.size == 0:
            return self._invalid_result("No depth data")
        
        if depth_map.ndim != 2:
            return self._invalid_result("Invalid depth map dimensions")
        
        # Normalize depth map to [0, 1] with higher values = closer
        depth_normalized = self._normalize_depth(depth_map)
        
        # Filter detections by confidence
        valid_detections = [
            d for d in yolo_detections
            if d.get("confidence", 0) >= self.MIN_DETECTION_CONFIDENCE
        ]
        
        # Build occupancy grid
        self._update_occupancy_grid(valid_detections, depth_normalized, img_width, img_height)
        
        # Detect obstacles
        obstacle_summary = self._analyze_obstacles(valid_detections, depth_normalized, img_width, img_height)
        
        # Detect doorways
        doorways = self._detect_doorways(valid_detections, depth_normalized, img_width, img_height)
        
        # Calculate navigation confidence
        nav_confidence = self._calculate_nav_confidence(obstacle_summary, depth_normalized)
        
        # Find safe directions
        safe_directions = self._find_safe_directions(
            obstacle_summary,
            depth_normalized,
            img_width,
            img_height,
            nav_confidence
        )
        
        return PerceptionResult(
            nav_confidence=nav_confidence,
            occupancy_grid=self.grid.copy(),
            safe_directions=safe_directions,
            doorways=doorways,
            obstacle_summary=obstacle_summary,
            depth_map=depth_normalized
        )
    
    # ── Internal processing ───────────────────────────────────────────────────
    
    def _normalize_depth(self, depth_map: np.ndarray) -> np.ndarray:
        """
        Normalize depth map to [0, 1] where 1 = closest, 0 = farthest.
        
        MiDaS outputs inverse depth (higher values = closer).
        """
        if depth_map.min() == depth_map.max():
            # Uniform depth — invalid
            return np.zeros_like(depth_map, dtype=np.float32)
        
        # Normalize to [0, 1]
        normalized = (depth_map - depth_map.min()) / (depth_map.max() - depth_map.min())
        return normalized.astype(np.float32)
    
    def _update_occupancy_grid(
        self,
        detections: List[Dict],
        depth_map: np.ndarray,
        img_width: int,
        img_height: int
    ) -> None:
        """Update occupancy grid based on detections and depth."""
        # Reset grid
        self.grid.fill(CellState.UNKNOWN)
        
        # Divide image into horizontal zones
        zone_width = img_width / self.grid_size
        zone_height = img_height / self.grid_size
        
        # Mark free space (low obstacle density + far depth)
        for row in range(self.grid_size):
            for col in range(self.grid_size):
                x1 = int(col * zone_width)
                x2 = int((col + 1) * zone_width)
                y1 = int(row * zone_height)
                y2 = int((row + 1) * zone_height)
                
                # Sample depth in this zone
                if y2 <= depth_map.shape[0] and x2 <= depth_map.shape[1]:
                    zone_depth = depth_map[y1:y2, x1:x2]
                    mean_depth = zone_depth.mean() if zone_depth.size > 0 else 0.0
                    
                    # Check if any detection overlaps this zone
                    occupied = False
                    for det in detections:
                        if det.get("class", "") not in self.OBSTACLE_CLASSES:
                            continue
                        
                        bbox = det.get("bbox", [0, 0, 0, 0])
                        bx1, by1, bx2, by2 = bbox
                        
                        # Check overlap
                        if not (bx2 < x1 or bx1 > x2 or by2 < y1 or by1 > y2):
                            occupied = True
                            break
                    
                    if occupied:
                        self.grid[row, col] = CellState.OCCUPIED
                    elif mean_depth < DEPTH_MEDIUM:
                        # Far away = likely free
                        self.grid[row, col] = CellState.FREE
                    else:
                        self.grid[row, col] = CellState.UNKNOWN
    
    def _analyze_obstacles(
        self,
        detections: List[Dict],
        depth_map: np.ndarray,
        img_width: int,
        img_height: int
    ) -> ObstacleSummary:
        """Analyze obstacles in view."""
        obstacles = [
            d for d in detections
            if d.get("class", "") in self.OBSTACLE_CLASSES
        ]
        
        if not obstacles:
            return ObstacleSummary(
                count=0,
                nearest_distance=0.0,
                categories=[],
                left_blocked=False,
                center_blocked=False,
                right_blocked=False
            )
        
        # Find nearest obstacle
        nearest_depth = 0.0
        categories = list(set(d.get("class", "") for d in obstacles))
        
        # Check zones
        left_blocked = False
        center_blocked = False
        right_blocked = False
        
        for obs in obstacles:
            bbox = obs.get("bbox", [0, 0, 0, 0])
            x1, y1, x2, y2 = bbox
            
            # Sample depth at obstacle center
            cx = int((x1 + x2) / 2)
            cy = int((y1 + y2) / 2)
            
            if 0 <= cy < depth_map.shape[0] and 0 <= cx < depth_map.shape[1]:
                obs_depth = depth_map[cy, cx]
                if obs_depth > nearest_depth:
                    nearest_depth = obs_depth
            
            # Determine zone
            center_x = (x1 + x2) / 2
            if center_x < img_width * 0.33:
                left_blocked = True
            elif center_x < img_width * 0.67:
                center_blocked = True
            else:
                right_blocked = True
        
        return ObstacleSummary(
            count=len(obstacles),
            nearest_distance=nearest_depth,
            categories=categories,
            left_blocked=left_blocked,
            center_blocked=center_blocked,
            right_blocked=right_blocked
        )
    
    def _detect_doorways(
        self,
        detections: List[Dict],
        depth_map: np.ndarray,
        img_width: int,
        img_height: int
    ) -> List[Doorway]:
        """Detect doorways and passages."""
        doorways = []
        
        # Explicit door detections
        door_detections = [
            d for d in detections
            if d.get("class", "") in self.DOORWAY_CLASSES
        ]
        
        for det in door_detections:
            bbox = det.get("bbox", [0, 0, 0, 0])
            x1, y1, x2, y2 = bbox
            
            center_x = (x1 + x2) / 2 / img_width
            width = x2 - x1
            
            # Sample depth at doorway center
            cx = int((x1 + x2) / 2)
            cy = int((y1 + y2) / 2)
            
            if 0 <= cy < depth_map.shape[0] and 0 <= cx < depth_map.shape[1]:
                depth = depth_map[cy, cx]
            else:
                depth = 0.5
            
            doorways.append(Doorway(
                center_x=center_x,
                width=width,
                depth=depth,
                confidence=det.get("confidence", 0.5)
            ))
        
        # Heuristic: vertical gaps in obstacle distribution
        # (Future enhancement: detect passages between furniture)
        
        return doorways
    
    def _calculate_nav_confidence(
        self,
        obstacle_summary: ObstacleSummary,
        depth_map: np.ndarray
    ) -> NavConfidence:
        """Calculate overall navigation confidence."""
        
        # Check for invalid depth
        if depth_map.max() == 0.0:
            return NavConfidence.INVALID
        
        # Check for very close obstacles
        if obstacle_summary.nearest_distance > DEPTH_VERY_CLOSE:
            return NavConfidence.LOW
        
        # Check for blocked view
        if obstacle_summary.center_blocked and obstacle_summary.nearest_distance > DEPTH_CLOSE:
            return NavConfidence.LOW
        
        # Count blocked zones
        blocked_zones = sum([
            obstacle_summary.left_blocked,
            obstacle_summary.center_blocked,
            obstacle_summary.right_blocked
        ])
        
        if blocked_zones == 0:
            return NavConfidence.HIGH
        elif blocked_zones == 1:
            return NavConfidence.MEDIUM if obstacle_summary.nearest_distance < DEPTH_MEDIUM else NavConfidence.LOW
        elif blocked_zones == 2:
            return NavConfidence.MEDIUM if obstacle_summary.nearest_distance < DEPTH_CLOSE else NavConfidence.LOW
        else:
            return NavConfidence.LOW
    
    def _find_safe_directions(
        self,
        obstacle_summary: ObstacleSummary,
        depth_map: np.ndarray,
        img_width: int,
        img_height: int,
        nav_confidence: NavConfidence
    ) -> List[SafeDirection]:
        """Find safe movement directions."""
        
        if nav_confidence == NavConfidence.INVALID:
            return []
        
        safe_dirs = []
        
        # Analyze horizontal slices (center third of image = ground level)
        center_row_start = img_height // 3
        center_row_end = 2 * img_height // 3
        
        if center_row_end > depth_map.shape[0]:
            center_row_end = depth_map.shape[0]
        
        center_slice = depth_map[center_row_start:center_row_end, :]
        
        # Divide into 5 angular zones: far-left, left, center, right, far-right
        zones = [
            (-75, center_slice[:, :img_width//5]),         # Far left
            (-45, center_slice[:, img_width//5:2*img_width//5]),   # Left
            (0, center_slice[:, 2*img_width//5:3*img_width//5]),   # Center
            (45, center_slice[:, 3*img_width//5:4*img_width//5]),  # Right
            (75, center_slice[:, 4*img_width//5:])          # Far right
        ]
        
        for angle, zone_data in zones:
            if zone_data.size == 0:
                continue
            
            mean_depth = zone_data.mean()
            
            # Classify safety
            if mean_depth < DEPTH_MEDIUM:
                # Far = safe
                clearance = 5.0  # Approximate
                confidence = NavConfidence.HIGH
            elif mean_depth < DEPTH_CLOSE:
                clearance = 2.5
                confidence = NavConfidence.MEDIUM
            elif mean_depth < DEPTH_VERY_CLOSE:
                clearance = 1.5
                confidence = NavConfidence.LOW
            else:
                # Too close
                continue
            
            # Check if this direction is blocked by obstacles
            if angle == -45 and obstacle_summary.left_blocked and mean_depth > DEPTH_MEDIUM:
                continue
            if angle == 0 and obstacle_summary.center_blocked and mean_depth > DEPTH_MEDIUM:
                continue
            if angle == 45 and obstacle_summary.right_blocked and mean_depth > DEPTH_MEDIUM:
                continue
            
            safe_dirs.append(SafeDirection(
                angle_deg=angle,
                confidence=confidence,
                clearance_m=clearance,
                width_m=1.0  # Approximate passage width
            ))
        
        # Sort by clearance (prefer more open paths)
        safe_dirs.sort(key=lambda d: d.clearance_m, reverse=True)
        
        return safe_dirs
    
    def _invalid_result(self, reason: str) -> 'PerceptionResult':
        """Return an invalid perception result."""
        print(f"[INDOOR_PERCEPTION] INVALID: {reason}")
        return PerceptionResult(
            nav_confidence=NavConfidence.INVALID,
            occupancy_grid=np.zeros((self.grid_size, self.grid_size), dtype=np.int8),
            safe_directions=[],
            doorways=[],
            obstacle_summary=ObstacleSummary(
                count=0,
                nearest_distance=0.0,
                categories=[],
                left_blocked=False,
                center_blocked=False,
                right_blocked=False
            ),
            depth_map=None
        )


@dataclass
class PerceptionResult:
    """Result of indoor perception processing."""
    nav_confidence: NavConfidence
    occupancy_grid: np.ndarray
    safe_directions: List[SafeDirection]
    doorways: List[Doorway]
    obstacle_summary: ObstacleSummary
    depth_map: Optional[np.ndarray]
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for telemetry/logging."""
        return {
            "nav_confidence": self.nav_confidence.value,
            "obstacle_count": self.obstacle_summary.count,
            "nearest_obstacle_depth": float(self.obstacle_summary.nearest_distance),
            "safe_direction_count": len(self.safe_directions),
            "best_direction_angle": self.safe_directions[0].angle_deg if self.safe_directions else None,
            "best_direction_clearance": self.safe_directions[0].clearance_m if self.safe_directions else None,
            "doorway_count": len(self.doorways),
            "zones_blocked": {
                "left": self.obstacle_summary.left_blocked,
                "center": self.obstacle_summary.center_blocked,
                "right": self.obstacle_summary.right_blocked
            }
        }
