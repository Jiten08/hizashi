"""Minimal two-party haggle over A2A, verified against a2a-sdk[http-server]==1.2.1.

Run the server:  python agent/examples/negotiation_sample.py serve
Run the client:  python agent/examples/negotiation_sample.py ask
"""
import asyncio
import sys
import uuid

import httpx
import uvicorn
from fastapi import FastAPI

from a2a.client import ClientConfig, create_client
from a2a.helpers import get_data_parts, new_data_message, new_data_part, new_task
from a2a.server.agent_execution import AgentExecutor, RequestContext
from a2a.server.events import EventQueue
from a2a.server.request_handlers import DefaultRequestHandler
from a2a.server.routes import (
    add_a2a_routes_to_fastapi,
    create_agent_card_routes,
    create_jsonrpc_routes,
)
from a2a.server.tasks import InMemoryTaskStore, TaskUpdater
from a2a.types import (
    AgentCapabilities,
    AgentCard,
    AgentInterface,
    AgentSkill,
    Message,
    Role,
    SendMessageRequest,
    TaskState,
)

PORT = 9099
URL = f"http://127.0.0.1:{PORT}/"
BUYER_LIMIT = 4.70


def card() -> AgentCard:
    return AgentCard(
        name="Hizashi agent · House 14",
        description="Buys spare rooftop solar for House 14",
        version="0.1.0",
        supported_interfaces=[
            AgentInterface(url=URL, protocol_binding="JSONRPC", protocol_version="1.0")
        ],
        capabilities=AgentCapabilities(streaming=False),
        default_input_modes=["application/json"],
        default_output_modes=["application/json"],
        skills=[
            AgentSkill(
                id="trade_block",
                name="Trade energy for one 15-minute block",
                description="Replies to an ask with a bid, an accept or a refusal",
                tags=["energy", "p2p"],
            )
        ],
    )


class BuyerExecutor(AgentExecutor):
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
        ask = data[0] if data else {}
        price = float(ask.get("price", 99))
        rnd = int(ask.get("round", 0))
        if price <= BUYER_LIMIT:
            reply = {"type": "accept", "price": price, "round": rnd}
            await updater.complete(self._msg(reply, context))
        else:
            bid = round(4.00 + 0.27 * rnd, 2)
            reply = {"type": "bid", "price": bid, "round": rnd}
            await updater.requires_input(self._msg(reply, context))

    async def cancel(self, context: RequestContext, event_queue: EventQueue) -> None:
        updater = TaskUpdater(event_queue, context.task_id, context.context_id)
        await updater.cancel()

    @staticmethod
    def _msg(data: dict, context: RequestContext) -> Message:
        return new_data_message(
            data, context_id=context.context_id, task_id=context.task_id, role=Role.ROLE_AGENT
        )


def build_app() -> FastAPI:
    agent_card = card()
    handler = DefaultRequestHandler(
        agent_executor=BuyerExecutor(),
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


async def seller() -> None:
    async with httpx.AsyncClient(timeout=10) as http:
        client = await create_client(
            URL, client_config=ClientConfig(streaming=False, httpx_client=http)
        )
        task_id, context_id = "", ""
        for rnd, ask_price in enumerate([5.40, 5.16, 4.92, 4.68]):
            msg = Message(
                message_id=str(uuid.uuid4()),
                role=Role.ROLE_USER,
                parts=[new_data_part({"type": "ask", "price": ask_price, "round": rnd})],
                task_id=task_id,
                context_id=context_id,
            )
            async for resp in client.send_message(SendMessageRequest(message=msg)):
                task = resp.task if resp.HasField("task") else None
                if task is None:
                    print("non-task response:", resp)
                    continue
                task_id, context_id = task.id, task.context_id
                state = TaskState.Name(task.status.state)
                reply = get_data_parts(task.status.message.parts)
                print(f"round {rnd}: ask {ask_price:.2f} -> {state} {reply}")
                if task.status.state == TaskState.TASK_STATE_COMPLETED:
                    return


if __name__ == "__main__":
    if sys.argv[1:] == ["serve"]:
        uvicorn.run(build_app(), host="127.0.0.1", port=PORT, log_level="warning")
    else:
        asyncio.run(seller())
