"""Tests for agent decisions and A2A negotiation (R1.5).

H12 (min_sell 4.20, buyback 3.89) vs H14 (max_buy 5.50).
- Asks 5.40, 5.16, 4.92, 4.68; bids 4.00, 4.30, 4.60; the buyer accepts 4.68 in round 3.
- A forged signature -> refuse.
- Different transformer -> refuse.
"""
from datetime import datetime, timezone
import uuid
import pytest
import httpx

from a2a.client import ClientConfig, create_client
from a2a.helpers import get_data_parts, new_data_part
from a2a.server.request_handlers import DefaultRequestHandler
from a2a.server.routes import add_a2a_routes_to_fastapi, create_agent_card_routes, create_jsonrpc_routes
from a2a.server.tasks import InMemoryTaskStore
from a2a.types import Message, Role, SendMessageRequest, TaskState
from fastapi import FastAPI

from hizashi_agent import card, negotiator
from hizashi_agent.executor import HouseExecutor
from hizashi_agent.hub_client import HubClient
from hizashi_shared import config, crypto, street
from hizashi_shared.models import BlockRef, Contract, HouseInfo, Mandate, Offer


class MockHubClient(HubClient):
    """Local test hub client that signs using real local keys and books in memory."""
    def __init__(self, house: str):
        super().__init__(house)
        self.booked_contracts: list[Contract] = []
        self.reported_guards: list[dict] = []
        self.key = crypto.load_key(config.KEYS_DIR / f"{house}.wallet.key")

    async def sign_offer(self, offer: Offer) -> dict:
        signed = offer.model_copy()
        signed.signature = crypto.sign(offer, self.key)
        return {"status": "signed", "offer": signed.model_dump(mode="json")}

    async def sign_contract(self, contract: Contract) -> dict:
        signed = contract.model_copy()
        if self.house == contract.seller:
            signed.seller_sig = crypto.sign(contract, self.key)
        elif self.house == contract.buyer:
            signed.buyer_sig = crypto.sign(contract, self.key)
        return {"status": "signed", "contract": signed.model_dump(mode="json")}

    async def book_contract(self, contract: Contract) -> dict:
        self.booked_contracts.append(contract)
        return {"status": "booked", "contract": contract.model_dump(mode="json")}

    async def report_guard(self, kind: str, detail: dict) -> dict:
        self.reported_guards.append({"kind": kind, "detail": detail})
        return {"status": "reported"}


def test_pure_decisions_deck_haggle():
    """H12 vs H14 decision progression."""
    s_limit = negotiator.seller_limit(4.20, 3.89)  # 4.20
    b_limit = negotiator.buyer_limit(5.50)         # 5.50

    asks = [negotiator.ask_price(r, s_limit) for r in range(4)]
    assert asks == [5.40, 5.16, 4.92, 4.68]

    bids = [negotiator.bid_price(r, b_limit) for r in range(3)]
    assert bids == [4.00, 4.30, 4.60]

    # Round 0: ask 5.40 -> counter 4.00
    dec0, p0, _ = negotiator.buyer_decide(5.40, 0, b_limit, remaining_need=0.40)
    assert dec0 == "counter"
    assert p0 == 4.00

    # Round 1: ask 5.16 -> counter 4.30
    dec1, p1, _ = negotiator.buyer_decide(5.16, 1, b_limit, remaining_need=0.40)
    assert dec1 == "counter"
    assert p1 == 4.30

    # Round 2: ask 4.92 -> counter 4.60
    dec2, p2, _ = negotiator.buyer_decide(4.92, 2, b_limit, remaining_need=0.40)
    assert dec2 == "counter"
    assert p2 == 4.60

    # Round 3: ask 4.68 -> accept 4.68
    dec3, p3, _ = negotiator.buyer_decide(4.68, 3, b_limit, remaining_need=0.40)
    assert dec3 == "accept"
    assert p3 == 4.68


def _build_test_buyer_app(house_id: str, hub: HubClient, mandate: Mandate | None = None,
                          houses: dict[str, HouseInfo] | None = None) -> FastAPI:
    all_houses = houses or street.load_houses()
    # Ensure pubkeys match local keys if present
    for hid in ("h12", "h14"):
        key_path = config.KEYS_DIR / f"{hid}.wallet.key"
        if key_path.exists():
            all_houses[hid] = all_houses[hid].model_copy(
                update={"wallet_pubkey": crypto.pub_b64(crypto.load_key(key_path))}
            )
    house_info = all_houses[house_id]
    agent_card = card.build_card(house_info)
    executor = HouseExecutor(house_id, hub=hub)
    executor._houses = all_houses
    if mandate:
        executor._mandates = {house_id: mandate}

    handler = DefaultRequestHandler(
        agent_executor=executor,
        task_store=InMemoryTaskStore(),
        agent_card=agent_card,
    )
    app = FastAPI()
    add_a2a_routes_to_fastapi(
        app,
        agent_card_routes=create_agent_card_routes(agent_card),
        jsonrpc_routes=create_jsonrpc_routes(handler, rpc_url="/"),
    )
    return app


