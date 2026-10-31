"""p10/p50/p90 solar + use per block (section 7.4).

Solar p50 = shared.solar on the hub's forecast weather; u = 0.10 + 0.40 x cloud_cover/100;
p10 = p50 (1 - u), p90 = p50 (1 + u). Use: p50 = mean, p10 = max(mean - 1.28 sd, 0),
p90 = mean + 1.28 sd, with Away/Guests/AC modifiers.
"""
from datetime import datetime

import pandas as pd

from hizashi_shared import config
from hizashi_shared.models import BlockRef, Forecast, HouseInfo
from hizashi_shared.profiles import load_profile
from hizashi_shared.solar import roof_kwh_per_block, weather_frame


def forecast_day(
    house: HouseInfo,
    weather: dict | pd.DataFrame,
    day: str | None = None,
    modifiers: dict | None = None,
) -> list[Forecast]:
    """Compute generation and consumption expectations per 15-min block (96 blocks)
    using p10/p50/p90 logic.
    """
    if isinstance(weather, dict):
        weather_df = weather_frame(weather)
        if day is None:
            day = weather.get("day")
    else:
        weather_df = weather

    if day is None:
        if not weather_df.empty and hasattr(weather_df.index, "strftime"):
            day = weather_df.index[0].strftime("%Y-%m-%d")
        else:
            day = config.SIM_DAY

    # Solar generation p50, p10, p90
    if house.roof is not None and house.roof.kwp > 0:
        solar_p50 = roof_kwh_per_block(house.roof, weather_df)
    else:
        solar_p50 = [0.0] * config.BLOCKS_PER_DAY

    cloud_values = (
        weather_df["cloud_cover"].tolist()
        if "cloud_cover" in weather_df.columns and len(weather_df) == config.BLOCKS_PER_DAY
        else [0.0] * config.BLOCKS_PER_DAY
    )

    # Consumption p50, p10, p90
    mean_use, std_use = load_profile(house.profile)
    mods = modifiers or {}

    if mods.get("away"):
        mean_use = [m * 0.4 for m in mean_use]
        std_use = [s * 0.4 for s in std_use]
    elif mods.get("guests"):
        mean_use = [m * 1.4 for m in mean_use]
        std_use = [s * 1.4 for s in std_use]

    if mods.get("ac"):
        # AC on: +1.0 kW -> 0.25 kWh per 15-minute block
        mean_use = [m + 0.25 for m in mean_use]

    made_at = datetime.now(tz=config.TZ)
    forecasts: list[Forecast] = []

    for i in range(config.BLOCKS_PER_DAY):
        # Solar uncertainty
        cloud = float(cloud_values[i])
        u = 0.10 + 0.40 * (cloud / 100.0)
        p50_s = round(float(solar_p50[i]), 4)
        p10_s = round(max(0.0, p50_s * (1.0 - u)), 4)
        p90_s = round(p50_s * (1.0 + u), 4)

        # Use uncertainty
        p50_u = round(float(mean_use[i]), 4)
        sd_u = float(std_use[i])
        p10_u = round(max(0.0, p50_u - 1.28 * sd_u), 4)
        p90_u = round(p50_u + 1.28 * sd_u, 4)

        forecasts.append(
            Forecast(
                house=house.id,
                block=BlockRef(day=day, index=i),
                solar_p10=p10_s,
                solar_p50=p50_s,
                solar_p90=p90_s,
                use_p10=p10_u,
                use_p50=p50_u,
                use_p90=p90_u,
                made_at=made_at,
            )
        )

    return forecasts
