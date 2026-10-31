"""Generate a meter key and a wallet key per house, plus keys/market.key.

Writes base64 seeds to keys/<house>.meter.key and keys/<house>.wallet.key and the
public keys into data/street.json. Idempotent: existing keys are kept unless --force.

    python scripts/gen_keys.py [--force]
"""
import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "shared"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from shared.hizashi_shared import config, crypto  # noqa: E402
from shared.hizashi_shared.models import HOUSES  # noqa: E402


def key_path(name: str) -> Path:
    return config.KEYS_DIR / f"{name}.key"


def ensure_key(name: str, force: bool) -> tuple[str, bool]:
    """Return (public key b64, created?) for keys/<name>.key."""
    path = key_path(name)
    if path.exists() and not force:
        return crypto.pub_b64(crypto.load_key(path)), False
    key = crypto.new_key()
    path.write_text(crypto.seed_b64(key) + "\n")
    return crypto.pub_b64(key), True


def public_keys(force: bool = False) -> dict[str, str]:
    config.KEYS_DIR.mkdir(exist_ok=True)
    pubs = {}
    for name in [f"{h}.{kind}" for h in HOUSES for kind in ("meter", "wallet")] + ["market"]:
        pubs[name], created = ensure_key(name, force)
        print(f"{'created' if created else 'kept   '} keys/{name}.key")
    return pubs


def apply_pubkeys(street: dict, pubs: dict[str, str]) -> dict:
    for h in street["houses"]:
        h["meter_pubkey"] = pubs.get(f"{h['id']}.meter", h.get("meter_pubkey"))
        h["wallet_pubkey"] = pubs.get(f"{h['id']}.wallet", h.get("wallet_pubkey"))
    street["market_pubkey"] = pubs.get("market", street.get("market_pubkey"))
    return street


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate meter, wallet and market keys.")
    parser.add_argument("--force", action="store_true", help="regenerate all keys")
    args = parser.parse_args()
    pubs = public_keys(args.force)
    if config.STREET_FILE.exists():
        street = json.loads(config.STREET_FILE.read_text(encoding="utf-8"))
    else:
        from seed import default_street
        street = default_street()
    apply_pubkeys(street, pubs)
    config.STREET_FILE.parent.mkdir(parents=True, exist_ok=True)
    config.STREET_FILE.write_text(json.dumps(street, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"public keys written to {config.STREET_FILE.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
