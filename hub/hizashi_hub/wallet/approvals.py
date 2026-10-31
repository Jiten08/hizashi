"""Plan + offer approvals: create (4-digit code), resolve, publish approval.requested/resolved.

Day plans arrive from the agent at PLANNED. Buy windows worth more than the mandate's
approve_above ask the owner; everything else is `auto`. Selling needs no OK: the
min price and per-block cap already bound it, and it earns rather than spends.

No answer is a yes: when the window's first block opens and the owner still hasn't
answered, the approval lapses (`expired`) and the window turns `auto`, so the agent
trades within the wallet's other limits. Only Decline stops it.
"""
import json
import secrets
import sqlite3
import uuid
from datetime import datetime

from hizashi_shared import blocks
from hizashi_shared import events as ev
from hizashi_shared.models import Approval, BlockRef, Event, Mandate, Offer, PlanWindow

from .. import bus
from ..settlement import ledger
from . import checks, signer


class ApprovalError(Exception):
    pass


def plan_summary(window: PlanWindow) -> str:
    """'Buy 2.4 kWh from neighbours, 10:00–13:00, for about ₹11.23?'"""
    verb = "Buy" if window.side == "buy" else "Sell"
    prep = "from" if window.side == "buy" else "to"
    return (f"{verb} {window.kwh:.1f} kWh {prep} neighbours, {checks.window_label(window)}, "
            f"for about ₹{window.expected_value:.2f}?")


def offer_summary(offer: Offer) -> str:
    verb = "Buy" if offer.side == "bid" else "Sell"
    return f"{verb} {offer.kwh:.2f} kWh at ₹{offer.price:.2f}/unit in the {blocks.label(offer.block)} block?"


def needs_ok(window: PlanWindow, mandate: Mandate) -> bool:
    return window.side == "buy" and window.expected_value > mandate.approve_above


# --- storage ------------------------------------------------------------------------

def _row_to_approval(r: sqlite3.Row) -> Approval:
    return Approval(approval_id=r["approval_id"], house=r["house"], kind=r["kind"], summary=r["summary"],
                    ref_id=r["ref_id"], code=r["code"], status=r["status"], created_at=r["created_at"])


def _dump(a: Approval, extra: dict | None = None) -> dict:
    return {**json.loads(a.model_dump_json()), **(extra or {})}


def get(conn: sqlite3.Connection, approval_id: str) -> Approval | None:
    r = conn.execute("SELECT * FROM approvals WHERE approval_id = ?", (approval_id,)).fetchone()
    return _row_to_approval(r) if r else None


def listing(conn: sqlite3.Connection, house: str | None = None) -> list[dict]:
    """Newest first, with channel and decided_at."""
    q = "SELECT * FROM approvals" + (" WHERE house = ?" if house else "") + " ORDER BY created_at DESC, rowid DESC"
    rows = conn.execute(q, (house,) if house else ()).fetchall()
    return [_dump(_row_to_approval(r), {"channel": r["channel"], "decided_at": r["decided_at"]}) for r in rows]


def _create(conn: sqlite3.Connection, house: str, kind: str, ref_id: str, summary: str, now: datetime) -> Approval:
    a = Approval(approval_id=str(uuid.uuid4()), house=house, kind=kind, summary=summary, ref_id=ref_id,
                 code=f"{secrets.randbelow(9000) + 1000}", created_at=now)
    conn.execute(
        "INSERT INTO approvals (approval_id, house, kind, ref_id, code, status, channel, summary, created_at, decided_at) "
        "VALUES (?, ?, ?, ?, ?, 'pending', NULL, ?, ?, NULL)",
        (a.approval_id, house, kind, ref_id, a.code, summary, now.isoformat()),
    )
    conn.commit()
    bus.publish(Event(type=ev.APPROVAL_REQUESTED, sim_time=now, house=house, data={"approval": _dump(a)}))
    return a


def plans_for(conn: sqlite3.Connection, house: str, day: str | None = None) -> list[PlanWindow]:
    rows = conn.execute("SELECT json FROM plans WHERE house = ?", (house,)).fetchall()
    windows = [PlanWindow.model_validate_json(r["json"]) for r in rows]
    return sorted((w for w in windows if day is None or w.day == day), key=lambda w: w.first_index)


def _save_plan(conn: sqlite3.Connection, w: PlanWindow) -> None:
    conn.execute("INSERT OR REPLACE INTO plans (plan_id, house, json, status) VALUES (?, ?, ?, ?)",
                 (w.plan_id, w.house, w.model_dump_json(), w.status))


def publish_plans(conn: sqlite3.Connection, house: str, day: str, now: datetime) -> list[PlanWindow]:
    windows = plans_for(conn, house, day)
    bus.publish(Event(type=ev.PLAN_UPDATED, sim_time=now, house=house,
                      data={"windows": [json.loads(w.model_dump_json()) for w in windows]}))
    return windows


def _set_status(conn: sqlite3.Connection, approval_id: str, status: str, channel: str | None, now: datetime) -> None:
    conn.execute("UPDATE approvals SET status = ?, channel = ?, decided_at = ? WHERE approval_id = ?",
                 (status, channel, now.isoformat(), approval_id))


