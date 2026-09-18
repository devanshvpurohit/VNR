"""
setup_offline_maps.py — One-time offline map preparation for SURDAS.

Run ONCE while internet is available. After this script completes,
all navigation functionality works with zero internet access.

Usage:
    python setup_offline_maps.py --place "Hyderabad, Telangana, India"
    python setup_offline_maps.py --place "Vijayawada, Andhra Pradesh, India"
    python setup_offline_maps.py --bbox 17.45 17.25 78.55 78.35

Output:
    navigation/data/maps/<normalized_name>/
        graph.graphml
        places.sqlite
        metadata.json
        README.md

Requirements:
    pip install osmnx shapely

After setup, the generated map directory is listed in .gitignore.
"""

import argparse
import json
import os
import re
import sqlite3
import sys
import traceback
from datetime import datetime, timezone
from pathlib import Path

# ── Ensure we can import navigation package ───────────────────────────────────
sys.path.insert(0, str(Path(__file__).parent))
from navigation.config import MAPS_DIR, OSM_NETWORK_TYPE


# ── Helpers ───────────────────────────────────────────────────────────────────

def _normalize_name(place: str) -> str:
    """Convert 'Hyderabad, Telangana, India' → 'hyderabad'."""
    first = place.split(",")[0].strip().lower()
    return re.sub(r"[^a-z0-9_-]", "_", first).strip("_") or "map"


def _gitignore_add(root: Path, pattern: str):
    """Add a pattern to .gitignore if not already present."""
    gi = root / ".gitignore"
    if gi.exists():
        existing = gi.read_text(encoding="utf-8")
        if pattern in existing:
            return
        gi.write_text(existing.rstrip() + f"\n{pattern}\n", encoding="utf-8")
    else:
        gi.write_text(f"{pattern}\n", encoding="utf-8")
    print(f"[SETUP] .gitignore updated with: {pattern}")


def _extract_place_nodes(G) -> list[dict]:
    """
    Extract nodes with useful place information from the OSM graph.
    Pulls: amenity, name, shop, tourism, railway, highway tags.
    Returns list of dicts for SQLite insertion.
    """
    places = []
    for node_id, data in G.nodes(data=True):
        name = data.get("name", "")
        if isinstance(name, list):
            name = name[0] if name else ""

        # Collect useful type tag
        ptype = (
            data.get("amenity")
            or data.get("shop")
            or data.get("tourism")
            or data.get("railway")
            or data.get("leisure")
            or data.get("historic")
            or data.get("highway")
            or ""
        )
        if isinstance(ptype, list):
            ptype = ptype[0] if ptype else ""

        lat = float(data.get("y", 0))
        lon = float(data.get("x", 0))

        if not lat or not lon:
            continue

        # Include if it has a name OR a meaningful type
        if name or (ptype and ptype not in ("turning_circle", "traffic_signals",
                                             "crossing", "give_way", "stop")):
            tags_subset = {
                k: v for k, v in data.items()
                if k in ("amenity", "name", "shop", "tourism", "railway",
                         "leisure", "historic", "highway", "addr:street",
                         "opening_hours", "phone", "website", "bus", "bus_stop")
                and v
            }
            places.append({
                "name": str(name),
                "type": str(ptype),
                "lat": lat,
                "lon": lon,
                "tags": json.dumps(tags_subset, ensure_ascii=False),
            })

    return places


def _extract_edge_places(G) -> list[dict]:
    """
    Extract named streets/roads from edges for the geocoding DB.
    """
    seen = set()
    places = []
    for u, v, data in G.edges(data=True):
        if isinstance(data, dict) and 0 in data:
            data = data[0]

        name = data.get("name", "")
        if isinstance(name, list):
            name = name[0] if name else ""
        if not name or name in seen:
            continue
        seen.add(name)

        # Use midpoint of edge for lat/lon
        un = G.nodes[u]
        vn = G.nodes[v]
        lat = (float(un.get("y", 0)) + float(vn.get("y", 0))) / 2
        lon = (float(un.get("x", 0)) + float(vn.get("x", 0))) / 2

        if not lat or not lon:
            continue

        highway = data.get("highway", "road")
        if isinstance(highway, list):
            highway = highway[0] if highway else "road"

        places.append({
            "name": str(name),
            "type": str(highway),
            "lat": lat,
            "lon": lon,
            "tags": json.dumps({"highway": highway, "name": name}, ensure_ascii=False),
        })

    return places


