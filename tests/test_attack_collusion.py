import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "shared"))

from attack_collusion import build_collusion_order, get_wallet_key
from hizashi_shared import blocks, config, crypto
from hizashi_shared.models import BlockRef, Offer

DAY = "2026-10-31"


def test_build_collusion_order():
    """Verify build_collusion_order constructs valid payload matching spec requirements."""
    block = BlockRef(day=DAY, index=32)
    payload = build_collusion_order("h16", block, price=4.80, kwh=0.50)

    assert "offer" in payload
    data = payload["offer"]

    assert data["house"] == "h16"
    assert data["block"]["index"] == 32
    assert data["block"]["day"] == DAY
    assert data["kwh"] == 0.50
    assert data["price"] == 4.80
    assert data["is_bid"] is False
    assert data["side"] == "ask"
    assert data["to"] is None
    assert data["round"] == 0
    assert data["signature"] is not None

    # Verify Pydantic model validation passes
    offer_obj = Offer.model_validate(data)
    assert offer_obj.house == "h16"
    assert offer_obj.price == 4.80
    assert offer_obj.side == "ask"
    assert offer_obj.to is None


def test_collusion_identical_asks():
    """Verify identical asks can be constructed for both h16 and h18 across 4 consecutive blocks."""
    price = 4.80
    kwh = 0.50
    h16_orders = []
    h18_orders = []

    for idx in range(30, 34):
        block = BlockRef(day=DAY, index=idx)
        o16 = build_collusion_order("h16", block, price=price, kwh=kwh)
        o18 = build_collusion_order("h18", block, price=price, kwh=kwh)

        h16_orders.append(o16["offer"])
        h18_orders.append(o18["offer"])

    assert len(h16_orders) == 4
    assert len(h18_orders) == 4

    for i in range(4):
        # Identical prices across houses and consecutive blocks
        assert h16_orders[i]["price"] == price
        assert h18_orders[i]["price"] == price
        assert h16_orders[i]["price"] == h18_orders[i]["price"]
        assert h16_orders[i]["kwh"] == kwh
        assert h16_orders[i]["kwh"] == h18_orders[i]["kwh"]
        assert h16_orders[i]["block"]["index"] == 30 + i
        assert h18_orders[i]["block"]["index"] == 30 + i


def test_collusion_signature_verification():
    """Verify that generated collusion orders are signed with house's key and verify."""
    key16 = crypto.new_key()
    block = BlockRef(day=DAY, index=32)
    payload16 = build_collusion_order("h16", block, price=4.80, kwh=0.50, key=key16)

    offer16 = Offer.model_validate(payload16["offer"])
    pub16 = crypto.pub_b64(key16)

    # Validates with h16's key
    assert crypto.verify(offer16, offer16.signature, pub16) is True

    # Fails with another house's key
    key18 = crypto.new_key()
    pub18 = crypto.pub_b64(key18)
    assert crypto.verify(offer16, offer16.signature, pub18) is False


def test_collusion_tokens_and_payload_structure():
    """Verify bearer tokens for h16 and h18 match expected dev conventions."""
    token16 = config.AGENT_TOKENS.get("h16", "dev-h16")
    token18 = config.AGENT_TOKENS.get("h18", "dev-h18")

    assert "h16" in token16
    assert "h18" in token18

    # Ensure gate_close timestamp is populated and valid
    block = BlockRef(day=DAY, index=35)
    payload = build_collusion_order("h16", block, price=4.80, kwh=0.50)
    assert payload["offer"]["expires_at"] is not None
