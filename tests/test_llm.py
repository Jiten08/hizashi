"""Sentence -> rules (N4) and the agents' haggle lines, with Gemini mocked out."""
import json
from datetime import datetime

import pytest

from hizashi_agent import voice
from hizashi_hub.llm import mandate_parser as mp
from hizashi_shared import config, llm
from hizashi_shared.config import TZ
from hizashi_shared.models import BlockRef, Mandate, Offer

CUR = Mandate(house="h14", min_sell_price=4.20, max_buy_price=5.50, daily_budget=50, max_promise_kwh=1.0, approve_above=10)


def fake_llm(monkeypatch, reply):
    calls = []

    async def gen(prompt, **kw):
        calls.append((prompt, kw))
        return reply
    monkeypatch.setattr(llm, "generate", gen)
    return calls


async def test_gemini_changes_are_merged_and_listed(monkeypatch):
    calls = fake_llm(monkeypatch, json.dumps({"max_buy_price": 5, "approve_above": 20, "paused": None}))
    p = await mp.parse("don't buy above ₹5, ask me over ₹20", CUR)
    assert p.source == "gemini"
    assert (p.mandate.max_buy_price, p.mandate.approve_above, p.mandate.min_sell_price) == (5.0, 20.0, 4.20)
    assert p.changes == [{"field": "max_buy_price", "label": "Never buy above", "from": "₹5.50", "to": "₹5.00"},
                         {"field": "approve_above", "label": "Ask me above", "from": "₹10", "to": "₹20"}]
    assert calls[0][1]["schema"] is mp.Changes


async def test_out_of_bounds_values_are_dropped(monkeypatch):
    fake_llm(monkeypatch, json.dumps({"max_buy_price": 400, "min_sell_price": 4.5}))
    p = await mp.parse("whatever", CUR)
    assert p.mandate.max_buy_price == 5.50 and p.mandate.min_sell_price == 4.5
    assert [c["field"] for c in p.changes] == ["min_sell_price"]


async def test_falls_back_to_rules_without_gemini(monkeypatch):
    fake_llm(monkeypatch, None)
    p = await mp.parse("Sell to anyone on the street, never below ₹4.50", CUR)
    assert p.source == "rules"
    assert (p.mandate.counterparties, p.mandate.min_sell_price) == ("street", 4.5)


async def test_nothing_understood_changes_nothing(monkeypatch):
    fake_llm(monkeypatch, "not json")
    p = await mp.parse("what's the weather like", CUR)
    assert p.source == "none" and p.changes == [] and p.mandate == CUR


@pytest.mark.parametrize("text,expected", [
    ("don't buy above ₹5 and ask me over ₹20", {"max_buy_price": 5.0, "approve_above": 20.0}),
    ("keep my spending under 30 rupees a day", {"daily_budget": 30.0}),
    ("promise at most 0.5 kwh per block", {"max_promise_kwh": 0.5}),
    ("pause trading", {"paused": True}),
    ("only my transformer please", {"counterparties": "same_transformer"}),
])
def test_rule_reader(text, expected):
    assert mp.rules_parse(text).model_dump(exclude_none=True) == expected


# --- voice -------------------------------------------------------------------------------------------

def offer(house="h14", to="h12", side="ask", price=5.40, rnd=0) -> Offer:
    return Offer(offer_id="o", negotiation_id="n", block=BlockRef(day="2026-10-31", index=48), side=side,
                 house=house, to=to, kwh=0.4, price=price, round=rnd,
                 expires_at=datetime(2026, 10, 31, 11, tzinfo=TZ), nonce="x")


async def test_voice_uses_gemini_for_talking_houses_and_never_sends_limits(monkeypatch):
    calls = fake_llm(monkeypatch, "Sunny noon ahead, ₹5.40 a unit beats the grid!\nextra line")
    text, source = await voice.line(offer(), {"spare_kwh": 1.2, "solar_kwh": 1.5})
    assert (text, source) == ("Sunny noon ahead, ₹5.40 a unit beats the grid!", "gemini")
    prompt = calls[0][0]
    assert "₹5.40" in prompt and "1.20 kWh spare" in prompt
    assert "4.20" not in prompt and "limit" not in prompt.lower()      # no owner limits in the prompt


async def test_voice_rejects_a_line_with_the_wrong_price(monkeypatch):
    fake_llm(monkeypatch, "Let's settle at ₹4.80, neighbour.")
    text, source = await voice.line(offer(side="bid", price=4.00, house="h12", to="h14"), {})
    assert source == "template" and "₹4.00" in text


async def test_voice_template_when_gemini_misses_or_house_is_quiet(monkeypatch):
    calls = fake_llm(monkeypatch, None)
    assert await voice.line(offer(side="bid", price=4.30, rnd=1, house="h12", to="h14"), {}) == (
        "Meet me at ₹4.30? I'm short at 12:00–12:15 and you'd beat the buyback.", "template")
    text, source = await voice.line(offer(house="h16"), {})
    assert source == "template" and "₹5.40" in text
    assert len(calls) == 1 and "h16" not in config.LLM_VOICE_HOUSES


async def test_llm_generate_without_key_returns_none(monkeypatch):
    monkeypatch.setattr(config, "GEMINI_API_KEY", "")
    assert await llm.generate("hi") is None


def test_honest_lines_quote_only_the_signed_price_or_the_grid():
    assert voice.honest("₹4.92 beats the grid's ₹5.80!", 4.92)
    assert not voice.honest("₹4.92 now, or ₹4.50 if you hurry", 4.92)
    assert not voice.honest("a great price today", 4.92)
