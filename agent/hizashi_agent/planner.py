"""Sell / buy / sit out per block + day plan windows (section 7.4).

spare_low = solar_p10 - use_p90. If spare_low > MIN_TRADE_KWH -> sell min(spare_low, max_promise_kwh).
Else if use_p10 > solar_p50 -> buy use_p10 - solar_p50.
Else none.

Plan windows group consecutive blocks with the same side, cut at the 3-hour slots
07:00 / 10:00 / 13:00 / 16:00 so the owner approves the day in readable chunks
("Buy 2.4 kWh from neighbours, 10:00–13:00, for about ₹11.23?").
"""
from typing import Literal
import uuid

from hizashi_shared import blocks, config
from hizashi_shared.models import Forecast, Mandate, PlanWindow

Intent = tuple[Literal["sell", "buy", "none"], float]

SLOT_STARTS = {28, 40, 52, 64}      # 07:00, 10:00, 13:00, 16:00


def plan_block(fc: Forecast, mandate: Mandate) -> Intent:
    """Determine intent for a single block."""
    spare_low = fc.solar_p10 - fc.use_p90
    if spare_low > config.MIN_TRADE_KWH:
        kwh = round(min(spare_low, mandate.max_promise_kwh), 3)
        return ("sell", kwh)
    elif fc.use_p10 > fc.solar_p50:
        kwh = round(fc.use_p10 - fc.solar_p50, 3)
        if kwh > 0:
            return ("buy", kwh)
        return ("none", 0.0)
    else:
        return ("none", 0.0)


# Alias block_intent to plan_block for compatibility
block_intent = plan_block


def plan_day(forecasts: list[Forecast], mandate: Mandate) -> dict[int, Intent]:
    """Determine intents for all TRADABLE blocks (26..70)."""
    intents: dict[int, Intent] = {}
    fc_by_idx = {fc.block.index: fc for fc in forecasts}
    for idx in blocks.TRADABLE:
        if idx in fc_by_idx:
            intents[idx] = plan_block(fc_by_idx[idx], mandate)
        else:
            intents[idx] = ("none", 0.0)
    return intents


def plan_windows(house: str, day: str, intents: dict[int, Intent]) -> list[PlanWindow]:
    """Group consecutive blocks with the same non-none side into PlanWindow objects."""
    windows: list[PlanWindow] = []
    sorted_indices = sorted(idx for idx in intents if idx in blocks.TRADABLE)

    current_side: Literal["buy", "sell"] | None = None
    first_idx: int = -1
    last_idx: int = -1
    total_kwh: float = 0.0

    def flush_window():
        nonlocal current_side, first_idx, last_idx, total_kwh
        if current_side is not None and total_kwh > 0:
            kwh = round(total_kwh, 3)
            expected_p = config.EXPECTED_P2P_PRICE
            exp_val = round(kwh * expected_p, 2)
            windows.append(
                PlanWindow(
                    plan_id=str(uuid.uuid4()),
                    house=house,  # type: ignore[arg-type]
                    side=current_side,
                    day=day,
                    first_index=first_idx,
                    last_index=last_idx,
                    kwh=kwh,
                    expected_price=expected_p,
                    expected_value=exp_val,
                    status="auto",
                )
            )
        current_side = None
        first_idx = -1
        last_idx = -1
        total_kwh = 0.0

    for idx in sorted_indices:
        side, kwh = intents[idx]
        if side in ("sell", "buy") and kwh > 0:
            if current_side == side and idx == last_idx + 1 and idx not in SLOT_STARTS:
                last_idx = idx
                total_kwh += kwh
            else:
                flush_window()
                current_side = side
                first_idx = idx
                last_idx = idx
                total_kwh = kwh
        else:
            flush_window()

    flush_window()
    return windows
