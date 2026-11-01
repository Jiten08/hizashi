"""Sentence -> proposed Mandate (N4). The one place an LLM touches the owner's rules, and it
only proposes: the owner sees the changes and taps Save (PUT /mandate), and the wallet
enforces whatever is saved.

Gemini returns only the fields the sentence changes (structured output); they're merged into
the current mandate and validated. If Gemini is unavailable or says nothing usable, a small
rule-based reader handles the common phrasings; if that finds nothing either, nothing changes.
"""
import json
import re
from typing import Literal

from pydantic import BaseModel, ValidationError

from hizashi_shared import config, llm
from hizashi_shared.models import Mandate

LABELS = {
    "min_sell_price": "Never sell below",
    "max_buy_price": "Never buy above",
    "daily_budget": "Daily budget",
    "max_promise_kwh": "Most to promise per block",
    "approve_above": "Ask me above",
    "counterparties": "Trade with",
    "paused": "Trading",
}
# Sane bounds: the parser may propose anything inside them, never outside.
BOUNDS = {
    "min_sell_price": (0.0, 20.0), "max_buy_price": (0.0, 20.0), "daily_budget": (0.0, 2000.0),
    "max_promise_kwh": (0.05, 10.0), "approve_above": (0.0, 2000.0),
}


class Changes(BaseModel):
    """What the sentence changes; anything left out stays as it is."""
    min_sell_price: float | None = None
    max_buy_price: float | None = None
    daily_budget: float | None = None
    max_promise_kwh: float | None = None
    approve_above: float | None = None
    counterparties: Literal["same_transformer", "street"] | None = None
    paused: bool | None = None


class Proposal(BaseModel):
    mandate: Mandate
    changes: list[dict]          # [{"field", "label", "from", "to"}]
    source: Literal["gemini", "rules", "none"]
    note: str


SYSTEM = f"""You turn a home owner's sentence about their rooftop-solar trading rules into JSON.
Fields (₹ are rupees per kWh unless said otherwise):
- min_sell_price: never sell below this ₹/kWh
- max_buy_price: never buy above this ₹/kWh
- daily_budget: most ₹ the agent may spend buying per day
- max_promise_kwh: most kWh to promise in one 15-minute block
- approve_above: ask the owner first for any plan or offer worth more than this many ₹
- counterparties: "same_transformer" (only my transformer / close neighbours) or "street" (anyone on the street)
- paused: true to stop trading, false to resume
Only include fields the sentence clearly changes. Use numbers, not strings. The grid (BESCOM) charges
₹{config.RETAIL_ENERGY_CHARGE:.2f}/kWh. If nothing in the sentence maps to a field, return {{}}."""


def _fmt(field: str, v) -> str:
    if field == "counterparties":
        return {"same_transformer": "My transformer", "street": "Whole street"}[v]
    if field == "paused":
        return "Paused" if v else "On"
    if field == "max_promise_kwh":
        return f"{v:g} kWh"
    if field in ("daily_budget", "approve_above"):
        return f"₹{v:g}"
    return f"₹{v:.2f}"


def merge(current: Mandate, changes: Changes) -> tuple[Mandate, list[dict]]:
    """Apply the changes inside BOUNDS; -> (proposed mandate, list of real changes)."""
    upd: dict = {}
    for field, v in changes.model_dump(exclude_none=True).items():
        if field in BOUNDS:
            lo, hi = BOUNDS[field]
            if not lo <= float(v) <= hi:
                continue
            v = round(float(v), 2)
        if getattr(current, field) != v:
            upd[field] = v
    proposed = current.model_copy(update=upd)
    rows = [{"field": f, "label": LABELS[f], "from": _fmt(f, getattr(current, f)), "to": _fmt(f, v)} for f, v in upd.items()]
    return proposed, rows


# --- rule-based fallback ---------------------------------------------------------------------

_NUM = r"₹?\s*(\d+(?:\.\d+)?)"
_RULES: list[tuple[str, str, object]] = [
    (rf"(?:don'?t|do not|never|not)\s+buy\s+(?:\w+\s+){{0,3}}(?:above|over|more than|for more than)\s+{_NUM}", "max_buy_price", float),
    (rf"(?:max(?:imum)?|at most)\s+(?:buy(?:ing)?\s+)?price\s+(?:of\s+|is\s+)?{_NUM}", "max_buy_price", float),
    (rf"buy\s+(?:\w+\s+){{0,3}}(?:up to|at most|max|below|under)\s+{_NUM}", "max_buy_price", float),
    (rf"(?:don'?t|do not|never|not)\s+sell\s+(?:\w+\s+){{0,3}}(?:below|under|less than|for less than)\s+{_NUM}", "min_sell_price", float),
    (rf"sell\s+(?:\w+\s+){{0,3}}(?:at least|no less than|min(?:imum)?|above|over)\s+{_NUM}", "min_sell_price", float),
    (rf"(?:budget|spend\w*)\s+(?:\w+\s+){{0,3}}?{_NUM}", "daily_budget", float),
    (rf"(?:never|not|don'?t go)\s+below\s+{_NUM}", "min_sell_price", float),
    (rf"(?:ask|check with|tell)\s+me\s+(?:\w+\s+){{0,3}}(?:above|over|beyond|more than)\s+{_NUM}", "approve_above", float),
    (r"(?:promise|commit|sell)\s+(?:\w+\s+){0,3}?(?:at most|max(?:imum)?|up to|no more than)\s+(\d+(?:\.\d+)?)\s*kwh", "max_promise_kwh", float),
    (r"\b(?:pause|stop|halt)\b.*\btrad", "paused", True),
    (r"\b(?:resume|restart|start)\b.*\btrad", "paused", False),
    (r"\b(?:whole street|anyone|anybody|everyone|any neighbou?r)\b", "counterparties", "street"),
    (r"\b(?:my transformer|same transformer|only (?:close|nearby|next-door) neighbou?rs)\b", "counterparties", "same_transformer"),
]


def rules_parse(text: str) -> Changes:
    t = text.lower().replace(",", "")
    found: dict = {}
    for pattern, field, kind in _RULES:
        if field in found:
            continue
        m = re.search(pattern, t)
        if m:
            found[field] = kind(m.group(1)) if kind is float else kind
    return Changes(**found)


async def gemini_parse(text: str, current: Mandate) -> Changes | None:
    prompt = f"Current rules: {current.model_dump_json(exclude={'house', 'version'})}\nOwner says: {text}"
    raw = await llm.generate(prompt, system=SYSTEM, schema=Changes, timeout=12.0, temperature=0.0)
    if raw is None:
        return None
    try:
        return Changes.model_validate(json.loads(raw))
    except (ValidationError, ValueError):
        return None


async def parse(text: str, current: Mandate) -> Proposal:
    """Never raises; with nothing understood, the proposal is the current mandate unchanged."""
    text = text.strip()[:500]
    changes = await gemini_parse(text, current)
    source = "gemini"
    if changes is None or not merge(current, changes)[1]:
        fallback = rules_parse(text)
        if merge(current, fallback)[1]:
            changes, source = fallback, "rules"
    proposed, rows = merge(current, changes or Changes())
    if not rows:
        return Proposal(mandate=current, changes=[], source="none",
                        note="I couldn't find a rule to change in that. Try “don't buy above ₹5” or “ask me over ₹20”.")
    return Proposal(mandate=proposed, changes=rows, source=source,
                    note="Check these, then Save. Your wallet enforces whatever you save.")
