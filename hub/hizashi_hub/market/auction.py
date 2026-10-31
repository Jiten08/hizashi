"""Gate-closure auction (KERC 4(b), average price). Per transformer first, then across
transformers with open_access=True. Each match -> Contract(route="auction") signed by the market."""
from hizashi_shared.models import Offer

Match = tuple[Offer, Offer, float, float]


def clear_with_leftovers(asks: list[Offer], bids: list[Offer]) -> tuple[list[Match], list[Offer], list[Offer]]:
    """Section 6.4's reference loop on copies: (matches, unsold asks, unmet bids)."""
    asks = sorted((o.model_copy() for o in asks), key=lambda o: (o.price, o.offer_id))
    bids = sorted((o.model_copy() for o in bids), key=lambda o: (-o.price, o.offer_id))
    matches: list[Match] = []
    while asks and bids and bids[0].price >= asks[0].price:
        a, b = asks[0], bids[0]
        q = round(min(a.kwh, b.kwh), 3)
        price = round((a.price + b.price) / 2, 2)
        matches.append((a, b, q, price))
        a.kwh -= q
        b.kwh -= q
        if a.kwh < 0.01:
            asks.pop(0)
        if b.kwh < 0.01:
            bids.pop(0)
    return matches, asks, bids


def clear(asks: list[Offer], bids: list[Offer]) -> list[Match]:
    """(ask, bid, kwh, price) matches; unsold asks -> BESCOM at buyback; unmet bids -> BESCOM at R."""
    return clear_with_leftovers(asks, bids)[0]
