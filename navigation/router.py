"""
navigation/router.py — Fully offline pedestrian routing via local OSM graph.

Uses a locally stored NetworkX graph (GraphML format) loaded by OfflineMapManager.
No internet access is required or allowed during routing.

Route calculation uses Dijkstra's algorithm weighted by edge length (metres).
Turn-by-turn steps are derived from bearing changes between consecutive edges.

Usage:
    manager = OfflineMapManager()
    manager.load_map("hyderabad")
    router = OfflineRouter(manager)
    result = router.route(17.3616, 78.4747, 17.3611, 78.4744)
"""
from __future__ import annotations

import math
from enum import Enum
from typing import Optional

from navigation.config import (
    WALK_SPEED_MPS,
    BEARING_STRAIGHT_MAX,
    BEARING_SLIGHT_MAX,
    BEARING_NORMAL_MAX,
    BEARING_SHARP_MAX,
    MERGE_STRAIGHT_M,
)


# ── Turn classification ───────────────────────────────────────────────────────

class TurnType(str, Enum):
    STRAIGHT    = "STRAIGHT"
    SLIGHT_LEFT = "SLIGHT_LEFT"
    SLIGHT_RIGHT= "SLIGHT_RIGHT"
    LEFT        = "LEFT"
    RIGHT       = "RIGHT"
    SHARP_LEFT  = "SHARP_LEFT"
    SHARP_RIGHT = "SHARP_RIGHT"
    U_TURN      = "U_TURN"
    ARRIVAL     = "ARRIVAL"
    DEPART      = "DEPART"


# ── Geometry helpers ──────────────────────────────────────────────────────────

