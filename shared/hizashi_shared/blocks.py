"""Block index <-> simulated IST time, and block lifecycle times (section 4.4)."""
from datetime import date, datetime, timedelta

from . import config
from .models import BlockRef

TRADABLE = range(24, 76)    # 06:00–18:45; other blocks never open
DAY_START = config.DAY_START
DAY_END = config.DAY_END
_BLOCK = timedelta(minutes=config.BLOCK_MINUTES)


def _day(d: str) -> date:
    return date.fromisoformat(d)


def day_start(day: str) -> datetime:
    return datetime.combine(_day(day), DAY_START, tzinfo=config.TZ)


def day_end(day: str) -> datetime:
    return datetime.combine(_day(day), DAY_END, tzinfo=config.TZ)


def block_start(ref: BlockRef) -> datetime:
    midnight = datetime.combine(_day(ref.day), datetime.min.time(), tzinfo=config.TZ)
    return midnight + ref.index * _BLOCK


def block_end(ref: BlockRef) -> datetime:
    return block_start(ref) + _BLOCK


def block_of(dt: datetime) -> BlockRef:
    """The block containing dt (naive datetimes are taken as IST)."""
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=config.TZ)
    dt = dt.astimezone(config.TZ)
    index = (dt.hour * 60 + dt.minute) // config.BLOCK_MINUTES
    return BlockRef(day=dt.date().isoformat(), index=index)


def gate_close(ref: BlockRef) -> datetime:
    return block_start(ref) - timedelta(minutes=60)


def open_time(ref: BlockRef) -> datetime:
    return max(day_start(ref.day), block_start(ref) - timedelta(minutes=120))


def settle_time(ref: BlockRef) -> datetime:
    return block_start(ref) + _BLOCK


def label(ref: BlockRef) -> str:
    """'12:00–12:15'"""
    s, e = block_start(ref), block_end(ref)
    return f"{s:%H:%M}–{e:%H:%M}"


def parse_key(key: str) -> BlockRef:
    day, idx = key.split("#")
    return BlockRef(day=day, index=int(idx))


def tradable_blocks(day: str) -> list[BlockRef]:
    return [BlockRef(day=day, index=i) for i in TRADABLE]


def state_at(ref: BlockRef, now: datetime) -> str | None:
    """Lifecycle state of a tradable block at sim time `now` (section 6.2).

    None for non-tradable blocks or before day start.
    """
    if ref.index not in TRADABLE or now < day_start(ref.day):
        return None
    if now >= settle_time(ref):
        return "SETTLED"
    if now >= block_start(ref):
        return "DELIVERING"
    if now >= gate_close(ref):
        return "GATE_CLOSED"
    if now >= open_time(ref):
        return "OPEN"
    return "PLANNED"
