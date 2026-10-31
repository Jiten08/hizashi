"""Send House 14's agent a real A2A ask that claims to be House 16, signed with a random key.
The agent refuses it and reports to the guard (a "Forged offer refused" flag on the street).

    python scripts/attack_fake_seller.py [--target h14] [--hub http://127.0.0.1:8000]
"""
import argparse
import json
import sys
from pathlib import Path

import httpx

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "shared"))

from hizashi_shared import config  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description="Forge an A2A ask from House 16 to House 14.")
    parser.add_argument("--target", default="h14")
    parser.add_argument("--hub", default=config.HUB_URL)
    args = parser.parse_args()
    r = httpx.post(f"{args.hub}/api/console/events", json={"type": "rogue_seller", "house": args.target}, timeout=15)
    r.raise_for_status()
    print(json.dumps(r.json()))


if __name__ == "__main__":
    main()
