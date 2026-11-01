"""The address phones use to reach the hub, in order: PUBLIC_URL from .env; the https
tunnel a local ngrok agent reports (http://127.0.0.1:4040/api/tunnels); else this
laptop's address on the local Wi-Fi (http://192.168.x.x:8000), which works for any
phone on the same network.

When the hub starts and no tunnel is running, it starts ngrok itself (if installed; AUTO_NGROK=0 turns
this off): on PUBLIC_URL when that is an ngrok domain, so the QR codes stay the same every run.
"""
import logging
import os
import shutil
import socket
import subprocess
import threading
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


NGROK_HOSTS = (".ngrok-free.dev", ".ngrok-free.app", ".ngrok.app", ".ngrok.dev", ".ngrok.io")


def _ngrok_domain(url: str) -> bool:
    host = url.split("://", 1)[-1].split("/", 1)[0]
    return host.endswith(NGROK_HOSTS)


def start_ngrok() -> None:
    """Start ngrok in the background unless a tunnel is already up: on PUBLIC_URL when that is an
    ngrok domain (the account's fixed one, so the QR codes never change), else on a new address.
    A failure only means phones need the laptop's Wi-Fi; the hub carries on."""
    global _proc
    if os.environ.get("AUTO_NGROK", "1") in ("0", "false", "False") or ngrok_url():
        return
    if config.PUBLIC_URL and not _ngrok_domain(config.PUBLIC_URL):
        return                          # someone else's tunnel (cloudflared etc.)
    exe = shutil.which("ngrok")
    if exe is None:
        log.warning("ngrok isn't installed; phones need the same Wi-Fi as this laptop")
        return
    args = [exe, "http", str(config.HUB_PORT), "--log=stdout"]
    if config.PUBLIC_URL:
        args.append(f"--url={config.PUBLIC_URL}")
    try:
        _proc = subprocess.Popen(args, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except OSError as e:
        log.warning("couldn't start ngrok (%s); phones need the same Wi-Fi as this laptop", e)
        return
    threading.Thread(target=_report, args=(_proc,), daemon=True).start()


def _report(proc: subprocess.Popen) -> None:
    """Say in the hub's log whether the tunnel came up (ngrok exits at once on a bad token or domain)."""
    for _ in range(30):
        if proc.poll() is not None:
            log.warning("ngrok stopped (exit %s); run `ngrok http 8000%s` to see why", proc.returncode,
                        f" --url={config.PUBLIC_URL}" if config.PUBLIC_URL else "")
            return
        url = ngrok_url()
        if url:
            log.info("phones reach the hub at %s (ngrok)", url)
            return
        time.sleep(0.5)
    log.warning("ngrok started but no tunnel showed up after 15 s")


def stop_ngrok() -> None:
    global _proc
    if _proc is not None and _proc.poll() is None:
        _proc.terminate()
    _proc = None
