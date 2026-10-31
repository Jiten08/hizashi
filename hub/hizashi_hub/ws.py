"""WebSocket endpoint /ws with fan-out by role (section 6.1).

    /ws?role=owner&house=h14
    /ws?role=street | role=console
    /ws?role=agent&house=h12&token=dev-h12

Owners get events for their house or house=None. Street/console get everything.
Screens get each house's meter readings at most once per simulated 5 minutes.
Agents get clock.tick, block.state, market.cleared, house.updated and mandate.updated,
plus approval.resolved, console.command, meter.reading and settlement.done for their house.
"""
import logging
from datetime import datetime, timedelta

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from hizashi_shared import config
from hizashi_shared import events as ev
from hizashi_shared.models import HOUSES, Event

from . import bus

log = logging.getLogger("hizashi.ws")
router = APIRouter()

ROLES = ("owner", "street", "console", "agent")
SCREEN_METER_EVERY = timedelta(minutes=5)
AGENT_GLOBAL = {ev.CLOCK_TICK, ev.BLOCK_STATE, ev.MARKET_CLEARED, ev.HOUSE_UPDATED, ev.MANDATE_UPDATED}
AGENT_SCOPED = {ev.APPROVAL_RESOLVED, ev.CONSOLE_COMMAND, ev.METER_READING, ev.SETTLEMENT_DONE}


class Filter:
    """Decides which events one socket receives."""

    def __init__(self, role: str, house: str | None) -> None:
        self.role = role
        self.house = house
        self._last_meter: dict[str, datetime] = {}

    def wants(self, e: Event) -> bool:
        if self.role == "agent":
            if e.type in AGENT_GLOBAL:
                return True
            return e.type in AGENT_SCOPED and e.house == self.house
        if self.role == "owner" and e.house not in (None, self.house):
            return False
        if e.type == ev.METER_READING:
            return self._meter_due(e)
        return True

    def _meter_due(self, e: Event) -> bool:
        last = self._last_meter.get(e.house or "")
        if last is not None and e.sim_time - last < SCREEN_METER_EVERY:
            return False
        self._last_meter[e.house or ""] = e.sim_time
        return True


@router.websocket("/ws")
async def websocket(ws: WebSocket, role: str = "street", house: str | None = None, token: str | None = None) -> None:
    if role not in ROLES or (role in ("owner", "agent") and house not in HOUSES):
        await ws.close(code=4400, reason="bad role or house")
        return
    if role == "agent" and token != config.AGENT_TOKENS.get(house):
        await ws.close(code=4401, reason="bad agent token")
        return
    await ws.accept()
    filt = Filter(role, house)
    q = bus.subscribe()
    log.info("ws connected role=%s house=%s", role, house)
    try:
        while True:
            e: Event = await q.get()
            if filt.wants(e):
                await ws.send_text(e.model_dump_json())
    except (WebSocketDisconnect, RuntimeError):
        pass
    finally:
        bus.unsubscribe(q)
        log.info("ws closed role=%s house=%s", role, house)