@pytest.mark.asyncio
async def test_a2a_deck_haggle_full_flow():
    """H12 client sends asks 5.40, 5.16, 4.92, 4.68 to H14 server; H14 counters then accepts 4.68."""
    h14_hub = MockHubClient("h14")
    app = _build_test_buyer_app("h14", h14_hub)
    h12_key = crypto.load_key(config.KEYS_DIR / "h12.wallet.key")

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://127.0.0.1:9014/") as http:
        client = await create_client(
            "http://127.0.0.1:9014/",
            client_config=ClientConfig(streaming=False, httpx_client=http),
        )

        task_id, context_id = "", ""
        nego_id = str(uuid.uuid4())
        block_ref = BlockRef(day="2026-10-31", index=48)
        exp = datetime(2026, 10, 31, 11, 0, tzinfo=timezone.utc)

        expected_asks = [5.40, 5.16, 4.92, 4.68]
        expected_replies = [
            ("bid", 4.00),
            ("bid", 4.30),
            ("bid", 4.60),
            ("accept", 4.68),
        ]

        for r, ask_p in enumerate(expected_asks):
            offer = Offer(
                offer_id=str(uuid.uuid4()),
                negotiation_id=nego_id,
                block=block_ref,
                side="ask",
                house="h12",
                to="h14",
                kwh=0.40,
                price=ask_p,
                round=r,
                expires_at=exp,
                nonce=str(uuid.uuid4()),
            )
            offer.signature = crypto.sign(offer, h12_key)

            msg = Message(
                message_id=str(uuid.uuid4()),
                role=Role.ROLE_USER,
                parts=[new_data_part({"type": "ask", "offer": offer.model_dump(mode="json")})],
                task_id=task_id,
                context_id=context_id,
            )

            task = None
            reply = {}
            async for resp in client.send_message(SendMessageRequest(message=msg)):
                if resp.HasField("task"):
                    task = resp.task
                    task_id, context_id = task.id, task.context_id
                    parts = get_data_parts(task.status.message.parts)
                    if parts:
                        reply = parts[0]

            assert task is not None
            exp_type, exp_p = expected_replies[r]
            assert reply.get("type") == exp_type
            if exp_type == "bid":
                assert task.status.state == TaskState.TASK_STATE_INPUT_REQUIRED
                bid_off = Offer.model_validate(reply["offer"])
                assert bid_off.price == exp_p
                # Verify buyer's signature
                assert crypto.verify(bid_off, bid_off.signature, crypto.pub_b64(h14_hub.key))
            else:
                assert exp_type == "accept"
                assert task.status.state == TaskState.TASK_STATE_COMPLETED
                contract = Contract.model_validate(reply["contract"])
                assert contract.price == exp_p
                assert contract.kwh == 0.40
                assert contract.buyer == "h14"
                assert contract.seller == "h12"
                assert crypto.verify(contract, contract.buyer_sig, crypto.pub_b64(h14_hub.key))


@pytest.mark.asyncio
async def test_forged_signature_refused():
    """An ask with an invalid signature must be refused and reported to guard."""
    h14_hub = MockHubClient("h14")
    app = _build_test_buyer_app("h14", h14_hub)

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://127.0.0.1:9014/") as http:
        client = await create_client(
            "http://127.0.0.1:9014/",
            client_config=ClientConfig(streaming=False, httpx_client=http),
        )

        offer = Offer(
            offer_id="fake_1",
            negotiation_id="n1",
            block=BlockRef(day="2026-10-31", index=48),
            side="ask",
            house="h12",
            to="h14",
            kwh=0.40,
            price=5.40,
            round=0,
            expires_at=datetime(2026, 10, 31, 11, 0, tzinfo=timezone.utc),
            nonce="nonce1",
            signature="aW52YWxpZF9zaWduYXR1cmVfZm9yZ2VkX2J5X2F0dGFja2Vy",  # forged
        )

        msg = Message(
            message_id=str(uuid.uuid4()),
            role=Role.ROLE_USER,
            parts=[new_data_part({"type": "ask", "offer": offer.model_dump(mode="json")})],
        )

        reply = {}
        async for resp in client.send_message(SendMessageRequest(message=msg)):
            if resp.HasField("task"):
                parts = get_data_parts(resp.task.status.message.parts)
                if parts:
                    reply = parts[0]

        assert reply.get("type") == "refuse"
        assert "signature" in reply.get("reason", "")
        assert len(h14_hub.reported_guards) == 1
        assert h14_hub.reported_guards[0]["kind"] == "bad_signature"


@pytest.mark.asyncio
async def test_different_transformer_refused():
    """If seller is on a different transformer, buyer refuses."""
    h14_hub = MockHubClient("h14")
    all_houses = street.load_houses()
    # Put H12 on T2 while H14 remains on T1
    all_houses["h12"] = all_houses["h12"].model_copy(update={"transformer": "T2"})
    h14_mandate = street.load_mandates()["h14"].model_copy(update={"counterparties": "same_transformer"})

    app = _build_test_buyer_app("h14", h14_hub, mandate=h14_mandate, houses=all_houses)
    h12_key = crypto.load_key(config.KEYS_DIR / "h12.wallet.key")

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://127.0.0.1:9014/") as http:
        client = await create_client(
            "http://127.0.0.1:9014/",
            client_config=ClientConfig(streaming=False, httpx_client=http),
        )

        offer = Offer(
            offer_id="diff_tf_1",
            negotiation_id="n_tf",
            block=BlockRef(day="2026-10-31", index=48),
            side="ask",
            house="h12",
            to="h14",
            kwh=0.40,
            price=5.40,
            round=0,
            expires_at=datetime(2026, 10, 31, 11, 0, tzinfo=timezone.utc),
            nonce="nonce2",
        )
        offer.signature = crypto.sign(offer, h12_key)

        msg = Message(
            message_id=str(uuid.uuid4()),
            role=Role.ROLE_USER,
            parts=[new_data_part({"type": "ask", "offer": offer.model_dump(mode="json")})],
        )

        reply = {}
        async for resp in client.send_message(SendMessageRequest(message=msg)):
            if resp.HasField("task"):
                parts = get_data_parts(resp.task.status.message.parts)
                if parts:
                    reply = parts[0]

        assert reply.get("type") == "refuse"
        assert "transformer" in reply.get("reason", "")
