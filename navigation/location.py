"""
navigation/location.py — GPS / Location abstraction for SURDAS.

Provides a unified LocationProvider interface that works with:
  1. ManualLocation  — hardcoded lat/lon (dev/testing)
  2. GPSSerialLocation — NMEA sentences from USB/Bluetooth GPS or ESP32
  3. LocationBridge   — HTTP polling from a phone GPS bridge app

Usage:
    provider = ManualLocation(lat=17.3616, lon=78.4747)
    loc = provider.get_location()
    # {"lat": 17.3616, "lon": 78.4747, "accuracy": 0.0, "timestamp": ...}

CLI test:
    python -m navigation.location --lat 17.3616 --lon 78.4747
"""
from __future__ import annotations

import time
import threading
from typing import Optional


class LocationUnavailableError(Exception):
    """Raised when location cannot be determined."""


class LocationProvider:
    """Base class. Override get_location()."""

    def get_location(self) -> dict:
        raise LocationUnavailableError(
            "No location provider configured. "
            "Use ManualLocation(lat, lon) for testing, "
            "or GPSSerialLocation() for a hardware GPS module."
        )

    @staticmethod
    def _make_result(lat: float, lon: float, accuracy: float = 0.0) -> dict:
        return {
            "lat": lat,
            "lon": lon,
            "accuracy": accuracy,
            "timestamp": time.time(),
        }


# ── Manual / Test location ────────────────────────────────────────────────────

class ManualLocation(LocationProvider):
    """
    Fixed coordinates for testing without GPS hardware.
    accuracy is reported as 0.0 (exact) so routing works,
    but the user must understand this is a manually set position.
    """

    def __init__(self, lat: float, lon: float):
        self._lat = lat
        self._lon = lon

    def get_location(self) -> dict:
        return self._make_result(self._lat, self._lon, accuracy=0.0)

    def update(self, lat: float, lon: float):
        """Allow live update (e.g. from test script simulating movement)."""
        self._lat = lat
        self._lon = lon


# ── Serial GPS (NMEA) ─────────────────────────────────────────────────────────

class GPSSerialLocation(LocationProvider):
    """
    Reads NMEA sentences from a serial GPS module (USB/Bluetooth/ESP32).
    Parses $GPRMC and $GPGGA sentences.

    Args:
        port:     Serial port path, e.g. "/dev/ttyUSB0" or "/dev/cu.usbserial-0001"
        baudrate: GPS baud rate (most modules: 9600)
        timeout:  Seconds to wait for a valid fix before raising LocationUnavailableError
    """

    def __init__(self, port: str, baudrate: int = 9600, timeout: float = 10.0):
        self._port = port
        self._baudrate = baudrate
        self._timeout = timeout
        self._lat: Optional[float] = None
        self._lon: Optional[float] = None
        self._accuracy: float = 99.0
        self._ts: float = 0.0
        self._lock = threading.Lock()
        self._running = False
        self._thread: Optional[threading.Thread] = None

    def start(self):
        """Start background NMEA reader thread."""
        self._running = True
        self._thread = threading.Thread(target=self._reader_loop, daemon=True, name="GPSReader")
        self._thread.start()

    def stop(self):
        self._running = False

    def _reader_loop(self):
        try:
            import serial  # pyserial — optional dep
            ser = serial.Serial(self._port, self._baudrate, timeout=1)
            while self._running:
                line = ser.readline().decode("ascii", errors="replace").strip()
                self._parse_nmea(line)
        except ImportError:
            print("[GPS] pyserial not installed. Install with: pip install pyserial")
            self._running = False
        except Exception as e:
            print(f"[GPS] Serial error: {e}")
            self._running = False

    def _parse_nmea(self, sentence: str):
        """Parse $GPRMC or $GPGGA sentences."""
        try:
            if sentence.startswith("$GPRMC"):
                parts = sentence.split(",")
                if len(parts) < 7 or parts[2] != "A":  # A = valid fix
                    return
                lat = self._nmea_coord(parts[3], parts[4])
                lon = self._nmea_coord(parts[5], parts[6])
                if lat is not None and lon is not None:
                    with self._lock:
                        self._lat, self._lon = lat, lon
                        self._accuracy = 15.0  # typical consumer GPS
                        self._ts = time.time()

            elif sentence.startswith("$GPGGA"):
                parts = sentence.split(",")
                if len(parts) < 10 or parts[6] == "0":  # fix quality 0 = invalid
                    return
                lat = self._nmea_coord(parts[2], parts[3])
                lon = self._nmea_coord(parts[4], parts[5])
                hdop = float(parts[8]) if parts[8] else 99.0
                if lat is not None and lon is not None:
                    with self._lock:
                        self._lat, self._lon = lat, lon
                        self._accuracy = hdop * 5.0  # rough accuracy estimate in meters
                        self._ts = time.time()
        except Exception:
            pass

    @staticmethod
    def _nmea_coord(raw: str, direction: str) -> Optional[float]:
        """Convert NMEA ddmm.mmmm format to decimal degrees."""
        if not raw:
            return None
        try:
            dot = raw.index(".")
            degrees = float(raw[:dot - 2])
            minutes = float(raw[dot - 2:])
            decimal = degrees + minutes / 60.0
            if direction in ("S", "W"):
                decimal = -decimal
            return decimal
        except Exception:
            return None

    def get_location(self) -> dict:
        deadline = time.time() + self._timeout
        while time.time() < deadline:
            with self._lock:
                if self._lat is not None and self._lon is not None:
                    return self._make_result(self._lat, self._lon, self._accuracy)
            time.sleep(0.2)
        raise LocationUnavailableError(
            f"GPS serial port {self._port}: no valid fix within {self._timeout}s. "
            "Check cable/port and that the GPS module has sky visibility."
        )


# ── HTTP Bridge (phone GPS) ───────────────────────────────────────────────────

class LocationBridge(LocationProvider):
    """
    Poll a local HTTP endpoint for GPS data.
    Useful when a phone runs a GPS-to-HTTP bridge app on the same Wi-Fi.

    The endpoint must return JSON: {"lat": ..., "lon": ..., "accuracy": ...}
    """

    def __init__(self, url: str = "http://192.168.4.1:8080/gps", timeout: float = 3.0):
        self._url = url
        self._timeout = timeout

    def get_location(self) -> dict:
        import urllib.request
        import json
        try:
            with urllib.request.urlopen(self._url, timeout=self._timeout) as resp:
                data = json.loads(resp.read().decode())
                return self._make_result(
                    float(data["lat"]),
                    float(data["lon"]),
                    float(data.get("accuracy", 10.0)),
                )
        except Exception as e:
            raise LocationUnavailableError(f"GPS bridge at {self._url} unreachable: {e}")


# ── CLI test mode ─────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import argparse, json
    parser = argparse.ArgumentParser(description="SURDAS Location Provider Test")
    parser.add_argument("--lat", type=float, required=True, help="Latitude (decimal degrees)")
    parser.add_argument("--lon", type=float, required=True, help="Longitude (decimal degrees)")
    parser.add_argument("--serial", type=str, default=None, help="Serial port for GPS module")
    args = parser.parse_args()

    if args.serial:
        provider = GPSSerialLocation(args.serial)
        provider.start()
    else:
        provider = ManualLocation(args.lat, args.lon)

    loc = provider.get_location()
    print(json.dumps(loc, indent=2))
