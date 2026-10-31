"""Settlement (KERC 8(g)) and savings. Deck block: 0.20 kWh at ₹4.68 ->
buyer saves ₹0.196, seller gains ₹0.158. Enable when R2.3 lands."""
import pytest

pytestmark = pytest.mark.skip(reason="TODO(R2.3): settlement/settle + savings")

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


def test_shortfall_penalty_and_outage():
    """s = q - d; penalty s*(R - p); 0 when the block had an outage."""