def _build_places_db(db_path: Path, G) -> int:
    """Build SQLite place database from OSM graph. Returns record count."""
    print("[SETUP] Building offline geocoding database...")
    places = _extract_place_nodes(G)
    street_places = _extract_edge_places(G)
    all_places = places + street_places
    print(f"[SETUP] Found {len(places)} POI nodes + {len(street_places)} named streets")

    conn = sqlite3.connect(str(db_path))
    cur = conn.cursor()
    cur.execute("DROP TABLE IF EXISTS places")
    cur.execute("""
        CREATE TABLE places (
            id   INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            type TEXT,
            lat  REAL NOT NULL,
            lon  REAL NOT NULL,
            tags TEXT
        )
    """)
    cur.execute("CREATE INDEX idx_name ON places(lower(name))")
    cur.execute("CREATE INDEX idx_type ON places(lower(type))")

    cur.executemany(
        "INSERT INTO places (name, type, lat, lon, tags) VALUES (:name, :type, :lat, :lon, :tags)",
        all_places,
    )
    conn.commit()
    count = cur.execute("SELECT COUNT(*) FROM places").fetchone()[0]
    conn.close()
    print(f"[SETUP] Geocoding DB: {count} entries written to {db_path}")
    return count


def _write_metadata(meta_path: Path, place: str, bbox: dict, G, map_dir: Path):
    """Write metadata.json for the map package."""
    meta = {
        "place": place,
        "bbox": bbox,
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "crs": "EPSG:4326",
        "network_type": OSM_NETWORK_TYPE,
        "node_count": G.number_of_nodes(),
        "edge_count": G.number_of_edges(),
        "graph_file": str(map_dir / "graph.graphml"),
        "places_db": str(map_dir / "places.sqlite"),
    }
    meta_path.write_text(json.dumps(meta, indent=2, ensure_ascii=False), encoding="utf-8")
    return meta


def _write_map_readme(map_dir: Path, place: str, meta: dict):
    """Write per-map README."""
    readme = f"""# SURDAS Offline Map — {place}

Generated: {meta['created_utc']}
Network type: {meta['network_type']}
Nodes: {meta['node_count']}
Edges: {meta['edge_count']}
CRS: {meta['crs']}

## Bounding Box
North: {meta['bbox']['north']}
South: {meta['bbox']['south']}
East:  {meta['bbox']['east']}
West:  {meta['bbox']['west']}

## Files
- graph.graphml   — pedestrian routing graph
- places.sqlite   — offline geocoding database
- metadata.json   — map metadata

## Refresh
Run setup_offline_maps.py again while online to refresh this map.
"""
    (map_dir / "README.md").write_text(readme, encoding="utf-8")


# ── Main download + build ─────────────────────────────────────────────────────

def setup_by_place(place: str) -> bool:
    """Download and build an offline map for a named place."""
    try:
        import osmnx as ox
    except ImportError:
        print("❌ osmnx is not installed. Run: pip install osmnx")
        return False

    map_name = _normalize_name(place)
    map_dir = MAPS_DIR / map_name
    map_dir.mkdir(parents=True, exist_ok=True)

    graph_path  = map_dir / "graph.graphml"
    places_path = map_dir / "places.sqlite"
    meta_path   = map_dir / "metadata.json"

    print(f"[SETUP] Downloading OSM pedestrian graph for: {place}")
    print("[SETUP] This may take a few minutes depending on city size...")

    try:
        # Suppress osmnx HTTP logs
        import logging
        logging.getLogger("osmnx").setLevel(logging.WARNING)

        G = ox.graph_from_place(
            place,
            network_type=OSM_NETWORK_TYPE,
            simplify=True,
            retain_all=False,
        )
    except Exception as e:
        print(f"❌ Failed to download graph for '{place}':\n   {e}")
        print()
        print("Possible causes:")
        print("  • No internet connection")
        print("  • Place name not recognised by Nominatim")
        print("  • Try a more specific place name, e.g. 'Hyderabad, Telangana, India'")
        return False

    print(f"[SETUP] Graph downloaded: {G.number_of_nodes()} nodes, {G.number_of_edges()} edges")
    print(f"[SETUP] Saving graph to {graph_path} ...")

    try:
        ox.save_graphml(G, filepath=str(graph_path))
    except Exception as e:
        print(f"❌ Failed to save graph: {e}")
        return False

    # Compute bounding box
    lats = [d["y"] for _, d in G.nodes(data=True)]
    lons = [d["x"] for _, d in G.nodes(data=True)]
    bbox = {
        "north": max(lats), "south": min(lats),
        "east":  max(lons), "west":  min(lons),
    }

    # Build geocoding DB
    _build_places_db(places_path, G)

    # Write metadata
    meta = _write_metadata(meta_path, place, bbox, G, map_dir)
    _write_map_readme(map_dir, place, meta)

    # Update .gitignore
    _gitignore_add(Path(__file__).parent, "navigation/data/maps/")

    # Success summary
    print()
    print("✅ Offline map created")
    print(f"Place: {place}")
    print(f"Nodes: {G.number_of_nodes()}")
    print(f"Edges: {G.number_of_edges()}")
    print(f"Graph: {graph_path}")
    print("Internet required for navigation: NO")
    print()
    return True


