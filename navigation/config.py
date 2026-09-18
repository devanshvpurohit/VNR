"""
navigation/config.py — Centralized constants for the SURDAS offline navigation system.

All tuneable parameters live here. No logic — just values.
"""
from pathlib import Path

# ── Paths ─────────────────────────────────────────────────────────────────────
# Root of the project (one level above this file)
_NAV_DIR  = Path(__file__).parent
MAPS_DIR  = _NAV_DIR / "data" / "maps"
DATA_DIR  = _NAV_DIR / "data"
ROUTE_HTML = DATA_DIR / "current_route.html"

# ── Pedestrian physics ────────────────────────────────────────────────────────
WALK_SPEED_MPS     = 1.4   # m/s  (~5 km/h, average pedestrian)
WALK_SPEED_KMH     = WALK_SPEED_MPS * 3.6

# ── osmnx network type ────────────────────────────────────────────────────────
OSM_NETWORK_TYPE = "walk"   # pedestrian-accessible ways only

# ── Navigation thresholds ─────────────────────────────────────────────────────
# Meters off the planned route before triggering reroute
REROUTE_THRESHOLD_M     = 50.0

# Announce upcoming turn when within this many meters
TURN_ANNOUNCE_DISTANCE_M = 30.0   # announce turn
TURN_WARN_DISTANCE_M     = 15.0   # "Turn now"

# Minimum distance change before announcing progress again (avoids spam)
PROGRESS_ANNOUNCE_MIN_M  = 20.0

# How far a node must be before we consider arrival (GPS imprecision buffer)
ARRIVAL_THRESHOLD_M      = 25.0

# ── Bearing / direction thresholds (degrees) ──────────────────────────────────
BEARING_STRAIGHT_MAX     = 20
BEARING_SLIGHT_MAX       = 45
BEARING_NORMAL_MAX       = 100
BEARING_SHARP_MAX        = 160
# >= BEARING_SHARP_MAX  → U_TURN

# ── Step simplification ───────────────────────────────────────────────────────
# Consecutive STRAIGHT segments shorter than this (m) are merged
MERGE_STRAIGHT_M = 15.0

# ── OSM amenity categories for "nearest X" queries ───────────────────────────
NEAREST_CATEGORIES: dict[str, list[str]] = {
    "hospital":        ["hospital", "clinic", "doctors"],
    "pharmacy":        ["pharmacy", "chemist"],
    "bus stop":        ["bus_stop", "bus stop"],
    "railway station": ["station", "train_station", "railway_station"],
    "restaurant":      ["restaurant", "food_court", "cafe", "fast_food"],
    "atm":             ["atm", "bank"],
    "police":          ["police", "police_station"],
    "school":          ["school", "college", "university"],
    "temple":          ["place_of_worship", "temple", "mandir"],
    "mosque":          ["place_of_worship", "mosque", "masjid"],
    "church":          ["place_of_worship", "church"],
    "park":            ["park", "garden", "playground"],
    "hotel":           ["hotel", "hostel", "guest_house"],
    "supermarket":     ["supermarket", "grocery", "convenience"],
    "petrol station":  ["fuel", "petrol_station", "gas_station"],
}

# Hindi category aliases → English canonical
NEAREST_HI_ALIASES: dict[str, str] = {
    "अस्पताल":       "hospital",
    "दवाखाना":       "pharmacy",
    "मेडिकल":        "pharmacy",
    "बस स्टॉप":      "bus stop",
    "रेलवे स्टेशन":  "railway station",
    "रेस्तरां":      "restaurant",
    "खाने की जगह":  "restaurant",
    "एटीएम":         "atm",
    "बैंक":          "atm",
    "पुलिस":         "police",
    "स्कूल":         "school",
    "मंदिर":         "temple",
    "मस्जिद":        "mosque",
    "पार्क":         "park",
    "होटल":          "hotel",
    "पेट्रोल":       "petrol station",
}
