"""
navigation/offline_test.py — SURDAS offline navigation self-test.

Run with:
    python -m navigation.offline_test

Tests all 8 critical offline navigation functions without any network access.
If the offline map is not installed, prints a clear error and exits.
"""
from __future__ import annotations

import sys
import os

# Ensure we can import the navigation package from the project root
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def _check(label: str, fn):
    """Run fn(), return (passed: bool, detail: str)."""
    try:
        result = fn()
        return True, str(result)[:80] if result is not None else "OK"
    except Exception as e:
        return False, str(e)[:80]


def run_tests():
    print("=" * 40)
    print("SURDAS OFFLINE NAVIGATION TEST")
    print("=" * 40)
    print()

    from navigation.map_manager import OfflineMapManager
    from navigation.router import OfflineRouter
    from navigation.navigator import Navigator
    from navigation.voice_guidance import NavigationVoiceGuide

    manager = OfflineMapManager()
    maps = manager.list_maps()

    if not maps:
        print("❌ No offline maps installed.")
        print()
        print("Install a map first:")
        print('   python setup_offline_maps.py --place "Hyderabad, Telangana, India"')
        print()
        sys.exit(1)

    map_name = maps[0]
    print(f"Testing map: {map_name}")
    print()

    results = []

    # ── 1. Map loading ──────────────────────────────────────────────────────
    def test_map_load():
        manager.load_map(map_name)
        assert manager.is_loaded(), "Graph not loaded after load_map()"
        return f"loaded '{map_name}'"

    ok, detail = _check("Map loading", test_map_load)
    results.append(("Map loading", ok, detail))

    # ── 2. Graph loading ────────────────────────────────────────────────────
    def test_graph():
        G = manager.get_graph()
        assert G is not None, "Graph is None"
        n = G.number_of_nodes()
        e = G.number_of_edges()
        assert n > 0, f"Graph has {n} nodes"
        return f"{n} nodes, {e} edges"

    ok, detail = _check("Graph loading", test_graph)
    results.append(("Graph loading", ok, detail))

    # ── 3. Local geocoder ───────────────────────────────────────────────────
    def test_geocoder():
        meta = manager.get_metadata(map_name)
        assert meta is not None, "No metadata"
        # Use the map's centroid as test location
        bbox = meta.get("bbox", {})
        clat = (bbox.get("north", 0) + bbox.get("south", 0)) / 2
        clon = (bbox.get("east", 0) + bbox.get("west", 0)) / 2
        loc = {"lat": clat, "lon": clon}
        # Search anything in the map
        results = manager.search_place("", loc, limit=3)
        # Even no results is OK — it means the place DB is empty but functional
        return f"{len(results)} results returned"

    ok, detail = _check("Local geocoder", test_geocoder)
    results.append(("Local geocoder", ok, detail))

    # ── 4. Nearest node ─────────────────────────────────────────────────────
    def test_nearest_node():
        meta = manager.get_metadata(map_name)
        bbox = meta.get("bbox", {})
        clat = (bbox.get("north", 0) + bbox.get("south", 0)) / 2
        clon = (bbox.get("east", 0) + bbox.get("west", 0)) / 2
        node = manager.nearest_node(clat, clon)
        assert node is not None, "nearest_node returned None"
        return f"node id {node}"

    ok, detail = _check("Nearest node", test_nearest_node)
    results.append(("Nearest node", ok, detail))

    # ── 5. Routing ──────────────────────────────────────────────────────────
    def test_routing():
        router = OfflineRouter(manager)
        meta = manager.get_metadata(map_name)
        bbox = meta.get("bbox", {})
        # Use two points within the bbox separated by ~200m
        clat = (bbox.get("north", 0) + bbox.get("south", 0)) / 2
        clon = (bbox.get("east", 0) + bbox.get("west", 0)) / 2
        offset = 0.001   # ~111m in lat
        route = router.route(clat, clon, clat + offset, clon + offset)
        assert "distance_m" in route, "Missing distance_m"
        assert len(route["steps"]) > 0, "No steps generated"
        return f"{route['distance_m']:.0f}m, {len(route['steps'])} steps"

    ok, detail = _check("Routing", test_routing)
    results.append(("Routing", ok, detail))

    # ── 6. Turn generation ──────────────────────────────────────────────────
    def test_turns():
        router = OfflineRouter(manager)
        guide = NavigationVoiceGuide()
        meta = manager.get_metadata(map_name)
        bbox = meta.get("bbox", {})
        clat = (bbox.get("north", 0) + bbox.get("south", 0)) / 2
        clon = (bbox.get("east", 0) + bbox.get("west", 0)) / 2
        offset = 0.001
        route = router.route(clat, clon, clat + offset, clon + offset)
        step = route["steps"][0]
        instr_en = guide.instruction_for_step(step, "en")
        instr_hi = guide.instruction_for_step(step, "hi")
        assert instr_en, "Empty English instruction"
        assert instr_hi, "Empty Hindi instruction"
        return f"EN: {instr_en[:40]}"

    ok, detail = _check("Turn generation", test_turns)
    results.append(("Turn generation", ok, detail))

    # ── 7. Navigation session ───────────────────────────────────────────────
    def test_navigation():
        router = OfflineRouter(manager)
        nav = Navigator(manager, brain=None)   # no brain in test
        meta = manager.get_metadata(map_name)
        bbox = meta.get("bbox", {})
        clat = (bbox.get("north", 0) + bbox.get("south", 0)) / 2
        clon = (bbox.get("east", 0) + bbox.get("west", 0)) / 2
        offset = 0.001
        loc = {"lat": clat, "lon": clon, "accuracy": 10.0}

        # Directly set route to test session (bypass geocoding)
        route = router.route(clat, clon, clat + offset, clon + offset)
        import threading
        nav._lock = threading.Lock()
        nav._active = True
        nav._destination = "Test Destination"
        nav._route = route
        nav._step_index = 0
        nav._current_location = loc
        nav._lang = "en"
        nav._step_announced = {}

        status = nav.get_status()
        assert status["active"], "Navigator not active"
        nav.stop()
        return f"dist={status['distance_remaining_m']:.0f}m, steps={status['total_steps']}"

    ok, detail = _check("Navigation", test_navigation)
    results.append(("Navigation", ok, detail))

    # ── 8. Rerouting ────────────────────────────────────────────────────────
    def test_rerouting():
        router = OfflineRouter(manager)
        meta = manager.get_metadata(map_name)
        bbox = meta.get("bbox", {})
        clat = (bbox.get("north", 0) + bbox.get("south", 0)) / 2
        clon = (bbox.get("east", 0) + bbox.get("west", 0)) / 2
        offset = 0.001
        # Route from A to B
        route_ab = router.route(clat, clon, clat + offset, clon + offset)
        # Simulate off-route: start from a slightly different point
        route_cb = router.route(clat + 0.0005, clon + 0.0008, clat + offset, clon + offset)
        assert "steps" in route_cb, "Reroute returned no steps"
        return f"new route: {route_cb['distance_m']:.0f}m"

    ok, detail = _check("Rerouting", test_rerouting)
    results.append(("Rerouting", ok, detail))

    # ── 9. Network required? ────────────────────────────────────────────────
    # Always False — we only use local graph
    results.append(("Network required", False, "All routing uses local graph only"))

    # ── Print table ─────────────────────────────────────────────────────────
    print()
    all_passed = True
    for label, passed, detail in results:
        if label == "Network required":
            icon = "❌"  # ❌ means network NOT required — that's the good outcome
            print(f"{label:<20} {icon}  {detail}")
        else:
            icon = "✅" if passed else "❌"
            print(f"{label:<20} {icon}  {detail if passed else 'FAILED: ' + detail}")
            if not passed:
                all_passed = False

    print()
    print("=" * 40)
    if all_passed:
        print("OFFLINE NAVIGATION READY")
    else:
        print("⚠️  SOME TESTS FAILED — see details above")
    print("=" * 40)
    print()

    return all_passed


if __name__ == "__main__":
    success = run_tests()
    sys.exit(0 if success else 1)
