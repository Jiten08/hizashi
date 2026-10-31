"""/api/console/...: demo controls: speed, reset, and sim / attack events."""
from typing import Literal

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from hizashi_shared import events as ev
from hizashi_shared.models import HOUSES, Event

from .. import bus, clock

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


SIM_TYPES = ("cloud", "outage", "ac", "guests", "away")
NEEDS_HOUSE = ("ac", "guests", "away")
PHASE3 = ("rogue_seller", "collusion")


@router.post("/events")
async def post_event(request: Request, body: ConsoleEventBody) -> dict:
    """cloud / outage / ac / guests / away change the sim; bad_bid etc. drive the attack demos."""
    now = clock.get().now
    if body.house is not None and body.house not in HOUSES:
        raise HTTPException(404, f"unknown house {body.house}")
    if body.type in SIM_TYPES:
        if body.type in NEEDS_HOUSE and body.house is None:
            raise HTTPException(422, f"{body.type} needs a house")
        e = request.app.state.sim.events.add(body.type, body.house, now, body.minutes)
        data = {"event": e.model_dump(mode="json")}
        bus.publish(Event(type=ev.SIM_EVENT, sim_time=now, house=e.house, data=data))
        if e.type == "outage":
            bus.publish(Event(type=ev.GRID_OUTAGE, sim_time=now,
                              data={"active": True, "start": e.start.isoformat(), "end": e.end.isoformat()}))
        return {"status": "ok", **data}
    if body.type == "bad_bid":
        house = body.house or "h14"
        bus.publish(Event(type=ev.CONSOLE_COMMAND, sim_time=now, house=house, data={"cmd": "bad_bid", "price": 40}))
        return {"status": "ok", "sent_to": house}
    raise HTTPException(501, f"{body.type} is a Phase 3 attack demo (N3)")
