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


def test_surplus_block_sells_90_percent():
    # H12 at 12:00: expected 0.80 solar, 0.20 use -> surplus 0.60 -> sell 0.54
    fc = _make_fc("h12", 48, solar_p10=0.65, solar_p50=0.80, solar_p90=0.95,
                  use_p10=0.15, use_p50=0.20, use_p90=0.25)
    assert plan_block(fc, _make_mandate("h12", max_promise=1.0)) == ("sell", 0.54)


def test_no_solar_house_buys_expected_use():
    fc = _make_fc("h14", 48, solar_p10=0.0, solar_p50=0.0, solar_p90=0.0,
                  use_p10=0.20, use_p50=0.30, use_p90=0.40)
    assert plan_block(fc, _make_mandate("h14", max_promise=1.0)) == ("buy", 0.30)


def test_solar_house_buys_in_a_deficit_block():
    # Evening: 0.05 solar, 0.40 use -> the seller of noon is a buyer now
    fc = _make_fc("h12", 70, solar_p10=0.04, solar_p50=0.05, solar_p90=0.06,
                  use_p10=0.30, use_p50=0.40, use_p90=0.50)
    assert plan_block(fc, _make_mandate("h12", max_promise=1.0)) == ("buy", 0.35)


def test_tiny_net_sits_out():
    fc = _make_fc("h12", 48, solar_p10=0.24, solar_p50=0.30, solar_p90=0.36,
                  use_p10=0.20, use_p50=0.26, use_p90=0.32)
    assert plan_block(fc, _make_mandate("h12", max_promise=1.0)) == ("none", 0.0)


def test_max_promise_caps_both_sides():
    fc = _make_fc("h12", 48, solar_p10=1.8, solar_p50=2.0, solar_p90=2.2,
                  use_p10=0.2, use_p50=0.25, use_p90=0.3)
    assert plan_block(fc, _make_mandate("h12", max_promise=1.0)) == ("sell", 1.0)
    fc = _make_fc("h14", 48, solar_p10=0, solar_p50=0, solar_p90=0, use_p10=1.2, use_p50=1.5, use_p90=1.8)
    assert plan_block(fc, _make_mandate("h14", max_promise=1.0)) == ("buy", 1.0)


def test_plan_day_and_windows():
    m = _make_mandate("h12", max_promise=1.0)
    fcs = [
        _make_fc("h12", idx, solar_p10=0.65, solar_p50=0.80, solar_p90=0.95,
                 use_p10=0.15, use_p50=0.20, use_p90=0.25)
        for idx in range(26, 71)
    ]
    intents = plan_day(fcs, m)
    assert len(intents) == 45  # blocks 26..70
    assert all(intents[i][0] == "sell" for i in range(26, 71))

    windows = plan_windows("h12", "2026-10-31", intents)
    assert [(w.first_index, w.last_index) for w in windows] == [(26, 27), (28, 39), (40, 51), (52, 63), (64, 70)]
    assert all(w.side == "sell" for w in windows)
    assert round(sum(w.kwh for w in windows), 2) == round(45 * 0.54, 2)
    w = windows[2]                                    # 10:00-13:00
    assert w.kwh == 6.48 and w.expected_value == round(6.48 * 4.68, 2)
