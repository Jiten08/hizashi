"""Signed minute meter readings and per-block totals (section 6.8).

export = max(solar - use, 0), import = max(use - solar, 0); sign with the meter key,
increment seq, publish meter.reading (house-scoped), add to block_meter.
During an outage: solar 0, export 0, import 0.

The clock calls `on_minute(now)` after advancing; the reading covers the minute that
just ended, [now - 1 min, now).
"""
import json
import sqlite3
from collections.abc import Callable
from datetime import datetime, timedelta

from nacl.signing import SigningKey

from hizashi_shared import blocks, crypto
from hizashi_shared import events as ev
from hizashi_shared.models import Event, MeterReading

from .. import bus
from ..wallet import keystore
from .events import SimEvents
from .load import LoadSim
from .pv import PvSim


class Meters:
    def __init__(self, pv: PvSim, load: LoadSim, conn: sqlite3.Connection, events: SimEvents | None = None,
                 key_fn: Callable[[str], SigningKey] | None = None) -> None:
        self.pv = pv
        self.load = load
        self.conn = conn
        self.events = events or pv.events
        self.key_fn = key_fn or keystore.meter_key
        self.seq: dict[str, int] = {}          # never reset: a replayed seq is a guard flag

    def reading(self, house: str, minute: datetime, now: datetime) -> tuple[MeterReading, float, float]:
        if self.events.outage(minute):
            solar_kw = use_kw = 0.0
        else:
            solar_kw = self.pv.solar_kw(house, minute)
            use_kw = self.load.use_kw(house, minute)
        to_wh = 1000 / 60
        self.seq[house] = self.seq.get(house, 0) + 1
        r = MeterReading(
            house=house, ts=now, seq=self.seq[house],
            solar_wh=round(solar_kw * to_wh, 3),
            import_wh=round(max(use_kw - solar_kw, 0) * to_wh, 3),
            export_wh=round(max(solar_kw - use_kw, 0) * to_wh, 3),
        )
        return r.model_copy(update={"signature": crypto.sign(r, self.key_fn(house))}), solar_kw, use_kw

    async def on_minute(self, now: datetime) -> list[MeterReading]:
        """Clock on_minute hook: one signed reading per house."""
        minute = now - timedelta(minutes=1)
        block_key = blocks.block_of(minute).key
        outage = self.events.outage(minute)
        out = []
        for house in self.pv.houses:
            r, solar_kw, use_kw = self.reading(house, minute, now)
            self.conn.execute(
                "INSERT INTO block_meter (house, block_key, solar_kwh, import_kwh, export_kwh, outage) "
                "VALUES (?, ?, ?, ?, ?, ?) ON CONFLICT (house, block_key) DO UPDATE SET "
                "solar_kwh = solar_kwh + excluded.solar_kwh, import_kwh = import_kwh + excluded.import_kwh, "
                "export_kwh = export_kwh + excluded.export_kwh, outage = MAX(outage, excluded.outage)",
                (house, block_key, r.solar_wh / 1000, r.import_wh / 1000, r.export_wh / 1000, int(outage)),
            )
            bus.publish(Event(type=ev.METER_READING, sim_time=now, house=house, data={
                "reading": json.loads(r.model_dump_json()), "block": block_key,
                "solar_kw": round(solar_kw, 3), "use_kw": round(use_kw, 3), "outage": outage,
            }))
            out.append(r)
        self.conn.commit()
        return out

    def block_totals(self, house: str, block_key: str) -> dict:
        row = self.conn.execute(
            "SELECT solar_kwh, import_kwh, export_kwh, outage FROM block_meter WHERE house = ? AND block_key = ?",
            (house, block_key),
        ).fetchone()
        if not row:
            return {"solar_kwh": 0.0, "import_kwh": 0.0, "export_kwh": 0.0, "outage": False}
        return {"solar_kwh": row["solar_kwh"], "import_kwh": row["import_kwh"],
                "export_kwh": row["export_kwh"], "outage": bool(row["outage"])}
