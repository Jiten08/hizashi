"""Console attack demos (N3) that the hub runs itself.

rogue_seller: an outsider sends House 14's agent a real A2A ask that claims to be House 16,
signed with a key House 16's wallet never had. The agent checks the signature against the
registry, refuses, and reports to the guard (guard.flag).
"""
import logging
import uuid
from datetime import datetime

import httpx
from a2a.client import ClientConfig, create_client
from a2a.helpers import get_data_parts, new_data_part
from a2a.types import Message, Role, SendMessageRequest
from nacl.signing import SigningKey

from hizashi_shared import blocks, crypto
from hizashi_shared.models import BlockRef, HouseInfo, Offer

log = logging.getLogger("hizashi.attacks")

FAKE_PRICE = 3.20          # a too-good-to-be-true price, to tempt the buyer


def forged_ask(target: str, claim: str, ref: BlockRef, key: SigningKey | None = None) -> Offer:
    offer = Offer(offer_id=str(uuid.uuid4()), negotiation_id=str(uuid.uuid4()), block=ref, side="ask",
                  house=claim, to=target, kwh=0.5, price=FAKE_PRICE, round=0,  # type: ignore[arg-type]
                  expires_at=blocks.gate_close(ref), nonce=str(uuid.uuid4()))
    return offer.model_copy(update={"signature": crypto.sign(offer, key or SigningKey.generate())})


def next_open_block(block_states: dict[str, str], now: datetime) -> BlockRef:
    keys = sorted(k for k, s in block_states.items() if s == "OPEN")
    return blocks.parse_key(keys[0]) if keys else blocks.block_of(now)


async def fake_seller(houses: dict[str, HouseInfo], block_states: dict[str, str], now: datetime,
                      target: str = "h14", claim: str = "h16") -> dict:
    """Send the forged ask; returns what the target agent answered."""
    offer = forged_ask(target, claim, next_open_block(block_states, now))
    msg = Message(message_id=str(uuid.uuid4()), role=Role.ROLE_USER,
                  parts=[new_data_part({"type": "ask", "offer": offer.model_dump(mode="json")})])
    try:
        async with httpx.AsyncClient(timeout=10) as http:
            client = await create_client(houses[target].agent_url, client_config=ClientConfig(streaming=False, httpx_client=http))
            reply: dict = {}
            async for resp in client.send_message(SendMessageRequest(message=msg)):
                if resp.HasField("task"):
                    parts = get_data_parts(resp.task.status.message.parts)
                    reply = parts[0] if parts else {}
    except Exception as e:
        log.warning("fake_seller: %s's agent unreachable (%s)", target, e)
        return {"status": "error", "reason": f"House {target[1:]}'s agent isn't reachable: {type(e).__name__}"}
    log.info("fake_seller: %s answered %s", target, reply)
    return {"status": "sent", "target": target, "claimed": claim, "reply": reply}
