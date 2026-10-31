"""The ordered offer checks (section 6.3); the first failure refuses.

1 token/house  2 not paused  3 block OPEN, expires_at <= gate closure  4 price limit
5 kwh <= max_promise_kwh  6 counterparty allowed  7 daily budget (bids)  8 approval
"""
from dataclasses import dataclass

from hizashi_shared.models import Contract, Mandate, Offer


@dataclass
class CheckResult:
    status: str                     # "ok" | "pending" | "refused"
    reason: str | None = None
    approval_id: str | None = None


def check_offer(house: str, token: str | None, offer: Offer, mandate: Mandate) -> CheckResult:
    raise NotImplementedError("TODO(R1.1, Jiten)")


def check_contract(house: str, token: str | None, contract: Contract, mandate: Mandate) -> CheckResult:
    raise NotImplementedError("TODO(R1.6, Jiten)")


def blocked_text(offer: Offer, mandate: Mandate) -> str:
    """'BLOCKED · Tried to buy at ₹40/unit. Your max is ₹5.50, so it was never sent.'"""
    raise NotImplementedError("TODO(R2.9, Jiten)")
