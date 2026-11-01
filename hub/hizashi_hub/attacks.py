"""The console's one attack demo: an outsider tries to sell.

"House 20" isn't on this street's registry (no wallet key on file), yet it walks into the market
with an ask at ₹40/kWh, signed with its own key. The market checks every seller against the
registry before taking an order, so the outsider is refused and its key blacklisted on the spot;
every later try from that key bounces at the door.
"""
import json
import uuid
from datetime import datetime

from nacl.signing import SigningKey

from hizashi_shared import blocks, crypto
from hizashi_shared.models import BlockRef

OUTSIDER = "h20"
OUTSIDER_PRICE = 40.0
OUTSIDER_KWH = 0.5

_key: SigningKey | None = None       # one outsider per hub run, so a second try shows the blacklist


def outsider_key() -> SigningKey:
    global _key
    if _key is None:
        _key = SigningKey.generate()
    return _key


def next_open_block(block_states: dict[str, str], now: datetime) -> BlockRef:
    keys = sorted(k for k, s in block_states.items() if s == "OPEN")
    return blocks.parse_key(keys[0]) if keys else blocks.block_of(now)


def outsider_ask(ref: BlockRef, key: SigningKey, house: str = OUTSIDER) -> dict:
    """A street-wide ask as the raw JSON a seller sends (an Offer can only name registered houses)."""
    ask = {"offer_id": str(uuid.uuid4()), "negotiation_id": f"market-{ref.key}", "block": ref.model_dump(mode="json"),
           "side": "ask", "house": house, "to": None, "kwh": OUTSIDER_KWH, "price": OUTSIDER_PRICE, "round": 0,
           "expires_at": blocks.block_start(ref).isoformat(), "nonce": str(uuid.uuid4())}
    body = json.dumps(ask, sort_keys=True, separators=(",", ":")).encode()
    return {**ask, "signature": key.sign(body).signature.hex()}


def pubkey(key: SigningKey) -> str:
    return crypto.pub_b64(key)
