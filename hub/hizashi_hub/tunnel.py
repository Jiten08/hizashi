"""The address phones use to reach the hub: PUBLIC_URL from .env, else the https tunnel
that a local ngrok agent reports on its API (http://127.0.0.1:4040/api/tunnels)."""
import logging
import time

import httpx

from hizashi_shared import config

log = logging.getLogger("hizashi.tunnel")

NGROK_API = "http://127.0.0.1:4040/api/tunnels"
TTL = 15.0                       # seconds between ngrok lookups

_cache: tuple[float, str | None] = (0.0, None)


def ngrok_url() -> str | None:
    """The https URL of the ngrok tunnel forwarding to the hub's port, if ngrok is running."""
    try:
        tunnels = httpx.get(NGROK_API, timeout=0.5).json().get("tunnels", [])
    except Exception:
        return None
    for t in tunnels:
        url = t.get("public_url", "")
        addr = str(t.get("config", {}).get("addr", ""))
        if url.startswith("https://") and addr.endswith(str(config.HUB_PORT)):
            return url.rstrip("/")
    return None


def public_url() -> str | None:
    global _cache
    if config.PUBLIC_URL:
        return config.PUBLIC_URL
    checked, url = _cache
    if time.monotonic() - checked > TTL:
        url = ngrok_url()
        if url != _cache[1]:
            log.info("phones reach the hub at %s", url or "(no tunnel found)")
        _cache = (time.monotonic(), url)
    return url
