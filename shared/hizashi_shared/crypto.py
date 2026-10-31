"""Canonical JSON + Ed25519 sign/verify (PyNaCl).

Always call canonical()/verify() on a pydantic model, never on a raw dict from A2A:
A2A data parts turn ints into floats, which changes the JSON. Re-parse with
Offer.model_validate(d) / Contract.model_validate(d) first.
"""
import base64
import json
from pathlib import Path

from nacl.signing import SigningKey, VerifyKey

SIG_FIELDS = {"signature", "seller_sig", "buyer_sig", "market_sig"}


def canonical(model) -> bytes:
    data = model.model_dump(mode="json", exclude=SIG_FIELDS)
    return json.dumps(data, sort_keys=True, separators=(",", ":")).encode()


def sign(model, key: SigningKey) -> str:
    return base64.b64encode(key.sign(canonical(model)).signature).decode()


def verify(model, sig: str | None, pub_b64: str) -> bool:
    if not sig:
        return False
    try:
        VerifyKey(base64.b64decode(pub_b64)).verify(canonical(model), base64.b64decode(sig))
        return True
    except Exception:
        return False


def pub_b64(key: SigningKey) -> str:
    return base64.b64encode(bytes(key.verify_key)).decode()


def seed_b64(key: SigningKey) -> str:
    return base64.b64encode(bytes(key)).decode()


def new_key() -> SigningKey:
    return SigningKey.generate()


def load_key(path: str | Path) -> SigningKey:
    """Load a signing key from a file holding its base64 seed."""
    return SigningKey(base64.b64decode(Path(path).read_text().strip()))
