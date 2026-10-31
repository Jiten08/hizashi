"""Per-block actions on state changes (section 6.2). The clock computes and publishes the
states (hizashi_shared.blocks.state_at); `Lifecycle.on_block_state` and `on_minute` are
registered as clock hooks.

GATE_CLOSED: wallets refuse new offers; agents post leftover orders;
then the auction runs (at the first tick >= gate + AUCTION_AFTER that is also >= AUCTION_REAL_WAIT
real seconds after gate closure, so fast speeds still leave agents time to post; at the
latest when the block starts delivering). SETTLED: settle every contract, update savings.
OPEN: plan approvals still unanswered for windows that have started lapse to `auto`.
Outage overlapping a block sets outage=True on it (no penalties, KERC 5(c)(iii)).
"""
import json
import logging
import sqlite3
import time
import uuid
from datetime import datetime, timedelta

from hizashi_shared import blocks, config
from hizashi_shared import events as ev
from hizashi_shared.models import BlockRef, Contract, Event, HouseInfo, Mandate, Settlement

from .. import bus
from ..settlement import ledger, savings, settle
from ..sim.events import SimEvents
from ..wallet import approvals
from . import auction, booking
from .orderbook import OrderBook

log = logging.getLogger("hizashi.market.lifecycle")

AUCTION_AFTER = timedelta(minutes=5)   # spec says 1; at 300x that is 0.2 s, too short for agents
AUCTION_REAL_WAIT = 2.0                 # seconds


