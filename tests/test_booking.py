"""Contract booking (R1.6): signatures, block OPEN, seller != buyer, open_access, market_sig."""
from datetime import datetime

import pytest

from hizashi_hub import bus, db
from hizashi_hub.market import booking
from hizashi_shared import crypto
from hizashi_shared.config import TZ
from hizashi_shared.models import BlockRef, Contract, HouseInfo

BLOCK = BlockRef(day="2026-10-31", index=48)
NOW = datetime(2026, 10, 31, 10, 30, tzinfo=TZ)
KEYS = {h: crypto.new_key() for h in ("h12", "h14", "h18")}
MARKET = crypto.new_key()
STREET = {
    h: HouseInfo(id=h, label=f"House {h[1:]}", transformer="T2" if h == "h18" else "T1", roof=None,
                 profile="p", buyback_rate=None, metering="none", agent_url="http://x/",
                 wallet_pubkey=crypto.pub_b64(k))
    for h, k in KEYS.items()
}


def open_only(key: str) -> str | None:
    return "OPEN" if key == BLOCK.key else "PLANNED"


def signed(seller="h12", buyer="h14", seller_key=None, **kw) -> Contract:
    c = Contract(contract_id=kw.pop("contract_id", "c1"), negotiation_id="n1", block=BLOCK,
                 seller=seller, buyer=buyer, kwh=0.20, price=4.68, route="haggle", **kw)
    return c.model_copy(update={"seller_sig": crypto.sign(c, seller_key or KEYS[seller]),
                                "buyer_sig": crypto.sign(c, KEYS[buyer])})


@pytest.fixture
def conn(tmp_path):
    c = db.connect(tmp_path / "t.db")
    db.init(c)
    yield c
    c.close()


def book(conn, c, state=open_only):
    return booking.book(conn, c, STREET, state, NOW, market_key=MARKET)


def test_both_signatures_valid_booked_with_market_sig(conn):
    q = bus.subscribe()
    try:
        b = book(conn, signed())
        assert crypto.verify(b, b.market_sig, crypto.pub_b64(MARKET))
        assert crypto.verify(b, b.seller_sig, STREET["h12"].wallet_pubkey)
        row = conn.execute("SELECT status FROM contracts WHERE contract_id = 'c1'").fetchone()
        assert row["status"] == "booked"
        got = [q.get_nowait() for _ in range(q.qsize())]
        assert [(e.type, e.house) for e in got] == [("contract.booked", "h12"), ("contract.booked", "h14")]
    finally:
        bus.unsubscribe(q)


def test_one_bad_signature_refused(conn):
    with pytest.raises(booking.BookingError, match="seller's signature"):
        book(conn, signed(seller_key=crypto.new_key()))
    assert conn.execute("SELECT COUNT(*) n FROM contracts").fetchone()["n"] == 0


def test_tampered_terms_refused(conn):
    with pytest.raises(booking.BookingError):
        book(conn, signed().model_copy(update={"price": 3.00}))


def test_seller_equals_buyer_refused(conn):
    with pytest.raises(booking.BookingError, match="same house"):
        book(conn, signed(seller="h12", buyer="h12"))


def test_block_not_open_refused(conn):
    with pytest.raises(booking.BookingError, match="isn't open any more"):
        book(conn, signed(), state=lambda k: "GATE_CLOSED")


def test_different_transformers_open_access_true(conn):
    b = book(conn, signed(buyer="h18", open_access=True))
    assert b.open_access is True
    with pytest.raises(booking.BookingError, match="open_access must be True"):
        book(conn, signed(buyer="h18", contract_id="c2"))


def test_double_booking_refused(conn):
    book(conn, signed())
    with pytest.raises(booking.BookingError, match="already booked"):
        book(conn, signed())
