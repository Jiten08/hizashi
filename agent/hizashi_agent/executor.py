"""A2A server side: answer incoming asks (section 7.3).

Trap (7.1): the executor must enqueue a Task before any status update.
Re-parse payloads with Offer.model_validate / Contract.model_validate before verifying signatures.
"""
from __future__ import annotations

import logging
import os
from typing import TYPE_CHECKING
import uuid

from a2a.helpers import get_data_parts, new_data_message, new_task
from a2a.server.agent_execution import AgentExecutor, RequestContext
from a2a.server.events import EventQueue
from a2a.server.tasks import TaskUpdater
from a2a.types import Message, Role, TaskState

from hizashi_shared import blocks, config, crypto, street
from hizashi_shared.models import Contract, HouseInfo, Mandate, Offer
from . import negotiator

if TYPE_CHECKING:
    from .hub_client import HubClient
    from .runtime import Runtime

log = logging.getLogger("hizashi.agent.executor")


class HouseExecutor(AgentExecutor):
    def __init__(
        self,
        house: str,
        runtime: Runtime | None = None,
        hub: HubClient | None = None,
    ) -> None:
        self.house = house
        self.runtime = runtime
        self.hub = hub
        self._houses: dict[str, HouseInfo] = {}
        self._mandates: dict[str, Mandate] = {}

    def get_house_info(self, house_id: str) -> HouseInfo | None:
        if self.runtime and self.runtime.houses:
            return self.runtime.houses.get(house_id)
        if not self._houses:
            try:
                self._houses = street.load_houses()
            except Exception:
                pass
        return self._houses.get(house_id)

    def get_mandate(self, house_id: str) -> Mandate | None:
        if self.runtime and self.runtime.mandates:
            return self.runtime.mandates.get(house_id)
        if not self._mandates:
            try:
                self._mandates = street.load_mandates()
            except Exception:
                pass
        return self._mandates.get(house_id)

    def get_remaining_buy(self, block_index: int) -> float:
        if self.runtime:
            return self.runtime.remaining_buy.get(block_index, 0.0)
        return 1.0  # default for standalone/tests if no runtime attached

    def deduct_buy_need(self, block_index: int, kwh: float) -> None:
        if self.runtime:
            current = self.runtime.remaining_buy.get(block_index, 0.0)
            self.runtime.remaining_buy[block_index] = max(0.0, round(current - kwh, 3))

    def is_block_open(self, block_key: str) -> bool:
        if self.runtime:
            return (self.runtime.block_states.get(block_key) == "OPEN"
                    and not self.runtime.outage_over(blocks.parse_key(block_key).index))
        return True  # default for tests

    def _verify_sig(self, model: Offer | Contract, sig: str | None, pub_key: str | None) -> bool:
        if os.environ.get("WALLET_MOCK", "0") in ("1", "true", "True"):
            return True
        if not pub_key:
            return False
        return crypto.verify(model, sig, pub_key)

    async def execute(self, context: RequestContext, event_queue: EventQueue) -> None:
        # A new negotiation: the executor must enqueue a Task before any status update.
        if context.current_task is None:
            await event_queue.enqueue_event(
                new_task(
                    context.task_id,
                    context.context_id,
                    TaskState.TASK_STATE_SUBMITTED,
                    history=[context.message],
                )
            )
        updater = TaskUpdater(event_queue, context.task_id, context.context_id)
        data = get_data_parts(context.message.parts)
        payload = data[0] if data else {}
        msg_type = payload.get("type")

        if msg_type == "ask":
            await self._handle_ask(payload, context, updater)
        elif msg_type == "accept":
            await self._handle_accept(payload, context, updater)
        else:
            log.warning("%s got unknown message type %s", self.house, msg_type)
            reply = {"type": "refuse", "reason": f"unknown message type {msg_type}"}
            await updater.reject(self._msg(reply, context))

    async def _handle_ask(self, payload: dict, context: RequestContext, updater: TaskUpdater) -> None:
        try:
            offer = Offer.model_validate(payload.get("offer"))
        except Exception as e:
            log.warning("%s failed to parse offer: %s", self.house, e)
            reply = {"type": "refuse", "reason": "invalid offer format"}
            await updater.reject(self._msg(reply, context))
            return

        seller_info = self.get_house_info(offer.house)
        my_info = self.get_house_info(self.house)
        my_mandate = self.get_mandate(self.house)

        # 1. Verify signature
        seller_pub = seller_info.wallet_pubkey if seller_info else None
        if not self._verify_sig(offer, offer.signature, seller_pub):
            log.warning("%s: bad signature from %s on offer %s", self.house, offer.house, offer.offer_id)
            if self.hub:
                await self.hub.report_guard("bad_signature", {
                    "house": offer.house,
                    "offer_id": offer.offer_id,
                })
            reply = {"type": "refuse", "reason": "bad signature"}
            await updater.reject(self._msg(reply, context))
            return

        # 2. Refusal checks
        is_open = self.is_block_open(offer.block.key)
        same_transformer = True
        if my_mandate and my_mandate.counterparties == "same_transformer":
            if my_info and seller_info and my_info.transformer != seller_info.transformer:
                same_transformer = False

        remaining_need = self.get_remaining_buy(offer.block.index)
        max_buy = my_mandate.max_buy_price if my_mandate else 5.50
        b_limit = negotiator.buyer_limit(max_buy)

        decision, price, reason = negotiator.buyer_decide(
            offer.price,
            offer.round,
            b_limit,
            remaining_need,
            is_open=is_open,
            same_transformer=same_transformer,
        )

        if decision == "refuse":
            log.info("%s refusing ask from %s (b%02d): %s", self.house, offer.house, offer.block.index, reason)
            reply = {"type": "refuse", "reason": reason}
            await updater.reject(self._msg(reply, context))
            return

        q = round(min(offer.kwh, remaining_need), 3)

        if decision == "accept":
            # Build contract signed by buyer
            contract = Contract(
                contract_id=str(uuid.uuid4()),
                negotiation_id=offer.negotiation_id,
                block=offer.block,
                seller=offer.house,
                buyer=self.house,  # type: ignore[arg-type]
                kwh=q,
                price=offer.price,
                route="haggle",
            )
            if self.hub:
                sign_res = await self.hub.sign_contract(contract)
                if sign_res.get("status") != "signed":
                    reason = sign_res.get("reason", "contract signing failed")
                    reply = {"type": "refuse", "reason": reason}
                    await updater.reject(self._msg(reply, context))
                    return
                contract = Contract.model_validate(sign_res["contract"])

            self.deduct_buy_need(offer.block.index, q)
            log.info("%s→%s b%02d r%d ask %.2f / accepted %.2f",
                     offer.house, self.house, offer.block.index, offer.round, offer.price, offer.price)
            reply = {"type": "accept", "contract": contract.model_dump(mode="json")}
            await updater.complete(self._msg(reply, context))

        elif decision == "counter":
            # Build counter bid offer
            bid_offer = Offer(
                offer_id=str(uuid.uuid4()),
                negotiation_id=offer.negotiation_id,
                block=offer.block,
                side="bid",
                house=self.house,  # type: ignore[arg-type]
                to=offer.house,
                kwh=q,
                price=price,
                round=offer.round,
                expires_at=offer.expires_at,
                nonce=str(uuid.uuid4()),
            )
            if self.hub:
                sign_res = await self.hub.sign_offer(bid_offer)
                if sign_res.get("status") != "signed":
                    reason = sign_res.get("reason", "bid signing failed")
                    reply = {"type": "refuse", "reason": reason}
                    await updater.reject(self._msg(reply, context))
                    return
                bid_offer = Offer.model_validate(sign_res["offer"])

            log.info("%s→%s b%02d r%d ask %.2f / bid %.2f",
                     offer.house, self.house, offer.block.index, offer.round, offer.price, price)
            reply = {"type": "bid", "offer": bid_offer.model_dump(mode="json")}
            await updater.requires_input(self._msg(reply, context))

    async def _handle_accept(self, payload: dict, context: RequestContext, updater: TaskUpdater) -> None:
        try:
            contract = Contract.model_validate(payload.get("contract"))
        except Exception as e:
            log.warning("%s failed to parse contract: %s", self.house, e)
            reply = {"type": "refuse", "reason": "invalid contract format"}
            await updater.reject(self._msg(reply, context))
            return

        seller_info = self.get_house_info(contract.seller)
        seller_pub = seller_info.wallet_pubkey if seller_info else None

        if not self._verify_sig(contract, contract.seller_sig, seller_pub):
            log.warning("%s: bad seller_sig from %s on contract %s", self.house, contract.seller, contract.contract_id)
            if self.hub:
                await self.hub.report_guard("bad_signature", {
                    "house": contract.seller,
                    "contract_id": contract.contract_id,
                })
            reply = {"type": "refuse", "reason": "bad seller signature"}
            await updater.reject(self._msg(reply, context))
            return

        # Countersign as buyer
        if self.hub:
            sign_res = await self.hub.sign_contract(contract)
            if sign_res.get("status") != "signed":
                reason = sign_res.get("reason", "countersigning failed")
                reply = {"type": "refuse", "reason": reason}
                await updater.reject(self._msg(reply, context))
                return
            contract = Contract.model_validate(sign_res["contract"])

            book_res = await self.hub.book_contract(contract)
            if book_res.get("status") != "booked":
                reason = book_res.get("reason", "booking failed")
                reply = {"type": "refuse", "reason": reason}
                await updater.reject(self._msg(reply, context))
                return

        self.deduct_buy_need(contract.block.index, contract.kwh)
        log.info("%s booked contract %s with seller %s for %.2f kWh @ ₹%.2f",
                 self.house, contract.contract_id, contract.seller, contract.kwh, contract.price)
        reply = {"type": "booked", "contract_id": contract.contract_id}
        await updater.complete(self._msg(reply, context))

    async def cancel(self, context: RequestContext, event_queue: EventQueue) -> None:
        updater = TaskUpdater(event_queue, context.task_id, context.context_id)
        await updater.cancel()

    @staticmethod
    def _msg(data: dict, context: RequestContext) -> Message:
        return new_data_message(
            data, context_id=context.context_id, task_id=context.task_id, role=Role.ROLE_AGENT
        )
