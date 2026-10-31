import asyncio
import json
import shutil
from pathlib import Path
from unittest.mock import AsyncMock, patch

import numpy as np
from fastapi.testclient import TestClient

from hizashi_agent.forecaster import forecast_day
from hizashi_hub.app import app
from hizashi_hub.sim import weather
from hizashi_shared import config
from hizashi_shared.models import HouseInfo, Roof
from hizashi_shared.profiles import load_profile
from hizashi_shared.solar import roof_kwh_per_block, weather_frame

DAY = "2026-10-31"
TEST_CACHE_DIR = Path(__file__).resolve().parent / "_test_weather_cache"


def setup_function():
    TEST_CACHE_DIR.mkdir(parents=True, exist_ok=True)


def teardown_function():
    if TEST_CACHE_DIR.exists():
        shutil.rmtree(TEST_CACHE_DIR, ignore_errors=True)


def test_load_profile():
    """Verify load_profile returns valid 96-element arrays for mean and std for all 4 profiles."""
    profiles = ["couple_away_day", "wfh_ac", "family_medium", "heavy_appliances"]
    for name in profiles:
        mean, std = load_profile(name)
        assert len(mean) == 96, f"{name}: expected 96 mean values, got {len(mean)}"
        assert len(std) == 96, f"{name}: expected 96 std values, got {len(std)}"
        assert all(isinstance(x, (float, int)) and x >= 0 for x in mean)
        assert all(isinstance(x, (float, int)) and x >= 0 for x in std)
        assert np.isclose(std[30], mean[30] * 0.20, atol=1e-3)


def test_clear_sky_fallback():
    """Verify clear-sky fallback produces a 96-block 15-minute DataFrame with required columns."""
    df = weather.clear_sky_fallback(DAY)
    assert len(df) == 96
    expected_cols = {"ghi", "dni", "dhi", "temp_air", "cloud_cover"}
    assert set(df.columns) == expected_cols
    assert (df["cloud_cover"] == 20.0).all()
    # At solar noon (around block 48 / 12:00), irradiance should be high
    assert df["ghi"].iloc[48] > 500
    # At night (00:00 / block 0), irradiance should be zero
    assert df["ghi"].iloc[0] == 0.0


def test_load_weather_offline_fallback():
    """Verify fetch failure gracefully falls back to clear-sky without raising exceptions."""
    async def mock_offline(day: str):
        raise RuntimeError("Offline")

    with patch.object(weather, "fetch_open_meteo", mock_offline):
        frame, source = asyncio.run(weather.load_weather(DAY, cache_dir=TEST_CACHE_DIR))
        assert source == "clear-sky fallback"
        assert len(frame) == 96
        assert (TEST_CACHE_DIR / f"{DAY}.json").exists()


def test_weather_cache_hit():
    """Verify load_weather uses the cached file when present on disk."""
    frame_orig = weather.clear_sky_fallback(DAY)
    cache_json = weather.to_json(frame_orig, "cached-test-source", DAY)
    (TEST_CACHE_DIR / f"{DAY}.json").write_text(json.dumps(cache_json), encoding="utf-8")

    frame, source = asyncio.run(weather.load_weather(DAY, cache_dir=TEST_CACHE_DIR))
    assert source == "cached-test-source"
    assert len(frame) == 96


def test_weather_frame():
    """Verify weather_frame converts weather JSON to a 15-min indexed DataFrame."""
    df_raw = weather.clear_sky_fallback(DAY)
    w_json = weather.to_json(df_raw, "test", DAY)
    df = weather_frame(w_json)

    assert len(df) == 96
    assert list(df.columns) == ["ghi", "dni", "dhi", "temp_air", "cloud_cover"]
    assert str(df.index.tz) == config.TZ_NAME
    assert df.index[0].hour == 0 and df.index[0].minute == 0
    assert df.index[95].hour == 23 and df.index[95].minute == 45


