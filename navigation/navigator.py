"""
navigation/navigator.py — Navigation session management for SURDAS.

Responsibilities:
  • start navigation to a destination (geocode → route → announce)
  • track current position via update_location()
  • announce upcoming turns at the right distance
  • detect deviation from route and trigger local rerouting
  • announce arrival
  • stop navigation
  • repeat last instruction

Thread-safe: update_location() may be called from a background GPS thread.
No internet access. All geocoding/routing uses local data.

Usage:
    nav = Navigator(map_manager, brain)
    nav.start("Charminar", current_location=loc_dict)
    nav.update_location(new_loc_dict)    # called periodically
    nav.stop()
"""
from __future__ import annotations

import math
import threading
import time
from typing import Optional, TYPE_CHECKING

from navigation.map_manager import OfflineMapManager
from navigation.router import OfflineRouter
from navigation.voice_guidance import NavigationVoiceGuide
from navigation.config import (
    REROUTE_THRESHOLD_M,
    TURN_ANNOUNCE_DISTANCE_M,
    TURN_WARN_DISTANCE_M,
    ARRIVAL_THRESHOLD_M,
    PROGRESS_ANNOUNCE_MIN_M,
)

if TYPE_CHECKING:
    pass   # avoid circular imports with brain


def _haversine_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    R = 6_371_000.0
    φ1, φ2 = math.radians(lat1), math.radians(lat2)
    Δφ = math.radians(lat2 - lat1)
    Δλ = math.radians(lon2 - lon1)
    a = math.sin(Δφ / 2) ** 2 + math.cos(φ1) * math.cos(φ2) * math.sin(Δλ / 2) ** 2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


