"""The attack demo: "House 20", an outsider with no wallet on the street's registry, enters the
market selling at ₹40/kWh. The market checks every seller against the registry and blacklists
its key on the spot ("Outsider blacklisted" on the street). Run it again and the same key
bounces at the door.

    python scripts/attack_impostor.py [--hub http://127.0.0.1:8000]
"""
import argparse
import json
import sys
from pathlib import Path

import httpx

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "shared"))

from hizashi_shared import config  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description="An outsider House 20 tries to sell at ₹40.")
    parser.add_argument("--hub", default=config.HUB_URL)
    args = parser.parse_args()
    r = httpx.post(f"{args.hub}/api/console/events", json={"type": "impostor"}, timeout=15)
    r.raise_for_status()
    print(json.dumps(r.json(), ensure_ascii=False))


if __name__ == "__main__":
    main()
