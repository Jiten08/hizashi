"""Write data/street.json (section 5), the four household profiles and default
mandates, then recreate hub/hizashi.db. Existing public keys are kept; key files
in keys/ take precedence.

    python scripts/seed.py
"""
import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "shared"))
sys.path.insert(0, str(ROOT / "hub"))

from hizashi_shared import config, crypto  # noqa: E402
from hizashi_shared.models import HouseInfo, Mandate  # noqa: E402

PROFILE_SOURCE = "synthetic, shaped after Prayas eMARC load curves"

# (hour, mean kWh per block) anchor points; interpolated, then smoothed (no cliffs).
PROFILE_ANCHORS: dict[str, list[tuple[float, float]]] = {
    "couple_away_day": [(0, .05), (6, .05), (6.75, .25), (8.25, .25), (9.5, .14), (10, .12),
                        (13.5, .16), (17, .14), (18.5, .35), (22, .35), (23.5, .08), (24, .05)],
    "wfh_ac": [(0, .10), (6, .10), (6.75, .25), (8.25, .25), (9.5, .28), (10, .30),
               (17, .30), (18.5, .40), (22, .40), (23.5, .15), (24, .10)],
    "family_medium": [(0, .06), (6, .06), (6.75, .30), (8.25, .30), (9.5, .20), (10, .18),
                      (17, .18), (18.5, .40), (22, .40), (23.5, .10), (24, .06)],
    "heavy_appliances": [(0, .08), (6, .08), (6.75, .30), (8.25, .30), (9.5, .28), (10, .28),
                         (13, .35), (17, .30), (18.5, .45), (22, .45), (23.5, .12), (24, .08)],
}


def _house(id_: str, n: int, roof, profile: str, buyback: float | None, metering: str) -> dict:
    return {
        "id": id_, "label": f"House {n}", "transformer": "T1",
        "roof": None if roof is None else dict(zip(("kwp", "tilt", "azimuth", "inverter_kw"), roof)),
        "profile": profile, "buyback_rate": buyback, "metering": metering,
        "agent_url": f"http://127.0.0.1:{config.AGENT_PORTS[id_]}/",
        "meter_pubkey": None, "wallet_pubkey": None,
    }


def default_street() -> dict:
    houses = [
        _house("h12", 12, (5.0, 13, 180, 5.0), "couple_away_day", 3.89, "net"),
        _house("h14", 14, None, "wfh_ac", None, "none"),
        _house("h16", 16, (3.0, 15, 90, 3.0), "family_medium", 2.14, "net"),
        _house("h18", 18, (2.0, 13, 180, 2.0), "heavy_appliances", 1.96, "net"),
    ]
    mandates = [
        Mandate(house="h12", min_sell_price=4.20, max_buy_price=5.50, daily_budget=50, max_promise_kwh=1.0, approve_above=10),
        Mandate(house="h14", min_sell_price=4.20, max_buy_price=5.50, daily_budget=50, max_promise_kwh=1.0, approve_above=10),
        Mandate(house="h16", min_sell_price=3.80, max_buy_price=5.40, daily_budget=50, max_promise_kwh=1.0, approve_above=25),
        Mandate(house="h18", min_sell_price=3.50, max_buy_price=5.40, daily_budget=60, max_promise_kwh=1.0, approve_above=25),
    ]
    for h in houses:
        HouseInfo.model_validate(h)
    return {
        "street": "Banashankari demo street",
        "transformers": ["T1"],
        "market_pubkey": None,
        "houses": houses,
        "mandates": [m.model_dump(mode="json") for m in mandates],
    }


def build_profile(name: str) -> dict:
    hours, values = zip(*PROFILE_ANCHORS[name])
    mids = (np.arange(config.BLOCKS_PER_DAY) + 0.5) * config.BLOCK_MINUTES / 60
    mean = np.interp(mids, hours, values)
    kernel = np.ones(5) / 5
    for _ in range(2):  # circular moving average softens the corners
        padded = np.concatenate([mean[-2:], mean, mean[:2]])
        mean = np.convolve(padded, kernel, mode="valid")
    mean = np.round(mean, 4)
    std = np.round(mean * 0.20, 4)
    return {"name": name, "source": PROFILE_SOURCE, "mean": mean.tolist(), "std": std.tolist()}


def merge_pubkeys(street: dict) -> dict:
    """Keep existing pubkeys from street.json; key files in keys/ take precedence."""
    old: dict[str, dict] = {}
    if config.STREET_FILE.exists():
        old_raw = json.loads(config.STREET_FILE.read_text(encoding="utf-8"))
        old = {h["id"]: h for h in old_raw.get("houses", [])}
        street["market_pubkey"] = old_raw.get("market_pubkey")
    for h in street["houses"]:
        for kind in ("meter", "wallet"):
            field = f"{kind}_pubkey"
            path = config.KEYS_DIR / f"{h['id']}.{kind}.key"
            h[field] = crypto.pub_b64(crypto.load_key(path)) if path.exists() else old.get(h["id"], {}).get(field)
    market = config.KEYS_DIR / "market.key"
    if market.exists():
        street["market_pubkey"] = crypto.pub_b64(crypto.load_key(market))
    return street


def main() -> None:
    street = merge_pubkeys(default_street())
    config.STREET_FILE.parent.mkdir(parents=True, exist_ok=True)
    config.STREET_FILE.write_text(json.dumps(street, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"wrote {config.STREET_FILE.relative_to(ROOT)}")

    config.PROFILES_DIR.mkdir(parents=True, exist_ok=True)
    for name in PROFILE_ANCHORS:
        path = config.PROFILES_DIR / f"{name}.json"
        path.write_text(json.dumps(build_profile(name), indent=1) + "\n", encoding="utf-8")
        print(f"wrote {path.relative_to(ROOT)}")

    missing = [h["id"] for h in street["houses"] if not h["wallet_pubkey"]]
    if missing:
        print(f"warning: no public keys for {missing}; run scripts/gen_keys.py")

    from hizashi_hub import db
    db.recreate(config.DB_PATH)
    conn = db.connect(config.DB_PATH)
    db.seed_street(conn, street)
    conn.close()
    print(f"recreated {config.DB_PATH.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
