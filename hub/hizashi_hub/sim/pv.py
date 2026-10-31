"""Actual roof output per minute: shared.solar on the forecast weather
x cloud factor from console events x seeded noise (+-5%)."""
from datetime import datetime

import pandas as pd

from hizashi_shared.models import HouseInfo


class PvSim:
    def __init__(self, houses: dict[str, HouseInfo], weather: pd.DataFrame, seed: int) -> None:
        raise NotImplementedError("TODO(R2.2, Anurag)")

    def solar_kw(self, house: str, minute: datetime) -> float:
        raise NotImplementedError("TODO(R2.2, Anurag)")
