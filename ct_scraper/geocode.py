"""Geocoding helpers with caching."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Optional, Tuple

from geopy.exc import GeocoderServiceError
from geopy.geocoders import Nominatim
from geopy.extra.rate_limiter import RateLimiter

BASE_DIR = Path(__file__).resolve().parents[1]
CACHE_PATH = BASE_DIR / "geocode_cache.json"

_geolocator: Optional[Nominatim] = None
_rate_limiter: Optional[RateLimiter] = None
_cache: dict[str, dict[str, float]] = {}


def _ensure_cache_loaded() -> None:
    if _cache:
        return
    if CACHE_PATH.exists():
        try:
            data = json.loads(CACHE_PATH.read_text())
        except json.JSONDecodeError:
            data = {}
        _cache.update(data)


def _save_cache() -> None:
    try:
        CACHE_PATH.write_text(json.dumps(_cache, indent=2))
    except OSError:
        pass


def _get_rate_limiter() -> RateLimiter:
    global _geolocator, _rate_limiter
    if _rate_limiter is None:
        _geolocator = Nominatim(user_agent="ct-scraper-service", timeout=15)
        _rate_limiter = RateLimiter(_geolocator.geocode, min_delay_seconds=1)
    return _rate_limiter


def geocode_address(address: str, town: str) -> Optional[Tuple[float, float]]:
    """Return (lat, lng) for an address using cached values when possible."""
    if not address or not town:
        return None

    _ensure_cache_loaded()
    key = f"{address}, {town}, CT"
    if key in _cache:
        data = _cache[key]
        return data.get("lat"), data.get("lng")

    rate_limiter = _get_rate_limiter()
    try:
        location = rate_limiter(key)
    except GeocoderServiceError:
        return None
    if location is None:
        return None

    coords = (float(location.latitude), float(location.longitude))
    _cache[key] = {"lat": coords[0], "lng": coords[1]}
    _save_cache()
    return coords
