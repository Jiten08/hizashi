"""The address phones use to reach the hub, in order: PUBLIC_URL from .env; the https
tunnel a local ngrok agent reports (http://127.0.0.1:4040/api/tunnels); else this
laptop's address on the local Wi-Fi (http://192.168.x.x:8000), which works for any
phone on the same network."""
import logging
import socket
import time

import httpx

from hizashi_shared import config

log = logging.getLogger("hizashi.tunnel")

NGROK_API = "http://127.0.0.1:4040/api/tunnels"
TTL = 15.0                       # seconds between lookups

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


def lan_url() -> str | None:
    """http://<this machine's LAN IP>:8000. The UDP connect sends nothing; it only picks
    the interface the OS would route through."""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.connect(("10.255.255.255", 1))
            ip = s.getsockname()[0]
    except OSError:
        return None
    return None if ip.startswith("127.") else f"http://{ip}:{config.HUB_PORT}"


def public_url() -> str | None:
    global _cache
    if config.PUBLIC_URL:
        return config.PUBLIC_URL
    checked, url = _cache
    if time.monotonic() - checked > TTL:
        url = ngrok_url() or lan_url()
        if url != _cache[1]:
            log.info("phones reach the hub at %s", url or "(no network address found)")
        _cache = (time.monotonic(), url)
    return url
