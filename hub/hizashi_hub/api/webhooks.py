"""/webhooks/twilio: WhatsApp replies "YES 4821" / "NO 4821" resolve approvals."""
from fastapi import APIRouter, Request

router = APIRouter(prefix="/webhooks", tags=["webhooks"])


@router.post("/twilio")
async def twilio(request: Request) -> str:
    raise NotImplementedError("TODO(N1, Tezash)")
