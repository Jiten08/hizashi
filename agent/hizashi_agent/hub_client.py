"""Hub connection for one agent: WebSocket subscribe (role=agent) with retry/backoff,
plus REST calls to the hub. Agents never hold keys; they ask the wallet to sign.
"""
import asyncio
import logging
import os
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
        self.token = token or config.AGENT_TOKENS.get(house, f"dev-{house}")
        self.handlers: list[Handler] = []
        self.connected = False

    @property
    def is_mock(self) -> bool:
        return os.environ.get("WALLET_MOCK", "0") in ("1", "true", "True")

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
            except Exception as e:
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
        async with httpx.AsyncClient(timeout=5) as http:
            r = await http.get(f"{self.hub_url}/api/weather")
            r.raise_for_status()
            return r.json()

    async def sign_offer(self, offer: Offer) -> dict:
        """POST /api/wallet/{house}/sign {"kind": "offer"} -> signed | pending | refused."""
        if self.is_mock:
            d = offer.model_dump(mode="json")
            d["signature"] = "mock"
            return {"status": "signed", "offer": d}

        async with httpx.AsyncClient(timeout=5) as http:
            try:
                r = await http.post(
                    f"{self.hub_url}/api/wallet/{self.house}/sign",
                    headers=self._auth,
                    json={"kind": "offer", "offer": offer.model_dump(mode="json")},
                )
                return r.json()
            except Exception as e:
                log.warning("%s sign_offer error: %s", self.house, e)
                return {"status": "refused", "reason": str(e)}

    async def sign_contract(self, contract: Contract) -> dict:
        """POST /api/wallet/{house}/sign {"kind": "contract"} -> signed | refused."""
        if self.is_mock:
            d = contract.model_dump(mode="json")
            if self.house == contract.seller:
                d["seller_sig"] = "mock"
            elif self.house == contract.buyer:
                d["buyer_sig"] = "mock"
            return {"status": "signed", "contract": d}

        async with httpx.AsyncClient(timeout=5) as http:
            try:
                r = await http.post(
                    f"{self.hub_url}/api/wallet/{self.house}/sign",
                    headers=self._auth,
                    json={"kind": "contract", "contract": contract.model_dump(mode="json")},
                )
                return r.json()
            except Exception as e:
                log.warning("%s sign_contract error: %s", self.house, e)
                return {"status": "refused", "reason": str(e)}

    async def post_plans(self, windows: list[PlanWindow]) -> dict:
        """POST /api/wallet/{house}/plans with plan windows."""
        payload = {"windows": [w.model_dump(mode="json") for w in windows]}
        if self.is_mock:
            return {"status": "ok", **payload}

        async with httpx.AsyncClient(timeout=5) as http:
            try:
                r = await http.post(
                    f"{self.hub_url}/api/wallet/{self.house}/plans",
                    headers=self._auth,
                    json=payload,
                )
                return r.json()
            except Exception as e:
                log.warning("%s post_plans error: %s", self.house, e)
                return {"status": "error", "reason": str(e)}

    async def book_contract(self, contract: Contract) -> dict:
        """POST /api/market/contracts with {"contract": ...}."""
        if self.is_mock:
            log.info("MOCK booking contract %s (%s -> %s, %.2f kWh @ ₹%.2f)",
                     contract.contract_id, contract.seller, contract.buyer, contract.kwh, contract.price)
            return {"status": "booked", "contract": contract.model_dump(mode="json")}

        async with httpx.AsyncClient(timeout=5) as http:
            try:
                r = await http.post(
                    f"{self.hub_url}/api/market/contracts",
                    headers=self._auth,
                    json={"contract": contract.model_dump(mode="json")},
                )
                return r.json()
            except Exception as e:
                log.warning("%s book_contract error: %s", self.house, e)
                return {"status": "refused", "reason": str(e)}

    async def post_order(self, offer: Offer) -> dict:
        raise NotImplementedError("TODO(R2.1, Anurag)")

    async def report_guard(self, kind: str, detail: dict) -> dict:
        """POST /api/guard/report. Ignore 404 or 501 for now."""
        try:
            async with httpx.AsyncClient(timeout=5) as http:
                r = await http.post(
                    f"{self.hub_url}/api/guard/report",
                    headers=self._auth,
                    json={"kind": kind, "detail": detail},
                )
                if r.status_code in (404, 501):
                    return {}
                return r.json()
        except Exception:
            return {}
