"""Sell / buy / sit out per block + day plan windows (section 7.4).

spare_low = solar_p10 - use_p90. Sell if spare_low > MIN_TRADE_KWH -> min(spare_low,
max_promise_kwh). Buy if use_p10 > solar_p50 -> use_p10 - solar_p50. Else sit out.
"""
from typing import Literal

from hizashi_shared.models import Forecast, Mandate, PlanWindow

Intent = tuple[Literal["sell", "buy", "none"], float]


def block_intent(f: Forecast, mandate: Mandate) -> Intent:
    raise NotImplementedError("TODO(R1.4, Anurag)")


def plan_windows(house: str, day: str, intents: dict[int, Intent]) -> list[PlanWindow]:
    raise NotImplementedError("TODO(R1.4, Anurag)")
