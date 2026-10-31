"""Make House 16 and House 18 agree to hold their asks at ₹5.60 (KERC 5(a)(ii) price coordination).
After 4 blocks the guard flags them and the wallet stops signing that price.

    python scripts/attack_collusion.py [--hub http://127.0.0.1:8000]

Run it while the roofs are producing (mid-morning to early afternoon), so both houses sell.
"""
import argparse
import json
import sys
from pathlib import Path

import httpx

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "shared"))

from hizashi_shared import config  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description="Make House 16 and House 18 fix their price.")
    parser.add_argument("--hub", default=config.HUB_URL)
    args = parser.parse_args()
    r = httpx.post(f"{args.hub}/api/console/events", json={"type": "collusion"}, timeout=5)
    r.raise_for_status()
    print(json.dumps(r.json()))


if __name__ == "__main__":
    main()
