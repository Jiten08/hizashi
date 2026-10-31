
"""python scripts/attack_fake_seller.py [--hub http://127.0.0.1:8000] [--target-url http://127.0.0.1:9014/] [--price 9.00] [--kwh 0.40]

The attack impersonates House 16 selling to House 14 with a throwaway in-memory
signing key and an ask price above BESCOM retail tariff (R = ₹5.80/kWh).
Expected outcome: House 14 verifies the signature against the registry and rejects it.
"""
from __future__ import annotations

import argparse
import asyncio
import os
import sys
import uuid
from pathlib import Path
from typing import Any

import httpx
from nacl.signing import SigningKey

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "shared"))
sys.path.insert(0, str(ROOT / "agent"))

from a2a.client import ClientConfig, create_client
from a2a.helpers import get_data_parts, new_data_part
from a2a.types import Message, Role, SendMessageRequest, TaskState
from hizashi_shared import blocks, config, crypto
from hizashi_shared.models import BlockRef, Offer

# Anything above BESCOM retail tariff (R = 5.80 ₹/kWh) is an exorbitant / high price
DEFAULT_HIGH_PRICE = 9.00
DEFAULT_KWH = 0.40


def build_fake_offer(
    block: BlockRef,
    kwh: float = DEFAULT_KWH,
    price: float = DEFAULT_HIGH_PRICE,
    key: SigningKey | None = None,
) -> tuple[Offer, SigningKey]:
    """Pure builder: build an Offer claiming to be from h16 to h14, signed with a throwaway key."""
    ephemeral_key = key or crypto.new_key()
    expires_at = blocks.gate_close(block)

    offer_data = {
        "offer_id": f"fake-{uuid.uuid4().hex[:8]}",
        "negotiation_id": str(uuid.uuid4()),
        "block": block,
        "side": "ask",
        "house": "h16",
        "to": "h14",
        "kwh": float(kwh),
        "price": float(price),
        "round": 0,
        "expires_at": expires_at,
        "nonce": uuid.uuid4().hex,
        "signature": None,
    }
    offer = Offer.model_validate(offer_data)
    sig = crypto.sign(offer, ephemeral_key)
    offer_with_sig = offer.model_copy(update={"signature": sig})
    return offer_with_sig, ephemeral_key


def classify_reply(task_state: str | None, reply_parts: list[dict[str, Any]]) -> tuple[bool, str, int]:
    """Interpret h14's reply.

    Returns (is_rejected, message, exit_code).
    exit_code 0: attack was properly rejected / refused (expected).
    exit_code 1: attack succeeded or was accepted / booked (bug).
    """
    reply = reply_parts[0] if reply_parts else {}
    msg_type = str(reply.get("type", "")).lower()
    reason = str(reply.get("reason", "")).lower()

    # Case 1: Explicit refusal due to bad signature
    if "bad signature" in reason or "signature" in reason:
        return (
            True,
            f"REJECTED: h14 refused the offer claiming h16 (bad signature: '{reply.get('reason')}')",
            0,
        )

    # Case 2: Rejected task state from A2A executor
    if task_state in ("TASK_STATE_REJECTED", "TASK_STATE_FAILED"):
        return (
            True,
            f"REJECTED: h14 rejected the A2A task (state={task_state}, reason='{reply.get('reason', 'unspecified')}')",
            0,
        )

    # Case 3: Refused for other reasons (e.g. block not open, price above buyer limit)
    if msg_type == "refuse":
        return (
            True,
            f"REFUSED: h14 refused the offer (reason='{reply.get('reason', 'unspecified')}')",
            0,
        )

    # Case 4: Acceptance or counter-bid -> attack succeeded (bug)
    if msg_type in ("accept", "bid") or task_state in ("TASK_STATE_COMPLETED", "TASK_STATE_INPUT_REQUIRED"):
        return (
            False,
            f"CRITICAL BUG / ATTACK SUCCEEDED: h14 accepted or bargained with fake seller! (state={task_state}, reply={reply})",
            1,
        )

    # Case 5: No meaningful response
    return (
        False,
        f"UNKNOWN / NO REPLY: task_state={task_state}, reply={reply}",
        1,
    )


