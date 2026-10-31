"""Per-contract settlement (KERC 8(g)), section 6.5.

Seller's metered export in the block is shared across its contracts by size;
d = min(share, q), s = q - d.  buyer_pays = (p + F) q;  seller_penalty = s (R - p)
(0 if outage);  seller_net = p d - seller_penalty;  fee = F q.
"""
from hizashi_shared.models import Contract, Settlement


def settle_block(contracts: list[Contract], seller_export_kwh: dict[str, float], outage: bool,
                 retail: float, fee: float) -> list[Settlement]:
    raise NotImplementedError("TODO(R2.3, Jiten)")
