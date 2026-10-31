"""FastAPI app for one house's agent: A2A routes (JSON-RPC at /, card at
/.well-known/agent-card.json) + the hub WebSocket client as a background task."""
import asyncio
from contextlib import asynccontextmanager

from a2a.server.request_handlers import DefaultRequestHandler
from a2a.server.routes import add_a2a_routes_to_fastapi, create_agent_card_routes, create_jsonrpc_routes
from a2a.server.tasks import InMemoryTaskStore
from fastapi import FastAPI

from hizashi_shared.models import HouseInfo

from .card import build_card
from .executor import HouseExecutor
from .hub_client import HubClient


def build_app(house: HouseInfo, hub: HubClient | None = None) -> FastAPI:
    hub = hub or HubClient(house.id)

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        task = asyncio.create_task(hub.run(), name=f"hub-{house.id}")
        try:
            yield
        finally:
            task.cancel()

    agent_card = build_card(house)
    handler = DefaultRequestHandler(
        agent_executor=HouseExecutor(house.id),
        task_store=InMemoryTaskStore(),
        agent_card=agent_card,
    )
    app = FastAPI(title=f"Hizashi agent {house.id}", lifespan=lifespan)
    app.state.hub = hub
    add_a2a_routes_to_fastapi(
        app,
        agent_card_routes=create_agent_card_routes(agent_card),
        jsonrpc_routes=create_jsonrpc_routes(handler, rpc_url="/"),
    )
    return app
