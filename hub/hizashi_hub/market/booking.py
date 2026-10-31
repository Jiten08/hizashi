"""Verify + book contracts: seller_sig and buyer_sig against registry pubkeys, block OPEN,
seller != buyer, guard checks; set open_access, add market_sig, store, ledger, contract.booked."""
import json
import sqlite3
from collections.abc import Callable
from datetime import datetime

from nacl.signing import SigningKey

from hizashi_shared import blocks, config, crypto
from hizashi_shared import events as ev
from hizashi_shared.models import Contract, Event, HouseInfo

from .. import bus
from ..guard import watch
from ..settlement import ledger
from ..wallet import keystore

BlockStateFn = Callable[[str], str | None]


class BookingError(Exception):
    """Refused, with a plain-sentence reason."""


def verify(contract: Contract, street: dict[str, HouseInfo], block_state_fn: BlockStateFn,
           now: datetime | None = None) -> Contract:
    """Return the contract with open_access set, or raise BookingError."""
    if contract.seller == contract.buyer:
        raise BookingError("The seller and the buyer are the same house.")
    for side in ("seller", "buyer"):
        house = getattr(contract, side)
        info = street.get(house)
        if info is None or not info.wallet_pubkey:
            raise BookingError(f"{house} isn't on this street.")
        if not crypto.verify(contract, getattr(contract, f"{side}_sig"), info.wallet_pubkey):
            raise BookingError(f"The {side}'s signature ({info.label}) doesn't check out.")
    state = block_state_fn(contract.block.key)
    if state != "OPEN" or (now is not None and now >= blocks.gate_close(contract.block)):
        raise BookingError(f"The {blocks.label(contract.block)} block isn't open any more, so it can't be booked.")
    if contract.kwh <= 0:
        raise BookingError("A contract needs more than 0 kWh.")
    open_access = street[contract.seller].transformer != street[contract.buyer].transformer
    if contract.open_access != open_access:
        # Both parties sign open_access, so the market can't flip it after the fact.
        raise BookingError(f"open_access must be {open_access} for these two houses; both wallets sign it.")
    return contract


def book(conn: sqlite3.Connection, contract: Contract, street: dict[str, HouseInfo],
         block_state_fn: BlockStateFn, now: datetime, market_key: SigningKey | None = None) -> Contract:
    """Verify, add market_sig, store (status 'booked'), publish contract.booked to both houses."""
    if conn.execute("SELECT 1 FROM contracts WHERE contract_id = ?", (contract.contract_id,)).fetchone():
        raise BookingError("This contract is already booked.")
    contract = verify(contract, street, block_state_fn, now)
    guard = watch.get()
    if guard:
        try:
            guard.check_contract(conn, contract, now)
        except watch.GuardRefusal as e:
            raise BookingError(str(e)) from e
    return record(conn, contract, now, market_key)


def record(conn: sqlite3.Connection, contract: Contract, now: datetime,
           market_key: SigningKey | None = None) -> Contract:
    """Add market_sig, store (status 'booked'), ledger entry, publish contract.booked to both houses.
    Shared by haggled bookings and auction matches."""
    key = market_key or keystore.market_key()
    booked = contract.model_copy(update={"market_sig": crypto.sign(contract, key)})
    conn.execute(
        "INSERT INTO contracts (contract_id, block_key, seller, buyer, kwh, price, route, status, json) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, 'booked', ?)",
        (booked.contract_id, booked.block.key, booked.seller, booked.buyer, booked.kwh, booked.price,
         booked.route, booked.model_dump_json()),
    )
    conn.commit()
    data = {"contract": json.loads(booked.model_dump_json())}
    ledger.append(conn, now.isoformat(), "contract.booked", booked.contract_id, data["contract"])
    for house in (booked.seller, booked.buyer):
        bus.publish(Event(type=ev.CONTRACT_BOOKED, sim_time=now, house=house, data=data))
    return booked


def any_agent_token(token: str | None) -> bool:
    return bool(token) and token in config.AGENT_TOKENS.values()