def _bearing(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Compass bearing (0° = N, 90° = E) between two WGS-84 points."""
    φ1, φ2 = math.radians(lat1), math.radians(lat2)
    Δλ = math.radians(lon2 - lon1)
    x = math.sin(Δλ) * math.cos(φ2)
    y = math.cos(φ1) * math.sin(φ2) - math.sin(φ1) * math.cos(φ2) * math.cos(Δλ)
    return (math.degrees(math.atan2(x, y)) + 360) % 360


def _haversine_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    R = 6_371_000.0
    φ1, φ2 = math.radians(lat1), math.radians(lat2)
    Δφ = math.radians(lat2 - lat1)
    Δλ = math.radians(lon2 - lon1)
    a = math.sin(Δφ / 2) ** 2 + math.cos(φ1) * math.cos(φ2) * math.sin(Δλ / 2) ** 2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def _angle_delta(bearing_from: float, bearing_to: float) -> float:
    """Signed turn angle (-180..+180). Negative = left, positive = right."""
    delta = (bearing_to - bearing_from + 360) % 360
    if delta > 180:
        delta -= 360
    return delta


def _classify_turn(delta_deg: float) -> TurnType:
    """Map signed bearing delta to a TurnType."""
    abs_d = abs(delta_deg)
    if abs_d < BEARING_STRAIGHT_MAX:
        return TurnType.STRAIGHT
    elif abs_d < BEARING_SLIGHT_MAX:
        return TurnType.SLIGHT_LEFT if delta_deg < 0 else TurnType.SLIGHT_RIGHT
    elif abs_d < BEARING_NORMAL_MAX:
        return TurnType.LEFT if delta_deg < 0 else TurnType.RIGHT
    elif abs_d < BEARING_SHARP_MAX:
        return TurnType.SHARP_LEFT if delta_deg < 0 else TurnType.SHARP_RIGHT
    else:
        return TurnType.U_TURN


def _street_name(G, u: int, v: int) -> str:
    """Extract street name from edge data, return empty string if unnamed."""
    edge_data = G.get_edge_data(u, v)
    if edge_data is None:
        return ""
    # MultiDiGraph: get first key
    if isinstance(edge_data, dict) and 0 in edge_data:
        edge_data = edge_data[0]
    name = edge_data.get("name", "")
    if isinstance(name, list):
        name = name[0] if name else ""
    return str(name) if name else ""


def _is_crossing(G, u: int, v: int) -> bool:
    """Check if this edge is a road crossing/footway crossing."""
    edge_data = G.get_edge_data(u, v)
    if edge_data is None:
        return False
    if isinstance(edge_data, dict) and 0 in edge_data:
        edge_data = edge_data[0]
    highway = edge_data.get("highway", "")
    footway = edge_data.get("footway", "")
    crossing = edge_data.get("crossing", "")
    if isinstance(highway, list):
        highway = highway[0] if highway else ""
    return (
        footway == "crossing"
        or crossing != ""
        or highway == "crossing"
    )


# ── Router ────────────────────────────────────────────────────────────────────

class OfflineRouter:
    """
    Pedestrian route calculator using a locally loaded OSM graph.

    The graph must have been loaded by OfflineMapManager.load_map() before
    calling route(). All computation is local — no network I/O.
    """

    def __init__(self, map_manager):
        self._manager = map_manager

    def route(
        self,
        start_lat: float,
        start_lon: float,
        dest_lat: float,
        dest_lon: float,
    ) -> dict:
        """
        Calculate the shortest pedestrian route between two coordinates.

        Returns:
            {
              "distance_m": float,
              "duration_s": float,
              "nodes": [node_id, ...],
              "coordinates": [[lat, lon], ...],
              "steps": [StepDict, ...],
            }

        Raises:
            RuntimeError  if no offline map is loaded
            ValueError    if no route exists between the points
        """
        try:
            import networkx as nx
        except ImportError:
            raise RuntimeError("networkx is required. Run: pip install networkx")

        G = self._manager.get_graph()
        if G is None:
            raise RuntimeError(
                "No offline map is loaded.\n"
                "Run: python setup_offline_maps.py --place \"<your city>\""
            )

        # Find nearest graph nodes
        orig_node = self._manager.nearest_node(start_lat, start_lon)
        dest_node = self._manager.nearest_node(dest_lat, dest_lon)

        if orig_node is None or dest_node is None:
            raise ValueError("Could not find graph nodes near the given coordinates.")

        if orig_node == dest_node:
            raise ValueError("Start and destination are the same point.")

        # Shortest path by edge 'length' attribute (metres)
        try:
            node_path = nx.shortest_path(G, orig_node, dest_node, weight="length")
        except nx.NetworkXNoPath:
            raise ValueError(
                "No pedestrian route exists between those coordinates in the installed map. "
                "The map area may not have sufficient pedestrian path coverage."
            )
        except nx.NodeNotFound as e:
            raise ValueError(f"Routing node not found in graph: {e}")

        # Build coordinate list
        coords = []
        for node in node_path:
            nd = G.nodes[node]
            coords.append([nd["y"], nd["x"]])  # osmnx stores lat=y, lon=x

        # Compute total distance
        total_m = 0.0
        for u, v in zip(node_path[:-1], node_path[1:]):
            edge_data = G.get_edge_data(u, v)
            if edge_data is None:
                continue
            if isinstance(edge_data, dict) and 0 in edge_data:
                edge_data = edge_data[0]
            total_m += float(edge_data.get("length", 0.0))

        duration_s = total_m / WALK_SPEED_MPS

        # Generate turn-by-turn steps
        steps = self._generate_steps(G, node_path, coords)

        return {
            "distance_m": round(total_m, 1),
            "duration_s": round(duration_s, 0),
            "nodes": node_path,
            "coordinates": coords,
            "steps": steps,
        }

    # ── Step generation ───────────────────────────────────────────────────────

    def _generate_steps(
        self,
        G,
        node_path: list[int],
        coords: list[list[float]],
    ) -> list[dict]:
        """
        Convert a node path into simplified human-readable navigation steps.

        Each step:
            {
              "turn":         TurnType string,
              "distance_m":   float,
              "street_name":  str,
              "is_crossing":  bool,
              "start_coord":  [lat, lon],
              "instruction":  str,   # English instruction string
            }
        """
        if len(node_path) < 2:
            return []

        # Build raw segment list (one per edge)
        segments = []
        for i, (u, v) in enumerate(zip(node_path[:-1], node_path[1:])):
            lat1, lon1 = coords[i]
            lat2, lon2 = coords[i + 1]
            seg_bearing = _bearing(lat1, lon1, lat2, lon2)

            edge_data = G.get_edge_data(u, v)
            if edge_data is None:
                seg_len = _haversine_m(lat1, lon1, lat2, lon2)
            else:
                if isinstance(edge_data, dict) and 0 in edge_data:
                    edge_data = edge_data[0]
                seg_len = float(edge_data.get("length", _haversine_m(lat1, lon1, lat2, lon2)))

            segments.append({
                "u": u, "v": v,
                "bearing": seg_bearing,
                "distance_m": seg_len,
                "street_name": _street_name(G, u, v),
                "is_crossing": _is_crossing(G, u, v),
                "lat": lat1, "lon": lon1,
            })

        # ── Merge consecutive STRAIGHT segments on the same street ────────────
        steps: list[dict] = []
        i = 0

        # First step is always DEPART
        first = segments[0]
        steps.append({
            "turn":        TurnType.DEPART,
            "distance_m":  first["distance_m"],
            "street_name": first["street_name"],
            "is_crossing": first["is_crossing"],
            "start_coord": [first["lat"], first["lon"]],
        })
        current = steps[-1]

        for seg in segments[1:]:
            prev_bearing = segments[i]["bearing"]
            cur_bearing  = seg["bearing"]
            delta        = _angle_delta(prev_bearing, cur_bearing)
            turn         = _classify_turn(delta)

            if (turn == TurnType.STRAIGHT
                    and seg["street_name"] == current["street_name"]
                    and not seg["is_crossing"]):
                # Merge into current step
                current["distance_m"] += seg["distance_m"]
            else:
                current = {
                    "turn":        turn,
                    "distance_m":  seg["distance_m"],
                    "street_name": seg["street_name"],
                    "is_crossing": seg["is_crossing"],
                    "start_coord": [seg["lat"], seg["lon"]],
                }
                steps.append(current)
            i += 1

        # Final step — ARRIVAL
        last_coord = coords[-1]
        steps.append({
            "turn":        TurnType.ARRIVAL,
            "distance_m":  0.0,
            "street_name": "",
            "is_crossing": False,
            "start_coord": last_coord,
        })

        return steps
