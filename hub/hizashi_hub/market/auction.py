"""Gate-closure auction (KERC 4(b), average price). Per transformer first, then across
transformers with open_access=True. Each match -> Contract(route="auction") signed by the market."""
from hizashi_shared.models import Offer


def clear(asks: list[Offer], bids: list[Offer]) -> list[tuple[Offer, Offer, float, float]]:
    """(ask, bid, kwh, price) matches; see section 6.4 for the reference code."""
    raise NotImplementedError("TODO(R2.1, Anurag)")
