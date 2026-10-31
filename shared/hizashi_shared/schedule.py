"""Owner schedules (N7): away, or guests at home, from a start to an end time.

While one is on, the home's use is multiplied by AWAY (0.4) or GUESTS (1.4). The hub's load
sim and the agent's forecast both take the factors from here, so the plan expects what the
meter will see.
"""
from datetime import datetime

from . import blocks, config
from .models import BlockRef, Schedule

AWAY = 0.4
GUESTS = 1.4
FACTOR = {"away": AWAY, "guests": GUESTS}


def factor_at(schedules: list[Schedule], minute: datetime) -> float:
    """The use multiplier for one minute (overlapping schedules multiply)."""
    f = 1.0
    for s in schedules:
        if s.start <= minute < s.end:
            f *= FACTOR[s.kind]
    return f


def use_factors(schedules: list[Schedule], day: str) -> list[float]:
    """Per block of `day`: the use multiplier, weighted by how much of the block each schedule covers."""
    out = []
    for i in range(config.BLOCKS_PER_DAY):
        ref = BlockRef(day=day, index=i)
        start, end = blocks.block_start(ref), blocks.block_end(ref)
        f = 1.0
        for s in schedules:
            overlap = (min(end, s.end) - max(start, s.start)).total_seconds()
            if overlap > 0:
                f *= 1 + (FACTOR[s.kind] - 1) * overlap / (end - start).total_seconds()
        out.append(round(f, 4))
    return out
