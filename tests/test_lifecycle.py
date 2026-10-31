"""Sim + meters (R2.2), console events (R2.7), auction run and settlement at SETTLED (R2.1, R2.3)."""
from datetime import datetime, timedelta

import pytest

from hizashi_hub import bus, db
from hizashi_hub.market import booking
from hizashi_hub.settlement import ledger
from hizashi_hub.sim.world import Sim, clear_day
from hizashi_hub.wallet import keystore
from hizashi_shared import blocks, config, crypto, solar
from hizashi_shared.config import TZ
from hizashi_shared.models import BlockRef, Contract, HouseInfo, Mandate, Offer, Roof

pytestmark = pytest.mark.filterwarnings("ignore::DeprecationWarning")

DAY = config.SIM_DAY
REF = BlockRef(day=DAY, index=48)
METER = {h: crypto.new_key() for h in ("h12", "h14")}
MARKET = crypto.new_key()


def houses() -> dict[str, HouseInfo]:
    roof = Roof(kwp=5, tilt=13, azimuth=180, inverter_kw=5)
    return {
        "h12": HouseInfo(id="h12", label="House 12", transformer="T1", roof=roof, profile="couple_away_day",
                         buyback_rate=3.89, metering="net", agent_url="x", meter_pubkey=crypto.pub_b64(METER["h12"])),
        "h14": HouseInfo(id="h14", label="House 14", transformer="T1", roof=None, profile="wfh_ac",
                         buyback_rate=None, metering="none", agent_url="x", meter_pubkey=crypto.pub_b64(METER["h14"])),
    }


MANDATES = {h: Mandate(house=h, min_sell_price=4.2, max_buy_price=5.5, daily_budget=50, max_promise_kwh=1,
                       approve_above=10) for h in ("h12", "h14")}


@pytest.fixture
def sim(tmp_path, monkeypatch):
    conn = db.connect(tmp_path / "t.db")
    db.init(conn)
    monkeypatch.setattr(keystore, "meter_key", lambda h: METER[h])
    monkeypatch.setattr(keystore, "market_key", lambda: MARKET)
    s = Sim(conn, houses(), MANDATES, solar.clear_sky_frame(DAY), seed=31)
    s.meters.key_fn = lambda h: METER[h]
    yield s
    conn.close()


async def run_minutes(sim: Sim, start: datetime, minutes: int) -> None:
    for m in range(1, minutes + 1):
        await sim.meters.on_minute(start + timedelta(minutes=m))


async def test_meters_sign_and_total_a_block(sim):
    q = bus.subscribe()
    try:
        await run_minutes(sim, blocks.block_start(REF), 15)
        readings = [e for e in (q.get_nowait() for _ in range(q.qsize())) if e.type == "meter.reading"]
    finally:
        bus.unsubscribe(q)
    assert len(readings) == 30
    r = readings[0].data["reading"]
    from hizashi_shared.models import MeterReading
    m = MeterReading.model_validate(r)
    assert crypto.verify(m, m.signature, sim.houses[m.house].meter_pubkey)
    t12 = sim.meters.block_totals("h12", REF.key)
    expected = solar.roof_kwh_per_block(sim.houses["h12"].roof, sim.weather)[48]
    assert t12["solar_kwh"] == pytest.approx(expected, rel=0.03)       # matches the forecast before noise
    assert t12["export_kwh"] > 0.5
    t14 = sim.meters.block_totals("h14", REF.key)
    assert t14["solar_kwh"] == 0 and t14["import_kwh"] > 0
    seqs = [e.data["reading"]["seq"] for e in readings if e.house == "h12"]
    assert seqs == list(range(1, 16))


