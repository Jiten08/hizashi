import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "shared"))

from attack_fake_seller import build_fake_offer, classify_reply
from hizashi_shared import crypto
from hizashi_shared.models import BlockRef, Offer

DAY = "2026-10-31"


def test_build_fake_offer():
    """Verify build_fake_offer returns a valid Offer claiming to be h16 selling to h14 with high price."""
    block = BlockRef(day=DAY, index=48)
    offer, key = build_fake_offer(block, kwh=0.40, price=9.00)

    assert isinstance(offer, Offer)
    assert offer.house == "h16"
    assert offer.to == "h14"
    assert offer.side == "ask"
    assert offer.kwh == 0.40
    assert offer.price == 9.00  # High price > 5.80 BESCOM rate
    assert offer.round == 0
    assert offer.signature is not None
    assert offer.block.index == 48
    assert offer.block.day == DAY


def test_fake_offer_signature_verification():
    """Verify signature passes with the throwaway key and fails with h16's real public key."""
    block = BlockRef(day=DAY, index=48)
    offer, fake_key = build_fake_offer(block, kwh=0.40, price=9.00)

    # 1. Verify against the ephemeral key used to sign it
    fake_pub = crypto.pub_b64(fake_key)
    assert crypto.verify(offer, offer.signature, fake_pub) is True

    # 2. Verify against House 16's real key from street.json
    street_file = ROOT / "data" / "street.json"
    h16_real_pub = None
    if street_file.exists():
        data = json.loads(street_file.read_text(encoding="utf-8"))
        for h in data.get("houses", []):
            if h.get("id") == "h16":
                h16_real_pub = h.get("wallet_pubkey")
                break

    if not h16_real_pub:
        # Fallback to an independent real-looking key if street.json doesn't have it
        h16_real_pub = crypto.pub_b64(crypto.new_key())

    # The signature must NOT verify against h16's official public key
    assert crypto.verify(offer, offer.signature, h16_real_pub) is False


def test_random_keys_differ_on_each_call():
    """Verify throwaway key is generated in memory and differs on every call."""
    block = BlockRef(day=DAY, index=48)
    offer1, key1 = build_fake_offer(block)
    offer2, key2 = build_fake_offer(block)

    pub1 = crypto.pub_b64(key1)
    pub2 = crypto.pub_b64(key2)

    assert pub1 != pub2
    assert offer1.signature != offer2.signature
    assert offer1.offer_id != offer2.offer_id
    assert offer1.nonce != offer2.nonce


def test_classify_reply_rejection():
    """Verify result classifier maps refused/bad-signature replies to exit_code 0."""
    # Bad signature rejection
    is_rejected, msg, code = classify_reply(
        "TASK_STATE_REJECTED",
        [{"type": "refuse", "reason": "bad signature"}],
    )
    assert is_rejected is True
    assert code == 0
    assert "bad signature" in msg

    # Task state rejected without explicit parts
    is_rejected, msg, code = classify_reply("TASK_STATE_REJECTED", [])
    assert is_rejected is True
    assert code == 0

    # Price / other refusal
    is_rejected, msg, code = classify_reply(
        None,
        [{"type": "refuse", "reason": "price above limit"}],
    )
    assert is_rejected is True
    assert code == 0


def test_classify_reply_accepted_or_booked_is_bug():
    """Verify result classifier maps accept/bid replies to exit_code 1 (critical bug)."""
    # Accept reply
    is_rejected, msg, code = classify_reply(
        "TASK_STATE_COMPLETED",
        [{"type": "accept", "price": 9.00}],
    )
    assert is_rejected is False
    assert code == 1
    assert "CRITICAL BUG" in msg

    # Bid counter-offer
    is_rejected, msg, code = classify_reply(
        "TASK_STATE_INPUT_REQUIRED",
        [{"type": "bid", "price": 4.50}],
    )
    assert is_rejected is False
    assert code == 1
    assert "CRITICAL BUG" in msg

