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


def dumps(payload: dict) -> str:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def append(conn: sqlite3.Connection, ts: str, kind: str, ref_id: str, payload: dict) -> dict:
    """Add one entry chained to the last one. `payload` names the houses involved
    (house / seller / buyer / houses) so GET /api/ledger?house= can filter."""
    last = conn.execute("SELECT seq, hash FROM ledger ORDER BY seq DESC LIMIT 1").fetchone()
    seq, prev = (last["seq"] + 1, last["hash"]) if last else (1, GENESIS)
    body = dumps(payload)
    h = entry_hash(prev, seq, ts, kind, ref_id, body)
    conn.execute(
        "INSERT INTO ledger (seq, ts, kind, ref_id, payload, prev_hash, hash) VALUES (?, ?, ?, ?, ?, ?, ?)",
        (seq, ts, kind, ref_id, body, prev, h),
    )
    conn.commit()
    return {"seq": seq, "ts": ts, "kind": kind, "ref_id": ref_id, "payload": payload, "prev_hash": prev, "hash": h}


def verify(conn: sqlite3.Connection) -> dict:
    """{"ok": True, "entries": n} or {"ok": False, "broken_at": seq}"""
    prev = GENESIS
    n = 0
    for r in conn.execute("SELECT * FROM ledger ORDER BY seq"):
        n += 1
        if r["seq"] != n or r["prev_hash"] != prev or                 r["hash"] != entry_hash(prev, r["seq"], r["ts"], r["kind"], r["ref_id"], r["payload"]):
            return {"ok": False, "broken_at": r["seq"]}
        prev = r["hash"]
    return {"ok": True, "entries": n}


def involves(payload: dict, house: str) -> bool:
    return house in (payload.get("house"), payload.get("seller"), payload.get("buyer"))         or house in payload.get("houses", [])


def entries(conn: sqlite3.Connection, house: str | None = None, limit: int = 500) -> list[dict]:
    """Newest first."""
    out = []
    for r in conn.execute("SELECT * FROM ledger ORDER BY seq DESC"):
        payload = json.loads(r["payload"])
        if house is None or involves(payload, house):
            out.append({"seq": r["seq"], "ts": r["ts"], "kind": r["kind"], "ref_id": r["ref_id"],
                        "payload": payload, "prev_hash": r["prev_hash"], "hash": r["hash"]})
            if len(out) >= limit:
                break
    return out
