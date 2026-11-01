"""/api/console/...: demo controls: speed, reset, and sim / attack events."""
from typing import Literal

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

import uuid

from hizashi_shared import blocks, config, street
from hizashi_shared import events as ev
from hizashi_shared.models import HOUSES, Event, PlanWindow

from .. import attacks, bus, clock, schedules
from .. import state as hub_state
from ..sim import weather
from ..wallet import approvals
from ..wallet import mandate as mandates
from .houses import _save as save_house
from .market import enter_market

router = APIRouter(prefix="/console", tags=["console"])


class SpeedBody(BaseModel):
    speed: int


class ResetBody(BaseModel):
    next_day: bool = False      # move to the day after (owners' schedules for it take effect)
    start_over: bool = False    # wipe the street's history and send every phone back to onboarding


class ConsoleEventBody(BaseModel):
    type: Literal["cloud", "outage", "ac", "guests", "away", "ask_owner", "impostor"]
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
async def reset(request: Request, body: ResetBody | None = None) -> dict:
    """Start the day over at 05:00, or with next_day start the following day (its own weather).
    start_over goes back to the first demo day as if nobody had used Hizashi yet."""
    c = clock.get()
    day = None
    if body and body.start_over:
        day = config.SIM_DAY
        frame, source = await weather.load_weather(day)
        request.app.state.sim.set_weather(frame)
        hub_state.get().weather_source = source
        _wipe_history(request.app.state.db)
    elif body and body.next_day:
        day = blocks.next_day(c.day)
        frame, source = await weather.load_weather(day)
        request.app.state.sim.set_weather(frame)
        hub_state.get().weather_source = source
    await c.reset(day)
    schedules.publish_all(request.app.state.db, c.now)
    if body and body.start_over:
        _back_to_onboarding(request, c.now)
    return {"sim_time": c.now.isoformat(), "speed": c.speed, "day": c.day}


# Kept by "start over": houses (roofs), keys and phones' push subscriptions.
HISTORY_TABLES = ("ledger", "mandates", "schedules")


def _wipe_history(conn) -> None:
    """The ledger, every rule change and every away / guests plan (the day's rows go in clock.reset)."""
    for t in HISTORY_TABLES:
        conn.execute(f"DELETE FROM {t}")
    conn.commit()


def _back_to_onboarding(request: Request, now) -> None:
    """Default rules for every house and each one un-onboarded; phones show onboarding on the event."""
    conn = request.app.state.db
    hs = hub_state.get()
    schedules.sync(conn, request.app.state.sim.events)
    for house in hs.houses:
        bus.publish(Event(type=ev.SCHEDULE_UPDATED, sim_time=now, house=house, data={"schedules": []}))
    for house, m in street.load_mandates().items():
        conn.execute("INSERT INTO mandates (house, version, json, created_at) VALUES (?, ?, ?, ?)",
                     (house, m.version, m.model_dump_json(), now.isoformat()))
        hs.mandates[house] = m
        bus.publish(Event(type=ev.MANDATE_UPDATED, sim_time=now, house=house, data={"mandate": m.model_dump(mode="json")}))
    conn.commit()
    for house, info in list(hs.houses.items()):
        info = info.model_copy(update={"onboarded": False})
        hs.houses[house] = info
        conn.execute("INSERT OR REPLACE INTO houses (id, json) VALUES (?, ?)", (house, info.model_dump_json()))
        save_house(info)
        bus.publish(Event(type=ev.HOUSE_UPDATED, sim_time=now, house=house, data={"house": info.model_dump(mode="json")}))
    conn.commit()


SIM_TYPES = ("cloud", "outage", "ac", "guests", "away")
NEEDS_HOUSE = ("ac", "guests", "away", "ask_owner")
ASK_BLOCKS = 4                 # the plan the owner is asked about covers the next hour


@router.post("/events")
async def post_event(request: Request, body: ConsoleEventBody) -> dict:
    """cloud / outage / ac / guests / away change the sim; ask_owner sends the owner a plan that is
    over their no-ask limit; impostor runs the attack demo."""
    now = clock.get().now
    if body.house is not None and body.house not in HOUSES:
        raise HTTPException(404, f"unknown house {body.house}")
    if body.type in NEEDS_HOUSE and body.house is None:
        raise HTTPException(422, f"{body.type} needs a house")
    conn = request.app.state.db
    if body.type in SIM_TYPES:
        e = request.app.state.sim.events.add(body.type, body.house, now, body.minutes)
        data = {"event": e.model_dump(mode="json")}
        bus.publish(Event(type=ev.SIM_EVENT, sim_time=now, house=e.house, data=data))
        if e.type == "outage":
            bus.publish(Event(type=ev.GRID_OUTAGE, sim_time=now,
                              data={"active": True, "start": e.start.isoformat(), "end": e.end.isoformat()}))
        return {"status": "ok", **data}
    if body.type == "ask_owner":
        return ask_owner(conn, body.house, now)  # type: ignore[arg-type]
    # impostor: "House 20", an outsider with no wallet on the registry, tries to sell at ₹40;
    # the market's door refuses it and blacklists its key.
    key = attacks.outsider_key()
    ask = attacks.outsider_ask(attacks.next_open_block(clock.get().block_states, now), key)
    refusal = enter_market(conn, ask, attacks.pubkey(key))
    return {"status": "refused" if refusal else "let in", "reason": refusal}


def ask_owner(conn, house: str, now) -> dict:
    """A one-hour buy plan worth more than the owner's no-ask limit: the wallet holds the house's buys
    in that hour until the owner taps Approve (or Decline) on the phone."""
    c = clock.get()
    # The next open block; before or after trading hours, the nearest trading hour (still a real ask).
    first = min(max(attacks.next_open_block(c.block_states, now).index, blocks.TRADABLE[0]),
                blocks.TRADABLE[-1] - ASK_BLOCKS + 1)
    last = first + ASK_BLOCKS - 1
    limit = mandates.current(conn, house).approve_above
    kwh = round(limit / config.EXPECTED_P2P_PRICE + 1.0, 1)
    window = PlanWindow(plan_id=f"ask-{uuid.uuid4().hex[:8]}", house=house, side="buy", day=c.day,  # type: ignore[arg-type]
                        first_index=first, last_index=last, kwh=kwh, expected_price=config.EXPECTED_P2P_PRICE,
                        expected_value=round(kwh * config.EXPECTED_P2P_PRICE, 2), status="pending")
    approvals.save_pending_plan(conn, window, now)
    return {"status": "asked", "house": house, "plan": window.model_dump(mode="json")}
