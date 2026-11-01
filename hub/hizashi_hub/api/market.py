"""/api/market/...: book haggled contracts, post market orders for the gate-closure auction."""
from fastapi import APIRouter, Body, Header, Request
from fastapi.responses import JSONResponse
from pydantic import ValidationError

from hizashi_shared import crypto
from hizashi_shared.models import Contract, Offer

from .. import clock
from .. import state as hub_state
from ..market import booking
from ..guard import watch
from ..market.orderbook import OrderBookClosed
from ..wallet import checks
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


def enter_market(conn, offer: Offer, presented_key: str | None) -> str | None:
    """The door: a seller's signature must be its house's registered wallet key (the guard
    blacklists impostors); None lets the order in."""
    guard = watch.get()
    if guard is not None:
        return guard.screen_seller(conn, offer, presented_key, clock.get().now)
    info = hub_state.get().houses.get(offer.house)
    if not info or not crypto.verify(offer, offer.signature, info.wallet_pubkey or ""):
        return "The order doesn't carry this house's wallet signature."
    return None


@router.post("/orders")
async def post_order(request: Request, body: dict = Body(...), authorization: str | None = Header(None)):
    """Body: a wallet-signed Offer with to=None, bare or as {"offer": {...}}. Only while the
    block is GATE_CLOSED and its auction hasn't run. -> {"status": "queued"} | refused"""
    try:
        offer = Offer.model_validate(body.get("offer", body))
    except ValidationError as e:
        return JSONResponse({"status": "refused", "reason": f"That order isn't well-formed: {e.errors()[0]['msg']}."}, 422)
    refusal = enter_market(request.app.state.db, offer, body.get("key"))
    if refusal:
        return JSONResponse({"status": "refused", "reason": refusal}, 403)
    if not checks.token_ok(offer.house, bearer(authorization)):
        return JSONResponse({"status": "refused", "reason": "Only the house's own agent can post its orders."}, 401)
    if offer.to is not None:
        return {"status": "refused", "reason": "Market orders go to the whole street (to must be empty)."}
    c = clock.get()
    if c.block_states.get(offer.block.key) != "GATE_CLOSED":
        return {"status": "refused", "reason": "Orders are only taken between gate closure and the auction."}
    try:
        request.app.state.sim.orderbook.add(offer)
    except OrderBookClosed as e:
        return {"status": "refused", "reason": str(e)}
    return {"status": "queued", "offer_id": offer.offer_id}
