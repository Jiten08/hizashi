"""Sign offers, plans and contracts with the house's wallet key (after checks pass)."""
from hizashi_shared.models import Contract, Offer, PlanWindow


def sign_offer(house: str, offer: Offer) -> Offer:
    raise NotImplementedError("TODO(R1.1, Jiten)")


def sign_plan(house: str, window: PlanWindow) -> PlanWindow:
    raise NotImplementedError("TODO(R2.5, Jiten)")


def sign_contract(house: str, contract: Contract) -> Contract:
    """Adds seller_sig or buyer_sig depending on which side `house` is."""
    raise NotImplementedError("TODO(R1.6, Jiten)")
