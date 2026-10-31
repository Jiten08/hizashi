"""Google Weather API forecast fetch + cache to data/weather/<date>.json, clear-sky fallback (section 6.8).

The Google Weather API (Maps Platform) returns hourly temperature and cloud cover but NO
solar radiation, so irradiance is derived: pvlib Ineichen clear-sky GHI is attenuated by cloud
cover (Kasten-Czeplak), then split into DNI/DHI with the Erbs decomposition.

Hours already past today come from the history endpoint (last 24 h); the rest from the forecast
endpoint (next 240 h). Each hourly value is placed at (hour start + 30 min) before interpolating
to 15 min. Columns: ghi, dni, dhi, temp_air, cloud_cover.
Offline: pvlib Ineichen clear-sky x 0.85, cloud_cover=20, source "clear-sky fallback".

Needs GOOGLE_MAPS_API_KEY in .env (loaded by hizashi_shared.config) with the Weather API
enabled on the key's Google Cloud project.
"""
import json
import logging
import os
from pathlib import Path

import httpx
import numpy as np
import pandas as pd
import pvlib

from hizashi_shared import config  # importing config runs load_dotenv(ROOT / ".env")
from hizashi_shared.solar import weather_frame

log = logging.getLogger("hizashi.sim.weather")

GOOGLE_FORECAST_URL = "https://weather.googleapis.com/v1/forecast/hours:lookup"
GOOGLE_HISTORY_URL = "https://weather.googleapis.com/v1/history/hours:lookup"
GOOGLE_SOURCE = "google-weather"
_MAX_PAGES = 12  # forecast: 240 h / 24 per page = 10 pages
_location = pvlib.location.Location(config.LAT, config.LON, config.TZ_NAME, config.ALT)


def _target_index(day: str) -> pd.DatetimeIndex:
    return pd.date_range(start=f"{day} 00:00", end=f"{day} 23:45", freq="15min", tz=config.TZ)


async def _fetch_pages(
    client: httpx.AsyncClient, url: str, list_key: str, hours: int, day_end: pd.Timestamp
) -> list[dict]:
    """Follow nextPageToken until the list ends or an entry past `day_end` has been seen."""
    params: dict = {
        "location.latitude": config.LAT,
        "location.longitude": config.LON,
        "hours": hours,
        "pageSize": 24,
        "unitsSystem": "METRIC",
    }
    entries: list[dict] = []
    for _ in range(_MAX_PAGES):
        resp = await client.get(url, params=params)
        resp.raise_for_status()
        data = resp.json()
        page = data.get(list_key, [])
        entries.extend(page)

        token = data.get("nextPageToken")
        if not token or not page:
            break
        last_start = pd.Timestamp(page[-1]["interval"]["startTime"]).tz_convert(config.TZ)
        if last_start > day_end:
            break
        params["pageToken"] = token
    return entries


async def _fetch_google_hours(day: str) -> list[dict]:
    """Hourly entries (history + forecast) from Google that may cover `day`."""
    api_key = os.getenv("GOOGLE_MAPS_API_KEY")
    if not api_key:
        raise RuntimeError("GOOGLE_MAPS_API_KEY is not set")

    day_start = pd.Timestamp(f"{day} 00:00", tz=config.TZ)
    day_end = pd.Timestamp(f"{day} 23:59", tz=config.TZ)
    now = pd.Timestamp.now(tz=config.TZ)

    # Key goes in a header, not the URL, so it never shows up in httpx error messages / logs.
    async with httpx.AsyncClient(timeout=10.0, headers={"X-Goog-Api-Key": api_key}) as client:
        entries: list[dict] = []
        # History only reaches back 24 h, so it is only useful for today / yesterday.
        if day_start <= now:
            try:
                entries += await _fetch_pages(client, GOOGLE_HISTORY_URL, "historyHours", 24, day_end)
            except Exception as err:
                log.warning("Google history fetch failed (%s); continuing with forecast only", err)
        if day_end >= now - pd.Timedelta(hours=1):
            entries += await _fetch_pages(client, GOOGLE_FORECAST_URL, "forecastHours", 240, day_end)
    return entries


