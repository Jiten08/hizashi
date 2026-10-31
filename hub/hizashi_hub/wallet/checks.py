"""The ordered wallet checks (section 6.3); the first failure refuses.

1 token/house  2 not paused  3 block OPEN, expires_at <= gate closure  4 price limit
5 kwh <= max_promise_kwh  6 counterparty allowed  7 daily budget  8 approval

Market orders (to=None) are the one exception to check 3: agents post leftovers after
gate closure, so they need the block GATE_CLOSED instead (the order book refuses them
once the auction has run). Check 8 covers buys only: selling earns, and its price and
size are already bounded by checks 4-5.

Pure functions: no clock, DB or keys. Callers pass the block state lookup, the street
and the sim time. Reasons are plain sentences the phone shows as they are.
"""
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from typing import Literal

from hizashi_shared import blocks, config, crypto
from hizashi_shared.models import BlockRef, Contract, HouseInfo, Mandate, Offer, PlanWindow

BlockStateFn = Callable[[str], str | None]   # block key -> BlockState (None = not in play)
Street = dict[str, HouseInfo]
Side = Literal["sell", "buy"]


@dataclass
class CheckResult:
    status: Literal["ok", "pending", "refused"]
    reason: str | None = None
    check: int | None = None            # which check refused (0 = duplicate / matching rules)
    approval_id: str | None = None

    @property
    def ok(self) -> bool:
        return self.status == "ok"


OK = CheckResult("ok")


def _refuse(check: int, reason: str) -> CheckResult:
    return CheckResult("refused", reason, check)


def _label(street: Street, house: str | None) -> str:
    return street[house].label if house in street else f"house {house}"


def _ist(dt: datetime) -> datetime:
    return dt.replace(tzinfo=config.TZ) if dt.tzinfo is None else dt


def token_ok(house: str, token: str | None, tokens: dict[str, str] | None = None) -> bool:
    expected = (tokens or config.AGENT_TOKENS).get(house)
    return bool(token) and token == expected


# --- checks shared by offers and contracts (2-6) -------------------------------------

def check_paused(mandate: Mandate) -> CheckResult:
    if mandate.paused:
        return _refuse(2, "Trading is paused in your rules, so it was never sent.")
    return OK


def check_block(block: BlockRef, expires_at: datetime | None, block_state_fn: BlockStateFn,
                now: datetime | None, market: bool = False) -> CheckResult:
    state = block_state_fn(block.key)
    gate = blocks.gate_close(block)
    if market:
        if state != "GATE_CLOSED" or (now is not None and _ist(now) >= blocks.block_start(block)):
            shown = (state or "not tradable").replace("_", " ").lower()
            return _refuse(3, f"Market orders for {blocks.label(block)} are only taken between gate closure "
                              f"and the auction (it's {shown}), so it was never sent.")
        return OK
    if state != "OPEN" or (now is not None and _ist(now) >= gate):
        shown = (state or "not tradable").replace("_", " ").lower()
        return _refuse(3, f"The {blocks.label(block)} block isn't open for deals (it's {shown}), so it was never sent.")
    if expires_at is not None and _ist(expires_at) > gate:
        return _refuse(3, f"The offer runs past gate closure at {gate:%H:%M}, so it was never sent.")
    return OK


def check_price(side: Side, price: float, mandate: Mandate) -> CheckResult:
    if side == "buy" and price > mandate.max_buy_price:
        return _refuse(4, f"Tried to buy at ₹{price:.2f}/unit. Your max is ₹{mandate.max_buy_price:.2f}, so it was never sent.")
    if side == "sell" and price < mandate.min_sell_price:
        return _refuse(4, f"Tried to sell at ₹{price:.2f}/unit. Your min is ₹{mandate.min_sell_price:.2f}, so it was never sent.")
    return OK


