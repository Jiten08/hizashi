"""The one attack (an impostor House 16 selling at ₹40 is blacklisted at the market's door) and
"ask the owner" (a plan over the no-ask limit holds the house's buys until the owner decides)."""
from datetime import datetime

import pytest

from hizashi_hub import attacks, bus, clock, db
from hizashi_hub.guard import watch
from hizashi_hub.wallet import approvals, checks, keystore, signer
from hizashi_shared import crypto
from hizashi_shared.config import TZ
from hizashi_shared.models import BlockRef

from test_approvals import bid
from test_wallet_checks import KEYS, MANDATES, STREET, TOKENS

DAY = "2026-10-31"
NOW = datetime(2026, 10, 31, 10, 30, tzinfo=TZ)


@pytest.fixture
def conn(tmp_path, monkeypatch):
    c = db.connect(tmp_path / "t.db")
    db.init(c)
    db.seed_street(c, {"houses": [h.model_dump(mode="json") for h in STREET.values()],
                       "mandates": [m.model_dump(mode="json") for m in MANDATES.values()]})
    monkeypatch.setattr(keystore, "wallet_key", lambda h: KEYS[h])
    monkeypatch.setattr(checks.config, "AGENT_TOKENS", TOKENS)
    yield c
    c.close()


@pytest.fixture
def flags():
    g = watch.init(STREET)
    q = bus.subscribe()
    yield lambda: [e for e in (q.get_nowait() for _ in range(q.qsize())) if e.type == "guard.flag"]
    bus.unsubscribe(q)
    watch._guard = None


def test_outsider_is_blacklisted_on_entry_and_bounces_after(conn, flags):
    guard = watch.get()
    key = crypto.new_key()
    ask = attacks.outsider_ask(BlockRef(day=DAY, index=48), key)
    assert ask["house"] == "h20" and ask["price"] == 40.0 and ask["to"] is None

    reason = guard.screen_seller(conn, ask, attacks.pubkey(key), NOW)
    assert reason == ("A seller calling itself House 20 tried to sell 0.50 kWh at ₹40.00, but House 20 isn't on "
                      "this street's registry (no wallet key on file). Blacklisted on entry; nothing traded.")
    [f] = flags()
    assert f.data["kind"] == "impostor" and f.data["title"] == "Outsider blacklisted" and f.data["houses"] == []
    assert f.data["detail"]["claimed"] == "h20" and attacks.pubkey(key) in guard.blacklist

    again = guard.screen_seller(conn, attacks.outsider_ask(BlockRef(day=DAY, index=49), key), attacks.pubkey(key), NOW)
    assert again == "Blacklisted: House 20 was already turned away." and flags() == []


def test_registered_name_with_the_wrong_signature_is_caught_too(conn, flags):
    guard = watch.get()
    real = signer.sign_offer("h16", offer_as("h16"), KEYS["h16"])
    assert guard.screen_seller(conn, real.model_dump(mode="json"), crypto.pub_b64(KEYS["h16"]), NOW) is None
    forged = signer.sign_offer("h16", offer_as("h16"), crypto.new_key())
    assert "isn't House 16's wallet" in guard.screen_seller(conn, forged.model_dump(mode="json"), "k2", NOW)


def offer_as(house):
    from hizashi_shared.models import Offer
    return Offer(offer_id="o1", negotiation_id="market-x", block=BlockRef(day=DAY, index=48), side="ask", house=house,
                 to=None, kwh=0.5, price=5.0, round=0, expires_at=NOW, nonce="n1")


def test_ask_owner_holds_buys_until_the_owner_decides(conn, monkeypatch):
    from hizashi_hub.api import console
    monkeypatch.setattr(clock, "_clock", type("C", (), {"block_states": {f"{DAY}#48": "OPEN"}, "day": DAY})(),
                        raising=False)
    monkeypatch.setattr(clock, "get", lambda: clock._clock)
    q = bus.subscribe()
    try:
        out = console.ask_owner(conn, "h14", NOW)
        w = out["plan"]
        assert (w["first_index"], w["last_index"], w["status"]) == (48, 51, "pending")
        assert w["expected_value"] > MANDATES["h14"].approve_above
        requested = [e for e in (q.get_nowait() for _ in range(q.qsize())) if e.type == "approval.requested"]
        assert requested and requested[0].house == "h14"
    finally:
        bus.unsubscribe(q)

    open48 = lambda key: "OPEN" if key == f"{DAY}#48" else "PLANNED"  # noqa: E731
    r = signer.sign_offer_request(conn, "h14", "dev-h14", bid(), open48, STREET, NOW)
    assert r["status"] == "refused" and "Waiting for your OK" in r["reason"]

    approvals.resolve(conn, requested[0].data["approval"]["approval_id"], "approve", "app", NOW)
    assert signer.sign_offer_request(conn, "h14", "dev-h14", bid(offer_id="b48b"), open48, STREET, NOW)["status"] == "signed"


async def test_test_approval_reaches_the_push_sender(conn, monkeypatch):
    import asyncio
    from types import SimpleNamespace

    from hizashi_hub.api import push
    from hizashi_hub.notify import webpush

    monkeypatch.setattr(clock, "_clock", type("C", (), {"block_states": {}, "day": DAY, "now": NOW})(), raising=False)
    monkeypatch.setattr(clock, "get", lambda: clock._clock)
    sent: list[tuple[str, dict, bool]] = []

    async def fake_send(c, house, payload, urgent=False):
        sent.append((house, payload, urgent))
        return 1
    monkeypatch.setattr(webpush, "send", fake_send)
    runner = asyncio.create_task(webpush.run(conn))
    await asyncio.sleep(0)
    try:
        req = SimpleNamespace(app=SimpleNamespace(state=SimpleNamespace(db=conn)))
        out = await push.test_approval(req, "h14", push.TestApprovalBody(delay=0))
        assert out["status"] == "scheduled" and out["subscribed"] == 0
        for _ in range(20):
            await asyncio.sleep(0.01)
            if sent:
                break
    finally:
        runner.cancel()
    house, payload, urgent = sent[0]
    assert house == "h14" and urgent and payload["title"] == "Needs your OK" and payload["approval_id"]
    assert payload["body"].startswith("Buy ") and "neighbours" in payload["body"]
