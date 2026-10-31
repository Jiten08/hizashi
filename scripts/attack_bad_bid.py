"""Post the console bad_bid event; h14's agent tries a ₹40 bid and the wallet refuses it.

    python scripts/attack_bad_bid.py [--house h14] [--hub http://127.0.0.1:8000]

Watch /h/h14: a red BLOCKED card ("Tried to buy at ₹40.00/unit. Your max is ₹5.50...").
"""
import argparse
import json
import sys
from pathlib import Path

import httpx

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "shared"))

from hizashi_shared import config  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description="Make a house agent try a ₹40 bid.")
    parser.add_argument("--house", default="h14")
    parser.add_argument("--hub", default=config.HUB_URL)
    args = parser.parse_args()
    r = httpx.post(f"{args.hub}/api/console/events", json={"type": "bad_bid", "house": args.house}, timeout=5)
    r.raise_for_status()
    print(json.dumps(r.json()))


if __name__ == "__main__":
    main()