class Navigator:
    """
    Navigation session controller.

    Calls brain.voice.speak() directly for instructions.
    The brain object is passed in so we can use its existing VoiceEngine
    without creating a parallel TTS system.
    """

    def __init__(self, map_manager: OfflineMapManager, brain=None):
        self._manager = map_manager
        self._router = OfflineRouter(map_manager)
        self._brain = brain          # SurdasBrain or SurdasWebcamTester
        self._guide = NavigationVoiceGuide()
        self._lock = threading.Lock()

        # Session state
        self._active = False
        self._destination: Optional[str] = None
        self._route: Optional[dict] = None
        self._step_index: int = 0
        self._current_location: Optional[dict] = None
        self._last_instruction: str = ""
        self._last_progress_m: float = 0.0
        self._rerouting: bool = False
        self._lang: str = "en"

        # Anti-spam: track last announce time per step index
        self._step_announced: dict[int, float] = {}

    # ── Public API ────────────────────────────────────────────────────────────

    def start(
        self,
        destination: str,
        current_location: Optional[dict] = None,
        lang: str = "en",
    ) -> bool:
        """
        Start navigation to destination.
        Geocodes locally, calculates route locally, speaks first instruction.

        Returns True if navigation started, False on error (error spoken aloud).
        """
        if not self._manager.is_loaded():
            if not self._manager.auto_load():
                self._speak(self._manager.no_map_error_message(), lang)
                return False

        loc = current_location or self._current_location
        if loc is None:
            self._speak(NavigationVoiceGuide.gps_unavailable(lang), lang)
            return False

        # ── Geocode destination ───────────────────────────────────────────────
        results = self._manager.search_place(destination, current_location=loc, limit=3)
        if not results:
            self._speak(NavigationVoiceGuide.destination_not_found(destination, lang), lang)
            return False

        best = results[0]
        dest_lat, dest_lon = best["lat"], best["lon"]
        dest_name = best["name"]

        # ── Calculate route ───────────────────────────────────────────────────
        try:
            route = self._router.route(
                loc["lat"], loc["lon"],
                dest_lat, dest_lon,
            )
        except ValueError as e:
            self._speak(NavigationVoiceGuide.no_route(dest_name, lang), lang)
            print(f"[NAV] Route error: {e}")
            return False
        except RuntimeError as e:
            self._speak(str(e), lang)
            return False

        with self._lock:
            self._active = True
            self._destination = dest_name
            self._route = route
            self._step_index = 0
            self._current_location = loc
            self._last_progress_m = 0.0
            self._rerouting = False
            self._lang = lang
            self._step_announced = {}

        # ── Announce start ────────────────────────────────────────────────────
        start_msg = NavigationVoiceGuide.navigation_started(
            dest_name, route["distance_m"], lang
        )
        self._speak(start_msg, lang)
        time.sleep(0.3)
        self._announce_current_step(lang)
        return True

    def stop(self, lang: str = "en") -> None:
        """Stop navigation session."""
        with self._lock:
            was_active = self._active
            self._active = False
            self._route = None
            self._destination = None
            self._step_index = 0

        if was_active:
            self._speak(NavigationVoiceGuide.navigation_stopped(lang), lang)

    def update_location(self, location: dict) -> None:
        """
        Called periodically with a new GPS location dict.
        Drives step advancement, deviation detection, and rerouting.
        """
        if not location:
            return

        with self._lock:
            if not self._active or self._route is None:
                self._current_location = location
                return
            self._current_location = location
            lang = self._lang
            route = self._route
            step_index = self._step_index
            steps = route["steps"]

        lat, lon = location["lat"], location["lon"]

        # ── Check arrival ──────────────────────────────────────────────────────
        final_coord = route["coordinates"][-1]
        dist_to_dest = _haversine_m(lat, lon, final_coord[0], final_coord[1])
        if dist_to_dest <= ARRIVAL_THRESHOLD_M:
            self._on_arrival(lang)
            return

        # ── Find nearest step ──────────────────────────────────────────────────
        best_step_idx, dist_to_route = self._nearest_step_index(lat, lon, steps, step_index)

        # ── Deviation check ────────────────────────────────────────────────────
        if dist_to_route > REROUTE_THRESHOLD_M and not self._rerouting:
            self._trigger_reroute(location, lang)
            return

        # ── Advance step index if needed ───────────────────────────────────────
        with self._lock:
            if best_step_idx > self._step_index:
                self._step_index = best_step_idx

        # ── Turn announcement ──────────────────────────────────────────────────
        if self._step_index < len(steps) - 1:
            next_step = steps[self._step_index + 1]
            next_coord = next_step.get("start_coord", [0, 0])
            dist_to_next = _haversine_m(lat, lon, next_coord[0], next_coord[1])

            last_announced = self._step_announced.get(self._step_index + 1, float("inf"))
            now = time.time()

            if dist_to_next <= TURN_WARN_DISTANCE_M and now - last_announced > 5:
                # "Turn now"
                instr = self._guide.instruction_for_step(next_step, lang)
                self._speak(instr, lang)
                self._last_instruction = instr
                self._step_announced[self._step_index + 1] = now

            elif dist_to_next <= TURN_ANNOUNCE_DISTANCE_M and now - last_announced > 10:
                # "In X metres, turn left"
                instr = f"In {int(dist_to_next)} metres, " + self._guide.instruction_for_step(next_step, lang).lower()
                if lang == "hi":
                    instr = f"{int(dist_to_next)} मीटर में " + self._guide.instruction_for_step(next_step, lang)
                self._speak(instr, lang)
                self._last_instruction = instr
                self._step_announced[self._step_index + 1] = now

    def repeat_instruction(self) -> None:
        """Re-speak the last navigation instruction."""
        with self._lock:
            instr = self._last_instruction
            lang = self._lang
        if instr:
            self._speak(instr, lang)
        elif self._active and self._route:
            self._announce_current_step(self._lang)

    def get_status(self) -> dict:
        """Return current navigation status dict."""
        with self._lock:
            if not self._active or self._route is None:
                return {"active": False}

            steps = self._route["steps"]
            step_index = self._step_index
            loc = self._current_location
            coords = self._route["coordinates"]

            # Remaining distance = sum of remaining step distances
            dist_remaining = sum(
                s.get("distance_m", 0.0) for s in steps[step_index:]
            )

            next_step = steps[step_index] if step_index < len(steps) else None
            next_instr = (
                self._guide.instruction_for_step(next_step, self._lang)
                if next_step else ""
            )

            next_turn_dist = None
            if loc and step_index + 1 < len(steps):
                nc = steps[step_index + 1].get("start_coord", [0, 0])
                next_turn_dist = _haversine_m(loc["lat"], loc["lon"], nc[0], nc[1])

            total = self._route["distance_m"] or 1.0
            progress = max(0.0, min(1.0, 1.0 - dist_remaining / total))

            return {
                "active": True,
                "destination": self._destination,
                "distance_remaining_m": round(dist_remaining, 1),
                "next_instruction": next_instr,
                "next_turn_distance_m": round(next_turn_dist, 1) if next_turn_dist else None,
                "progress": round(progress, 3),
                "step_index": step_index,
                "total_steps": len(steps),
            }

    @property
    def is_active(self) -> bool:
        return self._active

    @property
    def destination(self) -> Optional[str]:
        return self._destination

    # ── Internal helpers ──────────────────────────────────────────────────────

    def _speak(self, text: str, lang: str = "en") -> None:
        """Speak via the brain's VoiceEngine if available."""
        if not text:
            return
        if self._brain is not None:
            voice = getattr(self._brain, "voice", None)
            if voice:
                voice.speak(text, lang=lang)
                return
        # Fallback: print only (useful for testing without brain)
        print(f"[NAV] {text}")

    def _announce_current_step(self, lang: str) -> None:
        """Speak the instruction for the current step."""
        with self._lock:
            if not self._active or self._route is None:
                return
            steps = self._route["steps"]
            idx = self._step_index
        if idx < len(steps):
            instr = self._guide.instruction_for_step(steps[idx], lang)
            self._speak(instr, lang)
            self._last_instruction = instr

    def _nearest_step_index(
        self,
        lat: float,
        lon: float,
        steps: list[dict],
        current_idx: int,
    ) -> tuple[int, float]:
        """
        Find the step whose start_coord is closest to (lat, lon).
        Search from current_idx forward (never go backwards).
        Returns (best_idx, distance_to_best_coord_m).
        """
        best_idx = current_idx
        best_dist = float("inf")
        for i in range(current_idx, len(steps)):
            coord = steps[i].get("start_coord", [0, 0])
            d = _haversine_m(lat, lon, coord[0], coord[1])
            if d < best_dist:
                best_dist = d
                best_idx = i
        return best_idx, best_dist

    def _on_arrival(self, lang: str) -> None:
        """Handle arrival at destination."""
        with self._lock:
            dest = self._destination
            self._active = False
            self._route = None
            self._step_index = 0
        instr = self._guide.instruction_for_step(
            {"turn": "ARRIVAL", "distance_m": 0, "street_name": "",
             "is_crossing": False, "start_coord": [0, 0]}, lang
        )
        self._speak(instr, lang)
        print(f"[NAV] 🏁 Arrived at: {dest}")

    def _trigger_reroute(self, location: dict, lang: str) -> None:
        """Recalculate route from current position to same destination."""
        with self._lock:
            dest_name = self._destination
            self._rerouting = True

        self._speak(NavigationVoiceGuide.off_route(lang), lang)
        print("[NAV] Off route — recalculating...")

        # Find destination coordinates from last route (final coordinate)
        with self._lock:
            if self._route and self._route["coordinates"]:
                final = self._route["coordinates"][-1]
                dest_lat, dest_lon = final[0], final[1]
            else:
                self._rerouting = False
                return

        try:
            new_route = self._router.route(
                location["lat"], location["lon"],
                dest_lat, dest_lon,
            )
            with self._lock:
                self._route = new_route
                self._step_index = 0
                self._step_announced = {}
                self._rerouting = False

            self._speak(NavigationVoiceGuide.reroute_complete(lang), lang)
            time.sleep(0.3)
            self._announce_current_step(lang)

        except Exception as e:
            print(f"[NAV] Reroute failed: {e}")
            with self._lock:
                self._rerouting = False
            if lang == "hi":
                self._speak("नया रास्ता नहीं मिला। पिछले रास्ते पर वापस जाएँ।", lang)
            else:
                self._speak("Could not find a new route. Please return to the previous path.", lang)