class Lifecycle:
    def __init__(self, conn: sqlite3.Connection, houses: dict[str, HouseInfo], mandates: dict[str, Mandate],
                 orderbook: OrderBook, events: SimEvents) -> None:
        self.conn = conn
        self.houses = houses            # live dicts from hub state
        self.mandates = mandates
        self.orderbook = orderbook
        self.events = events
        self._pending: dict[str, tuple[BlockRef, datetime, float]] = {}

    def reset(self) -> None:
        self._pending.clear()
        self.orderbook.reset()

    # --- clock hooks ----------------------------------------------------------------

    async def on_block_state(self, ref: BlockRef, old: str | None, new: str) -> None:
        if new == "OPEN":
            approvals.lapse_at_open(self.conn, ref, blocks.open_time(ref))
        elif new == "GATE_CLOSED":
            now = blocks.gate_close(ref)
            self._pending[ref.key] = (ref, now + AUCTION_AFTER, time.monotonic())
        elif new == "DELIVERING" and ref.key in self._pending:
            self._pending.pop(ref.key)
            self.run_auction(ref, blocks.block_start(ref))
        elif new == "SETTLED":
            self.settle(ref, blocks.settle_time(ref))

    async def on_minute(self, now: datetime) -> None:
        for key, (ref, due, real) in list(self._pending.items()):
            if now >= due and time.monotonic() - real >= AUCTION_REAL_WAIT:
                self._pending.pop(key)
                self.run_auction(ref, now)

    # --- auction ----------------------------------------------------------------------

    def _street_mode(self, house: str) -> bool:
        m = self.mandates.get(house)
        return bool(m and m.counterparties == "street")

    def run_auction(self, ref: BlockRef, now: datetime) -> list[Contract]:
        asks, bids = self.orderbook.close(ref.key)
        booked: list[Contract] = []
        left_asks, left_bids = [], []
        for tf in sorted({h.transformer for h in self.houses.values()}):
            on = lambda o: self.houses[o.house].transformer == tf
            matches, la, lb = auction.clear_with_leftovers([a for a in asks if on(a)], [b for b in bids if on(b)])
            booked += self._book(ref, matches, now)
            left_asks += la
            left_bids += lb
        # Open access: only houses whose rules allow trading across transformers.
        street = lambda o: self._street_mode(o.house)
        matches, cross_asks, cross_bids = auction.clear_with_leftovers(
            [a for a in left_asks if street(a)], [b for b in left_bids if street(b)])
        booked += self._book(ref, matches, now)
        left = lambda os, cross: [{"house": o.house, "kwh": round(o.kwh, 3)}
                                  for o in [o for o in os if not street(o)] + cross]
        unsold, unmet = left(left_asks, cross_asks), left(left_bids, cross_bids)
        bus.publish(Event(type=ev.MARKET_CLEARED, sim_time=now, data={
            "block": ref.key, "index": ref.index, "orders": len(asks) + len(bids),
            "matches": [{"contract_id": c.contract_id, "seller": c.seller, "buyer": c.buyer, "kwh": c.kwh,
                         "price": c.price, "open_access": c.open_access} for c in booked],
            "unsold": unsold, "unmet": unmet,
        }))
        if asks or bids:
            log.info("auction %s: %d orders -> %d contracts", ref.key, len(asks) + len(bids), len(booked))
        return booked

    def _book(self, ref: BlockRef, matches: list[auction.Match], now: datetime) -> list[Contract]:
        out = []
        for a, b, q, price in matches:
            if a.house == b.house or q < config.MIN_TRADE_KWH / 5:
                continue
            c = Contract(contract_id=str(uuid.uuid4()), negotiation_id=None, block=ref, seller=a.house,
                         buyer=b.house, kwh=q, price=price, route="auction", fee_per_kwh=config.FEE_PER_KWH,
                         open_access=self.houses[a.house].transformer != self.houses[b.house].transformer)
            out.append(booking.record(self.conn, c, now))
        return out

    # --- settlement -------------------------------------------------------------------

    def _block_meter(self, house: str, key: str) -> dict:
        r = self.conn.execute("SELECT export_kwh, outage FROM block_meter WHERE house = ? AND block_key = ?",
                              (house, key)).fetchone()
        return {"export_kwh": r["export_kwh"], "outage": bool(r["outage"])} if r else {"export_kwh": 0.0, "outage": False}

    def settle(self, ref: BlockRef, now: datetime) -> list[Settlement]:
        rows = self.conn.execute("SELECT json FROM contracts WHERE block_key = ? AND status = 'booked'",
                                 (ref.key,)).fetchall()
        contracts = [Contract.model_validate_json(r["json"]) for r in rows]
        if not contracts:
            return []
        start, end = blocks.block_start(ref), blocks.block_end(ref)
        outage = bool(self.events.overlapping(start, end, "outage")) or any(
            self._block_meter(c.seller, ref.key)["outage"] for c in contracts)
        exports = {c.seller: self._block_meter(c.seller, ref.key)["export_kwh"] for c in contracts}
        results = settle.settle_block(contracts, exports, outage, config.RETAIL_ENERGY_CHARGE, config.FEE_PER_KWH)
        for s in results:
            data = json.loads(s.model_dump_json())
            self.conn.execute("INSERT OR REPLACE INTO settlements (contract_id, json) VALUES (?, ?)",
                              (s.contract_id, s.model_dump_json()))
            self.conn.execute("UPDATE contracts SET status = 'settled' WHERE contract_id = ?", (s.contract_id,))
            ledger.append(self.conn, now.isoformat(), "settlement", s.contract_id, data)
            for house in (s.seller, s.buyer):
                bus.publish(Event(type=ev.SETTLEMENT_DONE, sim_time=now, house=house, data={"settlement": data}))
        self.conn.commit()
        self.publish_savings(ref.day, now)
        return results

    def day_settlements(self, day: str) -> list[Settlement]:
        rows = self.conn.execute("SELECT json FROM settlements").fetchall()
        return [s for s in (Settlement.model_validate_json(r["json"]) for r in rows) if s.block.day == day]

    def publish_savings(self, day: str, now: datetime) -> dict[str, dict]:
        all_s = self.day_settlements(day)
        out = {}
        for h, info in self.houses.items():
            out[h] = {**savings.day_savings(h, all_s, info.buyback_rate), "day": day}
            bus.publish(Event(type=ev.SAVINGS_UPDATED, sim_time=now, house=h, data=out[h]))
        return out
