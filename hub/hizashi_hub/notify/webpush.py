"""Web Push to the phone app: when the wallet needs an owner's OK, every phone that turned on
notifications for that house gets one, even locked. When the approval is decided (or the
agent goes ahead), the same notification is replaced quietly with the outcome.

The VAPID key pair is made on first use and kept in keys/vapid.pem (never committed).
Browsers only allow push on a secure origin: the ngrok https link, or localhost.
"""
import asyncio
import json
import logging
import sqlite3
from base64 import urlsafe_b64encode
from datetime import datetime
from functools import cache

from cryptography.hazmat.primitives import serialization
from py_vapid import Vapid02 as Vapid
from pywebpush import WebPushException, webpush

from hizashi_shared import config
from hizashi_shared import events as ev
from hizashi_shared.models import Approval

from .. import bus

log = logging.getLogger("hizashi.notify.push")

VAPID_FILE = config.KEYS_DIR / "vapid.pem"
TTL = 3600                                  # an approval is moot once its window opens
OUTCOME = {"approved": "Approved", "declined": "Declined", "expired": "Went ahead"}


@cache
def _vapid() -> Vapid:
    if VAPID_FILE.exists():
        return Vapid.from_file(str(VAPID_FILE))
    v = Vapid()
    v.generate_keys()
    VAPID_FILE.parent.mkdir(parents=True, exist_ok=True)
    v.save_key(str(VAPID_FILE))
    log.info("made a VAPID key pair in %s", VAPID_FILE)
    return v


def public_key() -> str:
    """The applicationServerKey phones subscribe with (base64url, uncompressed P-256 point)."""
    raw = _vapid().public_key.public_bytes(serialization.Encoding.X962, serialization.PublicFormat.UncompressedPoint)
    return urlsafe_b64encode(raw).decode().rstrip("=")


# --- subscriptions --------------------------------------------------------------------------

def subscribe(conn: sqlite3.Connection, house: str, sub: dict, now: datetime) -> None:
    """One row per browser; subscribing again (or for another house) replaces it."""
    conn.execute("INSERT OR REPLACE INTO push_subscriptions (endpoint, house, json, created_at) VALUES (?, ?, ?, ?)",
                 (sub["endpoint"], house, json.dumps(sub), now.isoformat()))
    conn.commit()


def unsubscribe(conn: sqlite3.Connection, endpoint: str) -> None:
    conn.execute("DELETE FROM push_subscriptions WHERE endpoint = ?", (endpoint,))
    conn.commit()


def subscriptions(conn: sqlite3.Connection, house: str) -> list[dict]:
    rows = conn.execute("SELECT json FROM push_subscriptions WHERE house = ?", (house,)).fetchall()
    return [json.loads(r["json"]) for r in rows]


# --- sending --------------------------------------------------------------------------------

def _send_all(subs: list[dict], payload: dict, urgent: bool) -> list[str]:
    """Blocking (runs in a thread). Returns the endpoints the push service says are gone."""
    gone = []
    data = json.dumps(payload)
    for sub in subs:
        try:
            webpush(sub, data, vapid_private_key=_vapid(), vapid_claims={"sub": config.VAPID_SUBJECT},
                    ttl=TTL, headers={"Urgency": "high" if urgent else "normal"})
        except WebPushException as e:
            status = e.response.status_code if e.response is not None else None
            if status in (404, 410):
                gone.append(sub["endpoint"])
            else:
                log.warning("push to %s… failed: %s", sub["endpoint"][:40], e)
        except Exception as e:
            log.warning("push to %s… failed: %s", sub["endpoint"][:40], e)
    return gone


async def send(conn: sqlite3.Connection, house: str, payload: dict, urgent: bool = True) -> int:
    subs = subscriptions(conn, house)
    if not subs:
        return 0
    gone = await asyncio.to_thread(_send_all, subs, payload, urgent)
    for endpoint in gone:
        unsubscribe(conn, endpoint)
    return len(subs) - len(gone)


def approval_payload(a: Approval) -> dict:
    url = f"/app/?house={a.house}&tab=approvals"
    if a.status == "pending":
        return {"title": "Needs your OK", "body": a.summary, "tag": a.approval_id, "url": url,
                "approval_id": a.approval_id}
    return {"title": OUTCOME[a.status], "body": a.summary, "tag": a.approval_id, "url": url, "quiet": True}


async def run(conn: sqlite3.Connection) -> None:
    """Bus subscriber: approval.requested -> ping the owner's phones; approval.resolved -> update it."""
    q = bus.subscribe()
    try:
        while True:
            e = await q.get()
            if e.type not in (ev.APPROVAL_REQUESTED, ev.APPROVAL_RESOLVED) or not e.house:
                continue
            try:
                a = Approval.model_validate(e.data["approval"])
                await send(conn, e.house, approval_payload(a), urgent=e.type == ev.APPROVAL_REQUESTED)
            except Exception:
                log.exception("approval push failed")
    finally:
        bus.unsubscribe(q)
