"""Make h16 and h18 post identical asks for 4 blocks in a row (KERC 5(a)(ii)).

    python scripts/attack_collusion.py [--hub http://127.0.0.1:8000] [--price 4.80] [--kwh 0.50] [--start-block 30]

This simulates price coordination between two rooftop solar owners (h16 and h18)
posting identical ask prices across 4 consecutive blocks to test the market collusion guard.
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

from hizashi_shared import blocks, config, crypto
from hizashi_shared.models import BlockRef, Offer

DEFAULT_COLLUSION_PRICE = 4.80
DEFAULT_COLLUSION_KWH = 0.50
DEFAULT_NUM_BLOCKS = 4
DEFAULT_DELAY = 0.3


def get_wallet_key(house: str) -> SigningKey:
    """Load the house's wallet signing key from disk, or generate in-memory if absent."""
    key_path = config.KEYS_DIR / f"{house}.wallet.key"
    if key_path.exists():
        try:
            return crypto.load_key(key_path)
        except Exception:
            pass
    return crypto.new_key()


def build_collusion_order(
    house: str,
    block: BlockRef,
    price: float = DEFAULT_COLLUSION_PRICE,
    kwh: float = DEFAULT_COLLUSION_KWH,
    key: SigningKey | None = None,
) -> dict[str, Any]:
    """Build a market order payload (Offer with to=None) for house at specified price and block.

    The payload conforms to both Pydantic's Offer model and the task's expected order structure.
    """
    signing_key = key or get_wallet_key(house)
    expires_at = blocks.gate_close(block)

    offer_model = Offer(
        offer_id=str(uuid.uuid4()),
        negotiation_id=str(uuid.uuid4()),
        block=block,
        side="ask",
        house=house,  # type: ignore[arg-type]
        to=None,
        kwh=float(kwh),
        price=float(price),
        round=0,
        expires_at=expires_at,
        nonce=uuid.uuid4().hex,
        signature=None,
    )
    sig = crypto.sign(offer_model, signing_key)
    signed_offer = offer_model.model_copy(update={"signature": sig})

    offer_dict = signed_offer.model_dump(mode="json")
    offer_dict["is_bid"] = False

    return {"offer": offer_dict}


async def post_market_order(
    client: httpx.AsyncClient,
    hub_url: str,
    house: str,
    payload: dict[str, Any],
) -> dict[str, Any]:
    """Send POST /api/market/orders with the house's agent authorization."""
    token = config.AGENT_TOKENS.get(house, f"dev-{house}")
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }
    url = f"{hub_url.rstrip('/')}/api/market/orders"

    try:
        resp = await client.post(url, json=payload, headers=headers)
        data = resp.json() if resp.status_code in (200, 400, 401, 422) else {"raw": resp.text}
        return {
            "status_code": resp.status_code,
            "response": data,
            "ok": resp.status_code == 200 and data.get("status") == "queued",
        }
    except Exception as err:
        return {
            "status_code": 0,
            "response": {"error": str(err)},
            "ok": False,
        }


