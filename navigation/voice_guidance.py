"""
navigation/voice_guidance.py — English + Hindi spoken navigation instructions.

Converts route steps (from router.py) into human-readable, speakable sentences.
All output is plain text — no markdown, no symbols.
No internet required.

Crossing wording follows safety requirement:
  EN: "Crossing ahead. Check traffic before crossing."
  HI: "आगे सड़क पार करने की जगह है। सड़क पार करने से पहले ट्रैफिक देखें।"
"""
from __future__ import annotations

from navigation.router import TurnType


# ── English turn templates ────────────────────────────────────────────────────

_EN_TURN: dict[str, str] = {
    TurnType.DEPART:       "Head {dir} on {street}.",
    TurnType.STRAIGHT:     "Continue straight for {dist}.",
    TurnType.SLIGHT_LEFT:  "Bear slightly left{on_street}.",
    TurnType.SLIGHT_RIGHT: "Bear slightly right{on_street}.",
    TurnType.LEFT:         "Turn left{on_street}.",
    TurnType.RIGHT:        "Turn right{on_street}.",
    TurnType.SHARP_LEFT:   "Turn sharp left{on_street}.",
    TurnType.SHARP_RIGHT:  "Turn sharp right{on_street}.",
    TurnType.U_TURN:       "Make a U-turn.",
    TurnType.ARRIVAL:      "You have arrived at your destination.",
}

# ── Hindi turn templates ──────────────────────────────────────────────────────

_HI_TURN: dict[str, str] = {
    TurnType.DEPART:       "{dir} दिशा में {street} पर चलें।",
    TurnType.STRAIGHT:     "{dist} तक सीधे जाएँ।",
    TurnType.SLIGHT_LEFT:  "थोड़ा बाईं तरफ मुड़ें{on_street}।",
    TurnType.SLIGHT_RIGHT: "थोड़ा दाईं तरफ मुड़ें{on_street}।",
    TurnType.LEFT:         "बाईं तरफ मुड़ें{on_street}।",
    TurnType.RIGHT:        "दाईं तरफ मुड़ें{on_street}।",
    TurnType.SHARP_LEFT:   "तेज़ बाईं तरफ मुड़ें{on_street}।",
    TurnType.SHARP_RIGHT:  "तेज़ दाईं तरफ मुड़ें{on_street}।",
    TurnType.U_TURN:       "यू-टर्न लें।",
    TurnType.ARRIVAL:      "आप अपने गंतव्य पर पहुँच गए हैं।",
}

# ── Compass direction labels ──────────────────────────────────────────────────

def _compass_en(bearing: float) -> str:
    dirs = ["north", "northeast", "east", "southeast",
            "south", "southwest", "west", "northwest"]
    idx = round(bearing / 45) % 8
    return dirs[idx]


def _compass_hi(bearing: float) -> str:
    dirs = ["उत्तर", "उत्तर-पूर्व", "पूर्व", "दक्षिण-पूर्व",
            "दक्षिण", "दक्षिण-पश्चिम", "पश्चिम", "उत्तर-पश्चिम"]
    idx = round(bearing / 45) % 8
    return dirs[idx]


# ── Distance formatting ───────────────────────────────────────────────────────

def _fmt_dist_en(meters: float) -> str:
    if meters < 10:
        return "a few steps"
    if meters < 100:
        return f"{int(round(meters / 5) * 5)} metres"
    if meters < 1000:
        return f"{int(round(meters / 10) * 10)} metres"
    km = meters / 1000
    return f"{km:.1f} kilometres"


def _fmt_dist_hi(meters: float) -> str:
    if meters < 10:
        return "कुछ कदम"
    if meters < 100:
        return f"{int(round(meters / 5) * 5)} मीटर"
    if meters < 1000:
        return f"{int(round(meters / 10) * 10)} मीटर"
    km = meters / 1000
    return f"{km:.1f} किलोमीटर"


# ── Main instruction generator ────────────────────────────────────────────────

