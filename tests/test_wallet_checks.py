"""Wallet offer checks in order (section 6.3) and contract signing (R1.1, R1.6)."""
from datetime import datetime

import pytest

from hizashi_hub import bus, db
from hizashi_hub.wallet import checks, keystore, signer
from hizashi_shared import crypto
from hizashi_shared.config import TZ
from hizashi_shared.models import BlockRef, Contract, HouseInfo, Mandate, Offer, Roof

DAY = "2026-10-31"
BLOCK = BlockRef(day=DAY, index=48)                 # 12:00-12:15, gate closes 11:00
GATE = datetime(2026, 10, 31, 11, 0, tzinfo=TZ)
NOW = datetime(2026, 10, 31, 10, 30, tzinfo=TZ)
TOKENS = {"h12": "dev-h12", "h14": "dev-h14", "h16": "dev-h16", "h18": "dev-h18"}

KEYS = {h: crypto.new_key() for h in TOKENS}


def house(id_: str, transformer: str = "T1", solar: bool = True) -> HouseInfo:
    return HouseInfo(id=id_, label=f"House {id_[1:]}", transformer=transformer,
                     roof=Roof(kwp=5, tilt=13, azimuth=180, inverter_kw=5) if solar else None,
                     profile="p", buyback_rate=3.89 if solar else None, metering="net",
                     agent_url=f"http://127.0.0.1:90{id_[1:]}/", wallet_pubkey=crypto.pub_b64(KEYS[id_]))


STREET = {"h12": house("h12"), "h14": house("h14", solar=False), "h16": house("h16"), "h18": house("h18", "T2")}
MANDATES = {
    "h12": Mandate(house="h12", min_sell_price=4.20, max_buy_price=5.50, daily_budget=50, max_promise_kwh=1.0, approve_above=10),
    "h14": Mandate(house="h14", min_sell_price=4.20, max_buy_price=5.50, daily_budget=50, max_promise_kwh=1.0, approve_above=10),
}


def open_only(key: str) -> str | None:
    return "OPEN" if key == BLOCK.key else "PLANNED"


def offer(**kw) -> Offer:
    base = dict(offer_id="o1", negotiation_id="n1", block=BLOCK, side="ask", house="h12", to="h14",
                kwh=0.40, price=4.68, round=3, expires_at=GATE, nonce="x1")
    base.update(kw)
    return Offer(**base)


def run(o: Offer, house_="h12", token="dev-h12", mandate=None, state=open_only, now=NOW, dup=False):
    return checks.check_offer(mandate or MANDATES[house_], o, state, STREET, now,
                              house=house_, token=token, already_signed=dup, tokens=TOKENS)


# --- checks 1-6 (pure) --------------------------------------------------------------

def test_valid_offer_passes():
    assert run(offer()).ok


def test_check1_wrong_token():
    r = run(offer(), token="dev-h14")
    assert (r.status, r.check) == ("refused", 1)
    assert r.reason == "This agent isn't allowed to sign for House 12."


def test_check1_offer_from_other_house():
    r = run(offer(house="h14", to="h12"))
    assert r.check == 1
    assert r.reason == "The offer says it's from House 14, but this is House 12's wallet."


def test_check2_paused():
    r = run(offer(), mandate=MANDATES["h12"].model_copy(update={"paused": True}))
    assert r.check == 2 and r.reason == "Trading is paused in your rules, so it was never sent."


def test_check3_block_not_open():
    r = run(offer(), state=lambda k: "GATE_CLOSED")
    assert r.check == 3
    assert r.reason == "The 12:00–12:15 block isn't open for deals (it's gate closed), so it was never sent."


def test_check3_after_gate_even_if_state_lags():
    assert run(offer(), now=GATE).check == 3


def test_check3_expires_after_gate():
    r = run(offer(expires_at=datetime(2026, 10, 31, 11, 5, tzinfo=TZ)))
    assert r.check == 3 and r.reason == "The offer runs past gate closure at 11:00, so it was never sent."