async def run_collusion_attack(
    hub_url: str = "http://127.0.0.1:8000",
    start_block_idx: int | None = None,
    price: float = DEFAULT_COLLUSION_PRICE,
    kwh: float = DEFAULT_COLLUSION_KWH,
    num_blocks: int = DEFAULT_NUM_BLOCKS,
    delay: float = DEFAULT_DELAY,
) -> dict[str, Any]:
    """Execute the KERC 5(a)(ii) price coordination attack across h16 and h18."""
    hub_url = hub_url.rstrip("/")

    # Discover day and starting block index from hub state if not provided
    day = config.SIM_DAY
    start_idx = start_block_idx

    async with httpx.AsyncClient(timeout=5.0) as http:
        try:
            s_resp = await http.get(f"{hub_url}/api/state")
            if s_resp.status_code == 200:
                s_data = s_resp.json()
                sim_time_str = s_data.get("sim_time")
                if sim_time_str:
                    day = sim_time_str.split("T")[0]
                if start_idx is None:
                    # Look for first GATE_CLOSED or OPEN block, else default to 32 (08:00)
                    blocks_map = s_data.get("blocks", {})
                    for idx in blocks.TRADABLE:
                        key = f"{day}#{idx:02d}"
                        if blocks_map.get(key) in ("GATE_CLOSED", "OPEN"):
                            start_idx = idx
                            break
        except Exception:
            pass

    if start_idx is None:
        start_idx = 32  # 08:00 AM block (within tradable range 24..75)

    print(f"[collusion] Starting attack against hub at {hub_url}")
    print(f"[collusion] Target blocks: {start_idx} to {start_idx + num_blocks - 1} (Day: {day})")
    print(f"[collusion] Coordinating houses: h16 and h18 with identical ask price = Rs.{price:.2f}, kWh = {kwh}")

    results: list[dict[str, Any]] = []

    async with httpx.AsyncClient(timeout=10.0) as client:
        for offset in range(num_blocks):
            b_idx = start_idx + offset
            block = BlockRef(day=day, index=b_idx)
            block_label = blocks.label(block)
            print(f"\n[collusion] --- Block #{b_idx:02d} ({block_label}) ---")

            for house in ("h16", "h18"):
                order_payload = build_collusion_order(house, block, price=price, kwh=kwh)
                offer_id = order_payload["offer"]["offer_id"]

                res = await post_market_order(client, hub_url, house, order_payload)
                status_str = "SUCCESS" if res["ok"] else f"FAILED/REFUSED ({res['status_code']})"
                print(f"  [{house}] Post ask Rs.{price:.2f} ({kwh} kWh) -> {status_str}: {res['response']}")

                results.append({
                    "house": house,
                    "block_index": b_idx,
                    "offer_id": offer_id,
                    "result": res,
                })

                if delay > 0:
                    await asyncio.sleep(delay)

        # Check for guard flags triggered at hub
        flag_seen = False
        flags_found: list[dict[str, Any]] = []
        try:
            state_resp = await client.get(f"{hub_url}/api/state")
            if state_resp.status_code == 200:
                flags = state_resp.json().get("flags", [])
                for f in flags:
                    kind = str(f.get("kind", "")).lower()
                    detail = str(f.get("detail", "")).lower()
                    if "collusion" in kind or "coordination" in kind or "5(a)" in kind or "collusion" in detail or "price" in detail:
                        flag_seen = True
                        flags_found.append(f)
        except Exception as e:
            print(f"[collusion] Could not query hub state for guard flags: {e}")

    print("\n[collusion] Attack execution completed.")
    if flag_seen:
        print(f"[collusion] Guard flag TRIGGERED! Found: {flags_found}")
    else:
        print("[collusion] Guard check: No active collusion guard flag seen in hub state (verification depends on backend guard module).")

    return {
        "success": True,
        "blocks_posted": num_blocks,
        "total_orders": len(results),
        "flag_seen": flag_seen,
        "orders": results,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Coordinate identical asks from h16 and h18 across 4 consecutive blocks.")
    parser.add_argument("--hub", default=config.HUB_URL, help=f"Hub URL (default {config.HUB_URL})")
    parser.add_argument("--price", type=float, default=DEFAULT_COLLUSION_PRICE, help=f"Identical ask price in Rs/kWh (default {DEFAULT_COLLUSION_PRICE})")
    parser.add_argument("--kwh", type=float, default=DEFAULT_COLLUSION_KWH, help=f"Ask kWh per block (default {DEFAULT_COLLUSION_KWH})")
    parser.add_argument("--start-block", type=int, default=None, help="Starting block index (default next active or 32)")
    parser.add_argument("--num-blocks", type=int, default=DEFAULT_NUM_BLOCKS, help=f"Number of consecutive blocks (default {DEFAULT_NUM_BLOCKS})")
    parser.add_argument("--delay", type=float, default=DEFAULT_DELAY, help=f"Delay between requests in seconds (default {DEFAULT_DELAY})")
    args = parser.parse_args()

    result = asyncio.run(
        run_collusion_attack(
            hub_url=args.hub,
            start_block_idx=args.start_block,
            price=args.price,
            kwh=args.kwh,
            num_blocks=args.num_blocks,
            delay=args.delay,
        )
    )
    print(f"\n[collusion] Summary: Posted {result['total_orders']} orders across {result['blocks_posted']} blocks.")


if __name__ == "__main__":
    main()
