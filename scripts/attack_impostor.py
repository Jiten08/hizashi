"""The attack demo: an impostor claiming to be House 16 enters the market selling at ₹40/kWh,
signed with its own key. The market checks the signature against House 16's wallet and
blacklists the key on the spot ("Impostor blacklisted" on the street). Run it again and the
same key bounces at the door.

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
    parser = argparse.ArgumentParser(description="An impostor House 16 tries to sell at ₹40.")
    parser.add_argument("--hub", default=config.HUB_URL)
    args = parser.parse_args()
    r = httpx.post(f"{args.hub}/api/console/events", json={"type": "impostor"}, timeout=15)
    r.raise_for_status()
    print(json.dumps(r.json(), ensure_ascii=False))


if __name__ == "__main__":
    main()
