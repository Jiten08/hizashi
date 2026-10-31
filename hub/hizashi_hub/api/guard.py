"""/api/guard/report: agents report bad signatures etc. -> guard.flag."""
from fastapi import APIRouter, Header, HTTPException, Request
from pydantic import BaseModel

from hizashi_shared import config

from .. import clock
from ..guard import watch
from .wallet import bearer

router = APIRouter(prefix="/guard", tags=["guard"])


class ReportBody(BaseModel):
    kind: str
    detail: dict | str


@router.post("/report")
def report(request: Request, body: ReportBody, authorization: str | None = Header(None)) -> dict:
    """An agent caught something (a forged signature on an A2A offer). -> {"status": "flagged"}"""
    token = bearer(authorization)
    reporter = next((h for h, t in config.AGENT_TOKENS.items() if t == token), None)
    if reporter is None:
        raise HTTPException(401, "Only a house agent can report to the guard.")
    guard = watch.get()
    if guard is None:
        raise HTTPException(503, "The guard isn't running.")
    detail = body.detail if isinstance(body.detail, dict) else {"text": body.detail}
    claimed = str(detail.get("house") or "")
    if body.kind == "bad_signature" and claimed:
        text = (f"House {reporter[1:]}'s agent got an offer that claims to come from House {claimed[1:]}, "
                f"but House {claimed[1:]}'s wallet never signed it. Refused before any trade.")
        houses = sorted({reporter, claimed})
    else:
        text = f"House {reporter[1:]}'s agent reported {body.kind.replace('_', ' ')}."
        houses = [reporter]
    flag = guard.flag(request.app.state.db, body.kind, houses, text, clock.get().now,
                      {**detail, "reported_by": reporter}, once=(reporter, str(detail.get("offer_id", text))))
    return {"status": "flagged" if flag else "already flagged"}
