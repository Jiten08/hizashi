"""Main loop reacting to block states (section 7.6).

PLANNED: forecast the day, post plan windows. OPEN: sellers start negotiations, buyers
answer. GATE_CLOSED: post leftover kWh as a signed market order at the limit price.
DELIVERING: read own meter. SETTLED: read results; after a shortfall shrink promises 10%.
Console command bad_bid (h14): bid at ₹40 for the next OPEN block (the wallet refuses it).
"""
from hizashi_shared.models import Event


class Runtime:
    def __init__(self, house: str) -> None:
        self.house = house

    async def on_event(self, event: Event) -> None:
        raise NotImplementedError("TODO(R1.5, Anurag)")
