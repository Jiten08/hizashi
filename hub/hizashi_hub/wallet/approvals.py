"""Plan + offer approvals: create (4-digit code), resolve, publish approval.requested/resolved."""
from hizashi_shared.models import Approval, Offer, PlanWindow


def plan_summary(window: PlanWindow) -> str:
    """'Buy 2.4 kWh from neighbours, 10:00–13:00, for about ₹11.23?'"""
    raise NotImplementedError("TODO(R2.5, Jiten)")


def request_plan(window: PlanWindow) -> Approval:
    raise NotImplementedError("TODO(R2.5, Jiten)")


def request_offer(offer: Offer) -> Approval:
    raise NotImplementedError("TODO(R2.5, Jiten)")


def resolve(approval_id: str, decision: str, channel: str) -> Approval:
    raise NotImplementedError("TODO(R2.5, Jiten)")
