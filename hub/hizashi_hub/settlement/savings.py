"""Saved vs BESCOM per house per day.

Buyer: sum q (R - p - F).  Seller: sum [d (p - B) - s (R - p)] (the penalty is 0 in an outage).
projected_year = saved_today x 300 ("if the year had 300 days like today").
"""
from hizashi_shared import config
from hizashi_shared.models import Settlement

DAYS_PER_YEAR = 300


def buyer_saving(s: Settlement, retail: float, fee: float) -> float:
    return round(s.contracted_kwh * (retail - s.price - fee), 4)


def seller_saving(s: Settlement, retail: float, buyback: float) -> float:
    return round(s.delivered_kwh * (s.price - buyback) - s.seller_penalty, 4)


def day_savings(house: str, settlements: list[Settlement], buyback: float | None = None,
                retail: float = config.RETAIL_ENERGY_CHARGE, fee: float = config.FEE_PER_KWH) -> dict:
    """Totals for one house over the settlements given (one day's)."""
    as_buyer = [s for s in settlements if s.buyer == house]
    as_seller = [s for s in settlements if s.seller == house]
    bought = sum(buyer_saving(s, retail, fee) for s in as_buyer)
    sold = sum(seller_saving(s, retail, buyback or 0.0) for s in as_seller)
    saved = round(bought + sold, 4)
    return {
        "house": house,
        "saved_today": saved,
        "projected_year": round(saved * DAYS_PER_YEAR, 2),
        "as_buyer": round(bought, 4),
        "as_seller": round(sold, 4),
        "bought_kwh": round(sum(s.contracted_kwh for s in as_buyer), 4),
        "paid": round(sum(s.buyer_pays for s in as_buyer), 4),
        "sold_kwh": round(sum(s.contracted_kwh for s in as_seller), 4),
        "delivered_kwh": round(sum(s.delivered_kwh for s in as_seller), 4),
        "shortfall_kwh": round(sum(s.shortfall_kwh for s in as_seller), 4),
        "earned": round(sum(s.seller_net for s in as_seller), 4),
        "penalties": round(sum(s.seller_penalty for s in as_seller), 4),
        "trades": len(as_buyer) + len(as_seller),
    }
