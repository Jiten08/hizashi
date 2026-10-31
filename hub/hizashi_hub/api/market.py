"""/api/market/...: book haggled contracts, post market orders for the gate-closure auction."""
from fastapi import APIRouter, Header

from hizashi_shared.models import Contract, Offer

router = APIRouter(prefix="/market", tags=["market"])


@router.post("/contracts")
def book_contract(contract: Contract, authorization: str | None = Header(None)) -> dict:
    raise NotImplementedError("TODO(R1.6, Tezash)")


@router.post("/orders")
def post_order(offer: Offer, authorization: str | None = Header(None)) -> dict:
    raise NotImplementedError("TODO(R2.1, Tezash)")
