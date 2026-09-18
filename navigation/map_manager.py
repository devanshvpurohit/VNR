"""
navigation/map_manager.py — Offline map discovery, loading, and graph access.

Manages locally installed OSM map packages in navigation/data/maps/.
Never makes any internet requests.

Usage:
    manager = OfflineMapManager()
    print(manager.list_maps())          # ["hyderabad", "vijayawada"]
    manager.load_map("hyderabad")
    node = manager.nearest_node(17.36, 78.47)
    results = manager.search_place("Charminar")
    G = manager.get_graph()
"""
from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Optional

from navigation.config import MAPS_DIR
from navigation.geocoder import OfflineGeocoder


class OfflineMapManager:
    """
    Central hub for offline map data.

    A 'map' is a directory under navigation/data/maps/<name>/ containing:
        graph.graphml   — NetworkX pedestrian graph (osmnx format)
        places.sqlite   — offline geocoding database
        metadata.json   — place name, bbox, node/edge counts, etc.
    """

    def __init__(self):
        self._graph = None                      # networkx.MultiDiGraph
        self._metadata: Optional[dict] = None
        self._loaded_name: Optional[str] = None
        self._geocoder: Optional[OfflineGeocoder] = None
        MAPS_DIR.mkdir(parents=True, exist_ok=True)

    # ── Discovery ─────────────────────────────────────────────────────────────

    def list_maps(self) -> list[str]:
        """Return names of all installed offline maps."""
        if not MAPS_DIR.exists():
            return []
        names = []
        for d in sorted(MAPS_DIR.iterdir()):
            if d.is_dir() and (d / "graph.graphml").exists():
                names.append(d.name)
        return names

    def get_metadata(self, map_name: Optional[str] = None) -> Optional[dict]:
        """Return metadata for an installed map. Uses loaded map if name not given."""
        name = map_name or self._loaded_name
        if name is None:
            return None
        meta_path = MAPS_DIR / name / "metadata.json"
        if not meta_path.exists():
            return None
        with open(meta_path) as f:
            return json.load(f)

    # ── Loading ───────────────────────────────────────────────────────────────

    def load_map(self, map_name: str) -> None:
        """
        Load an offline map by name.
        Reads the GraphML and SQLite from disk — no internet access.

        Raises FileNotFoundError if map is not installed.
        """
        map_dir = MAPS_DIR / map_name
        graph_path = map_dir / "graph.graphml"

        if not graph_path.exists():
            installed = self.list_maps()
            hint = (
                f"Installed maps: {', '.join(installed)}" if installed
                else "No offline maps installed."
            )
            raise FileNotFoundError(
                f"No offline map named '{map_name}' found at {graph_path}\n"
                f"{hint}\n"
                "Run: python setup_offline_maps.py --place \"<city name>\""
            )

        print(f"[MAP] Loading graph: {graph_path}")
        try:
            import osmnx as ox
            self._graph = ox.load_graphml(str(graph_path))
        except ImportError:
            # Fallback: load with networkx directly (no osmnx needed at runtime)
            import networkx as nx
            self._graph = nx.read_graphml(str(graph_path))
            # Ensure node coordinates exist as floats
            for node, data in self._graph.nodes(data=True):
                data["x"] = float(data.get("x", 0))
                data["y"] = float(data.get("y", 0))

        self._loaded_name = map_name
        self._metadata = self.get_metadata(map_name)

        # Load geocoder
        try:
            self._geocoder = OfflineGeocoder(map_name)
        except FileNotFoundError:
            print(f"[MAP] Warning: no places.sqlite for {map_name} — geocoding disabled")
            self._geocoder = None

        node_count = self._graph.number_of_nodes()
        edge_count = self._graph.number_of_edges()
        print(f"[MAP] ✅ Loaded '{map_name}': {node_count} nodes, {edge_count} edges")

    def auto_load(self) -> bool:
        """
        Auto-load the first available offline map.
        Returns True if a map was loaded, False if none installed.
        """
        maps = self.list_maps()
        if not maps:
            return False
        self.load_map(maps[0])
        return True

    # ── Graph access ──────────────────────────────────────────────────────────

    def get_graph(self):
        """Return the loaded NetworkX graph, or None if not loaded."""
        return self._graph

    def is_loaded(self) -> bool:
        return self._graph is not None

    # ── Coordinate utilities ──────────────────────────────────────────────────

    def is_inside_map(self, lat: float, lon: float) -> bool:
        """Check whether coordinates are within the map's bounding box."""
        if self._metadata is None:
            return False
        bbox = self._metadata.get("bbox")
        if not bbox:
            return False
        # bbox: {"north", "south", "east", "west"}
        return (
            bbox["south"] <= lat <= bbox["north"]
            and bbox["west"] <= lon <= bbox["east"]
        )

    def nearest_node(self, lat: float, lon: float) -> Optional[int]:
        """
        Find the graph node closest to (lat, lon).
        Uses osmnx.nearest_nodes if available, falls back to brute-force.
        """
        if self._graph is None:
            return None

        try:
            import osmnx as ox
            node = ox.nearest_nodes(self._graph, lon, lat)
            return node
        except Exception:
            pass

        # Brute-force fallback: iterate all nodes
        best_node = None
        best_dist = float("inf")
        for node, data in self._graph.nodes(data=True):
            nlat = float(data.get("y", 0))
            nlon = float(data.get("x", 0))
            d = self._haversine_m(lat, lon, nlat, nlon)
            if d < best_dist:
                best_dist = d
                best_node = node
        return best_node

    def node_coords(self, node_id) -> tuple[float, float]:
        """Return (lat, lon) for a graph node."""
        data = self._graph.nodes[node_id]
        return float(data["y"]), float(data["x"])

    # ── Geocoding ─────────────────────────────────────────────────────────────

    def search_place(
        self,
        query: str,
        current_location: Optional[dict] = None,
        limit: int = 5,
    ) -> list[dict]:
        """Search locally stored OSM places. Requires geocoder."""
        if self._geocoder is None:
            return []
        return self._geocoder.search(query, current_location=current_location, limit=limit)

    # ── Internal helpers ──────────────────────────────────────────────────────

    @staticmethod
    def _haversine_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        R = 6_371_000.0
        φ1, φ2 = math.radians(lat1), math.radians(lat2)
        Δφ = math.radians(lat2 - lat1)
        Δλ = math.radians(lon2 - lon1)
        a = math.sin(Δφ / 2) ** 2 + math.cos(φ1) * math.cos(φ2) * math.sin(Δλ / 2) ** 2
        return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

    def no_map_error_message(self) -> str:
        return (
            "No offline map installed.\n"
            "Run setup_offline_maps.py while online to create one.\n"
            "Example: python setup_offline_maps.py --place \"Hyderabad, Telangana, India\""
        )
