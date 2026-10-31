"""Houses, transformers, agent URLs, public keys."""
from hizashi_shared.models import HouseInfo


def houses() -> dict[str, HouseInfo]:
    raise NotImplementedError("TODO(R1.6, Anurag)")


def wallet_pubkey(house: str) -> str:
    raise NotImplementedError("TODO(R1.6, Anurag)")


def same_transformer(a: str, b: str) -> bool:
    raise NotImplementedError("TODO(R1.6, Anurag)")
