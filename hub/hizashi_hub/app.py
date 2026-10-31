"""Hizashi hub: FastAPI app.

Startup: load config + street, open DB, load mandates, start the state consumer and
the simulated clock. Routers under /api, WebSocket at /ws, Twilio at /webhooks/twilio.
web/dist is served at / with SPA fallback (unknown non-/api paths return index.html).

    uvicorn hizashi_hub.app:app --port 8000

Startup also loads (or fetches) the day's weather and builds the simulated street
(sim/world.py): meters, console events, the market lifecycle (auction + settlement).
The previous run's day rows are cleared, since the clock always starts at 05:00.
Owners' away / guests schedules are loaded into the sim, and a Web Push task pings
owners' phones when an approval is requested. The guard (N2) watches meter readings and
is consulted by the wallet and booking.
"""
import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse, RedirectResponse, Response

from hizashi_shared import config, street
from hizashi_shared.models import Mandate

from . import clock, db, schedules, state, ws
from .guard import watch
from .notify import webpush
from .sim import weather
from .sim.world import Sim, clear_day
from .api import router as api_router
from .api import webhooks

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s")
log = logging.getLogger("hizashi.hub")

RESERVED_PREFIXES = ("api/", "ws", "webhooks/", "docs", "openapi.json", "app/")
MEDIA_TYPES = {".webmanifest": "application/manifest+json", ".js": "text/javascript", ".glb": "model/gltf-binary"}


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
    schedules.sync(conn, app.state.sim.events)
    hub_state.schedules = {h: [s.model_dump(mode="json") for s in schedules.listing(conn, h, config.SIM_DAY)]
                           for h in houses}
    tasks.append(asyncio.create_task(webpush.run(conn), name="webpush"))
    tasks.append(asyncio.create_task(watch.init(hub_state.houses).run(conn), name="guard"))
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


def _serve(dist, path: str, missing: str):
    """A file from a Vite build, else its index.html (SPA fallback)."""
    dist = dist.resolve()
    if path:
        f = (dist / path).resolve()
        if f.is_file() and f.is_relative_to(dist):
            headers = {"Cache-Control": "no-cache"} if f.name in ("sw.js", "push-sw.js", "index.html", "manifest.webmanifest") else None
            return FileResponse(f, media_type=MEDIA_TYPES.get(f.suffix), headers=headers)
    index = dist / "index.html"
    if index.is_file():
        return FileResponse(index, headers={"Cache-Control": "no-cache"})
    return HTMLResponse(f"<h1>Hizashi hub</h1><p>{missing}</p>")


# Earlier builds installed a service worker for the whole site (scope /). Phones keep using it,
# and it keeps serving the old cached app, until /sw.js changes. This one removes itself and its caches
# and reloads open pages, so those phones get the current dashboard and /app/ on their next visit.
RETIRE_SW = """
self.addEventListener('install', () => self.skipWaiting());
self.addEventListener('activate', (event) => {
  event.waitUntil((async () => {
    for (const key of await caches.keys()) await caches.delete(key);
    await self.registration.unregister();
    for (const client of await self.clients.matchAll({ type: 'window' })) client.navigate(client.url);
  })());
});
"""


@app.get("/sw.js", include_in_schema=False)
def retire_root_service_worker():
    return Response(RETIRE_SW, media_type="text/javascript", headers={"Cache-Control": "no-cache"})


@app.get("/app", include_in_schema=False)
def phone_app_root():
    return RedirectResponse("/app/")


@app.get("/app/{path:path}", include_in_schema=False)
def phone_app(path: str):
    """The owner's phone app (mobile/, a PWA)."""
    return _serve(config.MOBILE_DIST, path, "mobile/dist not built: cd mobile && npm run build")


@app.get("/{path:path}", include_in_schema=False)
def dashboard(path: str):
    """The street dashboard (web/), for the laptop."""
    if path.startswith(RESERVED_PREFIXES):
        raise HTTPException(404)
    return _serve(config.WEB_DIST, path, "web/dist not built: cd web && npm run build")
