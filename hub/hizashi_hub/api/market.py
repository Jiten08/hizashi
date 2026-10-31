"""/api/market/...: book haggled contracts, post market orders for the gate-closure auction."""
from fastapi import APIRouter, Body, Header, Request
from fastapi.responses import JSONResponse
from pydantic import ValidationError

from hizashi_shared.models import Contract, Offer

from .. import clock
from .. import state as hub_state
from ..market import booking
from .wallet import bearer

router = APIRouter(prefix="/market", tags=["market"])


@router.post("/contracts")
async def book_contract(request: Request, body: dict = Body(...), authorization: str | None = Header(None)):
    """Body: a Contract with seller_sig and buyer_sig, bare or as {"contract": {...}}.
    -> {"status": "booked", "contract": {... market_sig}} | {"status": "refused", "reason"}"""
    if not booking.any_agent_token(bearer(authorization)):
        return JSONResponse({"status": "refused", "reason": "Only a house agent can book contracts."}, 401)
    try:
        contract = Contract.model_validate(body.get("contract", body))
    except ValidationError as e:
        return JSONResponse({"status": "refused", "reason": f"That contract isn't well-formed: {e.errors()[0]['msg']}."}, 422)
    c = clock.get()
    try:
        booked = booking.book(request.app.state.db, contract, hub_state.get().houses,
                              lambda key: c.block_states.get(key), c.now)
    except booking.BookingError as e:
        return {"status": "refused", "reason": str(e)}
    return {"status": "booked", "contract": booked.model_dump(mode="json")}


@router.post("/orders")
def post_order(offer: Offer, authorization: str | None = Header(None)) -> dict:
    raise NotImplementedError("TODO(R2.1, Tezash)")
