"""Console events change trading: an outage stops it (wallet, booking, auction, agents), and a
cloud / AC / guests / away re-plans the agent's blocks the moment it hears of it."""
from datetime import datetime

import pytest

from hizashi_agent.runtime import Runtime
from hizashi_hub.market import booking
from hizashi_hub.sim import events as sim_events
from hizashi_hub.sim.events import SimEvents
from hizashi_hub.wallet import signer
from hizashi_shared.config import TZ
from hizashi_shared.models import BlockRef, Forecast

from test_approvals import DAY, bid, conn, events  # noqa: F401  (fixtures)
from test_wallet_checks import STREET, open_only

AT = lambda h, m=0: datetime(2026, 10, 31, h, m, tzinfo=TZ)  # noqa: E731


@pytest.fixture
def street_events():
    e = SimEvents()
    sim_events.use(e)
    yield e
    sim_events._current = None


def test_outage_reason_names_the_window(street_events):
    assert sim_events.outage_reason(BlockRef(day=DAY, index=48)) is None
    street_events.add("outage", None, AT(11, 50), 30)
    assert sim_events.outage_reason(BlockRef(day=DAY, index=48)) == \
        "Grid outage 11:50-12:20: no neighbour trades for 12:00–12:15."
    assert sim_events.outage_reason(BlockRef(day=DAY, index=50)) is None      # 12:30, after it


def test_wallet_and_booking_refuse_trades_in_an_outage(conn, events, street_events):  # noqa: F811
    street_events.add("outage", None, AT(11, 50), 30)
    r = signer.sign_offer_request(conn, "h14", "dev-h14", bid(), open_only, STREET, AT(10, 30))
    assert r["status"] == "refused" and r["reason"].startswith("Grid outage")
    assert not any(e.type == "wallet.blocked" for e in events())      # quiet: it's timing, not the owner's rules
    with pytest.raises(booking.BookingError, match="Grid outage"):
        booking.book(conn, type("C", (), {"contract_id": "c9", "block": BlockRef(day=DAY, index=48)})(),
                     STREET, open_only, AT(10, 30))
    # Once the outage is elsewhere, the same bid signs.
    street_events.events = []
    street_events.add("outage", None, AT(13), 30)
    assert signer.sign_offer_request(conn, "h14", "dev-h14", bid(offer_id="b48b"), open_only,
                                     STREET, AT(10, 30))["status"] == "signed"


def fc(index: int, solar: float, use: float) -> Forecast:
    return Forecast(house="h12", block=BlockRef(day=DAY, index=index), solar_p10=solar * 0.8, solar_p50=solar,
                    solar_p90=solar * 1.2, use_p10=use * 0.8, use_p50=use, use_p90=use * 1.2, made_at=AT(5))


def ev(type_, start, end, house="h12") -> dict:
    return {"type": type_, "house": house, "start": start.isoformat(), "end": end.isoformat()}


async def test_agent_replans_on_a_cloud_and_stops_selling():
    rt = Runtime("h12")
    rt.planned = True
    rt.forecasts = {48: fc(48, 1.0, 0.2), 49: fc(49, 1.0, 0.2)}
    rt.block_states = {f"{DAY}#48": "OPEN", f"{DAY}#49": "PLANNED"}
    rt.replan_block(48)
    rt.replan_block(49)
    before = dict(rt.remaining_sell)
    assert before[48] > 0.3

    await rt.on_sim_event(ev("cloud", AT(12), AT(12, 45)))
    assert rt.remaining_sell.get(48, 0) < before[48] * 0.5 and rt.remaining_sell.get(49, 0) < before[49] * 0.5

    await rt.on_sim_event(ev("cloud", AT(13), AT(14), house="h16"))    # someone else's cloud
    assert len(rt.sim_events) == 1


async def test_agent_load_events_and_outage():
    rt = Runtime("h12")
    base = fc(48, 0.5, 0.2)
    rt.sim_events = [{"type": "ac", "house": "h12", "start": AT(12), "end": AT(14)}]
    assert rt.event_adjust(base).use_p50 == pytest.approx(0.2 + 0.25)
    rt.sim_events = [{"type": "away", "house": "h12", "start": AT(12), "end": AT(14)}]
    assert rt.event_adjust(base).use_p50 == pytest.approx(0.08)
    rt.sim_events = [{"type": "guests", "house": "h12", "start": AT(12, 7, ), "end": AT(14)}]  # half the block
    assert rt.event_adjust(base).use_p50 == pytest.approx(0.2 * (1 + 0.4 * 8 / 15))
    rt.sim_events = [{"type": "outage", "house": None, "start": AT(11, 50), "end": AT(12, 20)}]
    assert rt.outage_over(48) and rt.outage_over(49) and not rt.outage_over(50)
