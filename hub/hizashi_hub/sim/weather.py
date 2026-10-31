"""Open-Meteo forecast fetch + cache to data/weather/<date>.json, clear-sky fallback (section 6.8).

Hourly radiation is the mean of the preceding hour: shift each value to (hour - 30 min)
before interpolating to 15 min. Columns: ghi, dni, dhi, temp_air, cloud_cover.
Offline: pvlib Ineichen clear-sky x 0.85, cloud_cover=20, source "clear-sky fallback".
"""
import json
import logging
from pathlib import Path

import httpx
import numpy as np
import pandas as pd
import pvlib

from hizashi_shared import config
from hizashi_shared.solar import weather_frame

log = logging.getLogger("hizashi.sim.weather")

OPEN_METEO_URL = "https://api.open-meteo.com/v1/forecast"
_location = pvlib.location.Location(config.LAT, config.LON, config.TZ_NAME, config.ALT)


async def fetch_open_meteo(day: str) -> pd.DataFrame:
    """Hourly forecast for `day`, converted to the 15-min frame."""
    params = {
        "latitude": config.LAT,
        "longitude": config.LON,
        "hourly": "shortwave_radiation,direct_normal_irradiance,diffuse_radiation,temperature_2m,cloud_cover",
        "timezone": config.TZ_NAME,
        "start_date": day,
        "end_date": day,
    }
    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.get(OPEN_METEO_URL, params=params)
        resp.raise_for_status()
        data = resp.json()

    hourly = data.get("hourly", {})
    times = hourly.get("time", [])
    if not times:
        raise ValueError(f"No hourly weather data returned for {day}")

    df_raw = pd.DataFrame(
        {
            "ghi": [float(x) for x in hourly["shortwave_radiation"]],
            "dni": [float(x) for x in hourly["direct_normal_irradiance"]],
            "dhi": [float(x) for x in hourly["diffuse_radiation"]],
            "temp_air": [float(x) for x in hourly["temperature_2m"]],
            "cloud_cover": [float(x) for x in hourly["cloud_cover"]],
        },
        index=pd.to_datetime(times),
    )

    if df_raw.index.tz is None:
        df_raw.index = df_raw.index.tz_localize(config.TZ)
    else:
        df_raw.index = df_raw.index.tz_convert(config.TZ)

    # Shift each value to (hour - 30 min) as hourly radiation represents the mean of the preceding hour
    df_shifted = df_raw.copy()
    df_shifted.index = df_shifted.index - pd.Timedelta(minutes=30)

    target_index = pd.date_range(
        start=f"{day} 00:00",
        end=f"{day} 23:45",
        freq="15min",
        tz=config.TZ,
    )

    combined_index = target_index.union(df_shifted.index).sort_values()
    df_interp = df_shifted.reindex(combined_index).interpolate(method="time").bfill().ffill()
    df_res = df_interp.reindex(target_index)

    df_res["ghi"] = df_res["ghi"].clip(lower=0.0).round(2)
    df_res["dni"] = df_res["dni"].clip(lower=0.0).round(2)
    df_res["dhi"] = df_res["dhi"].clip(lower=0.0).round(2)
    df_res["cloud_cover"] = df_res["cloud_cover"].clip(lower=0.0, upper=100.0).round(2)
    df_res["temp_air"] = df_res["temp_air"].round(2)

    return df_res


def clear_sky_fallback(day: str) -> pd.DataFrame:
    """Generate clear-sky fallback using pvlib Ineichen scaled by 0.85 with cloud_cover=20."""
    target_index = pd.date_range(
        start=f"{day} 00:00",
        end=f"{day} 23:45",
        freq="15min",
        tz=config.TZ,
    )
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

    source = "open-meteo"
    try:
        frame = await fetch_open_meteo(day)
    except Exception as err:
        log.warning("Open-Meteo fetch failed for %s (%s); using clear-sky fallback", day, err)
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
