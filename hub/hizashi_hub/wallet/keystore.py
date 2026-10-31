"""Load private keys from keys/ (base64 seeds)."""
from nacl.signing import SigningKey


def wallet_key(house: str) -> SigningKey:
    raise NotImplementedError("TODO(R1.1, Jiten)")


def meter_key(house: str) -> SigningKey:
    raise NotImplementedError("TODO(R2.2, Jiten)")


def market_key() -> SigningKey:
    raise NotImplementedError("TODO(R1.6, Jiten)")
