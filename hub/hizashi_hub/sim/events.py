"""Console events with start/end in sim time: cloud, outage, ac, guests, away.

house=None means street-wide (an outage is always street-wide). Owners' own away / guests
schedules (from the phone) sit beside them in `schedules` and survive a reset.
"""
from datetime import datetime, timedelta

from pydantic import BaseModel

from hizashi_shared import blocks, schedule
from hizashi_shared.models import BlockRef, Schedule

CLOUD_FACTOR = schedule.CLOUD_FACTOR
DEFAULT_MINUTES = {"cloud": 45, "outage": 30, "ac": 120, "guests": 180, "away": 240}


class SimEvent(BaseModel):
    type: str
    house: str | None
    start: datetime
    end: datetime


class SimEvents:
    def __init__(self) -> None:
        self.events: list[SimEvent] = []
        self.schedules: list[Schedule] = []

    def add(self, type_: str, house: str | None, start: datetime, minutes: int | None = None) -> SimEvent:
        minutes = minutes or DEFAULT_MINUTES.get(type_, 30)
        e = SimEvent(type=type_, house=None if type_ == "outage" else house,
                     start=start, end=start + timedelta(minutes=minutes))
        self.events.append(e)
        return e

    def active(self, minute: datetime, type_: str | None = None, house: str | None = None) -> list[SimEvent]:
        return [e for e in self.events
                if e.start <= minute < e.end
                and (type_ is None or e.type == type_)
                and (house is None or e.house in (None, house))]

    def overlapping(self, start: datetime, end: datetime, type_: str) -> list[SimEvent]:
        return [e for e in self.events if e.type == type_ and e.start < end and start < e.end]

    def cloud_factor(self, house: str, minute: datetime) -> float:
        """0.3 under a console cloud, else 1.0."""
        return CLOUD_FACTOR if self.active(minute, "cloud", house) else 1.0

    def use_factor(self, house: str, minute: datetime) -> float:
        """The owner's away / guests multiplier for this minute (1.0 when none is on)."""
        return schedule.factor_at([s for s in self.schedules if s.house == house], minute)

    def outage(self, minute: datetime) -> bool:
        return bool(self.active(minute, "outage"))

    def outage_in(self, ref: BlockRef) -> SimEvent | None:
        """The outage overlapping this block, if any: no neighbour trades for it (KERC 5(c)(iii))."""
        hits = self.overlapping(blocks.block_start(ref), blocks.block_end(ref), "outage")
        return hits[0] if hits else None

    def clear(self) -> None:
        self.events = []


_current: SimEvents | None = None


def use(events: SimEvents) -> None:
    """The running street's events, for the wallet and booking (tests leave it unset)."""
    global _current
    _current = events


def outage_reason(ref: BlockRef) -> str | None:
    """'Grid outage 11:00-11:30: no neighbour trades for 11:15-11:30.' or None."""
    e = _current.outage_in(ref) if _current else None
    if e is None:
        return None
    return f"Grid outage {e.start:%H:%M}-{e.end:%H:%M}: no neighbour trades for {blocks.label(ref)}."
