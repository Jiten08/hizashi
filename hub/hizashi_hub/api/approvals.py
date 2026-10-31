"""/api/approvals: list and decide plan/offer approvals."""
from typing import Literal

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from .. import clock
from ..wallet import approvals

router = APIRouter(prefix="/approvals", tags=["approvals"])


class DecisionBody(BaseModel):
    decision: Literal["approve", "decline"]
    channel: Literal["app", "whatsapp"] = "app"


@router.get("")
def list_approvals(request: Request, house: str | None = None) -> list[dict]:
    """Newest first: Approval fields plus channel and decided_at."""
    return approvals.listing(request.app.state.db, house)


@router.post("/{approval_id}")
async def decide(request: Request, approval_id: str, body: DecisionBody) -> dict:
    try:
        a = approvals.resolve(request.app.state.db, approval_id, body.decision, body.channel, clock.get().now)
    except approvals.ApprovalError as e:
        raise HTTPException(409, str(e)) from e
    return a.model_dump(mode="json")
