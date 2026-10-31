"""Owner away / guests schedules (N7), the next-day reset, and approval push payloads."""
import asyncio
from datetime import datetime

import pytest

from hizashi_agent import forecaster
from hizashi_hub import bus, db, schedules
from hizashi_hub.clock import SimClock
from hizashi_hub.notify import webpush
from hizashi_hub.sim import weather
from hizashi_hub.sim.events import SimEvents
from hizashi_hub.sim.load import LoadSim
from hizashi_shared import blocks, events as ev, schedule, street
from hizashi_shared.config import TZ
from hizashi_shared.models import Approval, Schedule

DAY = "2026-10-31"
NOW = datetime(2026, 10, 31, 8, 0, tzinfo=TZ)


def at(h: int, m: int = 0, day: int = 31) -> datetime:
    return datetime(2026, 10, day, h, m, tzinfo=TZ)


def sched(kind="away", start=at(9), end=at(18), house="h12") -> Schedule:
    return Schedule(schedule_id=f"{kind}{start:%H%M}", house=house, kind=kind, start=start, end=end, created_at=NOW)


@pytest.fixture
def conn(tmp_path):
    c = db.connect(tmp_path / "t.db")
    db.init(c)
    yield c
    c.close()


# --- factors ---------------------------------------------------------------------------------

def test_use_factors_whole_partial_and_overlapping_blocks():
    f = schedule.use_factors([sched("away", at(9), at(18))], DAY)
    assert f[35] == 1.0 and f[36] == 0.4 and f[71] == 0.4 and f[72] == 1.0     # 09:00 .. 17:45 blocks
    # 09:05 start covers 10 of the block's 15 minutes: 1 + (0.4 - 1) x 10/15 = 0.6
    assert schedule.use_factors([sched("away", at(9, 5), at(10))], DAY)[36] == 0.6
    # away and guests over the same block multiply, as the load sim does minute by minute
    both = [sched("away", at(12), at(13)), sched("guests", at(12), at(14))]
    assert schedule.use_factors(both, DAY)[48] == round(0.4 * 1.4, 4)
    assert schedule.use_factors(both, DAY)[52] == 1.4
    # a schedule on another day leaves this one alone
    assert set(schedule.use_factors([sched("away", at(9, day=30), at(18, day=30))], DAY)) == {1.0}


def test_forecast_and_load_sim_follow_the_schedule():
    houses = street.load_houses()
    frame = weather.clear_sky_fallback(DAY)
    plain = forecaster.forecast_day(houses["h12"], frame, DAY)
    factors = schedule.use_factors([sched("guests", at(12), at(13))], DAY)
    guests = forecaster.forecast_day(houses["h12"], frame, DAY, use_factors=factors)
    assert guests[48].use_p50 == pytest.approx(plain[48].use_p50 * 1.4, abs=1e-3)
    assert guests[47].use_p50 == plain[47].use_p50

    events = SimEvents()
    load = LoadSim(houses, seed=7, events=events)
    before = load.use_kw("h12", at(12, 30))
    other = load.use_kw("h14", at(12, 30))
    events.schedules = [sched("away", at(12), at(13))]
    assert load.use_kw("h12", at(12, 30)) == pytest.approx(before * 0.4)
    assert load.use_kw("h14", at(12, 30)) == other                                 # other houses untouched
    events.clear()                                                                 # a reset keeps owners' plans
    assert load.use_kw("h12", at(12, 30)) == pytest.approx(before * 0.4)


# --- hub store ---------------------------------------------------------------------------------

def test_add_list_remove_and_publish(conn):
    q = bus.subscribe()
    events = SimEvents()
    try:
        s = schedules.add(conn, events, "h12", "away", DAY, "09:00", "18:00", NOW)
        t = schedules.add(conn, events, "h12", "guests", "2026-11-01", "11:00", "24:00", NOW)
        assert (t.start, t.end) == (datetime(2026, 11, 1, 11, tzinfo=TZ), datetime(2026, 11, 2, 0, 0, tzinfo=TZ))
        assert [x.schedule_id for x in events.schedules] == [s.schedule_id, t.schedule_id]
        e = q.get_nowait()
        assert e.type == ev.SCHEDULE_UPDATED and e.house == "h12"
        # next day: today's plan has ended before the day began, so only tomorrow's is listed
        assert [x.schedule_id for x in schedules.listing(conn, "h12", "2026-11-01")] == [t.schedule_id]
        assert schedules.remove(conn, events, "h12", s.schedule_id, NOW)
        assert not schedules.remove(conn, events, "h14", t.schedule_id, NOW)        # not h14's to remove
        assert [x.schedule_id for x in events.schedules] == [t.schedule_id]
    finally:
        bus.unsubscribe(q)


