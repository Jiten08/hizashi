"""/api/wallet/{house}/...: sign offers/contracts, post plans, get/put/parse mandates."""
from fastapi import APIRouter, Header
from pydantic import BaseModel

from hizashi_shared.models import Contract, Mandate, Offer, PlanWindow

router = APIRouter(prefix="/wallet", tags=["wallet"])


class SignBody(BaseModel):
    kind: str                       # "offer" | "contract"
    offer: Offer | None = None
    contract: Contract | None = None


class PlansBody(BaseModel):
    windows: list[PlanWindow]


class ParseBody(BaseModel):
    text: str


@router.post("/{house}/sign")
def sign(house: str, body: SignBody, authorization: str | None = Header(None)) -> dict:
    """-> {"status": "signed", "offer"|"contract": ...} | {"status": "pending", "approval_id"} | {"status": "refused", "reason"}"""
    raise NotImplementedError("TODO(R1.1, Tezash)")


@router.post("/{house}/plans")
def post_plans(house: str, body: PlansBody, authorization: str | None = Header(None)) -> dict:
    raise NotImplementedError("TODO(R2.5, Tezash)")


@router.get("/{house}/mandate")
def get_mandate(house: str) -> Mandate:
    raise NotImplementedError("TODO(R2.8, Tezash)")


@router.put("/{house}/mandate")
def put_mandate(house: str, mandate: Mandate) -> Mandate:
    raise NotImplementedError("TODO(R2.8, Tezash)")


@router.post("/{house}/mandate/parse")
def parse_mandate(house: str, body: ParseBody) -> Mandate:
    raise NotImplementedError("TODO(N4, Tezash)")
