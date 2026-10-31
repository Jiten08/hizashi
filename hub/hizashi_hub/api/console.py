"""/api/console/...: demo controls. Speed and reset work now; events come in R2.7."""
from typing import Literal

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from .. import clock

router = APIRouter(prefix="/console", tags=["console"])


class SpeedBody(BaseModel):
    speed: int


class ConsoleEventBody(BaseModel):
    type: Literal["cloud", "outage", "ac", "guests", "away", "bad_bid", "rogue_seller", "collusion"]
    house: str | None = None
    minutes: int | None = None


@router.post("/speed")
def set_speed(body: SpeedBody) -> dict:
    try:
        clock.get().set_speed(body.speed)
    except ValueError as e:
        raise HTTPException(400, str(e)) from e
    return {"speed": body.speed}


@router.post("/reset")
async def reset() -> dict:
    c = clock.get()
    await c.reset()
    return {"sim_time": c.now.isoformat(), "speed": c.speed}


@router.post("/events")
def post_event(body: ConsoleEventBody) -> dict:
    """cloud / outage / ac / guests / away change the sim; bad_bid etc. drive the attack demos."""
    raise NotImplementedError("TODO(R2.7, Tezash)")
