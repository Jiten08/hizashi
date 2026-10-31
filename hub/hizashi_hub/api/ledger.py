"""/api/ledger?house= and /api/ledger/verify."""
from fastapi import APIRouter

router = APIRouter(prefix="/ledger", tags=["ledger"])


@router.get("")
def list_entries(house: str | None = None) -> list[dict]:
    raise NotImplementedError("TODO(R2.4, Tezash)")


@router.get("/verify")
def verify() -> dict:
    """-> {"ok": true} | {"ok": false, "broken_at": seq}"""
    raise NotImplementedError("TODO(R2.4, Tezash)")