def check_kwh(kwh: float, mandate: Mandate) -> CheckResult:
    if kwh <= 0:
        return _refuse(5, f"Tried to trade {kwh:.2f} kWh. It has to be more than 0, so it was never sent.")
    if kwh > mandate.max_promise_kwh:
        return _refuse(5, f"Tried to promise {kwh:.2f} kWh in one block. Your max is {mandate.max_promise_kwh:.2f} kWh, so it was never sent.")
    return OK


def check_counterparty(house: str, other: str | None, mandate: Mandate, street: Street) -> CheckResult:
    if other is None:
        return OK                       # market order at gate closure
    if other not in street:
        return _refuse(6, f"{_label(street, other)} isn't on this street, so it was never sent.")
    if other == house:
        return _refuse(6, "Can't trade with your own house, so it was never sent.")
    if mandate.counterparties == "same_transformer" and street[other].transformer != street[house].transformer:
        return _refuse(6, f"{_label(street, other)} isn't on your transformer ({street[house].transformer}), so it was never sent.")
    return OK


def check_budget(side: Side, kwh: float, price: float, mandate: Mandate, spent_today: float = 0.0) -> CheckResult:
    """`spent_today`: ₹ of today's booked contracts where this house is the buyer."""
    if side != "buy":
        return OK
    total = spent_today + kwh * price
    if total > mandate.daily_budget + 1e-9:
        return _refuse(7, f"Buying {kwh:.2f} kWh at ₹{price:.2f} would take today's spending to ₹{total:.2f}. "
                          f"Your daily budget is ₹{mandate.daily_budget:.2f}, so it was never sent.")
    return OK


def covering_window(block: BlockRef, side: Side, plans: list[PlanWindow]) -> PlanWindow | None:
    return next((w for w in plans if w.side == side and w.day == block.day
                 and w.first_index <= block.index <= w.last_index), None)


def window_label(w: PlanWindow) -> str:
    start = blocks.block_start(BlockRef(day=w.day, index=w.first_index))
    end = blocks.block_end(BlockRef(day=w.day, index=w.last_index))
    return f"{start:%H:%M}–{end:%H:%M}"


def check_approval(side: Side, kwh: float, price: float, block: BlockRef, mandate: Mandate,
                   plans: list[PlanWindow] | None = None, allow_pending: bool = True) -> CheckResult:
    """Buys only. A pending or declined plan window refuses; an approved/auto one passes.
    Outside any window, a buy worth more than approve_above waits for the owner (offers only)."""
    if side != "buy":
        return OK
    w = covering_window(block, side, plans or [])
    if w is not None:
        if w.status == "pending":
            return _refuse(8, f"Waiting for your OK on the {window_label(w)} buy plan, so it was never sent.")
        if w.status == "declined":
            return _refuse(8, f"You declined the {window_label(w)} buy plan, so it was never sent.")
        return OK
    if allow_pending and kwh * price > mandate.approve_above + 1e-9:
        return CheckResult("pending", f"Buying {kwh:.2f} kWh at ₹{price:.2f} is over your ₹{mandate.approve_above:.2f} "
                                      f"limit for deals without asking, so it's waiting for your OK.", 8)
    return OK


def _limits(house: str, side: Side, block: BlockRef, expires_at: datetime | None, price: float,
            kwh: float, other: str | None, mandate: Mandate, block_state_fn: BlockStateFn,
            street: Street, now: datetime | None, *, spent_today: float = 0.0,
            plans: list[PlanWindow] | None = None, market: bool = False,
            allow_pending: bool = True) -> CheckResult:
    """Checks 2-8 in order."""
    for check in (
        lambda: check_paused(mandate),
        lambda: check_block(block, expires_at, block_state_fn, now, market),
        lambda: check_price(side, price, mandate),
        lambda: check_kwh(kwh, mandate),
        lambda: check_counterparty(house, other, mandate, street),
        lambda: check_budget(side, kwh, price, mandate, spent_today),
        lambda: check_approval(side, kwh, price, block, mandate, plans, allow_pending),
    ):
        result = check()
        if not result.ok:
            return result
    return OK