async def test_cloud_ac_and_outage_change_the_meters(sim):
    start = blocks.block_start(REF)
    sim.events.add("cloud", "h12", start, 15)
    sim.events.add("ac", "h14", start, 15)
    m = start + timedelta(minutes=5)
    assert sim.events.cloud_factor("h12", m) == 0.3 and sim.events.cloud_factor("h14", m) == 1.0
    assert sim.load.use_kw("h14", m) == pytest.approx(sim.load._base["h14"][m.hour * 60 + m.minute] + 1.0)
    clear = sim.pv.base_kw("h12")[m.hour * 60 + m.minute]
    assert sim.pv.solar_kw("h12", m) == pytest.approx(clear * 0.3, rel=0.06)
    sim.events.add("outage", "h12", start, 15)
    await run_minutes(sim, start, 15)
    t = sim.meters.block_totals("h12", REF.key)
    assert t == {"solar_kwh": 0, "import_kwh": 0, "export_kwh": 0, "outage": True}


def order(oid, side, house, kwh, price) -> Offer:
    return Offer(offer_id=oid, negotiation_id="mkt", block=REF, side=side, house=house, to=None, kwh=kwh,
                 price=price, round=0, expires_at=blocks.block_start(REF), nonce=oid)


async def test_auction_books_and_settles(sim):
    q = bus.subscribe()
    sim.orderbook.add(order("a1", "ask", "h12", 0.5, 4.30))
    sim.orderbook.add(order("b1", "bid", "h14", 0.3, 5.36))
    [c] = sim.lifecycle.run_auction(REF, blocks.gate_close(REF) + timedelta(minutes=1))
    assert (c.seller, c.buyer, c.kwh, c.price, c.route) == ("h12", "h14", 0.3, 4.83, "auction")
    assert crypto.verify(c, c.market_sig, crypto.pub_b64(MARKET))
    with pytest.raises(Exception):
        sim.orderbook.add(order("late", "bid", "h14", 0.1, 5.0))

    await run_minutes(sim, blocks.block_start(REF), 15)
    [s] = sim.lifecycle.settle(REF, blocks.settle_time(REF))
    assert s.delivered_kwh == pytest.approx(0.3) and s.shortfall_kwh == 0
    got = [e for e in (q.get_nowait() for _ in range(q.qsize()))]
    bus.unsubscribe(q)
    cleared = [e for e in got if e.type == "market.cleared"][0].data
    assert cleared["unsold"] == [{"house": "h12", "kwh": 0.2}] and cleared["unmet"] == []
    saved = {e.house: e.data for e in got if e.type == "savings.updated"}
    assert saved["h14"]["saved_today"] == pytest.approx(0.3 * (5.80 - 4.83 - 0.14))
    assert saved["h12"]["saved_today"] == pytest.approx(0.3 * (4.83 - 3.89))
    kinds = [e["kind"] for e in ledger.entries(sim.conn)]
    assert kinds == ["settlement", "contract.booked"] and ledger.verify(sim.conn)["ok"]


async def test_shortfall_under_cloud(sim):
    c = Contract(contract_id="c1", negotiation_id="n", block=REF, seller="h12", buyer="h14", kwh=1.0,
                 price=4.68, route="haggle")
    booking.record(sim.conn, c, blocks.gate_close(REF))
    sim.events.add("cloud", "h12", blocks.block_start(REF), 15)
    await run_minutes(sim, blocks.block_start(REF), 15)
    [s] = sim.lifecycle.settle(REF, blocks.settle_time(REF))
    assert s.shortfall_kwh > 0.4 and s.seller_penalty == pytest.approx(s.shortfall_kwh * (5.80 - 4.68), rel=1e-3)


def test_clear_day_keeps_ledger(sim):
    ledger.append(sim.conn, "t", "mandate", "h12#v2", {"house": "h12"})
    sim.conn.execute("INSERT INTO contracts VALUES ('c', 'k', 'h12', 'h14', 1, 1, 'haggle', 'booked', '{}')")
    clear_day(sim.conn)
    assert sim.conn.execute("SELECT COUNT(*) n FROM contracts").fetchone()["n"] == 0
    assert ledger.verify(sim.conn) == {"ok": True, "entries": 1}