async def fetch_google_weather(day: str) -> pd.DataFrame:
    """Hourly Google weather for `day`, converted to the 15-min frame with derived irradiance."""
    entries = await _fetch_google_hours(day)

    rows = {}
    for e in entries:  # later entries (forecast) overwrite earlier ones (history) for the same hour
        start = pd.Timestamp(e["interval"]["startTime"]).tz_convert(config.TZ)
        if start.strftime("%Y-%m-%d") != day:
            continue
        # Hourly value is the hour's mean -> place it at the hour's midpoint
        rows[start + pd.Timedelta(minutes=30)] = {
            "temp_air": float(e["temperature"]["degrees"]),
            "cloud_cover": float(e.get("cloudCover", 20)),
        }
    if not rows:
        # Google only has ~24 h back and ~240 h ahead, so older/further days land here.
        raise ValueError(f"No hourly weather data returned for {day}")
    if len(rows) < 24:
        log.warning("Google returned only %d/24 hours for %s; edges are extended", len(rows), day)

    df_raw = pd.DataFrame.from_dict(rows, orient="index").sort_index()
    target_index = _target_index(day)

    combined_index = target_index.union(df_raw.index).sort_values()
    df_interp = df_raw.reindex(combined_index).interpolate(method="time").bfill().ffill()
    df_res = df_interp.reindex(target_index)
    df_res["cloud_cover"] = df_res["cloud_cover"].clip(lower=0.0, upper=100.0)

    # Irradiance: clear-sky GHI attenuated by cloud cover, then Erbs split into DNI / DHI.
    # apparent_zenith matches what solar.roof_kw uses for the plane-of-array transposition.
    cs = _location.get_clearsky(target_index, model="ineichen", linke_turbidity=3.0)
    solpos = _location.get_solarposition(target_index)
    okta_frac = df_res["cloud_cover"] / 100.0  # n/8
    ghi = (cs["ghi"] * (1.0 - 0.75 * okta_frac**3.4)).clip(lower=0.0)
    erbs = pvlib.irradiance.erbs(ghi, solpos["apparent_zenith"], target_index.dayofyear)

    df_res["ghi"] = ghi.round(2)
    df_res["dni"] = erbs["dni"].fillna(0.0).clip(lower=0.0).round(2)
    df_res["dhi"] = erbs["dhi"].fillna(0.0).clip(lower=0.0).round(2)
    df_res["cloud_cover"] = df_res["cloud_cover"].round(2)
    df_res["temp_air"] = df_res["temp_air"].round(2)

    return df_res[["ghi", "dni", "dhi", "temp_air", "cloud_cover"]]


def clear_sky_fallback(day: str) -> pd.DataFrame:
    """Generate clear-sky fallback using pvlib Ineichen scaled by 0.85 with cloud_cover=20."""
    target_index = _target_index(day)
    # Pass linke_turbidity=3.0 so pvlib does not attempt an offline/network file lookup
    cs = _location.get_clearsky(target_index, model="ineichen", linke_turbidity=3.0)

    ghi = (cs["ghi"] * 0.85).clip(lower=0.0).round(2)
    dni = (cs["dni"] * 0.85).clip(lower=0.0).round(2)
    dhi = (cs["dhi"] * 0.85).clip(lower=0.0).round(2)

    # Bengaluru diurnal temperature variation (~20°C min before dawn to ~28°C max early afternoon)
    hours = np.array([ts.hour + ts.minute / 60.0 for ts in target_index])
    temp_curve = 20.0 + 8.0 * np.sin(np.pi * np.clip(hours - 6.0, 0, 12) / 12.0)
    temp_air = pd.Series(temp_curve.round(2), index=target_index)

    cloud_cover = pd.Series([20.0] * config.BLOCKS_PER_DAY, index=target_index)

    return pd.DataFrame(
        {
            "ghi": ghi,
            "dni": dni,
            "dhi": dhi,
            "temp_air": temp_air,
            "cloud_cover": cloud_cover,
        },
        index=target_index,
    )


def to_json(frame: pd.DataFrame, source: str, day: str | None = None) -> dict:
    """Shape served by GET /api/weather."""
    if day is None:
        if not frame.empty and hasattr(frame.index, "strftime"):
            day = frame.index[0].strftime("%Y-%m-%d")
        else:
            day = config.SIM_DAY

    blocks = []
    for i, (ts, row) in enumerate(frame.iterrows()):
        blocks.append(
            {
                "index": i,
                "ts": ts.isoformat(),
                "ghi": round(float(row["ghi"]), 2),
                "dni": round(float(row["dni"]), 2),
                "dhi": round(float(row["dhi"]), 2),
                "temp_air": round(float(row["temp_air"]), 2),
                "cloud_cover": round(float(row["cloud_cover"]), 2),
            }
        )
    return {"day": day, "source": source, "blocks": blocks}


async def load_weather(day: str, cache_dir: Path | None = None) -> tuple[pd.DataFrame, str]:
    """(96-block frame, source). Uses the cache if present, else fetches, else falls back."""
    cdir = cache_dir or config.WEATHER_DIR
    cache_file = cdir / f"{day}.json"

    if cache_file.exists():
        try:
            cached_json = json.loads(cache_file.read_text(encoding="utf-8"))
            source = cached_json.get("source", "cached")
            frame = weather_frame(cached_json)
            if len(frame) == config.BLOCKS_PER_DAY:
                log.info("loaded weather for %s from cache (%s)", day, source)
                return frame, source
        except Exception as err:
            log.warning("failed reading weather cache %s: %s", cache_file, err)

    source = GOOGLE_SOURCE
    try:
        frame = await fetch_google_weather(day)
    except Exception as err:
        log.warning("Google Weather fetch failed for %s (%s); using clear-sky fallback", day, err)
        frame = clear_sky_fallback(day)
        source = "clear-sky fallback"

    try:
        cdir.mkdir(parents=True, exist_ok=True)
        cached_dict = to_json(frame, source, day)
        cache_file.write_text(json.dumps(cached_dict, indent=2), encoding="utf-8")
        log.info("cached weather for %s to %s", day, cache_file)
    except Exception as err:
        log.warning("could not write weather cache %s: %s", cache_file, err)

    return frame, source