@pytest.mark.parametrize("day,start,end,msg", [
    (DAY, "09:00", "09:00", "after the start"),
    (DAY, "09:10", "10:00", "quarter hour"),
    ("2026-10-30", "09:00", "10:00", "over"),
    (DAY, "06:00", "08:00", "past"),
    ("2026-11-09", "09:00", "10:00", "7 days"),
])
def test_add_refuses(conn, day, start, end, msg):
    with pytest.raises(schedules.ScheduleError, match=msg):
        schedules.add(conn, SimEvents(), "h12", "away", day, start, end, NOW)


# --- next day ------------------------------------------------------------------------------------

async def test_reset_can_move_to_the_next_day():
    q = bus.subscribe()
    c = SimClock(DAY, 60)
    try:
        await c.reset("2026-11-01")
        await c.stop()
        assert c.day == "2026-11-01" and c.now == blocks.day_start("2026-11-01")
        ticks = []
        while not q.empty():
            e = q.get_nowait()
            if e.type == ev.CLOCK_TICK and e.data.get("reset"):
                ticks.append(e)
        assert ticks and ticks[0].data["day"] == "2026-11-01"
    finally:
        await c.stop()
        bus.unsubscribe(q)
    assert blocks.next_day("2026-10-31") == "2026-11-01" and blocks.next_day("2026-12-31") == "2027-01-01"


# --- push ------------------------------------------------------------------------------------------

def test_approval_push_payloads():
    a = Approval(approval_id="a1", house="h14", kind="plan", ref_id="p1", code="4821",
                 summary="Buy 2.4 kWh from neighbours, 10:00–13:00, for about ₹11.23?", created_at=NOW)
    p = webpush.approval_payload(a)
    assert p == {"title": "Needs your OK", "body": a.summary, "tag": "a1",
                 "url": "/app/?house=h14&tab=approvals", "approval_id": "a1"}
    done = webpush.approval_payload(a.model_copy(update={"status": "expired"}))
    assert done["title"] == "Went ahead" and done["quiet"] and "approval_id" not in done


async def test_push_subscriptions_and_gone_endpoints(conn, monkeypatch):
    sub = {"endpoint": "https://push.example/abc", "keys": {"p256dh": "k", "auth": "a"}}
    webpush.subscribe(conn, "h14", sub, NOW)
    webpush.subscribe(conn, "h12", sub, NOW)                   # same phone moved to another house
    assert webpush.subscriptions(conn, "h14") == [] and webpush.subscriptions(conn, "h12") == [sub]
    monkeypatch.setattr(webpush, "_send_all", lambda subs, payload, urgent: [s["endpoint"] for s in subs])
    assert await webpush.send(conn, "h12", {"title": "x"}) == 0
    assert webpush.subscriptions(conn, "h12") == []            # the push service said it's gone


# --- agent restarted mid-day ------------------------------------------------------------------

async def test_agent_start_reads_day_mandates_and_blocks_from_the_hub(monkeypatch):
    from hizashi_agent.runtime import Runtime

    mandate = {**street.load_mandates()["h12"].model_dump(mode="json"), "version": 7, "min_sell_price": 4.5}

    class Hub:
        async def get_registry(self):
            return {}

        async def get_state(self):
            return {"sim_time": "2026-11-01T09:40:00+05:30", "mandates": {"h12": mandate},
                    "blocks": {"2026-11-01#46": "OPEN", "2026-11-01#38": "SETTLED"}}

    rt = Runtime("h12", hub=Hub())  # type: ignore[arg-type]
    planned, selling = [], []

    async def plan():
        planned.append(rt.day)
        rt.remaining_sell[46] = 0.5

    async def sell(ref):
        selling.append(ref.key)

    monkeypatch.setattr(rt, "forecast_and_plan", plan)
    monkeypatch.setattr(rt, "negotiate_sell", sell)
    await rt.start()
    await asyncio.sleep(0)
    assert rt.day == "2026-11-01" and planned == ["2026-11-01"]
    assert rt.current_sim_time == datetime(2026, 11, 1, 9, 40, tzinfo=TZ)
    assert rt.mandates["h12"].version == 7 and rt.mandates["h12"].min_sell_price == 4.5
    assert rt.block_states == {"2026-11-01#46": "OPEN", "2026-11-01#38": "SETTLED"}
    assert selling == ["2026-11-01#46"]                     # picks up the block that's already open
