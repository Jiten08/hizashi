"""In-memory live state + snapshot for GET /api/state.

`HubState.run()` subscribes to the bus and applies events; `snapshot()` returns one
JSON-able dict. Screens load the snapshot first, then apply the same events over /ws.
"""
import asyncio
from datetime import datetime

from hizashi_shared import config
from hizashi_shared import events as ev
from hizashi_shared.models import Event, HouseInfo, Mandate

from . import bus, tunnel

RECENT_EVENTS = 200


class HubState:
    def __init__(self, houses: dict[str, HouseInfo], mandates: dict[str, Mandate], speed: int) -> None:
        self.houses = houses
        self.mandates = mandates
        self.speed = speed
        self.weather_source: str | None = None
        self.schedules: dict[str, list[dict]] = {}   # house -> away / guests plans (kept across days)
        self.reset()

    def reset(self) -> None:
        """Forget everything that happened during the simulated day."""
        self.sim_time: datetime | None = None
        self.sun: dict | None = None                 # {azimuth, elevation} from the last tick
        self.running = False
        self.blocks: dict[str, str] = {}             # block key -> BlockState
        self.forecasts: dict[str, list[dict]] = {}   # house -> forecasts
        self.plans: dict[str, list[dict]] = {}       # house -> plan windows
        self.negotiations: dict[str, list[dict]] = {}  # negotiation_id -> offers
        self.contracts: list[dict] = []
        self.settlements: list[dict] = []
        self.savings: dict[str, dict] = {}
        self.approvals: list[dict] = []
        self.flags: list[dict] = []
        self.outage: dict | None = None
        self.recent: list[dict] = []
        self.live: dict[str, dict] = {}              # house -> latest {solar_kw, use_kw, ts}
        self.sim_events: list[dict] = []             # console cloud / ac / guests / away / outage
        self.blocked: list[dict] = []                # wallet refusals, newest last
        self.auctions: dict[str, dict] = {}          # block key -> market.cleared data

    def apply(self, e: Event) -> None:
        d = e.data
        if e.type == ev.CLOCK_TICK:
            self.sim_time = e.sim_time
            self.speed = d.get("speed", self.speed)
            self.running = d.get("running", self.running)
            self.sun = d.get("sun", self.sun)
            if d.get("reset"):
                self.reset()
                self.sim_time = e.sim_time
                self.sun = d.get("sun")
        elif e.type == ev.BLOCK_STATE:
            self.blocks[d["block"]] = d["state"]
        elif e.type == ev.MANDATE_UPDATED and e.house:
            self.mandates[e.house] = Mandate.model_validate(d["mandate"])
        elif e.type == ev.FORECAST_UPDATED and e.house:
            self.forecasts[e.house] = d.get("forecasts", [])
        elif e.type == ev.PLAN_UPDATED and e.house:
            self.plans[e.house] = d.get("windows", [])
        elif e.type == ev.NEGO_OFFER:
            offer = d.get("offer", {})
            nid = offer.get("negotiation_id")
            if nid and offer not in self.negotiations.setdefault(nid, []):
                self.negotiations[nid].append(offer)
        elif e.type == ev.CONTRACT_BOOKED:
            c = d.get("contract", {})
            if all(x.get("contract_id") != c.get("contract_id") for x in self.contracts):
                self.contracts.append(c)
        elif e.type == ev.SETTLEMENT_DONE:
            s = d.get("settlement", {})
            if all(x.get("contract_id") != s.get("contract_id") for x in self.settlements):
                self.settlements.append(s)
            for c in self.contracts:
                if c.get("contract_id") == s.get("contract_id"):
                    c["settled"] = True
        elif e.type == ev.METER_READING and e.house:
            self.live[e.house] = {"solar_kw": d.get("solar_kw", 0), "use_kw": d.get("use_kw", 0),
                                  "ts": e.sim_time.isoformat(), "outage": d.get("outage", False)}
        elif e.type == ev.SIM_EVENT:
            self.sim_events.append(d.get("event", {}))
        elif e.type == ev.WALLET_BLOCKED:
            self.blocked = (self.blocked + [{"house": e.house, "sim_time": e.sim_time.isoformat(), **d}])[-50:]
        elif e.type == ev.MARKET_CLEARED:
            self.auctions[d.get("block", "")] = d
        elif e.type == ev.HOUSE_UPDATED and e.house:
            self.houses[e.house] = HouseInfo.model_validate(d["house"])
        elif e.type == ev.SCHEDULE_UPDATED and e.house:
            self.schedules[e.house] = d.get("schedules", [])
        elif e.type == ev.SAVINGS_UPDATED and e.house:
            self.savings[e.house] = d
        elif e.type in (ev.APPROVAL_REQUESTED, ev.APPROVAL_RESOLVED):
            a = d.get("approval", {})
            self.approvals = [x for x in self.approvals if x.get("approval_id") != a.get("approval_id")] + [a]
        elif e.type == ev.GUARD_FLAG:
            self.flags.append(d)
        elif e.type == ev.GRID_OUTAGE:
            self.outage = d if d.get("active") else None

        if e.type not in (ev.CLOCK_TICK, ev.METER_READING):
            self.recent = (self.recent + [e.model_dump(mode="json")])[-RECENT_EVENTS:]

    def snapshot(self) -> dict:
        return {
            "sim_time": self.sim_time.isoformat() if self.sim_time else None,
            "speed": self.speed,
            "running": self.running,
            "sun": self.sun,
            "public_url": tunnel.public_url(),
            "houses": {h: info.model_dump(mode="json") for h, info in self.houses.items()},
            "mandates": {h: m.model_dump(mode="json") for h, m in self.mandates.items()},
            "blocks": self.blocks,
            "forecasts": self.forecasts,
            "plans": self.plans,
            "negotiations": self.negotiations,
            "contracts": self.contracts,
            "settlements": self.settlements,
            "savings": self.savings,
            "approvals": self.approvals,
            "flags": self.flags,
            "outage": self.outage,
            "weather_source": self.weather_source,
            "live": self.live,
            "sim_events": self.sim_events,
            "blocked": self.blocked,
            "auctions": self.auctions,
            "schedules": self.schedules,
            "recent_events": self.recent,
        }

    async def run(self) -> None:
        q = bus.subscribe()
        try:
            while True:
                self.apply(await q.get())
        finally:
            bus.unsubscribe(q)


_state: HubState | None = None


def init(houses: dict[str, HouseInfo], mandates: dict[str, Mandate], speed: int) -> HubState:
    global _state
    _state = HubState(houses, mandates, speed)
    return _state


def get() -> HubState:
    if _state is None:
        raise RuntimeError("hub state not initialised")
    return _state


def start(loop_tasks: list[asyncio.Task]) -> None:
    loop_tasks.append(asyncio.create_task(get().run(), name="state"))
