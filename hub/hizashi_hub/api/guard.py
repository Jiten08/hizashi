"""/api/guard/report: agents report bad signatures etc. -> guard.flag."""
from fastapi import APIRouter, Header
from pydantic import BaseModel

router = APIRouter(prefix="/guard", tags=["guard"])


class ReportBody(BaseModel):
    kind: str
    detail: dict | str


@router.post("/report")
def report(body: ReportBody, authorization: str | None = Header(None)) -> dict:
    raise NotImplementedError("TODO(N2, Tezash)")
