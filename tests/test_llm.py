"""Sentence -> rules (N4), with Gemini mocked out."""
import json

import pytest

from hizashi_hub.llm import mandate_parser as mp
from hizashi_shared import llm
from hizashi_shared.models import Mandate

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
