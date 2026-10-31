"""Hub connection for one agent: WebSocket subscribe (role=agent) with retry/backoff,
plus REST calls to the hub. Agents never hold keys; they ask the wallet to sign.
"""
import asyncio
import logging
from collections.abc import Awaitable, Callable

import httpx
import websockets

from hizashi_shared import config
from hizashi_shared import events as ev
from hizashi_shared.models import Contract, Event, Offer, PlanWindow

log = logging.getLogger("hizashi.agent.hub")

Handler = Callable[[Event], Awaitable[None]]
BACKOFF_MAX = 10.0


class HubClient:
    def __init__(self, house: str, hub_url: str = config.HUB_URL, token: str | None = None) -> None:
        self.house = house
        self.hub_url = hub_url.rstrip("/")
        self.token = token or config.AGENT_TOKENS[house]
        self.handlers: list[Handler] = []
        self.connected = False

    @property
    def ws_url(self) -> str:
        base = self.hub_url.replace("http://", "ws://").replace("https://", "wss://")
        return f"{base}/ws?role=agent&house={self.house}&token={self.token}"

    @property
    def _auth(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self.token}"}

    # --- WebSocket ---------------------------------------------------------------

    async def run(self) -> None:
        """Connect forever; the hub may start later or restart."""
        delay = 1.0
        while True:
            try:
                async with websockets.connect(self.ws_url) as sock:
                    self.connected, delay = True, 1.0
                    log.info("%s connected to hub %s", self.house, self.hub_url)
                    async for raw in sock:
                        await self._dispatch(Event.model_validate_json(raw))
            except asyncio.CancelledError:
                raise
            except Exception as e:  # noqa: BLE001 - any failure means reconnect
                log.info("%s hub not reachable (%s), retry in %.0fs", self.house, type(e).__name__, delay)
            finally:
                self.connected = False
            await asyncio.sleep(delay)
            delay = min(delay * 2, BACKOFF_MAX)

    async def _dispatch(self, event: Event) -> None:
        if event.type == ev.BLOCK_STATE:
            log.info("%s block %s -> %s", self.house, event.data.get("block"), event.data.get("state"))
        for handler in self.handlers:
            try:
                await handler(event)
            except NotImplementedError:
                pass
            except Exception:
                log.exception("%s handler failed on %s", self.house, event.type)

    # --- REST --------------------------------------------------------------------

    async def get_state(self) -> dict:
        async with httpx.AsyncClient(timeout=5) as http:
            r = await http.get(f"{self.hub_url}/api/state")
            r.raise_for_status()
            return r.json()

    async def get_registry(self) -> dict:
        async with httpx.AsyncClient(timeout=5) as http:
            r = await http.get(f"{self.hub_url}/api/registry")
            r.raise_for_status()
            return r.json()

    async def get_weather(self) -> dict:
        raise NotImplementedError("TODO(R1.3, Anurag)")

    async def sign_offer(self, offer: Offer) -> dict:
        """POST /api/wallet/{house}/sign {"kind": "offer"} -> signed | pending | refused."""
        raise NotImplementedError("TODO(R1.5, Anurag)")

    async def sign_contract(self, contract: Contract) -> dict:
        raise NotImplementedError("TODO(R1.6, Anurag)")

    async def post_plans(self, windows: list[PlanWindow]) -> dict:
        raise NotImplementedError("TODO(R1.4, Anurag)")

    async def book_contract(self, contract: Contract) -> dict:
        raise NotImplementedError("TODO(R1.6, Anurag)")

    async def post_order(self, offer: Offer) -> dict:
        raise NotImplementedError("TODO(R2.1, Anurag)")

    async def report_guard(self, kind: str, detail: dict) -> dict:
        raise NotImplementedError("TODO(N2, Anurag)")
