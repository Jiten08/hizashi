"""The address phones use to reach the hub, in order: PUBLIC_URL from .env; the https
tunnel a local ngrok agent reports (http://127.0.0.1:4040/api/tunnels); else this
laptop's address on the local Wi-Fi (http://192.168.x.x:8000), which works for any
phone on the same network.

When the hub starts without PUBLIC_URL or a running tunnel, it starts ngrok itself (if ngrok is
installed; AUTO_NGROK=0 turns this off), so phones on any network can scan the QR codes.
"""
import logging
import os
import shutil
import socket
import subprocess
import time

import httpx

from hizashi_shared import config

log = logging.getLogger("hizashi.tunnel")

NGROK_API = "http://127.0.0.1:4040/api/tunnels"
TTL = 15.0                       # seconds between lookups
PENDING_TTL = 2.0                # while the ngrok we started comes up

_proc: subprocess.Popen | None = None

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
    starting = _proc is not None and _proc.poll() is None and not (url or "").startswith("https://")
    if time.monotonic() - checked > (PENDING_TTL if starting else TTL):
        url = ngrok_url() or lan_url()
        if url != _cache[1]:
            log.info("phones reach the hub at %s", url or "(no network address found)")
        _cache = (time.monotonic(), url)
    return url


def start_ngrok() -> None:
    """Start `ngrok http 8000` in the background unless there is already a public address.
    A failure only means the QR codes use the Wi-Fi address; the hub carries on."""
    global _proc
    if config.PUBLIC_URL or os.environ.get("AUTO_NGROK", "1") in ("0", "false", "False") or ngrok_url():
        return
    exe = shutil.which("ngrok")
    if exe is None:
        log.info("ngrok isn't installed; phones need the same Wi-Fi as this laptop")
        return
    try:
        _proc = subprocess.Popen([exe, "http", str(config.HUB_PORT), "--log=stdout"],
                                 stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        log.info("started ngrok for the phones' QR codes")
    except OSError as e:
        log.warning("couldn't start ngrok (%s); phones need the same Wi-Fi as this laptop", e)


def stop_ngrok() -> None:
    global _proc
    if _proc is not None and _proc.poll() is None:
        _proc.terminate()
    _proc = None
