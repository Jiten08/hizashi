"""The guard's memory for the day and its flags.

Hooks: the wallet calls `check_ask` before signing an offer (replay, price coordination),
booking calls `check_contract` (wash trades), agents report bad signatures through
/api/guard/report, and `run()` watches every meter reading. Each finding is a flag: a row in
`flags`, a ledger entry and a `guard.flag` event (street-wide, naming the houses).
"""
import json
import logging
import sqlite3
from datetime import datetime

from hizashi_shared import blocks, crypto
from hizashi_shared import events as ev
from hizashi_shared.models import Contract, Event, HouseInfo, MeterReading, Offer

from .. import bus
from ..settlement import ledger
from . import rules

log = logging.getLogger("hizashi.guard")

TITLES = {
    "bad_signature": "Forged offer refused",
    "impossible_reading": "Impossible meter reading",
    "wash_trade": "Wash trade refused",
    "collusion": "Price-fixing caught",
    "replay": "Replay refused",
    "impostor": "Impostor blacklisted",
}


class GuardRefusal(Exception):
    """Refused by the guard, with a plain-sentence reason (already flagged)."""


class Guard:
    def __init__(self, houses: dict[str, HouseInfo]) -> None:
        self.houses = houses                 # live dict (onboarding can change a roof)
        self.blacklist: dict[str, dict] = {}  # signing key -> who it pretended to be (kept across days)
        self.reset()

    def reset(self) -> None:
        self.asks: dict[str, dict[str, list[float]]] = {}       # block key -> seller -> ask prices
        self.nonces: dict[str, str] = {}                        # offer nonce -> offer_id
        self.meter_seq: dict[str, int] = {}
        self.colluders: dict[frozenset[str], float] = {}        # pair -> price they fixed
        self._raised: set[tuple] = set()                        # one flag per finding

    # --- flags ------------------------------------------------------------------------------

    def flag(self, conn: sqlite3.Connection, kind: str, houses: list[str], text: str, now: datetime,
             detail: dict | None = None, once: tuple | None = None) -> dict | None:
        if once is not None:
            if (kind, *once) in self._raised:
                return None
            self._raised.add((kind, *once))
        data = {"kind": kind, "title": TITLES.get(kind, "Guard flag"), "text": text, "houses": houses,
                "detail": detail or {}, "ts": now.isoformat()}
        conn.execute("INSERT INTO flags (ts, kind, houses, detail) VALUES (?, ?, ?, ?)",
                     (now.isoformat(), kind, json.dumps(houses), json.dumps(data)))
        conn.commit()
        ledger.append(conn, now.isoformat(), "guard.flag", kind, {"houses": houses, "kind": kind, "text": text})
        bus.publish(Event(type=ev.GUARD_FLAG, sim_time=now, data=data))
        log.warning("guard: %s: %s", kind, text)
        return data

    # --- sellers entering the market -------------------------------------------------------

    def screen_seller(self, conn: sqlite3.Connection, offer: Offer, presented_key: str | None,
                      now: datetime) -> str | None:
        """None if the order really comes from the house it names. Otherwise a refusal: a key the guard
        has blacklisted bounces at once; a signature that isn't the house's registered wallet gets the
        sender's key blacklisted and one street-wide flag (the real house isn't blamed)."""
        name = f"House {offer.house[1:]}"
        if presented_key and presented_key in self.blacklist:
            return f"Blacklisted: this key already pretended to be {self.blacklist[presented_key]['claimed']}."
        info = self.houses.get(offer.house)
        if info is not None and crypto.verify(offer, offer.signature, info.wallet_pubkey or ""):
            return None
        reason = (f"A seller claiming to be {name} offered {offer.kwh:.2f} kWh at ₹{offer.price:.2f}, but the "
                  f"signature isn't {name}'s wallet. Blacklisted on entry; nothing traded.")
        if presented_key:
            self.blacklist[presented_key] = {"claimed": name, "ts": now.isoformat()}
        self.flag(conn, "impostor", [], reason, now,
                  {"claimed": offer.house, "price": offer.price, "kwh": offer.kwh, "key": presented_key},
                  once=(presented_key or offer.offer_id,))
        return reason

    # --- offers (wallet, before signing) ----------------------------------------------------

    def check_ask(self, conn: sqlite3.Connection, offer: Offer, now: datetime) -> None:
        """Raise GuardRefusal (after flagging) instead of signing a replayed or price-fixed offer."""
        reasons = rules.check_offer(offer, self.nonces.get(offer.nonce))
        if reasons:
            self.flag(conn, "replay", [offer.house], reasons[0], now, {"offer_id": offer.offer_id},
                      once=(offer.nonce,))
            raise GuardRefusal(reasons[0])
        if offer.side == "ask":
            for pair, price in self.colluders.items():
                if offer.house in pair and offer.price == price:
                    other = next(h for h in pair if h != offer.house)
                    raise GuardRefusal(f"House {offer.house[1:]} and House {other[1:]} were caught fixing the price at "
                                       f"₹{price:.2f} (KERC 5(a)(ii)), so the market won't sign that ask.")
            asks = {k: {h: list(p) for h, p in v.items()} for k, v in self.asks.items()}
            asks.setdefault(offer.block.key, {}).setdefault(offer.house, []).append(offer.price)
            found = rules.collusion(asks, offer.house)
            if found:
                other, price, keys = found
                self.colluders[frozenset((offer.house, other))] = price
                pair = sorted((offer.house, other))
                text = (f"House {pair[0][1:]} and House {pair[1][1:]} both held their ask at ₹{price:.2f} in "
                        f"{len(keys)} blocks without moving. That's price coordination (KERC 5(a)(ii)); "
                        "their asks at that price are refused for the rest of the day.")
                self.flag(conn, "collusion", pair, text, now, {"price": price, "blocks": keys})
                raise GuardRefusal(text)

    def signed(self, offer: Offer) -> None:
        """Remember a signed offer (its nonce, and its price if it's an ask)."""
        self.nonces[offer.nonce] = offer.offer_id
        if offer.side == "ask":
            self.asks.setdefault(offer.block.key, {}).setdefault(offer.house, []).append(offer.price)

    # --- contracts (booking) ----------------------------------------------------------------

    def check_contract(self, conn: sqlite3.Connection, contract: Contract, now: datetime) -> None:
        rows = conn.execute("SELECT json FROM contracts WHERE block_key = ?", (contract.block.key,)).fetchall()
        booked = [Contract.model_validate_json(r["json"]) for r in rows]
        reasons = rules.check_contract(contract, booked)
        if reasons:
            self.flag(conn, "wash_trade", sorted({contract.seller, contract.buyer}), reasons[0], now,
                      {"contract_id": contract.contract_id}, once=(contract.contract_id,))
            raise GuardRefusal(reasons[0])

    # --- meters -----------------------------------------------------------------------------

    def check_reading(self, conn: sqlite3.Connection, reading: MeterReading, now: datetime) -> list[str]:
        info = self.houses.get(reading.house)
        if info is None:
            return []
        reasons = rules.check_reading(reading, info, self.meter_seq.get(reading.house))
        self.meter_seq[reading.house] = max(reading.seq, self.meter_seq.get(reading.house, 0))
        for r in reasons:
            kind = "replay" if "again" in r else "impossible_reading"
            # One flag per house and kind per block, not one a minute.
            self.flag(conn, kind, [reading.house], r, now, {"seq": reading.seq},
                      once=(reading.house, blocks.block_of(reading.ts).key))
        return reasons

    async def run(self, conn: sqlite3.Connection) -> None:
        """Bus subscriber: check every meter reading; forget the day on a reset."""
        q = bus.subscribe()
        try:
            while True:
                e = await q.get()
                try:
                    if e.type == ev.METER_READING and e.data.get("reading"):
                        self.check_reading(conn, MeterReading.model_validate(e.data["reading"]), e.sim_time)
                    elif e.type == ev.CLOCK_TICK and e.data.get("reset"):
                        self.reset()
                except Exception:
                    log.exception("guard failed on %s", e.type)
        finally:
            bus.unsubscribe(q)


_guard: Guard | None = None


def init(houses: dict[str, HouseInfo]) -> Guard:
    global _guard
    _guard = Guard(houses)
    return _guard


def get() -> Guard | None:
    """None until the hub starts it (tests that don't need the guard skip it)."""
    return _guard
