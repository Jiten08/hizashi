"""Per-contract settlement (KERC 8(g)), section 6.5.

Seller's metered export in the block is shared across its contracts by size;
d = min(share, q), s = q - d.  buyer_pays = (p + F) q;  seller_penalty = s (R - p)
(0 if outage);  seller_net = p d - seller_penalty;  fee = F q.
"""
from collections import defaultdict

from hizashi_shared.models import Contract, Settlement


def _r(x: float) -> float:
    return round(x + 0.0, 4)


def settle_block(contracts: list[Contract], seller_export_kwh: dict[str, float], outage: bool,
                 retail: float, fee: float) -> list[Settlement]:
    pledged: dict[str, float] = defaultdict(float)
    for c in contracts:
        pledged[c.seller] += c.kwh
    out = []
    for c in contracts:
        q, p = c.kwh, c.price
        export = max(seller_export_kwh.get(c.seller, 0.0), 0.0)
        share = export * q / pledged[c.seller] if pledged[c.seller] > 0 else 0.0
        d = min(share, q)
        s = max(q - d, 0.0)
        penalty = 0.0 if outage else s * max(retail - p, 0.0)
        out.append(Settlement(
            contract_id=c.contract_id, block=c.block, seller=c.seller, buyer=c.buyer,
            contracted_kwh=_r(q), delivered_kwh=_r(d), shortfall_kwh=_r(s), price=p,
            buyer_pays=_r((p + fee) * q), seller_net=_r(p * d - penalty), seller_penalty=_r(penalty),
            fee=_r(fee * q), outage=outage,
        ))
    return out
