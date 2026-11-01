"""sqlite3 schema + small helpers (no ORM). DB file: hub/hizashi.db."""
import json
import sqlite3
from datetime import datetime
from pathlib import Path

from hizashi_shared import config

SCHEMA = """
CREATE TABLE IF NOT EXISTS houses (
    id TEXT PRIMARY KEY, json TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS mandates (
    house TEXT NOT NULL, version INTEGER NOT NULL, json TEXT NOT NULL, created_at TEXT NOT NULL,
    PRIMARY KEY (house, version)
);
CREATE TABLE IF NOT EXISTS plans (
    plan_id TEXT PRIMARY KEY, house TEXT NOT NULL, json TEXT NOT NULL, status TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS offers (
    offer_id TEXT PRIMARY KEY, negotiation_id TEXT, block_key TEXT NOT NULL, house TEXT NOT NULL,
    to_house TEXT, side TEXT NOT NULL, kwh REAL NOT NULL, price REAL NOT NULL, round INTEGER NOT NULL,
    status TEXT NOT NULL, reason TEXT, json TEXT NOT NULL, created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS offers_nego ON offers(negotiation_id);
CREATE INDEX IF NOT EXISTS offers_block ON offers(block_key);
CREATE TABLE IF NOT EXISTS approvals (
    approval_id TEXT PRIMARY KEY, house TEXT NOT NULL, kind TEXT NOT NULL, ref_id TEXT NOT NULL,
    code TEXT NOT NULL, status TEXT NOT NULL, channel TEXT, summary TEXT NOT NULL,
    created_at TEXT NOT NULL, decided_at TEXT
);
CREATE TABLE IF NOT EXISTS contracts (
    contract_id TEXT PRIMARY KEY, block_key TEXT NOT NULL, seller TEXT NOT NULL, buyer TEXT NOT NULL,
    kwh REAL NOT NULL, price REAL NOT NULL, route TEXT NOT NULL, status TEXT NOT NULL, json TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS contracts_block ON contracts(block_key);
CREATE TABLE IF NOT EXISTS block_meter (
    house TEXT NOT NULL, block_key TEXT NOT NULL, solar_kwh REAL NOT NULL DEFAULT 0,
    import_kwh REAL NOT NULL DEFAULT 0, export_kwh REAL NOT NULL DEFAULT 0, outage INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (house, block_key)
);
CREATE TABLE IF NOT EXISTS settlements (
    contract_id TEXT PRIMARY KEY, json TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS flags (
    id INTEGER PRIMARY KEY AUTOINCREMENT, ts TEXT NOT NULL, kind TEXT NOT NULL,
    houses TEXT NOT NULL, detail TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS schedules (
    schedule_id TEXT PRIMARY KEY, house TEXT NOT NULL, json TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS push_subscriptions (
    endpoint TEXT PRIMARY KEY, house TEXT NOT NULL, json TEXT NOT NULL, created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS ledger (
    seq INTEGER PRIMARY KEY, ts TEXT NOT NULL, kind TEXT NOT NULL, ref_id TEXT NOT NULL,
    payload TEXT NOT NULL, prev_hash TEXT NOT NULL, hash TEXT NOT NULL
);
"""


def connect(path: Path | str = config.DB_PATH) -> sqlite3.Connection:
    conn = sqlite3.connect(str(path), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def init(conn: sqlite3.Connection) -> None:
    conn.executescript(SCHEMA)
    conn.commit()


def recreate(path: Path | str = config.DB_PATH) -> None:
    """Delete the DB file (and WAL side files) and create the schema fresh."""
    path = Path(path)
    for p in (path, path.with_name(path.name + "-wal"), path.with_name(path.name + "-shm")):
        p.unlink(missing_ok=True)
    conn = connect(path)
    init(conn)
    conn.close()


def seed_street(conn: sqlite3.Connection, street: dict) -> None:
    now = datetime.now(config.TZ).isoformat()
    for h in street["houses"]:
        conn.execute("INSERT OR REPLACE INTO houses (id, json) VALUES (?, ?)", (h["id"], json.dumps(h)))
    for m in street.get("mandates", []):
        conn.execute(
            "INSERT OR REPLACE INTO mandates (house, version, json, created_at) VALUES (?, ?, ?, ?)",
            (m["house"], m.get("version", 1), json.dumps(m), now),
        )
    conn.commit()


def latest_mandates(conn: sqlite3.Connection) -> dict[str, dict]:
    rows = conn.execute(
        "SELECT m.house, m.json FROM mandates m JOIN "
        "(SELECT house, MAX(version) v FROM mandates GROUP BY house) x "
        "ON m.house = x.house AND m.version = x.v"
    ).fetchall()
    return {r["house"]: json.loads(r["json"]) for r in rows}
