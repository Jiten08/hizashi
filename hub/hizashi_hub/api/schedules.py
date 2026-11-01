"""/api/schedules: the owner's away / guests plans for today or a later day (N7)."""
from typing import Literal

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from hizashi_shared.models import HOUSES

from .. import clock, schedules

router = APIRouter(prefix="/schedules", tags=["schedules"])


class ScheduleBody(BaseModel):
    kind: Literal["away", "guests"]
    day: str                 # "2026-10-31"
    start: str               # "09:00" (quarter hours)
    end: str                 # "18:00"; "24:00" = until midnight


def _house(house: str) -> str:
    if house not in HOUSES:
        raise HTTPException(404, f"unknown house {house}")
    return house


@router.get("/{house}")
def list_schedules(request: Request, house: str) -> list[dict]:
    """Schedules that haven't ended before today, earliest first."""
    rows = schedules.listing(request.app.state.db, _house(house), clock.get().day)
    return [s.model_dump(mode="json") for s in rows]


@router.post("/{house}")
def add(request: Request, house: str, body: ScheduleBody) -> dict:
    try:
        s = schedules.add(request.app.state.db, request.app.state.sim.events, _house(house),
                          body.kind, body.day, body.start, body.end, clock.get().now)
    except schedules.ScheduleError as e:
        raise HTTPException(422, str(e)) from e
    return s.model_dump(mode="json")


@router.delete("/{house}/{schedule_id}")
def remove(request: Request, house: str, schedule_id: str) -> dict:
    if not schedules.remove(request.app.state.db, request.app.state.sim.events, _house(house), schedule_id,
                            clock.get().now):
        raise HTTPException(404, "no such schedule")
    return {"status": "ok"}
