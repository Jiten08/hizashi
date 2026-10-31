"""Gate-closure auction (KERC 4(b), average price). Enable when R2.1 lands."""
from datetime import datetime

from hizashi_shared.config import TZ
from hizashi_shared.models import BlockRef, Offer

def order(oid: str, side: str, house: str, kwh: float, price: float) -> Offer:
    return Offer(offer_id=oid, negotiation_id="mkt", block=BlockRef(day="2026-10-31", index=48),
                 side=side, house=house, to=None, kwh=kwh, price=price, round=0,
                 expires_at=datetime(2026, 10, 31, 11, tzinfo=TZ), nonce=oid)


def test_average_price_match():
    from hizashi_hub.market.auction import clear
    matches = clear([order("a1", "ask", "h12", 0.5, 4.20)], [order("b1", "bid", "h14", 0.3, 5.50)])
    assert [(a.offer_id, b.offer_id, q, p) for a, b, q, p in matches] == [("a1", "b1", 0.3, 4.85)]


def test_no_cross_no_match():
    from hizashi_hub.market.auction import clear
    assert clear([order("a1", "ask", "h12", 0.5, 5.00)], [order("b1", "bid", "h14", 0.5, 4.50)]) == []


def test_partial_fills_and_leftovers():
    from hizashi_hub.market.auction import clear_with_leftovers
    asks = [order("a1", "ask", "h12", 0.5, 4.20), order("a2", "ask", "h16", 0.2, 4.00)]
    bids = [order("b1", "bid", "h14", 0.6, 5.50), order("b2", "bid", "h18", 0.3, 4.10)]
    matches, left_a, left_b = clear_with_leftovers(asks, bids)
    assert [(a.offer_id, b.offer_id, q, p) for a, b, q, p in matches] == [
        ("a2", "b1", 0.2, 4.75), ("a1", "b1", 0.4, 4.85)]
    assert [(o.offer_id, round(o.kwh, 3)) for o in left_a] == [("a1", 0.1)]
    assert [o.offer_id for o in left_b] == ["b2"]
    assert asks[0].kwh == 0.5          # inputs untouched
