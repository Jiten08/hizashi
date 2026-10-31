from datetime import datetime

from hizashi_shared import crypto
from hizashi_shared.config import TZ
from hizashi_shared.models import BlockRef, Contract, Offer


def make_offer(**kw) -> Offer:
    base = dict(
        offer_id="o1", negotiation_id="n1", block=BlockRef(day="2026-10-31", index=48),
        side="ask", house="h12", to="h14", kwh=0.2, price=4.68, round=3,
        expires_at=datetime(2026, 10, 31, 11, 0, tzinfo=TZ), nonce="abc",
    )
    base.update(kw)
    return Offer(**base)


def test_sign_verify_roundtrip():
    key = crypto.new_key()
    offer = make_offer()
    sig = crypto.sign(offer, key)
    assert crypto.verify(offer, sig, crypto.pub_b64(key))


def test_signature_fields_excluded_from_canonical():
    key = crypto.new_key()
    offer = make_offer()
    offer.signature = crypto.sign(offer, key)
    assert b"signature" not in crypto.canonical(offer)
    assert crypto.verify(offer, offer.signature, crypto.pub_b64(key))


def test_tampered_field_fails():
    key = crypto.new_key()
    offer = make_offer()
    sig = crypto.sign(offer, key)
    assert not crypto.verify(offer.model_copy(update={"price": 40.0}), sig, crypto.pub_b64(key))
    assert not crypto.verify(offer.model_copy(update={"to": "h16"}), sig, crypto.pub_b64(key))


def test_wrong_key_and_missing_sig_fail():
    offer = make_offer()
    sig = crypto.sign(offer, crypto.new_key())
    assert not crypto.verify(offer, sig, crypto.pub_b64(crypto.new_key()))
    assert not crypto.verify(offer, None, crypto.pub_b64(crypto.new_key()))
    assert not crypto.verify(offer, "not-base64!!", crypto.pub_b64(crypto.new_key()))


def test_int_float_roundtrip_via_dict_then_model_validate():
    """A2A data parts turn ints into floats; re-parsing with pydantic restores them."""
    key = crypto.new_key()
    offer = make_offer()
    offer.signature = crypto.sign(offer, key)
    d = offer.model_dump(mode="json")
    d["round"] = float(d["round"])              # what protobuf Value does: 3 -> 3.0
    d["block"]["index"] = float(d["block"]["index"])
    parsed = Offer.model_validate(d)
    assert parsed.round == 3 and isinstance(parsed.round, int)
    assert crypto.verify(parsed, parsed.signature, crypto.pub_b64(key))


def test_contract_multiple_signatures():
    seller, buyer, market = crypto.new_key(), crypto.new_key(), crypto.new_key()
    c = Contract(contract_id="c1", negotiation_id="n1", block=BlockRef(day="2026-10-31", index=48),
                 seller="h12", buyer="h14", kwh=0.2, price=4.68, route="haggle")
    c.seller_sig = crypto.sign(c, seller)
    c.buyer_sig = crypto.sign(c, buyer)
    c.market_sig = crypto.sign(c, market)
    for sig, key in ((c.seller_sig, seller), (c.buyer_sig, buyer), (c.market_sig, market)):
        assert crypto.verify(c, sig, crypto.pub_b64(key))


def test_load_key(tmp_path):
    key = crypto.new_key()
    path = tmp_path / "x.key"
    path.write_text(crypto.seed_b64(key) + "\n")
    assert crypto.pub_b64(crypto.load_key(path)) == crypto.pub_b64(key)
