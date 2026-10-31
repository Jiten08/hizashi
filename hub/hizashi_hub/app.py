"""Hizashi hub: FastAPI app.

Startup: load config + street, open DB, load mandates, start the state consumer and
the simulated clock. Routers under /api, WebSocket at /ws, Twilio at /webhooks/twilio.
web/dist is served at / with SPA fallback (unknown non-/api paths return index.html).

    uvicorn hizashi_hub.app:app --port 8000

Startup also loads (or fetches) the day's weather and builds the simulated street
(sim/world.py): meters, console events, the market lifecycle (auction + settlement).
The previous run's day rows are cleared, since the clock always starts at 05:00.
Not yet wired: guard rules (N2).
"""
import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse

from hizashi_shared import config, street
from hizashi_shared.models import Mandate

from . import clock, db, state, ws
from .sim import weather
from .sim.world import Sim, clear_day
from .api import router as api_router
from .api import webhooks

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s")
log = logging.getLogger("hizashi.hub")

RESERVED_PREFIXES = ("api/", "ws", "webhooks/", "docs", "openapi.json")


def load_mandates(conn) -> dict[str, Mandate]:
    from_db = db.latest_mandates(conn)
    if from_db:
        return {h: Mandate.model_validate(m) for h, m in from_db.items()}
    return street.load_mandates()


@asynccontextmanager
async def lifespan(app: FastAPI):
    houses = street.load_houses()
    conn = db.connect(config.DB_PATH)
    db.init(conn)
    app.state.db = conn
    clear_day(conn)
    hub_state = state.init(houses, load_mandates(conn), config.SIM_SPEED)
    frame, source = await weather.load_weather(config.SIM_DAY)
    hub_state.weather_source = source
    tasks = [asyncio.create_task(hub_state.run(), name="state")]
    await asyncio.sleep(0)  # let the state consumer subscribe before the clock publishes
    sim_clock = clock.init(config.SIM_DAY, config.SIM_SPEED)
    app.state.sim = Sim(conn, hub_state.houses, hub_state.mandates, frame)
    app.state.sim.wire(sim_clock)
    sim_clock.start()
    log.info("hub up: day %s at %sx, %d houses", config.SIM_DAY, config.SIM_SPEED, len(houses))
    try:
        yield
    finally:
        await sim_clock.stop()
        for t in tasks:
            t.cancel()
        conn.close()


app = FastAPI(title="Hizashi hub", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])
app.include_router(api_router)
app.include_router(webhooks.router)
app.include_router(ws.router)


@app.get("/{path:path}", include_in_schema=False)
def spa(path: str):
    if path.startswith(RESERVED_PREFIXES):
        raise HTTPException(404)
    dist = config.WEB_DIST.resolve()
    if path:
        f = (dist / path).resolve()
        if f.is_file() and f.is_relative_to(dist):
            return FileResponse(f)
    index = dist / "index.html"
    if index.is_file():
        return FileResponse(index)
    return HTMLResponse("<h1>Hizashi hub</h1><p>web/dist not built: cd web && npm run build</p>")
