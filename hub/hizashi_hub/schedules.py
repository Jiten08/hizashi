"""Owners' away / guests schedules (N7), set from the phone for today or a later day.

Kept in the `schedules` table (not a day table, so a reset or "next day" keeps them) and
mirrored into the sim's events so the load sim follows them. Every change publishes
`schedule.updated` with the house's schedules; its agent re-forecasts on it.
"""
import sqlite3
import uuid
from datetime import datetime, time, timedelta

from hizashi_shared import config
from hizashi_shared import events as ev
from hizashi_shared.models import Event, Schedule

from . import bus
from .sim.events import SimEvents

MAX_DAYS_AHEAD = 7


class ScheduleError(ValueError):
    pass


def load(conn: sqlite3.Connection, house: str | None = None) -> list[Schedule]:
    rows = conn.execute("SELECT json FROM schedules" + (" WHERE house = ?" if house else ""),
                        (house,) if house else ()).fetchall()
    return sorted((Schedule.model_validate_json(r["json"]) for r in rows), key=lambda s: s.start)


def listing(conn: sqlite3.Connection, house: str, day: str) -> list[Schedule]:
    """The house's schedules that haven't ended before `day` began."""
    since = datetime.combine(datetime.fromisoformat(day).date(), time(0), tzinfo=config.TZ)
    return [s for s in load(conn, house) if s.end > since]


def _at(day: str, hhmm: str) -> datetime:
    """'2026-10-31', '09:30' -> IST datetime; '24:00' is the next midnight."""
    h, m = (int(x) for x in hhmm.split(":"))
    if not (0 <= h <= 24 and m in (0, 15, 30, 45)) or (h == 24 and m):
        raise ScheduleError(f"{hhmm} is not a quarter hour")
    midnight = datetime.combine(datetime.fromisoformat(day).date(), time(0), tzinfo=config.TZ)
    return midnight + timedelta(hours=h, minutes=m)


def add(conn: sqlite3.Connection, events: SimEvents, house: str, kind: str, day: str,
        start: str, end: str, now: datetime) -> Schedule:
    try:
        first, last = _at(day, start), _at(day, end)
    except ValueError as e:
        raise ScheduleError(str(e)) from e
    if last <= first:
        raise ScheduleError("the end has to be after the start")
    today = now.date().isoformat()
    if day < today:
        raise ScheduleError("that day is over")
    if day > (now.date() + timedelta(days=MAX_DAYS_AHEAD)).isoformat():
        raise ScheduleError(f"plan at most {MAX_DAYS_AHEAD} days ahead")
    if last <= now:
        raise ScheduleError("that time is already past")
    s = Schedule(schedule_id=str(uuid.uuid4()), house=house, kind=kind,  # type: ignore[arg-type]
                 start=first, end=last, created_at=now)
    conn.execute("INSERT INTO schedules (schedule_id, house, json) VALUES (?, ?, ?)",
                 (s.schedule_id, house, s.model_dump_json()))
    conn.commit()
    _changed(conn, events, house, now)
    return s


def remove(conn: sqlite3.Connection, events: SimEvents, house: str, schedule_id: str, now: datetime) -> bool:
    gone = conn.execute("DELETE FROM schedules WHERE schedule_id = ? AND house = ?", (schedule_id, house)).rowcount
    conn.commit()
    if gone:
        _changed(conn, events, house, now)
    return bool(gone)


def sync(conn: sqlite3.Connection, events: SimEvents) -> None:
    """Load every stored schedule into the sim (hub start)."""
    events.schedules = load(conn)


def _changed(conn: sqlite3.Connection, events: SimEvents, house: str, now: datetime) -> None:
    sync(conn, events)
    day = now.date().isoformat()
    bus.publish(Event(type=ev.SCHEDULE_UPDATED, sim_time=now, house=house,  # type: ignore[arg-type]
                      data={"schedules": [s.model_dump(mode="json") for s in listing(conn, house, day)]}))


def publish_all(conn: sqlite3.Connection, now: datetime) -> None:
    """Every house's current list (after a day change, so yesterday's drop off the phones)."""
    day = now.date().isoformat()
    for house in {s.house for s in load(conn)}:
        bus.publish(Event(type=ev.SCHEDULE_UPDATED, sim_time=now, house=house,
                          data={"schedules": [s.model_dump(mode="json") for s in listing(conn, house, day)]}))

