"""/api/state, /api/registry, /api/weather."""
from fastapi import APIRouter

from hizashi_shared import config, street

from .. import state as hub_state
from ..sim import weather

router = APIRouter(tags=["state"])


@router.get("/state")
def get_state() -> dict:
    """The live snapshot: clock, speed, houses, mandates, block states, trades, savings..."""
    return hub_state.get().snapshot()


@router.get("/registry")
def get_registry() -> dict:
    """Houses (with agent URLs and public keys), transformers and the market key."""
    raw = street.load_raw()
    return {
        "houses": [h.model_dump(mode="json") for h in hub_state.get().houses.values()],
        "transformers": raw.get("transformers", []),
        "market_pubkey": raw.get("market_pubkey"),
    }


@router.get("/weather")
async def get_weather(day: str | None = None) -> dict:
    """The 96-block forecast frame + source ("open-meteo" or "clear-sky fallback")."""
    target_day = day or config.SIM_DAY
    frame, source = await weather.load_weather(target_day)
    return weather.to_json(frame, source, target_day)
