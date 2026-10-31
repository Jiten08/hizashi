"""Houses, transformers, agent URLs, public keys."""
from hizashi_shared.models import HouseInfo

from .. import state as hub_state


def houses() -> dict[str, HouseInfo]:
    return hub_state.get().houses


def wallet_pubkey(house: str) -> str:
    """KeyError for an unknown house; ValueError if keys haven't been generated."""
    key = houses()[house].wallet_pubkey
    if not key:
        raise ValueError(f"{house} has no wallet key; run scripts/gen_keys.py")
    return key


def same_transformer(a: str, b: str) -> bool:
    h = houses()
    return h[a].transformer == h[b].transformer