async def run_attack(
    hub_url: str = "http://127.0.0.1:8000",
    target_url: str | None = None,
    kwh: float = DEFAULT_KWH,
    price: float = DEFAULT_HIGH_PRICE,
) -> dict[str, Any]:
    """Execute the fake-seller attack against House 14."""
    hub_url = hub_url.rstrip("/")

    # 1. Fetch registry to find h14's agent URL and h16's real public key
    h14_url = target_url or os.environ.get("H14_URL")
    h16_real_pubkey = None

    async with httpx.AsyncClient(timeout=5.0) as http:
        try:
            reg_resp = await http.get(f"{hub_url}/api/registry")
            if reg_resp.status_code == 200:
                houses = reg_resp.json().get("houses", [])
                for h in houses:
                    if h.get("id") == "h14" and not h14_url:
                        h14_url = h.get("agent_url")
                    if h.get("id") == "h16":
                        h16_real_pubkey = h.get("wallet_pubkey")
        except Exception as e:
            print(f"[attack] Note: Could not fetch /api/registry from hub ({e}); using defaults.")

    h14_url = (h14_url or "http://127.0.0.1:9014/").rstrip("/") + "/"

    # 2. Pick current or next open block from hub state
    target_block = BlockRef(day=config.SIM_DAY, index=48)
    async with httpx.AsyncClient(timeout=5.0) as http:
        try:
            state_resp = await http.get(f"{hub_url}/api/state")
            if state_resp.status_code == 200:
                state_data = state_resp.json()
                blocks_map = state_data.get("blocks", {})
                # Look for an OPEN block in tradable range (24..75)
                for b_idx in blocks.TRADABLE:
                    b_key = f"{config.SIM_DAY}#{b_idx:02d}"
                    if blocks_map.get(b_key) == "OPEN":
                        target_block = BlockRef(day=config.SIM_DAY, index=b_idx)
                        break
        except Exception:
            pass

    # 3. Build fake offer signed with in-memory throwaway key
    fake_offer, fake_key = build_fake_offer(target_block, kwh=kwh, price=price)
    fake_pubkey = crypto.pub_b64(fake_key)

    print(f"[attack] Target agent: {h14_url}")
    print(f"[attack] Block: {target_block.key} (gate close: {fake_offer.expires_at})")
    print(f"[attack] Impersonating: h16 -> to: h14 (kwh={fake_offer.kwh}, price=Rs.{fake_offer.price:.2f})")
    print(f"[attack] Real h16 pubkey: {h16_real_pubkey or 'unknown'}")
    print(f"[attack] Fake throwaway pubkey: {fake_pubkey}")

    # 4. Send A2A message to h14
    task_state: str | None = None
    reply_parts: list[dict[str, Any]] = []

    try:
        async with httpx.AsyncClient(timeout=10.0) as http:
            client = await create_client(
                h14_url,
                client_config=ClientConfig(streaming=False, httpx_client=http),
            )
            msg = Message(
                message_id=str(uuid.uuid4()),
                role=Role.ROLE_USER,
                parts=[new_data_part({"type": "ask", "offer": fake_offer.model_dump(mode="json")})],
                task_id="",
                context_id="",
            )
            async for resp in client.send_message(SendMessageRequest(message=msg)):
                task = resp.task if resp.HasField("task") else None
                if task:
                    task_state = TaskState.Name(task.status.state)
                    if task.status and task.status.message:
                        reply_parts.extend(get_data_parts(task.status.message.parts))
    except Exception as e:
        print(f"[attack] Connection to h14 ({h14_url}) failed: {e}")
        return {
            "status": "error",
            "message": f"Connection to h14 failed: {e}",
            "exit_code": 1,
            "flag_seen": False,
            "offer": fake_offer.model_dump(mode="json"),
        }

    # 5. Classify the outcome
    is_rejected, summary_line, exit_code = classify_reply(task_state, reply_parts)
    print(summary_line)

    # 6. Check if hub logged a guard flag
    flag_seen = False
    try:
        async with httpx.AsyncClient(timeout=3.0) as http:
            s_resp = await http.get(f"{hub_url}/api/state")
            if s_resp.status_code == 200:
                flags = s_resp.json().get("flags", [])
                for f in flags:
                    if f.get("kind") == "bad_signature":
                        detail = str(f.get("detail", ""))
                        if "h16" in detail or fake_offer.offer_id in detail:
                            flag_seen = True
                            break
    except Exception:
        pass

    if flag_seen:
        print("[attack] Guard check: Flag 'bad_signature' logged at hub.")
    else:
        print("[attack] Guard check: No 'bad_signature' flag seen in hub state (or hub offline).")

    return {
        "status": "rejected" if is_rejected else "accepted",
        "message": summary_line,
        "exit_code": exit_code,
        "flag_seen": flag_seen,
        "offer": fake_offer.model_dump(mode="json"),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Send an A2A ask claiming to be h16 with a fake key.")
    parser.add_argument("--hub", default=config.HUB_URL, help="Hub URL (default http://127.0.0.1:8000)")
    parser.add_argument("--target-url", default=None, help="House 14 agent URL override")
    parser.add_argument("--kwh", type=float, default=DEFAULT_KWH, help=f"Ask kWh (default {DEFAULT_KWH})")
    parser.add_argument("--price", type=float, default=DEFAULT_HIGH_PRICE, help=f"Ask price in Rs/kWh (default {DEFAULT_HIGH_PRICE})")
    args = parser.parse_args()

    result = asyncio.run(
        run_attack(
            hub_url=args.hub,
            target_url=args.target_url,
            kwh=args.kwh,
            price=args.price,
        )
    )
    sys.exit(result["exit_code"])


if __name__ == "__main__":
    main()