def setup_by_bbox(north: float, south: float, east: float, west: float) -> bool:
    """Download and build an offline map for a bounding box."""
    try:
        import osmnx as ox
    except ImportError:
        print("❌ osmnx is not installed. Run: pip install osmnx")
        return False

    map_name = f"bbox_{north:.3f}_{south:.3f}_{east:.3f}_{west:.3f}"
    map_name = map_name.replace(".", "p").replace("-", "n")
    map_dir = MAPS_DIR / map_name
    map_dir.mkdir(parents=True, exist_ok=True)

    graph_path  = map_dir / "graph.graphml"
    places_path = map_dir / "places.sqlite"
    meta_path   = map_dir / "metadata.json"

    print(f"[SETUP] Downloading OSM graph for bbox: N{north} S{south} E{east} W{west}")

    try:
        import logging
        logging.getLogger("osmnx").setLevel(logging.WARNING)

        G = ox.graph_from_bbox(
            north, south, east, west,
            network_type=OSM_NETWORK_TYPE,
            simplify=True,
            retain_all=False,
        )
    except Exception as e:
        print(f"❌ Failed to download graph for bbox:\n   {e}")
        return False

    print(f"[SETUP] Graph: {G.number_of_nodes()} nodes, {G.number_of_edges()} edges")
    ox.save_graphml(G, filepath=str(graph_path))

    bbox = {"north": north, "south": south, "east": east, "west": west}
    _build_places_db(places_path, G)

    place_label = f"BBox N{north} S{south} E{east} W{west}"
    meta = _write_metadata(meta_path, place_label, bbox, G, map_dir)
    _write_map_readme(map_dir, place_label, meta)
    _gitignore_add(Path(__file__).parent, "navigation/data/maps/")

    print()
    print("✅ Offline map created")
    print(f"Bounding box: N{north} S{south} E{east} W{west}")
    print(f"Nodes: {G.number_of_nodes()}")
    print(f"Edges: {G.number_of_edges()}")
    print(f"Graph: {graph_path}")
    print("Internet required for navigation: NO")
    print()
    return True


# ── CLI ───────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="SURDAS offline map setup — download and prepare map data for offline navigation.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python setup_offline_maps.py --place "Hyderabad, Telangana, India"
  python setup_offline_maps.py --place "Vijayawada, Andhra Pradesh, India"
  python setup_offline_maps.py --bbox 17.45 17.25 78.55 78.35

After setup, verify with:
  python -m navigation.offline_test
        """,
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument(
        "--place", type=str,
        help='Named place, e.g. "Hyderabad, Telangana, India"',
    )
    group.add_argument(
        "--bbox", nargs=4, type=float, metavar=("NORTH", "SOUTH", "EAST", "WEST"),
        help="Bounding box in decimal degrees: north south east west",
    )
    args = parser.parse_args()

    if args.place:
        ok = setup_by_place(args.place)
    else:
        north, south, east, west = args.bbox
        ok = setup_by_bbox(north, south, east, west)

    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
