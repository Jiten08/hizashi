"""The deck haggle: H12 (min_sell 4.20, buyback 3.89) vs H14 (max_buy 5.50).
Asks 5.40, 5.16, 4.92, 4.68; bids 4.00, 4.30, 4.60; buyer accepts ₹4.68 in round 3."""
from hizashi_agent import negotiator as n

H12_LIMIT = n.seller_limit(min_sell_price=4.20, buyback=3.89)
H14_LIMIT = n.buyer_limit(max_buy_price=5.50)


def test_limits_and_openings():
    assert n.seller_open() == 5.40
    assert H12_LIMIT == 4.20
    assert n.buyer_open() == 4.00
    assert H14_LIMIT == 5.50          # min(5.50, 5.80 - 0.14)


def test_seller_limit_uses_buyback_floor():
    assert n.seller_limit(3.50, 3.89) == 3.99
    assert n.seller_limit(4.20, None) == 4.20
    assert n.buyer_limit(6.00) == 5.66


def test_concession_curves():
    assert [n.ask_price(r, H12_LIMIT) for r in range(6)] == [5.40, 5.16, 4.92, 4.68, 4.44, 4.20]
    assert [n.bid_price(r, H14_LIMIT) for r in range(6)] == [4.00, 4.30, 4.60, 4.90, 5.20, 5.50]


def test_deck_haggle():
    h = n.simulate(H12_LIMIT, H14_LIMIT)
    assert h.asks == [5.40, 5.16, 4.92, 4.68]
    assert h.bids == [4.00, 4.30, 4.60]
    assert h.deal_price == 4.68
    assert h.deal_round == 3
    assert h.accepted_by == "buyer"


def test_accept_rules():
    assert not n.buyer_accepts(4.92, 2, H14_LIMIT)    # own bid in round 2 is 4.60
    assert n.buyer_accepts(4.68, 3, H14_LIMIT)        # own bid in round 3 would be 4.90
    assert not n.seller_accepts(4.60, 3, H12_LIMIT)   # own next ask is 4.68
    assert n.seller_accepts(4.70, 3, H12_LIMIT)


def test_no_deal_when_limits_do_not_cross():
    h = n.simulate(n.seller_limit(5.00, None), n.buyer_limit(4.50))
    assert h.deal_price is None
    assert len(h.asks) == 6 and len(h.bids) == 6


def test_round_clamped_after_last():
    assert n.ask_price(99, H12_LIMIT) == 4.20
