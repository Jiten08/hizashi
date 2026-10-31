"""A2A client side: send asks to neighbours, one negotiation = one A2A task (section 7.3).

Copy the client pattern from agent/examples/negotiation_sample.py (create_client,
SendMessageRequest, task_id/context_id carried across rounds). Re-parse every reply with
Offer.model_validate / Contract.model_validate before verifying signatures.
"""
from __future__ import annotations

import asyncio
import logging
import os
from typing import TYPE_CHECKING
import uuid

import httpx

from a2a.client import ClientConfig, create_client
from a2a.helpers import get_data_parts, new_data_part
from a2a.types import Message, Role, SendMessageRequest, TaskState

from hizashi_shared import blocks, config, crypto
from hizashi_shared.models import BlockRef, Contract, HouseInfo, Offer
from . import negotiator

if TYPE_CHECKING:
    from .hub_client import HubClient

log = logging.getLogger("hizashi.agent.client")


def _verify_sig(model: Offer | Contract, sig: str | None, pub_key: str | None) -> bool:
    if os.environ.get("WALLET_MOCK", "0") in ("1", "true", "True"):
        return True
    if not pub_key:
        return False
    return crypto.verify(model, sig, pub_key)


async def negotiate_sale(
    me: HouseInfo,
    buyer: HouseInfo,
    first_ask: Offer | None = None,
    hub: HubClient | None = None,
    seller_limit: float | None = None,
    remaining_kwh: float | None = None,
    http: httpx.AsyncClient | None = None,
    fixed_price: float | None = None,
) -> Contract | None:
    """Run an A2A negotiation as seller with a neighbouring buyer agent. `fixed_price` (the
    console's collusion demo) asks that price every round instead of conceding."""
    if first_ask is not None:
        block_ref = first_ask.block
        kwh = first_ask.kwh if remaining_kwh is None else remaining_kwh
        nego_id = first_ask.negotiation_id
        start_round = first_ask.round
    else:
        raise ValueError("first_ask or explicit block_ref required")

    s_limit = (
        seller_limit
        if seller_limit is not None
        else negotiator.seller_limit(4.20, me.buyback_rate)
    )

    should_close_http = False
    if http is None:
        http = httpx.AsyncClient(timeout=10.0)
        should_close_http = True

    try:
        client = await create_client(
            buyer.agent_url,
            client_config=ClientConfig(streaming=False, httpx_client=http),
        )
        task_id, context_id = "", ""
        expires_at = blocks.gate_close(block_ref)

        for r in range(start_round, config.MAX_ROUNDS):
            ask_p = fixed_price if fixed_price is not None else negotiator.ask_price(r, s_limit)
            if r == start_round and first_ask.signature:
                signed_offer = first_ask
            else:
                offer = Offer(
                    offer_id=str(uuid.uuid4()),
                    negotiation_id=nego_id,
                    block=block_ref,
                    side="ask",
                    house=me.id,
                    to=buyer.id,
                    kwh=kwh,
                    price=ask_p,
                    round=r,
                    expires_at=expires_at,
                    nonce=str(uuid.uuid4()),
                )
                if hub:
                    sign_res = await hub.sign_offer(offer)
                    if sign_res.get("status") != "signed":
                        log.info("%s sign_offer refused: %s", me.id, sign_res.get("reason"))
                        return None
                    signed_offer = Offer.model_validate(sign_res["offer"])
                else:
                    signed_offer = offer

            msg = Message(
                message_id=str(uuid.uuid4()),
                role=Role.ROLE_USER,
                parts=[new_data_part({"type": "ask", "offer": signed_offer.model_dump(mode="json")})],
                task_id=task_id,
                context_id=context_id,
            )

            task: TaskState | None = None
            reply: dict = {}
            async for resp in client.send_message(SendMessageRequest(message=msg)):
                if resp.HasField("task"):
                    task = resp.task
                    task_id, context_id = task.id, task.context_id
                    parts = get_data_parts(task.status.message.parts)
                    if parts:
                        reply = parts[0]

            if not task:
                log.warning("%s got no task in response from %s", me.id, buyer.id)
                return None

            reply_type = reply.get("type")

            if reply_type == "bid":
                try:
                    bid_offer = Offer.model_validate(reply["offer"])
                except Exception as e:
                    log.warning("%s failed to parse bid offer: %s", me.id, e)
                    return None

                if not _verify_sig(bid_offer, bid_offer.signature, buyer.wallet_pubkey):
                    log.warning("%s: bad signature from %s on bid %s", me.id, buyer.id, bid_offer.offer_id)
                    if hub:
                        await hub.report_guard("bad_signature", {
                            "house": buyer.id,
                            "offer_id": bid_offer.offer_id,
                        })
                    return None

                log.info("%s→%s b%02d r%d ask %.2f / bid %.2f",
                         me.id, buyer.id, block_ref.index, r, ask_p, bid_offer.price)

                dec = negotiator.seller_decide(bid_offer.price, r, s_limit)
                if dec == "accept":
                    contract = Contract(
                        contract_id=str(uuid.uuid4()),
                        negotiation_id=nego_id,
                        block=block_ref,
                        seller=me.id,
                        buyer=buyer.id,
                        kwh=bid_offer.kwh,
                        price=bid_offer.price,
                        route="haggle",
                    )
                    if hub:
                        sign_res = await hub.sign_contract(contract)
                        if sign_res.get("status") != "signed":
                            log.warning("%s failed to sign contract: %s", me.id, sign_res)
                            return None
                        contract = Contract.model_validate(sign_res["contract"])

                    accept_msg = Message(
                        message_id=str(uuid.uuid4()),
                        role=Role.ROLE_USER,
                        parts=[new_data_part({"type": "accept", "contract": contract.model_dump(mode="json")})],
                        task_id=task_id,
                        context_id=context_id,
                    )

                    booked = False
                    async for accept_resp in client.send_message(SendMessageRequest(message=accept_msg)):
                        if accept_resp.HasField("task"):
                            b_parts = get_data_parts(accept_resp.task.status.message.parts)
                            b_reply = b_parts[0] if b_parts else {}
                            if b_reply.get("type") == "booked":
                                booked = True

                    if booked or os.environ.get("WALLET_MOCK", "0") in ("1", "true", "True"):
                        log.info("%s deal with %s booked: %.2f kWh @ ₹%.2f",
                                 me.id, buyer.id, contract.kwh, contract.price)
                        return contract
                    return contract

                # Delay between rounds so humans/screens can follow
                await asyncio.sleep(config.NEGOTIATION_ROUND_DELAY_MS / 1000.0)

            elif reply_type == "accept":
                try:
                    contract = Contract.model_validate(reply["contract"])
                except Exception as e:
                    log.warning("%s failed to parse contract: %s", me.id, e)
                    return None

                if not _verify_sig(contract, contract.buyer_sig, buyer.wallet_pubkey):
                    log.warning("%s: bad buyer_sig from %s on contract %s", me.id, buyer.id, contract.contract_id)
                    if hub:
                        await hub.report_guard("bad_signature", {
                            "house": buyer.id,
                            "contract_id": contract.contract_id,
                        })
                    return None

                if hub:
                    sign_res = await hub.sign_contract(contract)
                    if sign_res.get("status") != "signed":
                        return None
                    contract = Contract.model_validate(sign_res["contract"])
                    book_res = await hub.book_contract(contract)
                    if book_res.get("status") != "booked":
                        return None

                log.info("%s deal with %s accepted: %.2f kWh @ ₹%.2f",
                         me.id, buyer.id, contract.kwh, contract.price)
                return contract

            elif reply_type == "refuse":
                log.info("%s neighbour %s refused: %s", me.id, buyer.id, reply.get("reason"))
                return None

            if task.status.state in (
                TaskState.TASK_STATE_COMPLETED,
                TaskState.TASK_STATE_REJECTED,
                TaskState.TASK_STATE_FAILED,
                TaskState.TASK_STATE_CANCELED,
            ):
                break

        return None
    finally:
        if should_close_http:
            await http.aclose()
