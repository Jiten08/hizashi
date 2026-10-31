"""A2A client side: send asks to neighbours, one negotiation = one A2A task (section 7.3).

Copy the client pattern from agent/examples/negotiation_sample.py (create_client,
SendMessageRequest, task_id/context_id carried across rounds). Re-parse every reply with
Offer.model_validate / Contract.model_validate before verifying signatures.
"""
from hizashi_shared.models import Contract, HouseInfo, Offer


async def negotiate_sale(me: HouseInfo, buyer: HouseInfo, first_ask: Offer) -> Contract | None:
    raise NotImplementedError("TODO(R1.5, Anurag)")
