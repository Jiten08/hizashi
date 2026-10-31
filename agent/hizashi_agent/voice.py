"""What an agent says with each offer: one short sentence for the screens' haggle feed.

Prices are decided by the negotiator and checked by the wallet; this only explains them.
Agents in config.LLM_VOICE_HOUSES ask Gemini (rate-limited, 45 s limit; a late line still lands
beside its offer); everyone else, and any miss, uses a template. The prompt never includes the
agent's limits, so nothing leaks.
"""
import re

from hizashi_shared import blocks, config, llm
from hizashi_shared.models import Offer

VOICE_PER_MINUTE = 5          # per agent: 2 talking agents = 10 of the free tier's ~12 RPM, ~2 left for the parser

SYSTEM = ("You are a friendly home energy agent on a street in Bengaluru, haggling with a neighbour's agent "
          "over rooftop solar for one 15-minute block. Write ONE short sentence (at most 18 words) to send with "
          "your offer. Quote your price exactly as given (₹X.XX), and no other price. Be warm, a little "
          "playful, never rude. Vary your openings: don't start with 'Come on' or 'Hey'. Never mention any "
          "minimum or maximum you would accept. No emojis, no quotes.")

MOOD = {0: "This is your opening offer.", 1: "You're making a first move toward them.",
        2: "You're meeting them partway.", 3: "The gate is getting close; nudge toward a deal.",
        4: "Time is short; be keen to close.", 5: "Last round; this is your final offer."}


def _name(h: str | None) -> str:
    return f"House {h[1:]}" if h else "the street"


def template(offer: Offer, ctx: dict) -> str:
    p = f"₹{offer.price:.2f}"
    when = blocks.label(offer.block)
    if offer.side == "ask":
        if offer.round == 0:
            return f"I'll have spare sun at {when}. {p} a unit, well under the grid's ₹{config.RETAIL_ENERGY_CHARGE:.2f}."
        return f"I can come down to {p} for {when}. Still a better deal than BESCOM."
    if offer.round == 0:
        return f"I'd take some of that for {when}. How about {p}?"
    return f"Meet me at {p}? I'm short at {when} and you'd beat the buyback."


def prompt(offer: Offer, ctx: dict) -> str:
    role = "selling to" if offer.side == "ask" else "buying from"
    lines = [
        f"You are House {offer.house[1:]}'s agent, {role} {_name(offer.to)} for {blocks.label(offer.block)}.",
        f"Round {offer.round + 1} of {config.MAX_ROUNDS}. Your offer: {offer.kwh:.2f} kWh at ₹{offer.price:.2f}/kWh.",
        f"The grid charges ₹{config.RETAIL_ENERGY_CHARGE:.2f}/kWh.",
        MOOD.get(offer.round, ""),
    ]
    if ctx.get("spare_kwh") is not None:
        s = ctx["spare_kwh"]
        lines.append(f"Your forecast for that block: {abs(s):.2f} kWh {'spare' if s >= 0 else 'short'}.")
    if ctx.get("solar_kwh") is not None:
        lines.append(f"Your roof should make {ctx['solar_kwh']:.2f} kWh then.")
    return "\n".join(lines)


def honest(text: str, price: float) -> bool:
    """The line quotes the price the wallet signed, and any other ₹ figure is the real grid tariff."""
    quoted = {round(float(x), 2) for x in re.findall(r"₹\s*(\d+(?:\.\d+)?)", text)}
    return round(price, 2) in quoted and quoted <= {round(price, 2), round(config.RETAIL_ENERGY_CHARGE, 2)}


async def line(offer: Offer, ctx: dict) -> tuple[str, str]:
    """-> (sentence, "gemini" | "template")"""
    if offer.house in config.LLM_VOICE_HOUSES:
        text = await llm.generate(prompt(offer, ctx), system=SYSTEM, timeout=45.0,
                                  per_minute=VOICE_PER_MINUTE, temperature=0.9)
        text = (text or "").splitlines()[0].strip().strip('"')[:160] if text else ""
        if honest(text, offer.price):
            return text, "gemini"
    return template(offer, ctx), "template"
