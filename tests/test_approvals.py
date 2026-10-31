"""Wallet checks 7-8, plan approvals and the 10:00-13:00 deck card (R2.5)."""
from datetime import datetime

import pytest

from hizashi_hub import bus, db
from hizashi_hub.wallet import approvals, checks, keystore, signer
from hizashi_shared import crypto
from hizashi_shared.config import TZ
from hizashi_shared.models import BlockRef, Mandate, Offer, PlanWindow

from test_wallet_checks import KEYS, MANDATES, STREET, TOKENS, open_only

DAY = "2026-10-31"
NOW = datetime(2026, 10, 31, 10, 30, tzinfo=TZ)
H14 = MANDATES["h14"]


def window(first=40, last=51, kwh=2.4, side="buy", status="auto", house="h14") -> PlanWindow:
    return PlanWindow(plan_id=f"p{first}{side}", house=house, side=side, day=DAY, first_index=first,
                      last_index=last, kwh=kwh, expected_price=4.68, expected_value=round(kwh * 4.68, 2),
                      status=status)


def bid(index=48, kwh=0.2, price=4.60, **kw) -> Offer:
    return Offer(**{**dict(offer_id=f"b{index}", negotiation_id="n1", block=BlockRef(day=DAY, index=index),
                           side="bid", house="h14", to="h12", kwh=kwh, price=price, round=1,
                           expires_at=datetime(2026, 10, 31, 11, tzinfo=TZ), nonce="n"), **kw})


def test_deck_summary():
    assert approvals.plan_summary(window()) == "Buy 2.4 kWh from neighbours, 10:00–13:00, for about ₹11.23?"


def test_check7_daily_budget():
    r = checks.check_budget("buy", 1.0, 5.0, H14, spent_today=46.0)
    assert r.check == 7
    assert r.reason == ("Buying 1.00 kWh at ₹5.00 would take today's spending to ₹51.00. "
                        "Your daily budget is ₹50.00, so it was never sent.")
    assert checks.check_budget("buy", 0.5, 5.0, H14, spent_today=46.0).ok
    assert checks.check_budget("sell", 1.0, 5.0, H14, spent_today=99).ok


def test_check8_plan_windows():
    b = BlockRef(day=DAY, index=48)
    assert checks.check_approval("buy", 0.2, 4.6, b, H14, [window(status="pending")]).reason == \
        "Waiting for your OK on the 10:00–13:00 buy plan, so it was never sent."
    assert checks.check_approval("buy", 0.2, 4.6, b, H14, [window(status="declined")]).check == 8
    assert checks.check_approval("buy", 0.2, 4.6, b, H14, [window(status="approved")]).ok
    assert checks.check_approval("sell", 0.2, 4.6, b, H14, [window(side="buy", status="pending")]).ok


def test_check8_big_uncovered_offer_waits():
    big = H14.model_copy(update={"approve_above": 0.5, "max_promise_kwh": 5})
    r = checks.check_approval("buy", 0.2, 4.6, BlockRef(day=DAY, index=48), big, [])
    assert r.status == "pending" and r.check == 8
    r = checks.check_approval("buy", 0.2, 4.6, BlockRef(day=DAY, index=48), big, [], allow_pending=False)
    assert r.ok


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
def events():
    q = bus.subscribe()
    yield lambda: [q.get_nowait() for _ in range(q.qsize())]
    bus.unsubscribe(q)


def test_plan_flow_pending_then_approved(conn, events):
    small, big = window(28, 39, kwh=1.5), window(40, 51, kwh=2.4)
    saved = approvals.store_plans(conn, "h14", [small, big], H14, NOW)
    assert [w.status for w in saved] == ["auto", "pending"]
    assert all(crypto.verify(w, w.signature, STREET["h14"].wallet_pubkey) for w in saved)
    got = events()
    [req] = [e for e in got if e.type == "approval.requested"]
    a = req.data["approval"]
    assert a["summary"] == "Buy 2.4 kWh from neighbours, 10:00–13:00, for about ₹11.23?" and len(a["code"]) == 4

    # While pending, the wallet refuses bids in that window.
    r = signer.sign_offer_request(conn, "h14", "dev-h14", bid(), open_only, STREET, NOW)
    assert r["status"] == "refused" and "Waiting for your OK on the 10:00–13:00" in r["reason"]
    assert [e.data["text"] for e in events() if e.type == "wallet.blocked"][0].startswith("BLOCKED · Waiting")

    approvals.resolve(conn, a["approval_id"], "approve", "app", NOW)
    assert [w.status for w in approvals.plans_for(conn, "h14", DAY)] == ["auto", "approved"]
    assert signer.sign_offer_request(conn, "h14", "dev-h14", bid(), open_only, STREET, NOW)["status"] == "signed"
    resolved = [e for e in events() if e.type == "approval.resolved"]
    assert resolved[0].data["approval"]["status"] == "approved"
    with pytest.raises(approvals.ApprovalError):
        approvals.resolve(conn, a["approval_id"], "decline", "app", NOW)


def test_replanning_keeps_decisions_and_expires_dropped(conn):
    approvals.store_plans(conn, "h14", [window(40, 51)], H14, NOW)
    [a] = approvals.listing(conn, "h14")
    approvals.resolve(conn, a["approval_id"], "decline", "app", NOW)
    again = approvals.store_plans(conn, "h14", [window(40, 51), window(52, 63, kwh=2.6)], H14, NOW)
    assert [w.status for w in again] == ["declined", "pending"]
    q = bus.subscribe()
    approvals.store_plans(conn, "h14", [window(40, 51)], H14, NOW)        # 13:00 window dropped
    statuses = sorted(x["status"] for x in approvals.listing(conn, "h14"))
    assert statuses == ["declined", "expired"]
    told = [e.data["approval"]["status"] for e in (q.get_nowait() for _ in range(q.qsize())) if e.type == "approval.resolved"]
    bus.unsubscribe(q)
    assert told == ["expired"]                                            # the phone hears about it


def test_expire_at_gate_closure(conn):
    approvals.store_plans(conn, "h14", [window(40, 51)], H14, NOW)
    assert approvals.expire_through(conn, BlockRef(day=DAY, index=50), NOW) == []
    [a] = approvals.expire_through(conn, BlockRef(day=DAY, index=51), NOW)
    assert a.status == "expired"
    [w] = approvals.plans_for(conn, "h14", DAY)
    assert w.status == "expired" and checks.check_approval("buy", 0.1, 4.6, BlockRef(day=DAY, index=48), H14, [w]).check == 8


def test_budget_counts_booked_contracts(conn):
    conn.execute("INSERT INTO contracts VALUES ('c1', '2026-10-31#40', 'h12', 'h14', 9.0, 5.4, 'haggle', 'booked', '{}')")
    assert signer.spent_today(conn, "h14", DAY) == pytest.approx(48.6)
    r = signer.sign_offer_request(conn, "h14", "dev-h14", bid(kwh=0.5, price=5.0), open_only, STREET, NOW)
    assert r["status"] == "refused" and "daily budget" in r["reason"]
