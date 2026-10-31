"""Settlement (KERC 8(g)) and savings. Deck block: 0.20 kWh at ₹4.68 ->
buyer saves ₹0.196, seller gains ₹0.158. Enable when R2.3 lands."""
import pytest

R, F, B = 5.80, 0.14, 3.89


def test_deck_block_savings():
    from hizashi_hub.settlement import savings, settle
    from hizashi_shared.models import BlockRef, Contract
    c = Contract(contract_id="c1", negotiation_id="n1", block=BlockRef(day="2026-10-31", index=48),
                 seller="h12", buyer="h14", kwh=0.20, price=4.68, route="haggle")
    [s] = settle.settle_block([c], {"h12": 0.20}, outage=False, retail=R, fee=F)
    assert s.buyer_pays == pytest.approx((4.68 + F) * 0.20)
    assert s.shortfall_kwh == 0
    assert savings.buyer_saving(s, R, F) == pytest.approx(0.196)
    assert savings.seller_saving(s, R, B) == pytest.approx(0.158)


def contract(cid, seller, buyer, kwh, price=4.68):
    from hizashi_shared.models import BlockRef, Contract
    return Contract(contract_id=cid, negotiation_id="n", block=BlockRef(day="2026-10-31", index=48),
                    seller=seller, buyer=buyer, kwh=kwh, price=price, route="haggle")


def test_shortfall_penalty_and_outage():
    """s = q - d; penalty s*(R - p); 0 when the block had an outage."""
    from hizashi_hub.settlement import savings, settle
    [s] = settle.settle_block([contract("c1", "h12", "h14", 0.40)], {"h12": 0.30}, outage=False, retail=R, fee=F)
    assert (s.delivered_kwh, s.shortfall_kwh) == (pytest.approx(0.30), pytest.approx(0.10))
    assert s.seller_penalty == pytest.approx(0.10 * (R - 4.68))
    assert s.seller_net == pytest.approx(4.68 * 0.30 - 0.112)
    assert s.buyer_pays == pytest.approx((4.68 + F) * 0.40)       # pledged quantity, 8(g)(iv)
    assert savings.seller_saving(s, R, B) == pytest.approx(0.30 * (4.68 - B) - 0.112)
    [o] = settle.settle_block([contract("c1", "h12", "h14", 0.40)], {"h12": 0.30}, outage=True, retail=R, fee=F)
    assert o.seller_penalty == 0 and o.outage


def test_export_shared_by_size():
    from hizashi_hub.settlement import settle
    a, b = settle.settle_block([contract("a", "h12", "h14", 0.30), contract("b", "h12", "h18", 0.10)],
                               {"h12": 0.20}, outage=False, retail=R, fee=F)
    assert a.delivered_kwh == pytest.approx(0.15) and b.delivered_kwh == pytest.approx(0.05)


def test_day_savings_totals():
    from hizashi_hub.settlement import savings, settle
    ss = settle.settle_block([contract("c1", "h12", "h14", 0.20)], {"h12": 0.50}, outage=False, retail=R, fee=F)
    buyer = savings.day_savings("h14", ss, None, R, F)
    seller = savings.day_savings("h12", ss, B, R, F)
    assert buyer["saved_today"] == pytest.approx(0.196) and buyer["projected_year"] == pytest.approx(58.8)
    assert seller["saved_today"] == pytest.approx(0.158) and seller["delivered_kwh"] == pytest.approx(0.20)
    assert savings.day_savings("h16", ss, 2.14)["saved_today"] == 0
