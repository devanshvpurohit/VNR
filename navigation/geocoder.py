"""
navigation/geocoder.py — Fully offline place search using a local SQLite database.

The database is built by setup_offline_maps.py from OSM node/way attributes
(amenity, name, shop, tourism, etc.) and is stored at:
    navigation/data/maps/<map_name>/places.sqlite

After setup, zero internet is required.

Usage:
    gc = OfflineGeocoder("hyderabad")
    results = gc.search("Charminar", current_location={"lat":17.36,"lon":78.47})
    results = gc.search("nearest hospital", current_location={"lat":17.36,"lon":78.47})
"""
from __future__ import annotations

import math
import re
import sqlite3
from pathlib import Path
from typing import Optional

from navigation.config import MAPS_DIR, NEAREST_CATEGORIES, NEAREST_HI_ALIASES


def _haversine_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Return distance in metres between two WGS-84 coordinates."""
    R = 6_371_000.0
    φ1, φ2 = math.radians(lat1), math.radians(lat2)
    Δφ = math.radians(lat2 - lat1)
    Δλ = math.radians(lon2 - lon1)
    a = math.sin(Δφ / 2) ** 2 + math.cos(φ1) * math.cos(φ2) * math.sin(Δλ / 2) ** 2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


class OfflineGeocoder:
    """
    Local place search backed by SQLite built from OSM data.

    The DB has one table:
        places(id INTEGER PRIMARY KEY,
               name TEXT,
               type TEXT,
               lat  REAL,
               lon  REAL,
               tags TEXT)    -- JSON blob of raw OSM tags
    """

    def __init__(self, map_name: str):
        self.map_name = map_name
        self._db_path = MAPS_DIR / map_name / "places.sqlite"
        self._conn: Optional[sqlite3.Connection] = None
        self._load()

    def _load(self):
        if not self._db_path.exists():
            raise FileNotFoundError(
                f"Offline geocoding database not found: {self._db_path}\n"
                "Run: python setup_offline_maps.py --place \"<your city>\""
            )
        self._conn = sqlite3.connect(str(self._db_path), check_same_thread=False)
        self._conn.row_factory = sqlite3.Row

    def close(self):
        if self._conn:
            self._conn.close()

    # ── Public API ────────────────────────────────────────────────────────────

    def search(
        self,
        query: str,
        current_location: Optional[dict] = None,
        limit: int = 5,
    ) -> list[dict]:
        """
        Search locally stored OSM places.

        Supports:
          • Named place: "Charminar", "IARE", "home"
          • Nearest category: "nearest hospital", "nearest bus stop"
          • Hindi category: "नजदीकी अस्पताल"

        Returns list of dicts:
            {"name", "lat", "lon", "type", "distance_m"}
        Sorted by (distance if location given, else text score).
        """
        q = query.strip()

        # ── Resolve Hindi nearest queries ─────────────────────────────────────
        for hi_keyword, en_category in NEAREST_HI_ALIASES.items():
            if hi_keyword in q:
                q = f"nearest {en_category}"
                break

        # ── Detect "nearest X" pattern ────────────────────────────────────────
        nearest_match = re.match(r"nearest\s+(.+)", q, re.IGNORECASE)
        if nearest_match:
            category_str = nearest_match.group(1).strip().lower()
            return self._search_nearest_category(category_str, current_location, limit)

        # ── Named place search ────────────────────────────────────────────────
        return self._search_by_name(q, current_location, limit)

    # ── Internal helpers ──────────────────────────────────────────────────────

    def _search_by_name(
        self,
        query: str,
        current_location: Optional[dict],
        limit: int,
    ) -> list[dict]:
        """Full-text name search with distance ranking."""
        rows = self._conn.execute(
            "SELECT name, type, lat, lon FROM places "
            "WHERE lower(name) LIKE ? OR lower(tags) LIKE ? "
            "LIMIT 50",
            (f"%{query.lower()}%", f"%{query.lower()}%"),
        ).fetchall()

        results = []
        for row in rows:
            dist = None
            if current_location:
                dist = _haversine_m(
                    current_location["lat"], current_location["lon"],
                    row["lat"], row["lon"],
                )
            results.append({
                "name": row["name"] or "Unknown",
                "lat": row["lat"],
                "lon": row["lon"],
                "type": row["type"] or "",
                "distance_m": round(dist, 1) if dist is not None else None,
            })

        # Sort: closest first if we have a location, else alphabetical
        if current_location:
            results.sort(key=lambda r: r["distance_m"] or 1e9)
        else:
            results.sort(key=lambda r: r["name"])

        return results[:limit]

    def _search_nearest_category(
        self,
        category_str: str,
        current_location: Optional[dict],
        limit: int,
    ) -> list[dict]:
        """Find nearest places matching an OSM amenity/type category."""
        # Resolve canonical category
        type_keywords: list[str] = []
        for cat_name, keywords in NEAREST_CATEGORIES.items():
            if category_str in cat_name or cat_name in category_str:
                type_keywords = keywords
                break
            # substring match
            if any(kw in category_str for kw in keywords):
                type_keywords = keywords
                break

        if not type_keywords:
            # fallback: use the raw query as keyword
            type_keywords = [category_str]

        clauses = " OR ".join(
            ["lower(type) LIKE ? OR lower(tags) LIKE ?"] * len(type_keywords)
        )
        params = []
        for kw in type_keywords:
            params += [f"%{kw}%", f"%{kw}%"]

        rows = self._conn.execute(
            f"SELECT name, type, lat, lon FROM places WHERE {clauses} LIMIT 200",
            params,
        ).fetchall()

        results = []
        for row in rows:
            dist = None
            if current_location:
                dist = _haversine_m(
                    current_location["lat"], current_location["lon"],
                    row["lat"], row["lon"],
                )
            results.append({
                "name": row["name"] or category_str.title(),
                "lat": row["lat"],
                "lon": row["lon"],
                "type": row["type"] or "",
                "distance_m": round(dist, 1) if dist is not None else None,
            })

        if current_location:
            results.sort(key=lambda r: r["distance_m"] or 1e9)

        return results[:limit]

    def count_places(self) -> int:
        """Return total number of places in the local database."""
        row = self._conn.execute("SELECT COUNT(*) FROM places").fetchone()
        return row[0] if row else 0
