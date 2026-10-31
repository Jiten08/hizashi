"""Saved vs BESCOM per house per day.

Buyer: sum q (R - p - F).  Seller: sum [d (p - B) - s (R - p)].
projected_year = saved_today x 300 ("if the year had 300 days like today").
"""
from hizashi_shared.models import Settlement


def buyer_saving(s: Settlement, retail: float, fee: float) -> float:
    raise NotImplementedError("TODO(R2.3, Jiten)")


def seller_saving(s: Settlement, retail: float, buyback: float) -> float:
    raise NotImplementedError("TODO(R2.3, Jiten)")


def day_savings(house: str, settlements: list[Settlement]) -> dict:
    raise NotImplementedError("TODO(R2.3, Jiten)")
