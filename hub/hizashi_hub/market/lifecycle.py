"""Per-block actions on state changes (section 6.2). The clock already computes and
publishes the states (hizashi_shared.blocks.state_at); register `on_block_state` with
clock.get().on_block_state to act on them.

GATE_CLOSED: wallets refuse new offers; agents post leftover orders within 1 sim minute;
then run the auction. SETTLED: settle every contract. Outage overlapping a block sets
outage=True (no penalties, KERC 5(c)(iii)).
"""
from hizashi_shared.models import BlockRef


async def on_block_state(ref: BlockRef, old: str | None, new: str) -> None:
    raise NotImplementedError("TODO(R2.1, Anurag)")