def test_check4_ask_below_min():
    r = run(offer(price=4.00))
    assert r.check == 4 and r.reason == "Tried to sell at ₹4.00/unit. Your min is ₹4.20, so it was never sent."


def test_check4_bid_above_max():
    r = run(offer(side="bid", house="h14", to="h12", price=5.60), house_="h14", token="dev-h14")
    assert r.check == 4 and r.reason == "Tried to buy at ₹5.60/unit. Your max is ₹5.50, so it was never sent."


def test_check5_too_much_kwh():
    r = run(offer(kwh=1.5))
    assert r.check == 5
    assert r.reason == "Tried to promise 1.50 kWh in one block. Your max is 1.00 kWh, so it was never sent."
    assert run(offer(kwh=0)).check == 5


def test_check6_other_transformer():
    r = run(offer(to="h18"))
    assert r.check == 6 and r.reason == "House 18 isn't on your transformer (T1), so it was never sent."


def test_check6_street_mode_and_market_orders_allowed():
    street_mode = MANDATES["h12"].model_copy(update={"counterparties": "street"})
    assert run(offer(to="h18"), mandate=street_mode).ok
    assert run(offer(to=None)).ok
    assert run(offer(to="h12")).check == 6


def test_order_first_failure_wins():
    r = run(offer(price=40.0, kwh=5.0), state=lambda k: "SETTLED")
    assert r.check == 3


def test_duplicate_refused():
    r = run(offer(), dup=True)
    assert r.status == "refused" and r.reason == "This offer was already signed."


# --- the wallet flow (DB, keys, bus) --------------------------------------------------

@pytest.fixture
def conn(tmp_path, monkeypatch):
    c = db.connect(tmp_path / "t.db")
    db.init(c)
    db.seed_street(c, {"houses": [h.model_dump(mode="json") for h in STREET.values()],
                       "mandates": [m.model_dump(mode="json") for m in MANDATES.values()]})
    monkeypatch.setattr(keystore, "wallet_key", lambda h: KEYS[h])
    yield c
    c.close()


@pytest.fixture
def events():
    q = bus.subscribe()
    yield lambda: [q.get_nowait() for _ in range(q.qsize())]
    bus.unsubscribe(q)


def sign_offer(conn, o, house_="h12", token="dev-h12"):
    return signer.sign_offer_request(conn, house_, token, o, open_only, STREET, NOW)


def test_valid_offer_signed_and_verifies(conn, events):
    r = sign_offer(conn, offer())
    assert r["status"] == "signed"
    signed = Offer.model_validate(r["offer"])
    assert crypto.verify(signed, signed.signature, STREET["h12"].wallet_pubkey)
    row = conn.execute("SELECT status FROM offers WHERE offer_id = 'o1'").fetchone()
    assert row["status"] == "signed"
    got = [(e.type, e.house) for e in events()]
    assert got == [("nego.offer", "h12"), ("nego.offer", "h14")]


def test_duplicate_offer_id_refused(conn, events):
    assert sign_offer(conn, offer())["status"] == "signed"
    r = sign_offer(conn, offer())
    assert r == {"status": "refused", "reason": "This offer was already signed."}
    assert conn.execute("SELECT status FROM offers WHERE offer_id = 'o1'").fetchone()["status"] == "signed"


def test_forty_rupee_bid_from_h14_refused(conn, events):
    bad = offer(offer_id="bad", side="bid", house="h14", to="h12", kwh=0.5, price=40)
    r = sign_offer(conn, bad, "h14", "dev-h14")
    assert r == {"status": "refused",
                 "reason": "Tried to buy at ₹40.00/unit. Your max is ₹5.50, so it was never sent."}
    row = conn.execute("SELECT status, reason FROM offers WHERE offer_id = 'bad'").fetchone()
    assert row["status"] == "refused" and row["reason"] == r["reason"]
    [e] = events()
    assert (e.type, e.house, e.data["reason"]) == ("wallet.blocked", "h14", r["reason"])
    assert e.data["offer"]["price"] == 40


