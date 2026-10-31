"""Leftover market orders (Offer with to=None) per block, accepted only while GATE_CLOSED
and before that block's auction has run."""
from collections import defaultdict

from hizashi_shared.models import Offer


class OrderBookClosed(Exception):
    pass


class OrderBook:
    def __init__(self) -> None:
        self._orders: dict[str, dict[str, Offer]] = defaultdict(dict)
        self._cleared: set[str] = set()

    def add(self, offer: Offer) -> None:
        key = offer.block.key
        if key in self._cleared:
            raise OrderBookClosed(f"The auction for this block has already run.")
        if offer.offer_id in self._orders[key]:
            raise OrderBookClosed("This order is already in the book.")
        self._orders[key][offer.offer_id] = offer

    def orders(self, block_key: str) -> tuple[list[Offer], list[Offer]]:
        """(asks, bids) for one block."""
        book = self._orders.get(block_key, {}).values()
        return [o for o in book if o.side == "ask"], [o for o in book if o.side == "bid"]

    def close(self, block_key: str) -> tuple[list[Offer], list[Offer]]:
        """Stop taking orders for the block and hand back what's in it."""
        self._cleared.add(block_key)
        return self.orders(block_key)

    def is_closed(self, block_key: str) -> bool:
        return block_key in self._cleared

    def reset(self) -> None:
        self._orders.clear()
        self._cleared.clear()
