"""/api/wallet/{house}/...: sign offers/contracts, post plans, get/put/parse mandates."""
from fastapi import APIRouter, Body, Header, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ValidationError

from hizashi_shared.models import HOUSES, Contract, Mandate, Offer, PlanWindow

from .. import clock
from ..llm import mandate_parser
from .. import state as hub_state
from ..wallet import approvals, checks, signer
from ..wallet import mandate as mandates

router = APIRouter(prefix="/wallet", tags=["wallet"])


class PlansBody(BaseModel):
    windows: list[PlanWindow]


class ParseBody(BaseModel):
    text: str


def bearer(authorization: str | None) -> str | None:
    if authorization and authorization.lower().startswith("bearer "):
        return authorization[7:].strip()
    return None


def _house(house: str) -> str:
    if house not in HOUSES:
        raise HTTPException(404, f"unknown house {house}")
    return house


def _block_state(key: str) -> str | None:
    return clock.get().block_states.get(key)


@router.post("/{house}/sign")
async def sign(request: Request, house: str, body: dict = Body(...), authorization: str | None = Header(None)):
    """{"kind": "offer", "offer": {...}} | {"kind": "contract", "contract": {...}}
    -> {"status": "signed", "offer"|"contract": ...} | {"status": "refused", "reason"}"""
    _house(house)
    conn = request.app.state.db
    street = hub_state.get().houses
    now = clock.get().now
    kind = body.get("kind")
    try:
        if kind == "offer":
            offer = Offer.model_validate(body.get("offer"))
            return signer.sign_offer_request(conn, house, bearer(authorization), offer, _block_state, street, now)
        if kind == "contract":
            contract = Contract.model_validate(body.get("contract"))
            return signer.sign_contract_request(conn, house, bearer(authorization), contract, _block_state, street, now)
    except ValidationError as e:
        return JSONResponse({"status": "refused", "reason": f"That {kind} isn't well-formed: {e.errors()[0]['msg']}."}, 422)
    return JSONResponse({"status": "refused", "reason": 'kind must be "offer" or "contract".'}, 422)


@router.post("/{house}/plans")
async def post_plans(request: Request, house: str, body: PlansBody, authorization: str | None = Header(None)):
    """-> {"status": "ok", "windows": [PlanWindow with status auto|pending|approved|declined]}"""
    _house(house)
    if not checks.token_ok(house, bearer(authorization)):
        return JSONResponse({"status": "refused", "reason": f"This agent isn't allowed to plan for {house}."}, 401)
    conn = request.app.state.db
    saved = approvals.store_plans(conn, house, body.windows, mandates.current(conn, house), clock.get().now)
    return {"status": "ok", "windows": [w.model_dump(mode="json") for w in saved]}


@router.get("/{house}/mandate")
async def get_mandate(request: Request, house: str) -> Mandate:
    return mandates.current(request.app.state.db, _house(house))


@router.put("/{house}/mandate")
async def put_mandate(request: Request, house: str, mandate: Mandate) -> Mandate:
    return mandates.update(request.app.state.db, _house(house), mandate, clock.get().now)


@router.post("/{house}/mandate/parse")
async def parse_mandate(request: Request, house: str, body: ParseBody) -> dict:
    """The owner's sentence -> a proposed mandate + the changes (not saved; Save = PUT /mandate).
    -> {"mandate", "changes": [{"field", "label", "from", "to"}], "source": "gemini"|"rules"|"none", "note"}"""
    current = mandates.current(request.app.state.db, _house(house))
    return (await mandate_parser.parse(body.text, current)).model_dump(mode="json")
