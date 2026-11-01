"""Builds the simulated street (events, pv, load, meters) plus the market lifecycle and
wires them into the clock. One instance lives at app.state.sim.

Order on each tick: meters read the minute that just ended, the outage watcher publishes
grid.outage changes, the lifecycle runs any due auction; then the clock publishes the tick
and moves blocks (auction / settlement hooks).
"""
import sqlite3
from dataclasses import dataclass, field
from datetime import datetime, timedelta

import pandas as pd

from hizashi_shared import config
from hizashi_shared import events as ev
from hizashi_shared.models import Event, HouseInfo, Mandate

from .. import bus
from ..clock import SimClock
from ..market.lifecycle import Lifecycle
from ..market.orderbook import OrderBook
from . import events as sim_events
from .events import SimEvents
from .load import LoadSim
from .meters import Meters
from .pv import PvSim

# Rows that belong to one simulated day; a reset (or hub start) clears them. The ledger
# and mandate versions are kept.
DAY_TABLES = ("offers", "plans", "approvals", "contracts", "block_meter", "settlements", "flags")


def clear_day(conn: sqlite3.Connection) -> None:
    for t in DAY_TABLES:
        conn.execute(f"DELETE FROM {t}")
    conn.commit()


@dataclass
class Sim:
    conn: sqlite3.Connection
    houses: dict[str, HouseInfo]
    mandates: dict[str, Mandate]
    weather: pd.DataFrame
    seed: int = config.SIM_SEED
    events: SimEvents = field(default_factory=SimEvents)
    orderbook: OrderBook = field(default_factory=OrderBook)

    def __post_init__(self) -> None:
        self.pv = PvSim(self.houses, self.weather, self.seed, self.events)
        self.load = LoadSim(self.houses, self.seed, self.events)
        self.meters = Meters(self.pv, self.load, self.conn, self.events)
        self.lifecycle = Lifecycle(self.conn, self.houses, self.mandates, self.orderbook, self.events)
        self._outage = False
        sim_events.use(self.events)

    def wire(self, clock: SimClock) -> None:
        clock.on_minute += [self.meters.on_minute, self.watch_outage, self.lifecycle.on_minute]
        clock.on_block_state.append(self.lifecycle.on_block_state)
        clock.on_reset.append(self.reset)

    def watch_outage(self, now: datetime) -> None:
        active = self.events.outage(now - timedelta(minutes=1))
        if active != self._outage:
            self._outage = active
            bus.publish(Event(type=ev.GRID_OUTAGE, sim_time=now, data={"active": active}))

    def set_weather(self, weather: pd.DataFrame) -> None:
        """A new day's forecast weather (console "next day"): roofs recompute their output."""
        self.weather = weather
        self.pv.weather = weather
        self.pv._base.clear()

    def reset(self) -> None:
        clear_day(self.conn)
        self.events.clear()
        self.lifecycle.reset()
        self._outage = False
