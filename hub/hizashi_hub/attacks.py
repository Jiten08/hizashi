"""The console's one attack demo: an impostor seller.

Someone claiming to be House 16 enters the street market with an ask at ₹40/kWh, signed with a key
House 16's wallet never had (they can copy a name, not a private key). The market checks every
seller's signature against the registered wallet key before taking the order, so the impostor is
refused and its key blacklisted on the spot; every later try from that key bounces at the door.
"""
import uuid
from datetime import datetime

from nacl.signing import SigningKey

from hizashi_shared import blocks, crypto
from hizashi_shared.models import BlockRef, Offer

IMPOSTOR_PRICE = 40.0
IMPOSTOR_KWH = 0.5

_key: SigningKey | None = None       # one impostor per hub run, so a second try shows the blacklist


def impostor_key() -> SigningKey:
    global _key
    if _key is None:
        _key = SigningKey.generate()
    return _key


def next_open_block(block_states: dict[str, str], now: datetime) -> BlockRef:
    keys = sorted(k for k, s in block_states.items() if s == "OPEN")
    return blocks.parse_key(keys[0]) if keys else blocks.block_of(now)


def impostor_ask(claim: str, ref: BlockRef, key: SigningKey) -> Offer:
    """A street-wide ask (to=None) in `claim`'s name, signed with the impostor's own key."""
    offer = Offer(offer_id=str(uuid.uuid4()), negotiation_id=f"market-{ref.key}", block=ref, side="ask",
                  house=claim, to=None, kwh=IMPOSTOR_KWH, price=IMPOSTOR_PRICE, round=0,  # type: ignore[arg-type]
                  expires_at=blocks.block_start(ref), nonce=str(uuid.uuid4()))
    return offer.model_copy(update={"signature": crypto.sign(offer, key)})


def pubkey(key: SigningKey) -> str:
    return crypto.pub_b64(key)
