"""Guard rules (N2): wash trades, impossible readings, replays, price coordination, reports."""
from datetime import datetime

import pytest
from fastapi.testclient import TestClient

from hizashi_hub import bus, db
from hizashi_hub.guard import rules, watch
from hizashi_hub.market import booking
from hizashi_hub.wallet import signer
from hizashi_shared import events as ev
from hizashi_shared.config import TZ
from hizashi_shared.models import BlockRef, Contract, MeterReading, Offer

from test_wallet_checks import KEYS, STREET, offer

DAY = "2026-10-31"
NOW = datetime(2026, 10, 31, 10, 30, tzinfo=TZ)


def contract(seller="h12", buyer="h16", index=48, cid="c1") -> Contract:
    return Contract(contract_id=cid, negotiation_id="n", block=BlockRef(day=DAY, index=index),
                    seller=seller, buyer=buyer, kwh=0.4, price=4.68, route="haggle")


def reading(house="h12", h=12, seq=5, solar=50.0, export=20.0) -> MeterReading:
    return MeterReading(house=house, ts=datetime(2026, 10, 31, h, 1, tzinfo=TZ), seq=seq,
                        solar_wh=solar, import_wh=0, export_wh=export)


@pytest.fixture
def conn(tmp_path):
    c = db.connect(tmp_path / "t.db")
    db.init(c)
    yield c
    c.close()


@pytest.fixture
def guard():
    g = watch.init(STREET)
    q = bus.subscribe()
    g.flags = q          # the test reads guard.flag events from here
    yield g
    bus.unsubscribe(q)
    watch._guard = None


def flags(g) -> list[dict]:
    out = []
    while not g.flags.empty():
        e = g.flags.get_nowait()
        if e.type == ev.GUARD_FLAG:
            out.append(e.data)
    return out


# --- pure rules ---------------------------------------------------------------------------------

def test_wash_trades():
    assert rules.check_contract(contract("h12", "h12"), []) == ["House 12 tried to trade with itself."]
    assert rules.check_contract(contract("h16", "h12"), [contract("h12", "h16")]) == [
        "House 16 and House 12 tried to sell to each other in the 12:00–12:15 block. "
        "That's a wash trade, so it wasn't booked."]
    assert rules.check_contract(contract("h18", "h12"), [contract("h16", "h12")]) == []


def test_impossible_readings():
    h12 = STREET["h12"]                               # 5 kW inverter -> at most 87.5 Wh a minute
    assert rules.check_reading(reading(), h12, 4) == []
    assert rules.check_reading(reading(h=21), h12, 4) == ["House 12's meter reported 50 Wh of solar but it's dark."]
    assert rules.check_reading(reading(house="h14"), STREET["h14"], None) == [
        "House 14's meter reported 50 Wh of solar but has no solar panels."]
    assert rules.check_reading(reading(solar=95, export=90), h12, 4) == [
        "House 12's meter exported 90 Wh in a minute; its 5 kW inverter can't do more than 88 Wh."]
    assert rules.check_reading(reading(seq=4), h12, 4) == [
        "House 12's meter sent reading #4 again (last was #4). A replayed reading isn't counted."]


def test_held_price_ignores_the_opening_ask_and_conceding():
    assert rules.OPENING_ASK == 5.40
    assert rules.held_price([5.40]) is None                     # every honest seller opens here
    assert rules.held_price([5.40, 5.16, 4.92]) is None         # conceding
    assert rules.held_price([5.60, 5.60, 5.60]) == 5.60


def test_collusion_needs_two_sellers_holding_one_price_in_four_blocks():
    asks = {f"{DAY}#{i}": {"h16": [5.6, 5.6], "h18": [5.6]} for i in (40, 41, 42)}
    assert rules.collusion(asks, "h16") is None
    asks[f"{DAY}#44"] = {"h16": [5.6], "h18": [5.6, 5.6]}
    assert rules.collusion(asks, "h16") == ("h18", 5.6, [f"{DAY}#40", f"{DAY}#41", f"{DAY}#42", f"{DAY}#44"])
    honest = {f"{DAY}#{i}": {"h16": [5.40, 5.16], "h18": [5.40, 5.16]} for i in range(40, 50)}
    assert rules.collusion(honest, "h16") is None


# --- the guard at work ----------------------------------------------------------------------------

