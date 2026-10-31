"""/api/approvals: list and decide plan/offer approvals."""
from typing import Literal

from fastapi import APIRouter
from pydantic import BaseModel

from hizashi_shared.models import Approval

router = APIRouter(prefix="/approvals", tags=["approvals"])


class DecisionBody(BaseModel):
    decision: Literal["approve", "decline"]
    channel: Literal["app", "whatsapp"] = "app"


@router.get("")
def list_approvals(house: str | None = None) -> list[Approval]:
    raise NotImplementedError("TODO(R2.5, Tezash)")


@router.post("/{approval_id}")
def decide(approval_id: str, body: DecisionBody) -> Approval:
    raise NotImplementedError("TODO(R2.5, Tezash)")
