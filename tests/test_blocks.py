from datetime import datetime, timedelta

from hizashi_shared import blocks
from hizashi_shared.config import TZ
from hizashi_shared.models import BlockRef

DAY = "2026-10-31"


def t(h: int, m: int = 0) -> datetime:
    return datetime(2026, 10, 31, h, m, tzinfo=TZ)


def test_key_format():
    assert BlockRef(day=DAY, index=48).key == "2026-10-31#48"
    assert BlockRef(day=DAY, index=5).key == "2026-10-31#05"
    assert blocks.parse_key("2026-10-31#05") == BlockRef(day=DAY, index=5)


def test_block_start_and_of():
    ref = BlockRef(day=DAY, index=48)
    assert blocks.block_start(ref) == t(12)
    assert blocks.block_end(ref) == t(12, 15)
    assert blocks.block_of(t(12)) == ref
    assert blocks.block_of(t(12, 14)) == ref
    assert blocks.block_of(t(12, 15)).index == 49
    assert blocks.block_of(datetime(2026, 10, 31, 12, 7)) == ref   # naive = IST
    assert blocks.label(ref) == "12:00–12:15"


def test_block_of_roundtrip_all_blocks():
    for i in range(96):
        ref = BlockRef(day=DAY, index=i)
        assert blocks.block_of(blocks.block_start(ref)) == ref


def test_lifecycle_times():
    ref = BlockRef(day=DAY, index=48)
    assert blocks.gate_close(ref) == t(11)
    assert blocks.open_time(ref) == t(10)
    assert blocks.settle_time(ref) == t(12, 15)


def test_open_time_clamped_to_day_start():
    first = BlockRef(day=DAY, index=24)     # 06:00
    assert blocks.open_time(first) == t(5)
    assert blocks.gate_close(first) == t(5)
    assert blocks.open_time(BlockRef(day=DAY, index=28)) == t(5)   # 07:00 - 120 = 05:00
    assert blocks.open_time(BlockRef(day=DAY, index=29)) == t(5, 15)


def test_tradable_range():
    assert blocks.TRADABLE == range(24, 76)
    assert blocks.label(BlockRef(day=DAY, index=24)) == "06:00–06:15"
    assert blocks.label(BlockRef(day=DAY, index=75)) == "18:45–19:00"
    assert len(blocks.tradable_blocks(DAY)) == 52


def test_state_at_walks_the_lifecycle():
    ref = BlockRef(day=DAY, index=48)
    assert blocks.state_at(ref, t(4, 59)) is None
    assert blocks.state_at(ref, t(5)) == "PLANNED"
    assert blocks.state_at(ref, t(9, 59)) == "PLANNED"
    assert blocks.state_at(ref, t(10)) == "OPEN"
    assert blocks.state_at(ref, t(10, 59)) == "OPEN"
    assert blocks.state_at(ref, t(11)) == "GATE_CLOSED"
    assert blocks.state_at(ref, t(12)) == "DELIVERING"
    assert blocks.state_at(ref, t(12, 15)) == "SETTLED"
    assert blocks.state_at(BlockRef(day=DAY, index=10), t(12)) is None   # never opens


def test_all_blocks_settled_at_day_end():
    end = blocks.day_end(DAY)
    assert all(blocks.state_at(r, end) == "SETTLED" for r in blocks.tradable_blocks(DAY))
    assert blocks.state_at(BlockRef(day=DAY, index=75), end - timedelta(minutes=1)) == "DELIVERING"