def test_roof_kwh_per_block():
    """Verify House 12 (~0.8 kWh at noon block) and House 14 (0 kWh)."""
    df_weather = weather.clear_sky_fallback(DAY)

    # House 12: 5 kWp roof, 13 deg tilt, 180 deg azimuth, 5 kW inverter
    roof_h12 = Roof(kwp=5.0, tilt=13.0, azimuth=180.0, inverter_kw=5.0)
    kwh_h12 = roof_kwh_per_block(roof_h12, df_weather)

    assert len(kwh_h12) == 96
    # Noon block is block 48 (12:00-12:15) - yields ~0.8 kWh
    noon_kwh = kwh_h12[48]
    assert 0.70 <= noon_kwh <= 1.05, f"Expected ~0.8 kWh for House 12 at noon, got {noon_kwh}"

    # House 14: non-solar (roof=None)
    kwh_h14 = roof_kwh_per_block(None, df_weather)
    assert len(kwh_h14) == 96
    assert all(x == 0.0 for x in kwh_h14)


def test_forecast_day():
    """Verify forecast_day outputs 96 Forecast objects with correct p10/p50/p90 logic."""
    df_weather = weather.clear_sky_fallback(DAY)
    w_json = weather.to_json(df_weather, "test", DAY)

    house_h12 = HouseInfo(
        id="h12",
        label="House 12",
        transformer="T1",
        roof=Roof(kwp=5.0, tilt=13.0, azimuth=180.0, inverter_kw=5.0),
        profile="couple_away_day",
        buyback_rate=3.89,
        metering="net",
        agent_url="http://127.0.0.1:9012/",
    )
    house_h14 = HouseInfo(
        id="h14",
        label="House 14",
        transformer="T1",
        roof=None,
        profile="wfh_ac",
        buyback_rate=None,
        metering="none",
        agent_url="http://127.0.0.1:9014/",
    )

    forecasts_12 = forecast_day(house_h12, w_json)
    assert len(forecasts_12) == 96

    for f in forecasts_12:
        assert f.house == "h12"
        assert f.solar_p10 <= f.solar_p50 <= f.solar_p90
        assert f.use_p10 <= f.use_p50 <= f.use_p90

    # Solar checks for H12 noon
    assert forecasts_12[48].solar_p50 > 0.5

    # Solar checks for H14 (no solar)
    forecasts_14 = forecast_day(house_h14, w_json)
    assert len(forecasts_14) == 96
    for f in forecasts_14:
        assert f.solar_p10 == 0.0
        assert f.solar_p50 == 0.0
        assert f.solar_p90 == 0.0
        assert f.use_p10 <= f.use_p50 <= f.use_p90

    # Modifiers check: AC on should increase consumption by 0.25 kWh
    forecasts_14_ac = forecast_day(house_h14, w_json, modifiers={"ac": True})
    assert forecasts_14_ac[48].use_p50 > forecasts_14[48].use_p50
    assert np.isclose(forecasts_14_ac[48].use_p50 - forecasts_14[48].use_p50, 0.25, atol=1e-3)


def test_api_weather_route():
    """Verify GET /api/weather endpoint serves valid 96-block forecast data."""
    # Ensure cache exists so test doesn't wait on external network
    frame_orig = weather.clear_sky_fallback(DAY)
    cache_json = weather.to_json(frame_orig, "clear-sky fallback", DAY)
    config.WEATHER_DIR.mkdir(parents=True, exist_ok=True)
    cache_file = config.WEATHER_DIR / f"{config.SIM_DAY}.json"
    cache_file.write_text(json.dumps(cache_json), encoding="utf-8")

    client = TestClient(app)
    resp = client.get("/api/weather")
    assert resp.status_code == 200
    data = resp.json()
    assert "day" in data
    assert "source" in data
    assert "blocks" in data
    assert len(data["blocks"]) == 96
    b0 = data["blocks"][0]
    for key in ("index", "ts", "ghi", "dni", "dhi", "temp_air", "cloud_cover"):
        assert key in b0
