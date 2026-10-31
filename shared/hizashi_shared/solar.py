"""Roof output per 15-min block with pvlib (used by the hub sim AND the agents).

Chain: solar position -> plane-of-array irradiance -> SAPM cell temperature
-> PVWatts DC -> PVWatts inverter (clips at inverter_kw) -> kW x 0.25 h.
pvlib arguments are passed positionally where names changed across versions.
"""
import json
import logging
import os
from pathlib import Path

import httpx
import numpy as np
import pandas as pd
import pvlib

from . import config
from .models import Roof

GAMMA_PDC = -0.004          # %/°C power temperature coefficient (typical c-Si)
ETA_INV = 0.96
WIND_SPEED = 1.0            # m/s, no wind data from the forecast
_TEMP_PARAMS = pvlib.temperature.TEMPERATURE_MODEL_PARAMETERS["sapm"]["close_mount_glass_glass"]

log = logging.getLogger("hizashi.sim.weather")

GOOGLE_FORECAST_URL = "https://weather.googleapis.com/v1/forecast/hours:lookup"
GOOGLE_HISTORY_URL = "https://weather.googleapis.com/v1/history/hours:lookup"
GOOGLE_SOURCE = "google-weather"
_MAX_PAGES = 12  # forecast: 240 h / 24 per page = 10 pages
_location = pvlib.location.Location(config.LAT, config.LON, config.TZ_NAME, config.ALT)


def _target_index(day: str) -> pd.DatetimeIndex:
    return pd.date_range(start=f"{day} 00:00", end=f"{day} 23:45", freq="15min", tz=config.TZ)


def weather_frame(w_json: dict) -> pd.DataFrame:
    """Convert weather JSON (shape from GET /api/weather or cache) to a 15-min indexed DataFrame."""
    blocks = w_json.get("blocks", [])
    if not blocks:
        return pd.DataFrame(columns=["ghi", "dni", "dhi", "temp_air", "cloud_cover"])

    records = []
    index = []
    for b in blocks:
        ts = pd.Timestamp(b["ts"])
        if ts.tz is None:
            ts = ts.tz_localize(config.TZ)
        else:
            ts = ts.tz_convert(config.TZ)
        index.append(ts)
        records.append(
            {
                "ghi": float(b.get("ghi", 0.0)),
                "dni": float(b.get("dni", 0.0)),
                "dhi": float(b.get("dhi", 0.0)),
                "temp_air": float(b.get("temp_air", 0.0)),
                "cloud_cover": float(b.get("cloud_cover", 0.0)),
            }
        )
    df = pd.DataFrame(records, index=pd.DatetimeIndex(index))
    return df[["ghi", "dni", "dhi", "temp_air", "cloud_cover"]]


def roof_kw(roof: Roof, weather: pd.DataFrame) -> pd.Series:
    """AC kW at each timestamp of `weather` (needs ghi, dni, dhi, temp_air)."""
    solpos = _location.get_solarposition(weather.index)
    poa = pvlib.irradiance.get_total_irradiance(
        roof.tilt,
        roof.azimuth,
        solpos["apparent_zenith"],
        solpos["azimuth"],
        weather["dni"],
        weather["ghi"],
        weather["dhi"],
    )
    poa_global = poa["poa_global"].fillna(0).clip(lower=0)
    t_cell = pvlib.temperature.sapm_cell(
        poa_global,
        weather["temp_air"],
        WIND_SPEED,
        _TEMP_PARAMS["a"],
        _TEMP_PARAMS["b"],
        _TEMP_PARAMS["deltaT"],
    )
    pdc = pvlib.pvsystem.pvwatts_dc(poa_global, t_cell, roof.kwp * 1000, GAMMA_PDC)
    pac = pvlib.inverter.pvwatts(pdc, roof.inverter_kw * 1000 / ETA_INV, ETA_INV)
    pac = pd.Series(np.asarray(pac, dtype=float), index=weather.index)
    return (pac.clip(lower=0, upper=roof.inverter_kw * 1000) / 1000).fillna(0)


def roof_kwh_per_block(roof: Roof | None, weather: pd.DataFrame) -> list[float]:
    """96 values of kWh per block. `weather` has a 15-min Asia/Kolkata DatetimeIndex
    with columns ghi, dni, dhi, temp_air, cloud_cover. Blocks missing from it are 0."""
    out = [0.0] * config.BLOCKS_PER_DAY
    if roof is None or weather.empty:
        return out
    kw = roof_kw(roof, weather)
    for ts, value in kw.items():
        idx = (ts.hour * 60 + ts.minute) // config.BLOCK_MINUTES
        out[idx] = round(float(value) * 0.25, 4)
    return out


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

    async with httpx.AsyncClient(timeout=10.0, headers={"X-Goog-Api-Key": api_key}) as client:
        entries: list[dict] = []
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
    for e in entries:
        start = pd.Timestamp(e["interval"]["startTime"]).tz_convert(config.TZ)
        if start.strftime("%Y-%m-%d") != day:
            continue
        rows[start + pd.Timedelta(minutes=30)] = {
            "temp_air": float(e["temperature"]["degrees"]),
            "cloud_cover": float(e.get("cloudCover", 20)),
        }
    if not rows:
        raise ValueError(f"No hourly weather data returned for {day}")
    if len(rows) < 24:
        log.warning("Google returned only %d/24 hours for %s; edges are extended", len(rows), day)

    df_raw = pd.DataFrame.from_dict(rows, orient="index").sort_index()
    target_index = _target_index(day)

    combined_index = target_index.union(df_raw.index).sort_values()
    df_interp = df_raw.reindex(combined_index).interpolate(method="time").bfill().ffill()
    df_res = df_interp.reindex(target_index)
    df_res["cloud_cover"] = df_res["cloud_cover"].clip(lower=0.0, upper=100.0)

    cs = _location.get_clearsky(target_index, model="ineichen", linke_turbidity=3.0)
    solpos = _location.get_solarposition(target_index)
    okta_frac = df_res["cloud_cover"] / 100.0
    ghi = (cs["ghi"] * (1.0 - 0.75 * okta_frac**3.4)).clip(lower=0.0)
    erbs = pvlib.irradiance.erbs(ghi, solpos["apparent_zenith"], target_index.dayofyear)

    df_res["ghi"] = ghi.round(2)
    df_res["dni"] = erbs["dni"].fillna(0.0).clip(lower=0.0).round(2)
    df_res["dhi"] = erbs["dhi"].fillna(0.0).clip(lower=0.0).round(2)
    df_res["cloud_cover"] = df_res["cloud_cover"].round(2)
    df_res["temp_air"] = df_res["temp_air"].round(2)

    return df_res[["ghi", "dni", "dhi", "temp_air", "cloud_cover"]]
