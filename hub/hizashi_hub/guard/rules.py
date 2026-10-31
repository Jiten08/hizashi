"""Guard rules (N2): bad signature (reported by agents), impossible reading (solar at night,
export above the inverter), wash trade (self, or both ways in one block), price coordination
(2+ sellers holding the same ask in COLLUSION_BLOCKS blocks, KERC 5(a)(ii)), replay (a reused
offer nonce or meter seq).

Pure functions: each returns plain-sentence reasons, empty = ok. guard/watch.py keeps the
day's memory and raises the flags.
"""
from hizashi_shared import blocks, config
from hizashi_shared.models import Contract, HouseInfo, MeterReading, Offer

# Blocks with any clear-sky output (blocks.TRADABLE), plus one block either side for dawn / dusk.
DAYLIGHT = range(blocks.TRADABLE.start - 1, blocks.TRADABLE.stop + 1)
INVERTER_SLACK = 1.05            # meters round; allow 5% over the inverter's rating
COLLUSION_BLOCKS = 4
OPENING_ASK = round(config.RETAIL_ENERGY_CHARGE - config.SELLER_OPEN_DISCOUNT, 2)   # every seller opens here


def _name(h: str) -> str:
    return f"House {h[1:]}"


def check_contract(contract: Contract, booked_in_block: list[Contract]) -> list[str]:
    """Wash trades: a house selling to itself, or two houses selling to each other in one block."""
    if contract.seller == contract.buyer:
        return [f"{_name(contract.seller)} tried to trade with itself."]
    if any(c.seller == contract.buyer and c.buyer == contract.seller for c in booked_in_block):
        return [f"{_name(contract.seller)} and {_name(contract.buyer)} tried to sell to each other in the "
                f"{blocks.label(contract.block)} block. That's a wash trade, so it wasn't booked."]
    return []


def check_reading(reading: MeterReading, info: HouseInfo, last_seq: int | None) -> list[str]:
    reasons = []
    if last_seq is not None and reading.seq <= last_seq:
        reasons.append(f"{_name(reading.house)}'s meter sent reading #{reading.seq} again (last was #{last_seq}). "
                       "A replayed reading isn't counted.")
    index = blocks.block_of(reading.ts).index
    if reading.solar_wh > 0 and (info.roof is None or index not in DAYLIGHT):
        why = "has no solar panels" if info.roof is None else "it's dark"
        reasons.append(f"{_name(reading.house)}'s meter reported {reading.solar_wh:.0f} Wh of solar but {why}.")
    if info.roof is not None:
        cap_wh = info.roof.inverter_kw * 1000 / 60 * INVERTER_SLACK
        if reading.export_wh > cap_wh:
            reasons.append(f"{_name(reading.house)}'s meter exported {reading.export_wh:.0f} Wh in a minute; "
                           f"its {info.roof.inverter_kw:g} kW inverter can't do more than {cap_wh:.0f} Wh.")
    return reasons


def check_offer(offer: Offer, nonce_owner: str | None) -> list[str]:
    """Replay: the nonce was already used by a different offer."""
    if nonce_owner is not None and nonce_owner != offer.offer_id:
        return [f"{_name(offer.house)}'s offer reuses a nonce from an earlier offer. A replayed offer isn't signed."]
    return []


def held_price(prices: list[float]) -> float | None:
    """The one price a seller asked every time in a block, unless it's the standard opening ask
    (every honest seller opens there) or the seller moved at all."""
    if not prices or len(set(prices)) != 1 or prices[0] == OPENING_ASK:
        return None
    return prices[0]


def collusion(asks: dict[str, dict[str, list[float]]], house: str) -> tuple[str, float, list[str]] | None:
    """asks: block key -> seller -> ask prices (including the one being signed now).
    -> (other seller, price, blocks) when `house` and another seller held the same price in
    COLLUSION_BLOCKS or more blocks today, else None."""
    shared: dict[tuple[str, float], list[str]] = {}
    for key in sorted(asks):
        mine = held_price(asks[key].get(house, []))
        if mine is None:
            continue
        for other, prices in asks[key].items():
            if other != house and held_price(prices) == mine:
                shared.setdefault((other, mine), []).append(key)
    for (other, price), keys in sorted(shared.items(), key=lambda kv: -len(kv[1])):
        if len(keys) >= COLLUSION_BLOCKS:
            return other, price, keys
    return None
