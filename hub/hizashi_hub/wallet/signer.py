"""Sign offers and contracts with the house's wallet key, after the checks pass.

`sign_offer_request` / `sign_contract_request` are the whole wallet flow behind
POST /api/wallet/{house}/sign: run the checks, sign, store, publish.
"""
import json
import sqlite3
from datetime import datetime

from nacl.signing import SigningKey

from hizashi_shared import crypto
from hizashi_shared import events as ev
from hizashi_shared.models import Contract, Event, Offer, PlanWindow

from .. import bus
from . import checks, keystore
from . import mandate as mandates


def sign_offer(house: str, offer: Offer, key: SigningKey | None = None) -> Offer:
    key = key or keystore.wallet_key(house)
    return offer.model_copy(update={"signature": crypto.sign(offer, key)})


def sign_plan(house: str, window: PlanWindow, key: SigningKey | None = None) -> PlanWindow:
    key = key or keystore.wallet_key(house)
    return window.model_copy(update={"signature": crypto.sign(window, key)})


def sign_contract(house: str, contract: Contract, key: SigningKey | None = None) -> Contract:
    """Adds seller_sig or buyer_sig depending on which side `house` is."""
    key = key or keystore.wallet_key(house)
    field = "seller_sig" if house == contract.seller else "buyer_sig"
    return contract.model_copy(update={field: crypto.sign(contract, key)})


# --- storage ------------------------------------------------------------------------

def offer_status(conn: sqlite3.Connection, offer_id: str) -> str | None:
    row = conn.execute("SELECT status FROM offers WHERE offer_id = ?", (offer_id,)).fetchone()
    return row["status"] if row else None


def store_offer(conn: sqlite3.Connection, offer: Offer, status: str, reason: str | None, now: datetime) -> None:
    conn.execute(
        "INSERT OR REPLACE INTO offers (offer_id, negotiation_id, block_key, house, to_house, side, kwh, "
        "price, round, status, reason, json, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (offer.offer_id, offer.negotiation_id, offer.block.key, offer.house, offer.to, offer.side,
         offer.kwh, offer.price, offer.round, status, reason, offer.model_dump_json(), now.isoformat()),
    )
    conn.commit()


def signed_offers(conn: sqlite3.Connection, negotiation_id: str | None) -> list[Offer]:
    if not negotiation_id:
        return []
    rows = conn.execute(
        "SELECT json FROM offers WHERE negotiation_id = ? AND status = 'signed'", (negotiation_id,)
    ).fetchall()
    return [Offer.model_validate_json(r["json"]) for r in rows]


def spent_today(conn: sqlite3.Connection, house: str, day: str) -> float:
    """₹ committed to buys today: booked or settled contracts where `house` is the buyer."""
    row = conn.execute(
        "SELECT COALESCE(SUM(kwh * price), 0) v FROM contracts WHERE buyer = ? AND block_key LIKE ?",
        (house, f"{day}#%"),
    ).fetchone()
    return float(row["v"])


def plans(conn: sqlite3.Connection, house: str, day: str) -> list[PlanWindow]:
    rows = conn.execute("SELECT json FROM plans WHERE house = ?", (house,)).fetchall()
    return [w for w in (PlanWindow.model_validate_json(r["json"]) for r in rows) if w.day == day]


# --- the wallet flow ------------------------------------------------------------------

def _dump(model) -> dict:
    return json.loads(model.model_dump_json())


# Refusals the owner should see as a red card: their own limits stopped the agent.
# Check 3 (block timing) and 0 (duplicates, mismatched terms) are protocol noise; check 8
# (plan waiting / declined) is already on the phone as the approval card.
OWNER_CHECKS = {2, 4, 5, 6, 7}


def _blocked(house: str, reason: str, payload: dict, now: datetime, check: int | None = None) -> dict:
    bus.publish(Event(type=ev.WALLET_BLOCKED, sim_time=now, house=house,
                      data={"reason": reason, "text": checks.blocked_text(reason), "check": check,
                            "owner_rule": check in OWNER_CHECKS, **payload}))
    return {"status": "refused", "reason": reason}


def sign_offer_request(conn: sqlite3.Connection, house: str, token: str | None, offer: Offer,
                       block_state_fn: checks.BlockStateFn, street: checks.Street, now: datetime) -> dict:
    """-> {"status": "signed", "offer"} | {"status": "pending", "approval_id"} | {"status": "refused", "reason"}"""
    if not checks.token_ok(house, token) or house not in street:
        # Unauthenticated: answer, but don't write to the house's records or phone.
        return {"status": "refused", "reason": f"This agent isn't allowed to sign for {house}."}
    mandate = mandates.current(conn, house)
    day = offer.block.day
    result = checks.check_offer(mandate, offer, block_state_fn, street, now, house=house, token=token,
                                already_signed=offer_status(conn, offer.offer_id) == "signed",
                                spent_today=spent_today(conn, house, day), plans=plans(conn, house, day))
    if result.status == "pending":
        from . import approvals
        a = approvals.request_offer(conn, offer, now)
        return {"status": "pending", "approval_id": a.approval_id, "reason": result.reason}
    if not result.ok:
        if result.check != 0:           # keep the original row of a duplicate
            store_offer(conn, offer, "refused", result.reason, now)
        return _blocked(house, result.reason, {"offer": _dump(offer)}, now, result.check)

    signed = sign_offer(house, offer)
    store_offer(conn, signed, "signed", None, now)
    data = {"offer": _dump(signed)}
    bus.publish(Event(type=ev.NEGO_OFFER, sim_time=now, house=house, data=data))
    if signed.to:
        bus.publish(Event(type=ev.NEGO_OFFER, sim_time=now, house=signed.to, data=data))
    return {"status": "signed", "offer": data["offer"]}


def sign_contract_request(conn: sqlite3.Connection, house: str, token: str | None, contract: Contract,
                          block_state_fn: checks.BlockStateFn, street: checks.Street, now: datetime) -> dict:
    """-> {"status": "signed", "contract"} | {"status": "refused", "reason"}. Doesn't book."""
    if not checks.token_ok(house, token) or house not in street:
        return {"status": "refused", "reason": f"This agent isn't allowed to sign for {house}."}
    mandate = mandates.current(conn, house)
    if contract.seller in street and contract.buyer in street:
        # open_access is covered by both signatures, so fix it before signing.
        contract = contract.model_copy(update={"open_access": checks.needs_open_access(contract, street)})
    day = contract.block.day
    result = checks.check_contract(mandate, contract, block_state_fn, street, now, house=house, token=token,
                                   signed_offers=signed_offers(conn, contract.negotiation_id),
                                   spent_today=spent_today(conn, house, day), plans=plans(conn, house, day))
    if not result.ok:
        return _blocked(house, result.reason, {"contract": _dump(contract)}, now, result.check)
    return {"status": "signed", "contract": _dump(sign_contract(house, contract))}
