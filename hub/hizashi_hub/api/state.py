"""/api/state, /api/registry, /api/weather."""
from fastapi import APIRouter

from hizashi_shared import config, street

from .. import clock
from .. import state as hub_state
from .. import tunnel
from ..sim import weather

router = APIRouter(tags=["state"])


@router.get("/state")
def get_state() -> dict:
    """The live snapshot: clock, speed, houses, mandates, block states, trades, savings..."""
    return hub_state.get().snapshot()


@router.get("/connect")
def get_connect() -> dict:
    """What the dashboard puts in each house's QR code: a link to the phone app for that house."""
    hub = tunnel.public_url()
    return {"hub": hub, "houses": [{"house": h, "label": info.label, "url": f"{hub}/app/?house={h}" if hub else None}
                                   for h, info in hub_state.get().houses.items()]}


@router.get("/registry")
def get_registry() -> dict:
    """Houses (with agent URLs and public keys), transformers and the market key."""
    raw = street.load_raw()
    return {
        "houses": [h.model_dump(mode="json") for h in hub_state.get().houses.values()],
        "transformers": raw.get("transformers", []),
        "market_pubkey": raw.get("market_pubkey"),
    }


def _today() -> str:
    """The day the clock is on (it moves on with console "next day"); SIM_DAY before it starts."""
    try:
        return clock.get().day
    except RuntimeError:
        return config.SIM_DAY


@router.get("/weather")
async def get_weather(day: str | None = None) -> dict:
    """The 96-block forecast frame + source ("open-meteo" or "clear-sky fallback")."""
    target_day = day or _today()
    frame, source = await weather.load_weather(target_day)
    return weather.to_json(frame, source, target_day)