class NavigationVoiceGuide:
    """
    Generates spoken navigation instructions from route steps.
    Stateless — call instruction_for_step() for each step.
    """

    @staticmethod
    def instruction_for_step(step: dict, lang: str = "en") -> str:
        """
        Convert a step dict (from OfflineRouter.route()["steps"]) to
        a spoken instruction string.

        Args:
            step: Step dict with keys: turn, distance_m, street_name,
                  is_crossing, start_coord
            lang: "en" or "hi"

        Returns:
            Plain spoken string, e.g. "Turn left onto Station Road."
        """
        turn = step.get("turn", TurnType.STRAIGHT)
        dist_m = float(step.get("distance_m", 0.0))
        street = str(step.get("street_name", "") or "")
        is_crossing = bool(step.get("is_crossing", False))
        start_coord = step.get("start_coord", [0, 0])

        # Crossing always gets safety wording — interrupts normal template
        if is_crossing:
            if lang == "hi":
                return "आगे सड़क पार करने की जगह है। सड़क पार करने से पहले ट्रैफिक देखें।"
            else:
                return "Crossing ahead. Check traffic before crossing."

        # Build instruction from template
        if lang == "hi":
            tmpl = _HI_TURN.get(turn, "सीधे जाएँ।")
            on_street = f" {street} पर" if street else ""
            dist_str = _fmt_dist_hi(dist_m)
            bearing_approx = 0.0
            dir_str = _compass_hi(bearing_approx)

            text = (tmpl
                    .replace("{dir}", dir_str)
                    .replace("{street}", street or "सड़क")
                    .replace("{dist}", dist_str)
                    .replace("{on_street}", on_street))
        else:
            tmpl = _EN_TURN.get(turn, "Continue straight.")
            on_street = f" onto {street}" if street else ""
            dist_str = _fmt_dist_en(dist_m)
            bearing_approx = 0.0
            if isinstance(start_coord, (list, tuple)) and len(start_coord) == 2:
                bearing_approx = 0.0   # bearing computed from route, not stored per step
            dir_str = _compass_en(bearing_approx)

            text = (tmpl
                    .replace("{dir}", dir_str)
                    .replace("{street}", street or "the road")
                    .replace("{dist}", dist_str)
                    .replace("{on_street}", on_street))

        return text

    @staticmethod
    def distance_announcement(dist_remaining_m: float, lang: str = "en") -> str:
        """Short progress update: 'In 200 metres, turn left.'"""
        if lang == "hi":
            return f"{_fmt_dist_hi(dist_remaining_m)} में मुड़ें।"
        return f"In {_fmt_dist_en(dist_remaining_m)}, turn."

    @staticmethod
    def off_route(lang: str = "en") -> str:
        if lang == "hi":
            return "आप रास्ते से हट गए हैं। नया रास्ता खोज रहा हूँ।"
        return "You are off route. Recalculating."

    @staticmethod
    def reroute_complete(lang: str = "en") -> str:
        if lang == "hi":
            return "नया रास्ता मिल गया।"
        return "Route updated. Continue with new directions."

    @staticmethod
    def no_route(destination: str, lang: str = "en") -> str:
        if lang == "hi":
            return f"{destination} तक कोई रास्ता नहीं मिला।"
        return f"No route found to {destination}."

    @staticmethod
    def destination_not_found(destination: str, lang: str = "en") -> str:
        if lang == "hi":
            return f"माफ़ करें, {destination} ऑफ़लाइन मानचित्र में नहीं मिला।"
        return f"Sorry, {destination} was not found in the offline map."

    @staticmethod
    def gps_unavailable(lang: str = "en") -> str:
        if lang == "hi":
            return "जीपीएस उपलब्ध नहीं है। नेविगेशन शुरू नहीं हो सकता।"
        return "GPS location is unavailable. Cannot start navigation."

    @staticmethod
    def navigation_started(destination: str, distance_m: float, lang: str = "en") -> str:
        if lang == "hi":
            dist = _fmt_dist_hi(distance_m)
            return f"{destination} के लिए नेविगेशन शुरू। कुल दूरी {dist}।"
        dist = _fmt_dist_en(distance_m)
        return f"Starting navigation to {destination}. Total distance: {dist}."

    @staticmethod
    def navigation_stopped(lang: str = "en") -> str:
        if lang == "hi":
            return "नेविगेशन बंद।"
        return "Navigation stopped."

    @staticmethod
    def where_am_i(
        nearest_place: str,
        distance_m: float,
        accuracy_m: float,
        lang: str = "en",
    ) -> str:
        if lang == "hi":
            dist = _fmt_dist_hi(distance_m)
            return (
                f"आप {nearest_place} के पास हैं, लगभग {dist} दूर। "
                f"जीपीएस सटीकता: {int(accuracy_m)} मीटर।"
            )
        dist = _fmt_dist_en(distance_m)
        return (
            f"You are near {nearest_place}, approximately {dist} away. "
            f"GPS accuracy: {int(accuracy_m)} metres."
        )

    @staticmethod
    def nearest_result(result: dict, category: str, lang: str = "en") -> str:
        name = result.get("name", "Unknown")
        dist = float(result.get("distance_m") or 0.0)
        if lang == "hi":
            dist_str = _fmt_dist_hi(dist)
            return f"सबसे नज़दीकी {category} है {name}, {dist_str} दूर।"
        dist_str = _fmt_dist_en(dist)
        return f"The nearest {category} is {name}, {dist_str} away."

    @staticmethod
    def no_nearby(category: str, lang: str = "en") -> str:
        if lang == "hi":
            return f"ऑफ़लाइन मानचित्र में कोई {category} नहीं मिला।"
        return f"No {category} found in the installed offline map."
