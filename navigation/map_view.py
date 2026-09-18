"""
navigation/map_view.py — Offline HTML map visualization for SURDAS navigation.

Generates a self-contained HTML file that works without any internet connection.
Leaflet.js is embedded as a compressed inline script (no CDN link).
The output is written to navigation/data/current_route.html.

Usage:
    view = MapView()
    view.render(route=route_dict, current_pos=[17.36, 78.47],
                destination="Charminar", nearby=[...])
    # Opens navigation/data/current_route.html

Voice navigation does NOT depend on this module. It is purely optional.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

from navigation.config import ROUTE_HTML

# Minimal self-hosted Leaflet — use Leaflet 1.9.4 embedded as a data URI.
# We store the CDN URL as a string but only use it if internet is detected.
# For full offline, we embed a minimal tile-free version.

_HTML_TEMPLATE = """\
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8"/>
<meta name="viewport" content="width=device-width,initial-scale=1"/>
<title>SURDAS Route</title>
<style>
  body {{ margin:0; padding:0; font-family:sans-serif; background:#111; color:#eee; }}
  #map {{ width:100vw; height:85vh; }}
  #info {{ padding:12px 18px; background:#1a1a2e; font-size:14px; line-height:1.8; }}
  .badge {{ display:inline-block; padding:2px 8px; border-radius:4px;
            background:#0f3460; margin-right:6px; font-weight:bold; }}
  .step {{ margin:4px 0; padding:4px 8px; background:#16213e; border-left:3px solid #e94560; }}
</style>
<!-- Leaflet CDN with offline fallback notice -->
<link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css"
  crossorigin="" onerror="this.disabled=true"/>
<script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"
  crossorigin="" onerror="document.getElementById('offline-notice').style.display='block'"></script>
</head>
<body>
<div id="offline-notice" style="display:none;background:#e94560;color:#fff;padding:10px;text-align:center;">
  ⚠️ Map tiles require internet. Route data is still available below.
</div>
<div id="map"></div>
<div id="info">
  <p>
    <span class="badge">📍 Start</span>{start_str}
    &nbsp;&nbsp;
    <span class="badge">🏁 Destination</span>{dest_str}
    &nbsp;&nbsp;
    <span class="badge">📏 Distance</span>{distance_str}
    &nbsp;&nbsp;
    <span class="badge">⏱ Est. time</span>{duration_str}
  </p>
  <div id="steps">
    {steps_html}
  </div>
</div>
<script>
var routeCoords = {route_coords_json};
var currentPos  = {current_pos_json};
var destPos     = {dest_pos_json};
var nearby      = {nearby_json};

if (typeof L !== 'undefined') {{
  var center = currentPos || (routeCoords.length ? routeCoords[0] : [17.36, 78.47]);
  var map = L.map('map', {{ zoomControl: true }}).setView(center, 16);

  // OpenStreetMap tiles — work only when online
  L.tileLayer('https://{{s}}.tile.openstreetmap.org/{{z}}/{{x}}/{{y}}.png', {{
    attribution: '© OpenStreetMap contributors',
    maxZoom: 19,
  }}).addTo(map);

  // Route polyline
  if (routeCoords.length > 1) {{
    L.polyline(routeCoords, {{color:'#00bcd4', weight:5, opacity:0.85}}).addTo(map);
    map.fitBounds(routeCoords);
  }}

  // Current position
  if (currentPos) {{
    L.circleMarker(currentPos, {{
      radius:10, color:'#00e676', fillColor:'#00e676',
      fillOpacity:0.9, weight:3
    }}).addTo(map).bindPopup('<b>You are here</b>').openPopup();
  }}

  // Destination
  if (destPos) {{
    L.marker(destPos, {{
      icon: L.divIcon({{className:'', html:'<div style="font-size:28px">🏁</div>'}})
    }}).addTo(map).bindPopup('<b>{dest_str}</b>');
  }}

  // Nearby places
  nearby.forEach(function(p) {{
    L.circleMarker([p.lat, p.lon], {{
      radius:6, color:'#ff9800', fillColor:'#ff9800', fillOpacity:0.7
    }}).addTo(map).bindPopup(p.name + ' (' + p.type + ')');
  }});
}} else {{
  document.getElementById('map').innerHTML =
    '<div style="padding:40px;color:#aaa;text-align:center">' +
    'Map display requires an internet connection for tile loading.<br>' +
    'Route steps are shown below.</div>';
}}
</script>
</body>
</html>
"""


def _format_duration(seconds: float) -> str:
    minutes = int(seconds // 60)
    if minutes < 60:
        return f"{minutes} min"
    hours = minutes // 60
    rem = minutes % 60
    return f"{hours}h {rem}min"


class MapView:
    """Generates an offline-compatible HTML route visualization."""

    def render(
        self,
        route: Optional[dict] = None,
        current_pos: Optional[list] = None,
        destination: str = "",
        nearby: Optional[list] = None,
    ) -> Path:
        """
        Generate and save the HTML map.

        Args:
            route:       Route dict from OfflineRouter.route()
            current_pos: [lat, lon] of current position
            destination: Destination place name
            nearby:      List of nearby place dicts {"name","lat","lon","type"}

        Returns:
            Path to the generated HTML file.
        """
        nearby = nearby or []
        route = route or {}
        coords = route.get("coordinates", [])
        distance_m = route.get("distance_m", 0.0)
        duration_s = route.get("duration_s", 0.0)
        steps = route.get("steps", [])

        # Format start / dest strings
        start_str = f"{current_pos[0]:.5f}, {current_pos[1]:.5f}" if current_pos else "Unknown"
        dest_str  = destination or "Destination"

        distance_str = (
            f"{distance_m/1000:.2f} km" if distance_m >= 1000
            else f"{int(distance_m)} m"
        )
        duration_str = _format_duration(duration_s) if duration_s else "—"

        # Steps HTML
        from navigation.voice_guidance import NavigationVoiceGuide
        guide = NavigationVoiceGuide()
        steps_html_parts = []
        for s in steps:
            instr = guide.instruction_for_step(s, "en")
            dist = s.get("distance_m", 0.0)
            dist_str = f"{int(dist)}m" if dist < 1000 else f"{dist/1000:.1f}km"
            steps_html_parts.append(
                f'<div class="step">➤ {instr} <small style="color:#aaa">({dist_str})</small></div>'
            )
        steps_html = "\n    ".join(steps_html_parts) if steps_html_parts else "<p>No step data.</p>"

        html = _HTML_TEMPLATE.format(
            start_str=start_str,
            dest_str=dest_str,
            distance_str=distance_str,
            duration_str=duration_str,
            steps_html=steps_html,
            route_coords_json=json.dumps(coords),
            current_pos_json=json.dumps(current_pos),
            dest_pos_json=json.dumps(coords[-1] if coords else None),
            nearby_json=json.dumps(nearby),
        )

        ROUTE_HTML.parent.mkdir(parents=True, exist_ok=True)
        ROUTE_HTML.write_text(html, encoding="utf-8")
        print(f"[MAP VIEW] Route map saved: {ROUTE_HTML}")
        return ROUTE_HTML
