"""Actual roof output per minute: shared.solar on the forecast weather
x cloud factor from console events x seeded noise (+-5%).

Each 15-min weather value is the block's mean, placed at the block's midpoint and
interpolated to minutes, so a block's metered kWh matches the forecast before noise.
"""
from datetime import datetime

import numpy as np
import pandas as pd

from hizashi_shared import solar
from hizashi_shared.models import HouseInfo

from .events import SimEvents

MINUTES = 24 * 60


def minute_of_day(minute: datetime) -> int:
    return minute.hour * 60 + minute.minute


def _seed(seed: int, house: str, salt: int) -> int:
    return seed * 1000 + int(house[1:]) * 10 + salt


class PvSim:
    def __init__(self, houses: dict[str, HouseInfo], weather: pd.DataFrame, seed: int,
                 events: SimEvents | None = None) -> None:
        self.houses = houses          # live dict: onboarding can change a roof
        self.weather = weather
        self.seed = seed
        self.events = events or SimEvents()
        self._base: dict[str, np.ndarray] = {}
        self._noise = {h: np.random.default_rng(_seed(seed, h, 1)).uniform(0.95, 1.05, MINUTES)
                       for h in houses}

    def refresh(self, house: str) -> None:
        self._base.pop(house, None)

    def base_kw(self, house: str) -> np.ndarray:
        """Clear-weather kW for every minute of the day (no cloud events, no noise)."""
        if house not in self._base:
            roof = self.houses[house].roof
            if roof is None or self.weather.empty:
                self._base[house] = np.zeros(MINUTES)
            else:
                kw = solar.roof_kw(roof, self.weather)
                mids = np.array([minute_of_day(ts) + 7.5 for ts in kw.index])
                self._base[house] = np.interp(np.arange(MINUTES) + 0.5, mids, kw.to_numpy(), left=0, right=0)
        return self._base[house]

    def solar_kw(self, house: str, minute: datetime) -> float:
        m = minute_of_day(minute)
        kw = self.base_kw(house)[m] * self.events.cloud_factor(house, minute) * self._noise[house][m]
        return max(0.0, float(kw))
