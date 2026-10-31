"""p10/p50/p90 solar + use per block (section 7.4).

Solar p50 = shared.solar on the hub's forecast weather; u = 0.10 + 0.40 x cloud_cover/100;
p10 = p50 (1 - u), p90 = p50 (1 + u). Use: p50 = mean, p10 = max(mean - 1.28 sd, 0),
p90 = mean + 1.28 sd, with Away/Guests/AC modifiers.
"""
import pandas as pd

from hizashi_shared.models import Forecast, HouseInfo


def forecast_day(house: HouseInfo, weather: pd.DataFrame, day: str) -> list[Forecast]:
    raise NotImplementedError("TODO(R1.3, Anurag)")
