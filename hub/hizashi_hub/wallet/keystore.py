"""Load private keys from keys/ (base64 seeds). Only wallet/, market/ and sim/meters.py call this."""
from functools import lru_cache
from pathlib import Path

from nacl.signing import SigningKey

from hizashi_shared import config, crypto


@lru_cache(maxsize=None)
def _load(path: str) -> SigningKey:
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"{p} missing: run python scripts/gen_keys.py")
    return crypto.load_key(p)


def wallet_key(house: str) -> SigningKey:
    return _load(str(config.KEYS_DIR / f"{house}.wallet.key"))


def meter_key(house: str) -> SigningKey:
    return _load(str(config.KEYS_DIR / f"{house}.meter.key"))


def market_key() -> SigningKey:
    return _load(str(config.KEYS_DIR / "market.key"))