def test_wrong_token_not_recorded(conn, events):
    r = sign_offer(conn, offer(), token="nope")
    assert r["status"] == "refused"
    assert events() == []
    assert conn.execute("SELECT COUNT(*) n FROM offers").fetchone()["n"] == 0


# --- contract signing ----------------------------------------------------------------

def contract(**kw) -> Contract:
    base = dict(contract_id="c1", negotiation_id="n1", block=BLOCK, seller="h12", buyer="h14",
                kwh=0.20, price=4.68, route="haggle")
    base.update(kw)
    return Contract(**base)


@pytest.fixture
def h12_ask(conn):
    """H12's signed 0.40 kWh ask at ₹4.68, stored by the wallet."""
    r = sign_offer(conn, offer(kwh=0.40, price=4.68))
    assert r["status"] == "signed"
    return Offer.model_validate(r["offer"])


def sign_c(conn, c, house_="h14", token="dev-h14"):
    return signer.sign_contract_request(conn, house_, token, c, open_only, STREET, NOW)


def test_h14_signs_contract_matching_h12_ask(conn, h12_ask):
    r = sign_c(conn, contract())
    assert r["status"] == "signed"
    c = Contract.model_validate(r["contract"])
    assert c.seller_sig is None
    assert crypto.verify(c, c.buyer_sig, STREET["h14"].wallet_pubkey)


def test_contract_price_mismatch_refused(conn, h12_ask):
    r = sign_c(conn, contract(price=4.70))
    assert r["status"] == "refused"
    assert r["reason"] == "No signed offer in this negotiation matches 0.20 kWh at ₹4.70, so it was never signed."


def test_contract_more_kwh_than_offered_refused(conn, h12_ask):
    assert sign_c(conn, contract(kwh=0.50))["status"] == "refused"


def test_forged_counterparty_signature_refused(conn):
    forged = offer(offer_id="f1")
    forged = forged.model_copy(update={"signature": crypto.sign(forged, crypto.new_key())})
    signer.store_offer(conn, forged, "signed", None, NOW)     # even if it got into the table
    assert sign_c(conn, contract())["status"] == "refused"


def test_contract_wrong_party_or_side_refused(conn, h12_ask):
    assert sign_c(conn, contract(), "h16", "dev-h16")["status"] == "refused"           # not a party
    assert sign_c(conn, contract(seller="h14", buyer="h12"))["status"] == "refused"    # parties swapped


def test_contract_passes_own_limits(conn, h12_ask):
    tight = MANDATES["h14"].model_copy(update={"max_buy_price": 4.50})
    r = checks.check_contract(tight, contract(), open_only, STREET, NOW, house="h14", token="dev-h14",
                              signed_offers=[h12_ask], tokens=TOKENS)
    assert r.check == 4 and r.reason == "Tried to buy at ₹4.68/unit. Your max is ₹4.50, so it was never sent."
    r = checks.check_contract(MANDATES["h14"], contract(), lambda k: "GATE_CLOSED", STREET, NOW,
                              house="h14", token="dev-h14", signed_offers=[h12_ask], tokens=TOKENS)
    assert r.check == 3


def test_both_wallets_sign(conn, h12_ask):
    c = Contract.model_validate(sign_c(conn, contract())["contract"])
    r = sign_c(conn, c, "h12", "dev-h12")
    assert r["status"] == "signed"
    both = Contract.model_validate(r["contract"])
    assert crypto.verify(both, both.seller_sig, STREET["h12"].wallet_pubkey)
    assert crypto.verify(both, both.buyer_sig, STREET["h14"].wallet_pubkey)


def test_contract_survives_a2a_float_roundtrip(conn, h12_ask):
    d = sign_c(conn, contract())["contract"]
    d["block"]["index"] = float(d["block"]["index"])           # what A2A data parts do
    c = Contract.model_validate(d)
    assert crypto.verify(c, c.buyer_sig, STREET["h14"].wallet_pubkey)
