"""Tests for planner.py (R1.4)."""
from datetime import datetime, timezone
from hizashi_shared.models import BlockRef, Forecast, Mandate
from hizashi_agent.planner import plan_block, plan_day, plan_windows


def _make_fc(house: str, block_idx: int, solar_p10: float, solar_p50: float, solar_p90: float,
              use_p10: float, use_p50: float, use_p90: float) -> Forecast:
    return Forecast(
        house=house,  # type: ignore[arg-type]
        block=BlockRef(day="2026-10-31", index=block_idx),
        solar_p10=solar_p10,
        solar_p50=solar_p50,
        solar_p90=solar_p90,
        use_p10=use_p10,
        use_p50=use_p50,
        use_p90=use_p90,
        made_at=datetime(2026, 10, 31, 5, 0, tzinfo=timezone.utc),
    )


def _make_mandate(house: str, max_promise: float = 1.0) -> Mandate:
    return Mandate(
        house=house,  # type: ignore[arg-type]
        min_sell_price=4.20,
        max_buy_price=5.50,
        daily_budget=50.0,
        max_promise_kwh=max_promise,
        approve_above=10.0,
    )


def test_deck_block():
    # H12 at 12:00 (block 48) with solar_p10 0.65 and use_p90 0.25 -> sell 0.40
    fc = _make_fc("h12", 48, solar_p10=0.65, solar_p50=0.80, solar_p90=0.95,
                  use_p10=0.15, use_p50=0.20, use_p90=0.25)
    m = _make_mandate("h12", max_promise=1.0)
    intent = plan_block(fc, m)
    assert intent == ("sell", 0.40)


def test_no_solar_house():
    # A no-solar house with use_p10 0.20 -> buy 0.20
    fc = _make_fc("h14", 48, solar_p10=0.0, solar_p50=0.0, solar_p90=0.0,
                  use_p10=0.20, use_p50=0.30, use_p90=0.40)
    m = _make_mandate("h14", max_promise=1.0)
    intent = plan_block(fc, m)
    assert intent == ("buy", 0.20)


def test_tiny_spare():
    # spare_low <= MIN_TRADE_KWH (0.05) -> none
    fc = _make_fc("h12", 48, solar_p10=0.24, solar_p50=0.40, solar_p90=0.50,
                  use_p10=0.10, use_p50=0.15, use_p90=0.20)
    # spare_low = 0.24 - 0.20 = 0.04 <= 0.05
    # use_p10 (0.10) <= solar_p50 (0.40) -> none
    m = _make_mandate("h12", max_promise=1.0)
    intent = plan_block(fc, m)
    assert intent == ("none", 0.0)


def test_max_promise_caps_sale():
    # spare_low = 1.5, max_promise = 1.0 -> sell 1.0
    fc = _make_fc("h12", 48, solar_p10=1.8, solar_p50=2.0, solar_p90=2.2,
                  use_p10=0.2, use_p50=0.25, use_p90=0.3)
    # spare_low = 1.8 - 0.3 = 1.5 > max_promise (1.0)
    m = _make_mandate("h12", max_promise=1.0)
    intent = plan_block(fc, m)
    assert intent == ("sell", 1.0)


def test_plan_day_and_windows():
    m = _make_mandate("h12", max_promise=1.0)
    fcs = [
        _make_fc("h12", idx, solar_p10=0.65, solar_p50=0.80, solar_p90=0.95,
                 use_p10=0.15, use_p50=0.20, use_p90=0.25)
        for idx in range(24, 76)
    ]
    intents = plan_day(fcs, m)
    assert len(intents) == 52  # blocks 24..75
    assert all(intents[i][0] == "sell" for i in range(24, 76))

    windows = plan_windows("h12", "2026-10-31", intents)
    assert len(windows) == 1
    w = windows[0]
    assert w.first_index == 24
    assert w.last_index == 75
    assert w.side == "sell"
    assert round(w.kwh, 2) == round(52 * 0.40, 2)
