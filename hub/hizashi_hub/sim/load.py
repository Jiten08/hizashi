"""Actual household use per minute: profile mean (interpolated to minutes) + seeded noise
+ modifiers (AC on +1.0 kW, Guests x1.4, Away x0.4).

The noise is one draw per block from the profile's std, so a block's total varies the
way the forecaster's p10/p90 expect, plus a small per-minute wobble.
"""
from datetime import datetime

import numpy as np

from hizashi_shared import config, profiles
from hizashi_shared.models import HouseInfo

from .events import SimEvents
from .pv import MINUTES, _seed, minute_of_day

AC_KW = 1.0
GUESTS = 1.4
AWAY = 0.4
MIN_KW = 0.02


class LoadSim:
    def __init__(self, houses: dict[str, HouseInfo], seed: int, events: SimEvents | None = None) -> None:
        self.houses = houses
        self.events = events or SimEvents()
        self._base: dict[str, np.ndarray] = {}
        for h, info in houses.items():
            try:
                mean, std = profiles.load_profile(info.profile)
            except Exception:
                mean, std = [0.2] * config.BLOCKS_PER_DAY, [0.04] * config.BLOCKS_PER_DAY
            rng = np.random.default_rng(_seed(seed, h, 2))
            mean, std = np.asarray(mean), np.asarray(std)
            mids = np.arange(config.BLOCKS_PER_DAY) * config.BLOCK_MINUTES + 7.5
            minute_mean = np.interp(np.arange(MINUTES) + 0.5, mids, mean)          # kWh per block
            block_dev = np.repeat(rng.normal(0, std), config.BLOCK_MINUTES)          # kWh per block
            wobble = rng.normal(1, 0.03, MINUTES)
            kw = (minute_mean + block_dev) * (60 / config.BLOCK_MINUTES) * wobble
            self._base[h] = np.clip(kw, MIN_KW, None)

    def use_kw(self, house: str, minute: datetime) -> float:
        kw = float(self._base[house][minute_of_day(minute)])
        if self.events.active(minute, "away", house):
            kw *= AWAY
        if self.events.active(minute, "guests", house):
            kw *= GUESTS
        if self.events.active(minute, "ac", house):
            kw += AC_KW
        return kw
