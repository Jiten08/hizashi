"""Hash-chained ledger: ledger(seq, ts, kind, ref_id, payload, prev_hash, hash).
First prev_hash = "0" * 64. Entries: contract booked, settlement, mandate change,
approval decision, guard flag."""
import hashlib
import json
import sqlite3

GENESIS = "0" * 64


def entry_hash(prev_hash: str, seq: int, ts: str, kind: str, ref_id: str, payload: str) -> str:
    body = json.dumps([prev_hash, seq, ts, kind, ref_id, payload], separators=(",", ":"))
    return hashlib.sha256(body.encode()).hexdigest()


def append(conn: sqlite3.Connection, ts: str, kind: str, ref_id: str, payload: dict) -> dict:
    raise NotImplementedError("TODO(R2.4, Jiten)")


def verify(conn: sqlite3.Connection) -> dict:
    """{"ok": True} or {"ok": False, "broken_at": seq}"""
    raise NotImplementedError("TODO(R2.4, Jiten)")
