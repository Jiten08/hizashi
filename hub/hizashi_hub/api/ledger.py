"""/api/ledger?house= and /api/ledger/verify."""
from fastapi import APIRouter, Request

from ..settlement import ledger

router = APIRouter(prefix="/ledger", tags=["ledger"])


@router.get("")
def list_entries(request: Request, house: str | None = None) -> list[dict]:
    """Newest first; with ?house= only entries that involve that house."""
    return ledger.entries(request.app.state.db, house)


@router.get("/verify")
def verify(request: Request) -> dict:
    """-> {"ok": true, "entries": n} | {"ok": false, "broken_at": seq}"""
    return ledger.verify(request.app.state.db)
