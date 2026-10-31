"""/api/state, /api/registry, /api/weather."""
from fastapi import APIRouter

from hizashi_shared import street

from .. import state as hub_state

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
def get_weather() -> dict:
    """The 96-block forecast frame + source ("open-meteo" or "clear-sky fallback")."""
    raise NotImplementedError("TODO(R1.2, Tezash)")
