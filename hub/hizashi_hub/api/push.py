"""/api/push: Web Push subscriptions for the phone app (approval notifications)."""
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from hizashi_shared.models import HOUSES

from .. import clock
from ..notify import webpush

router = APIRouter(prefix="/push", tags=["push"])


class Keys(BaseModel):
    p256dh: str
    auth: str


class Subscription(BaseModel):          # PushSubscription.toJSON() from the browser
    endpoint: str
    keys: Keys
    expirationTime: float | None = None


class EndpointBody(BaseModel):
    endpoint: str


def _house(house: str) -> str:
    if house not in HOUSES:
        raise HTTPException(404, f"unknown house {house}")
    return house


@router.get("/key")
def vapid_key() -> dict:
    """The applicationServerKey to subscribe with."""
    return {"key": webpush.public_key()}


@router.post("/{house}")
def subscribe(request: Request, house: str, body: Subscription) -> dict:
    webpush.subscribe(request.app.state.db, _house(house), body.model_dump(exclude_none=True), clock.get().now)
    return {"status": "ok"}


@router.delete("/{house}")
def unsubscribe(request: Request, house: str, body: EndpointBody) -> dict:
    _house(house)
    webpush.unsubscribe(request.app.state.db, body.endpoint)
    return {"status": "ok"}


@router.post("/{house}/test")
async def test(request: Request, house: str) -> dict:
    """Ping every phone subscribed for this house (lock the phone first to see it arrive)."""
    sent = await webpush.send(request.app.state.db, _house(house), {
        "title": "Hizashi", "body": "Notifications work. Your agent will ask here when it needs your OK.",
        "tag": "test", "url": f"/app/?house={house}"})
    return {"sent": sent}
