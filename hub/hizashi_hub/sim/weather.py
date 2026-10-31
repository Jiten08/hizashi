"""Open-Meteo forecast fetch + cache to data/weather/<date>.json, clear-sky fallback (section 6.8).

Hourly radiation is the mean of the preceding hour: shift each value to (hour - 30 min)
before interpolating to 15 min. Columns: ghi, dni, dhi, temp_air, cloud_cover.
Offline: pvlib Ineichen clear-sky x 0.85, cloud_cover=20, source "clear-sky fallback".
"""
import pandas as pd

OPEN_METEO_URL = "https://api.open-meteo.com/v1/forecast"


async def fetch_open_meteo(day: str) -> pd.DataFrame:
    """Hourly forecast for `day`, converted to the 15-min frame."""
    raise NotImplementedError("TODO(R1.2, Anurag)")


def clear_sky_fallback(day: str) -> pd.DataFrame:
    raise NotImplementedError("TODO(R1.2, Anurag)")


async def load_weather(day: str) -> tuple[pd.DataFrame, str]:
    """(96-block frame, source). Uses the cache if present, else fetches, else falls back."""
    raise NotImplementedError("TODO(R1.2, Anurag)")


def to_json(frame: pd.DataFrame, source: str) -> dict:
    """Shape served by GET /api/weather."""
    raise NotImplementedError("TODO(R1.2, Anurag)")