# --- offers -----------------------------------------------------------------------

def check_offer(mandate: Mandate, offer: Offer, block_state_fn: BlockStateFn, street: Street,
                now: datetime | None, *, house: str, token: str | None,
                already_signed: bool = False, tokens: dict[str, str] | None = None,
                spent_today: float = 0.0, plans: list[PlanWindow] | None = None) -> CheckResult:
    if not token_ok(house, token, tokens):
        return _refuse(1, f"This agent isn't allowed to sign for {_label(street, house)}.")
    if offer.house != house:
        return _refuse(1, f"The offer says it's from {_label(street, offer.house)}, but this is {_label(street, house)}'s wallet.")
    if already_signed:
        return _refuse(0, "This offer was already signed.")
    side: Side = "sell" if offer.side == "ask" else "buy"
    return _limits(house, side, offer.block, offer.expires_at, offer.price, offer.kwh, offer.to,
                   mandate, block_state_fn, street, now, spent_today=spent_today, plans=plans,
                   market=offer.to is None)


# --- contracts ----------------------------------------------------------------------

def offer_matches(contract: Contract, offer: Offer, street: Street) -> bool:
    """The contract's terms follow from `offer`, and the offer carries its house's valid signature."""
    if offer.negotiation_id != contract.negotiation_id or offer.block != contract.block:
        return False
    if round(offer.price, 2) != round(contract.price, 2) or contract.kwh > offer.kwh + 1e-9:
        return False
    if offer.side == "ask":
        parties = offer.house == contract.seller and offer.to == contract.buyer
    else:
        parties = offer.house == contract.buyer and offer.to == contract.seller
    pub = street[offer.house].wallet_pubkey if offer.house in street else None
    return parties and bool(pub) and crypto.verify(offer, offer.signature, pub)


def check_contract(mandate: Mandate, contract: Contract, block_state_fn: BlockStateFn, street: Street,
                   now: datetime | None, *, house: str, token: str | None, signed_offers: list[Offer],
                   tokens: dict[str, str] | None = None, spent_today: float = 0.0,
                   plans: list[PlanWindow] | None = None) -> CheckResult:
    """`signed_offers`: offers the wallet signed in contract.negotiation_id, by either side."""
    if not token_ok(house, token, tokens):
        return _refuse(1, f"This agent isn't allowed to sign for {_label(street, house)}.")
    if house not in (contract.seller, contract.buyer):
        return _refuse(1, f"{_label(street, house)} isn't the seller or the buyer in this contract.")
    if contract.seller == contract.buyer:
        return _refuse(0, "The seller and the buyer are the same house.")
    if contract.route != "haggle" or round(contract.fee_per_kwh, 2) != round(config.FEE_PER_KWH, 2):
        return _refuse(0, f"Only haggled contracts with the ₹{config.FEE_PER_KWH:.2f}/kWh fee are signed here.")
    if not any(offer_matches(contract, o, street) for o in signed_offers):
        return _refuse(0, f"No signed offer in this negotiation matches {contract.kwh:.2f} kWh at ₹{contract.price:.2f}, so it was never signed.")
    side: Side = "sell" if house == contract.seller else "buy"
    other = contract.buyer if side == "sell" else contract.seller
    return _limits(house, side, contract.block, None, contract.price, contract.kwh, other,
                   mandate, block_state_fn, street, now, spent_today=spent_today, plans=plans,
                   allow_pending=False)


def needs_open_access(contract: Contract, street: Street) -> bool:
    return street[contract.seller].transformer != street[contract.buyer].transformer


def blocked_text(reason: str) -> str:
    """'BLOCKED · Tried to buy at ₹40.00/unit. Your max is ₹5.50, so it was never sent.'"""
    return f"BLOCKED · {reason}"