def ask(house, index, price=5.6, n=0) -> Offer:
    return Offer(offer_id=f"{house}-{index}-{n}", negotiation_id="n", block=BlockRef(day=DAY, index=index),
                 side="ask", house=house, to="h12", kwh=0.3, price=price, round=n,
                 expires_at=NOW, nonce=f"{house}-{index}-{n}")


def test_guard_catches_collusion_then_refuses_that_price(conn, guard):
    for i in (40, 41, 42, 43):
        guard.check_ask(conn, ask("h16", i), NOW)
        guard.signed(ask("h16", i))
        if i < 43:
            guard.check_ask(conn, ask("h18", i), NOW)
            guard.signed(ask("h18", i))
    with pytest.raises(watch.GuardRefusal, match="held their ask at ₹5.60 in 4 blocks"):
        guard.check_ask(conn, ask("h18", 43), NOW)
    with pytest.raises(watch.GuardRefusal, match="caught fixing the price"):
        guard.check_ask(conn, ask("h16", 45), NOW)
    guard.check_ask(conn, ask("h16", 45, price=5.16), NOW)        # a real price is still fine
    [f] = flags(guard)
    assert f["kind"] == "collusion" and f["houses"] == ["h16", "h18"] and f["title"] == "Price-fixing caught"
    assert conn.execute("SELECT kind FROM ledger").fetchone()["kind"] == "guard.flag"
    assert conn.execute("SELECT COUNT(*) FROM flags").fetchone()[0] == 1


def test_guard_refuses_a_replayed_nonce(conn, guard):
    guard.signed(ask("h16", 40))
    replay = ask("h16", 40).model_copy(update={"offer_id": "other"})
    with pytest.raises(watch.GuardRefusal, match="reuses a nonce"):
        guard.check_ask(conn, replay, NOW)
    assert flags(guard)[0]["kind"] == "replay"


def test_wallet_turns_a_guard_refusal_into_a_blocked_card(conn, guard):
    guard.colluders[frozenset(("h12", "h18"))] = 4.68
    r = signer.sign_offer_request(conn, "h12", "dev-h12", offer(), lambda k: "OPEN", STREET, NOW)
    assert r["status"] == "refused" and "fixing the price at ₹4.68" in r["reason"]
    events = []
    while not guard.flags.empty():
        events.append(guard.flags.get_nowait())
    [b] = [e for e in events if e.type == ev.WALLET_BLOCKED]
    assert b.house == "h12" and b.data["check"] == signer.GUARD_CHECK and b.data["owner_rule"]


def test_booking_refuses_a_wash_trade(conn, guard):
    first = contract("h12", "h16", cid="c1")
    booking.record(conn, first, NOW, KEYS["h12"])
    with pytest.raises(watch.GuardRefusal, match="wash trade"):
        guard.check_contract(conn, contract("h16", "h12", cid="c2"), NOW)
    assert flags(guard)[-1]["kind"] == "wash_trade"


def test_meter_flags_once_per_block(conn, guard):
    guard.check_reading(conn, reading(h=21, seq=1), NOW)
    guard.check_reading(conn, reading(h=21, seq=2), NOW)
    assert [f["kind"] for f in flags(guard)] == ["impossible_reading"]


def test_agent_report_becomes_a_flag(tmp_path, guard, monkeypatch):
    from hizashi_hub import clock
    from hizashi_hub.api import guard as guard_api
    from fastapi import FastAPI

    c = db.connect(tmp_path / "r.db")
    db.init(c)
    app = FastAPI()
    app.include_router(guard_api.router, prefix="/api")
    app.state.db = c
    clock.init(DAY, 60)
    client = TestClient(app)
    body = {"kind": "bad_signature", "detail": {"house": "h16", "offer_id": "x"}}
    assert client.post("/api/guard/report", json=body).status_code == 401
    r = client.post("/api/guard/report", json=body, headers={"Authorization": "Bearer dev-h14"})
    assert r.json() == {"status": "flagged"}
    again = client.post("/api/guard/report", json=body, headers={"Authorization": "Bearer dev-h14"})
    assert again.json() == {"status": "already flagged"}
    [f] = flags(guard)
    assert f["houses"] == ["h14", "h16"] and "never signed it" in f["text"]
    c.close()
