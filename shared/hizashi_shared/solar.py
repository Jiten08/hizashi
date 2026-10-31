"""Roof output per 15-min block with pvlib (used by the hub sim AND the agents).

Chain: solar position -> plane-of-array irradiance -> SAPM cell temperature
-> PVWatts DC -> PVWatts inverter (clips at inverter_kw) -> kW x 0.25 h.
pvlib arguments are passed positionally where names changed across versions.
"""
import numpy as np
import pandas as pd
import pvlib

from . import config
from .models import Roof

GAMMA_PDC = -0.004          # %/°C power temperature coefficient (typical c-Si)
ETA_INV = 0.96
WIND_SPEED = 1.0            # m/s, no wind data from the forecast
_TEMP_PARAMS = pvlib.temperature.TEMPERATURE_MODEL_PARAMETERS["sapm"]["close_mount_glass_glass"]

_location = pvlib.location.Location(config.LAT, config.LON, config.TZ_NAME, config.ALT)


def roof_kw(roof: Roof, weather: pd.DataFrame) -> pd.Series:
    """AC kW at each timestamp of `weather` (needs ghi, dni, dhi, temp_air)."""
    solpos = _location.get_solarposition(weather.index)
    poa = pvlib.irradiance.get_total_irradiance(
        roof.tilt, roof.azimuth,
        solpos["apparent_zenith"], solpos["azimuth"],
        weather["dni"], weather["ghi"], weather["dhi"],
    )
    poa_global = poa["poa_global"].fillna(0).clip(lower=0)
    t_cell = pvlib.temperature.sapm_cell(
        poa_global, weather["temp_air"], WIND_SPEED,
        _TEMP_PARAMS["a"], _TEMP_PARAMS["b"], _TEMP_PARAMS["deltaT"],
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
