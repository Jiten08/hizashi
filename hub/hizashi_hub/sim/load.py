"""Actual household use per minute: profile mean (interpolated to minutes) + seeded noise
+ modifiers (AC on +1.0 kW, Guests x1.4, Away x0.4)."""
from datetime import datetime

from hizashi_shared.models import HouseInfo


class LoadSim:
    def __init__(self, houses: dict[str, HouseInfo], seed: int) -> None:
        raise NotImplementedError("TODO(R2.2, Anurag)")

    def use_kw(self, house: str, minute: datetime) -> float:
        raise NotImplementedError("TODO(R2.2, Anurag)")
