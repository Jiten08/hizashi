"""Mandate store + versions (table mandates). Starts from the defaults seed.py wrote;
PUT stores a new version and publishes mandate.updated."""
import json
import sqlite3
from datetime import datetime

from hizashi_shared import events as ev
from hizashi_shared import street
from hizashi_shared.models import Event, Mandate

from .. import bus


def current(conn: sqlite3.Connection, house: str) -> Mandate:
    row = conn.execute(
        "SELECT json FROM mandates WHERE house = ? ORDER BY version DESC LIMIT 1", (house,)
    ).fetchone()
    if row:
        return Mandate.model_validate_json(row["json"])
    defaults = street.load_mandates()
    if house not in defaults:
        raise KeyError(f"no mandate for {house}")
    return defaults[house]


def update(conn: sqlite3.Connection, house: str, new: Mandate, sim_time: datetime) -> Mandate:
    """Save `new` as the next version for `house` (house and version are set here)."""
    version = current(conn, house).version + 1
    saved = new.model_copy(update={"house": house, "version": version})
    conn.execute(
        "INSERT INTO mandates (house, version, json, created_at) VALUES (?, ?, ?, ?)",
        (house, version, saved.model_dump_json(), sim_time.isoformat()),
    )
    conn.commit()
    # TODO(R2.4, Jiten): ledger entry for the mandate change
    bus.publish(Event(type=ev.MANDATE_UPDATED, sim_time=sim_time, house=house,
                      data={"mandate": json.loads(saved.model_dump_json())}))
    return saved