def _expire(conn: sqlite3.Connection, approval_id: str, now: datetime) -> Approval | None:
    """Mark a pending approval expired and tell the phone (approval.resolved)."""
    r = conn.execute("SELECT * FROM approvals WHERE approval_id = ?", (approval_id,)).fetchone()
    if r is None or r["status"] != "pending":
        return None
    _set_status(conn, approval_id, "expired", None, now)
    a = _row_to_approval(r).model_copy(update={"status": "expired"})
    bus.publish(Event(type=ev.APPROVAL_RESOLVED, sim_time=now, house=a.house,
                      data={"approval": _dump(a, {"channel": None, "decided_at": now.isoformat()})}))
    return a


# --- plans --------------------------------------------------------------------------

def store_plans(conn: sqlite3.Connection, house: str, windows: list[PlanWindow], mandate: Mandate,
                now: datetime) -> list[PlanWindow]:
    """Replace the house's plan for each day posted. A window the owner already decided
    (same side and blocks) keeps that decision; open approvals for dropped windows expire."""
    days = {w.day for w in windows}
    old = [w for d in days for w in plans_for(conn, house, d)]
    decided = {(w.side, w.first_index, w.last_index): w.status for w in old if w.status in ("approved", "declined")}
    for w in old:
        for r in conn.execute("SELECT approval_id FROM approvals WHERE ref_id = ? AND status = 'pending'", (w.plan_id,)).fetchall():
            _expire(conn, r["approval_id"], now)
        conn.execute("DELETE FROM plans WHERE plan_id = ?", (w.plan_id,))

    saved = []
    asks: list[PlanWindow] = []
    for w in windows:
        w = w.model_copy(update={"house": house})
        status = decided.get((w.side, w.first_index, w.last_index))
        if status is None:
            status = "pending" if needs_ok(w, mandate) else "auto"
        w = w.model_copy(update={"status": status})
        w = signer.sign_plan(house, w)
        _save_plan(conn, w)
        saved.append(w)
        if status == "pending":
            asks.append(w)
    conn.commit()
    for w in asks:
        _create(conn, house, "plan", w.plan_id, plan_summary(w), now)
    for d in days:
        publish_plans(conn, house, d, now)
    return saved


def request_plan(conn: sqlite3.Connection, window: PlanWindow, now: datetime) -> Approval:
    return _create(conn, window.house, "plan", window.plan_id, plan_summary(window), now)


def request_offer(conn: sqlite3.Connection, offer: Offer, now: datetime) -> Approval:
    signer.store_offer(conn, offer, "pending", "Waiting for your OK.", now)
    return _create(conn, offer.house, "offer", offer.offer_id, offer_summary(offer), now)


# --- decisions ----------------------------------------------------------------------

def resolve(conn: sqlite3.Connection, approval_id: str, decision: str, channel: str, now: datetime) -> Approval:
    a = get(conn, approval_id)
    if a is None:
        raise ApprovalError("No such approval.")
    if a.status != "pending":
        raise ApprovalError(f"This was already {a.status}.")
    status = "approved" if decision == "approve" else "declined"
    _set_status(conn, approval_id, status, channel, now)
    extra: dict = {}
    if a.kind == "plan":
        r = conn.execute("SELECT json FROM plans WHERE plan_id = ?", (a.ref_id,)).fetchone()
        if r:
            w = PlanWindow.model_validate_json(r["json"]).model_copy(update={"status": status})
            _save_plan(conn, signer.sign_plan(w.house, w))
            conn.commit()
            publish_plans(conn, w.house, w.day, now)
    else:
        r = conn.execute("SELECT json FROM offers WHERE offer_id = ?", (a.ref_id,)).fetchone()
        if r:
            offer = Offer.model_validate_json(r["json"])
            if status == "approved":
                signed = signer.sign_offer(offer.house, offer)
                signer.store_offer(conn, signed, "signed", None, now)
                extra["offer"] = json.loads(signed.model_dump_json())
            else:
                signer.store_offer(conn, offer, "refused", "You declined it.", now)
    conn.commit()
    resolved = a.model_copy(update={"status": status})
    ledger.append(conn, now.isoformat(), "approval", approval_id,
                  {"house": a.house, "kind": a.kind, "ref_id": a.ref_id, "summary": a.summary,
                   "decision": status, "channel": channel})
    bus.publish(Event(type=ev.APPROVAL_RESOLVED, sim_time=now, house=a.house,
                      data={"approval": _dump(resolved, {"channel": channel, "decided_at": now.isoformat()}), **extra}))
    return resolved


def lapse_at_open(conn: sqlite3.Connection, ref: BlockRef, now: datetime) -> list[Approval]:
    """When a block opens, unanswered plan approvals for windows that have started lapse:
    the approval is `expired` and its window goes `auto` (the agent may trade)."""
    out = []
    touched: set[str] = set()
    for r in conn.execute("SELECT * FROM approvals WHERE status = 'pending' AND kind = 'plan'").fetchall():
        p = conn.execute("SELECT json FROM plans WHERE plan_id = ?", (r["ref_id"],)).fetchone()
        if not p:
            continue
        w = PlanWindow.model_validate_json(p["json"])
        if w.day == ref.day and w.first_index <= ref.index:
            a = _expire(conn, r["approval_id"], now)
            if a:
                out.append(a)
                ledger.append(conn, now.isoformat(), "approval", a.approval_id,
                              {"house": a.house, "kind": a.kind, "ref_id": a.ref_id, "summary": a.summary,
                               "decision": "no answer, agent went ahead", "channel": None})
            _save_plan(conn, signer.sign_plan(w.house, w.model_copy(update={"status": "auto"})))
            touched.add(w.house)
    conn.commit()
    for house in touched:
        publish_plans(conn, house, ref.day, now)
    return out
