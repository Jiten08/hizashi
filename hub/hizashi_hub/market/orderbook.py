"""Leftover market orders (Offer with to=None) per block, accepted only while GATE_CLOSED."""
from hizashi_shared.models import Offer


class OrderBook:
    def add(self, offer: Offer) -> None:
        raise NotImplementedError("TODO(R2.1, Anurag)")

    def orders(self, block_key: str) -> tuple[list[Offer], list[Offer]]:
        """(asks, bids) for one block."""
        raise NotImplementedError("TODO(R2.1, Anurag)")
