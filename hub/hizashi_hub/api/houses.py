"""/api/houses/{house}/setup: onboarding. The owner says whether the home has rooftop solar,
its size and facing, and whether it took the PM Surya Ghar subsidy; the hub sets the roof,
the BESCOM buyback rate and metering, saves it to data/street.json and publishes house.updated.

`preview: true` returns the result (with a clear-day solar estimate) without saving.
"""
import json
from typing import Literal

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from hizashi_shared import config, solar, street
from hizashi_shared import events as ev
from hizashi_shared.models import HOUSES, Event, HouseInfo, Roof

from .. import bus, clock
from .. import state as hub_state
from ..wallet import mandate as mandates

router = APIRouter(prefix="/houses", tags=["houses"])

AZIMUTH = {"south": 180, "east": 90, "west": 270, "north": 0}


class SetupBody(BaseModel):
    has_solar: bool
    kwp: float = Field(3.0, ge=0.5, le=10)
    facing: Literal["south", "east", "west", "north"] = "south"
    subsidized: bool = False
    metering: Literal["net", "gross"] = "net"
    preview: bool = False


def tariffs() -> dict:
    return {
        "retail": config.RETAIL_ENERGY_CHARGE,
        "fee": config.FEE_PER_KWH,
        "buyback": {"unsubsidized": config.BUYBACK_UNSUBSIDISED,
                    "subsidized_upto_2kw": config.BUYBACK_SUBSIDISED_2KW,
                    "subsidized_above_2kw": config.BUYBACK_SUBSIDISED},
        "expected_p2p_price": config.EXPECTED_P2P_PRICE,
    }


def apply_setup(info: HouseInfo, body: SetupBody) -> HouseInfo:
    if not body.has_solar:
        return info.model_copy(update={"roof": None, "buyback_rate": None, "metering": "none",
                                       "subsidized": None, "onboarded": True})
    tilt = info.roof.tilt if info.roof else 13
    roof = Roof(kwp=round(body.kwp, 2), tilt=tilt, azimuth=AZIMUTH[body.facing], inverter_kw=round(body.kwp, 2))
    return info.model_copy(update={"roof": roof, "buyback_rate": config.buyback_rate(body.kwp, body.subsidized),
                                   "metering": body.metering, "subsidized": body.subsidized, "onboarded": True})


def clear_day_kwh(info: HouseInfo) -> float:
    if info.roof is None:
        return 0.0
    return round(sum(solar.roof_kwh_per_block(info.roof, solar.clear_sky_frame(config.SIM_DAY))), 1)


def _save(info: HouseInfo) -> None:
    raw = street.load_raw()
    raw["houses"] = [json.loads(info.model_dump_json()) if h["id"] == info.id else h for h in raw["houses"]]
    config.STREET_FILE.write_text(json.dumps(raw, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


@router.get("/tariffs")
def get_tariffs() -> dict:
    return tariffs()


@router.post("/{house}/setup")
async def setup(request: Request, house: str, body: SetupBody) -> dict:
    """-> {"house": HouseInfo, "clear_day_kwh", "mandate", "tariffs", "saved"}"""
    if house not in HOUSES:
        raise HTTPException(404, f"unknown house {house}")
    houses = hub_state.get().houses
    info = apply_setup(houses[house], body)
    conn = request.app.state.db
    out = {"house": info.model_dump(mode="json"), "clear_day_kwh": clear_day_kwh(info),
           "mandate": mandates.current(conn, house).model_dump(mode="json"), "tariffs": tariffs(),
           "saved": not body.preview}
    if body.preview:
        return out
    houses[house] = info
    conn.execute("INSERT OR REPLACE INTO houses (id, json) VALUES (?, ?)", (house, info.model_dump_json()))
    conn.commit()
    _save(info)
    sim = getattr(request.app.state, "sim", None)
    if sim is not None:
        sim.pv.refresh(house)
    bus.publish(Event(type=ev.HOUSE_UPDATED, sim_time=clock.get().now, house=house,
                      data={"house": out["house"]}))
    return out
