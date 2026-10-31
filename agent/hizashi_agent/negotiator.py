"""Opening prices, concession curve and accept rule (section 7.5). Pure functions.

    seller_open  = R - SELLER_OPEN_DISCOUNT            (5.40)
    seller_limit = max(min_sell_price, buyback + 0.10)
    buyer_open   = BUYER_OPEN_PRICE                     (4.00)
    buyer_limit  = min(max_buy_price, R - F)

    ask(r) = seller_open - (seller_open - seller_limit) * (r / (MAX_ROUNDS-1)) ** (1/beta)
    bid(r) = buyer_open  + (buyer_limit - buyer_open)  * (r / (MAX_ROUNDS-1)) ** (1/beta)

Accept the other side's latest price as soon as it's at least as good as your own next offer.
"""
from dataclasses import dataclass, field
from typing import Literal

from hizashi_shared import config


def seller_open(retail: float = config.RETAIL_ENERGY_CHARGE, discount: float = config.SELLER_OPEN_DISCOUNT) -> float:
    return round(retail - discount, 2)


def seller_limit(min_sell_price: float, buyback: float | None) -> float:
    if buyback is None:
        return round(min_sell_price, 2)
    return round(max(min_sell_price, buyback + 0.10), 2)


def buyer_open(open_price: float = config.BUYER_OPEN_PRICE) -> float:
    return round(open_price, 2)


def buyer_limit(max_buy_price: float, retail: float = config.RETAIL_ENERGY_CHARGE,
                fee: float = config.FEE_PER_KWH) -> float:
    return round(min(max_buy_price, retail - fee), 2)


def _progress(r: int, max_rounds: int, beta: float) -> float:
    r = min(max(r, 0), max_rounds - 1)
    return (r / (max_rounds - 1)) ** (1 / beta)


def ask_price(r: int, limit: float, open_: float | None = None,
              max_rounds: int = config.MAX_ROUNDS, beta: float = config.CONCESSION_BETA) -> float:
    o = seller_open() if open_ is None else open_
    return round(o - (o - limit) * _progress(r, max_rounds, beta), 2)


def bid_price(r: int, limit: float, open_: float | None = None,
              max_rounds: int = config.MAX_ROUNDS, beta: float = config.CONCESSION_BETA) -> float:
    o = buyer_open() if open_ is None else open_
    return round(o + (limit - o) * _progress(r, max_rounds, beta), 2)


def seller_accepts(bid: float, next_round: int, limit: float, **kw) -> bool:
    """Seller takes the buyer's bid if it is >= the seller's own next ask."""
    return round(bid, 2) >= ask_price(next_round, limit, **kw)


def buyer_accepts(ask: float, this_round: int, limit: float, **kw) -> bool:
    """Buyer takes the seller's ask if it is <= the bid it would make this round."""
    return round(ask, 2) <= bid_price(this_round, limit, **kw)


@dataclass
class Haggle:
    asks: list[float] = field(default_factory=list)
    bids: list[float] = field(default_factory=list)
    deal_price: float | None = None
    deal_round: int | None = None
    accepted_by: Literal["buyer", "seller"] | None = None


def simulate(s_limit: float, b_limit: float, max_rounds: int = config.MAX_ROUNDS,
             beta: float = config.CONCESSION_BETA) -> Haggle:
    """Run the protocol locally: seller asks each round, buyer answers. Used by tests
    and as the reference for the A2A negotiation."""
    kw = {"max_rounds": max_rounds, "beta": beta}
    h = Haggle()
    for r in range(max_rounds):
        if h.bids and seller_accepts(h.bids[-1], r, s_limit, **kw):
            h.deal_price, h.deal_round, h.accepted_by = h.bids[-1], r - 1, "seller"
            return h
        ask = ask_price(r, s_limit, **kw)
        h.asks.append(ask)
        if buyer_accepts(ask, r, b_limit, **kw):
            h.deal_price, h.deal_round, h.accepted_by = ask, r, "buyer"
            return h
        h.bids.append(bid_price(r, b_limit, **kw))
    return h
