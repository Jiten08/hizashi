"""The hub serves the dashboard (web/dist) at / and the phone PWA (mobile/dist) at /app/."""
import pytest
from fastapi.testclient import TestClient

from hizashi_hub import app as hub_app
from hizashi_shared import config


@pytest.fixture
def client(tmp_path, monkeypatch):
    web, mobile = tmp_path / "web", tmp_path / "mobile"
    for d, name in ((web, "dashboard"), (mobile, "phone")):
        (d / "assets").mkdir(parents=True)
        (d / "index.html").write_text(f"<h1>{name}</h1>")
        (d / "assets" / "a.js").write_text("1")
    (mobile / "manifest.webmanifest").write_text("{}")
    (mobile / "sw.js").write_text("//")
    monkeypatch.setattr(config, "WEB_DIST", web)
    monkeypatch.setattr(config, "MOBILE_DIST", mobile)
    return TestClient(hub_app.app)          # no `with`: the lifespan (clock, DB) doesn't start


def test_dashboard_at_root(client):
    assert "dashboard" in client.get("/").text
    assert "dashboard" in client.get("/console").text          # SPA fallback
    assert client.get("/assets/a.js").status_code == 200


def test_phone_app_at_app(client):
    assert client.get("/app", follow_redirects=False).headers["location"] == "/app/"
    assert "phone" in client.get("/app/?house=h14").text
    assert "phone" in client.get("/app/anything").text         # SPA fallback stays in the phone app
    m = client.get("/app/manifest.webmanifest")
    assert m.headers["content-type"].startswith("application/manifest+json")
    sw = client.get("/app/sw.js")
    assert sw.headers["cache-control"] == "no-cache"


def test_api_and_ws_not_swallowed(client):
    assert client.get("/api/nope").status_code == 404
    assert "dashboard" in client.get("/application-notes").text  # only app/ is reserved
