"""Main loop reacting to block states (section 7.6).

PLANNED: forecast the day, post plan windows. OPEN: sellers start negotiations, buyers
answer. GATE_CLOSED: post leftover kWh as a signed market order at the limit price.
DELIVERING: read own meter. SETTLED: read results; after a shortfall shrink promises 10%.
Console command bad_bid (h14): bid at ₹40 for the next OPEN block (the wallet refuses it).
"""
from __future__ import annotations

import asyncio
from datetime import datetime, timedelta
import logging
import uuid

import httpx

from hizashi_shared import blocks, config, events as ev, profiles, solar, street
from hizashi_shared.models import BlockRef, Contract, Event, Forecast, HouseInfo, Mandate, Offer
from . import forecaster, negotiator, planner
from .a2a_client import negotiate_sale
from .hub_client import HubClient

log = logging.getLogger("hizashi.agent.runtime")


class Runtime:
    def __init__(self, house: str, hub: HubClient | None = None, day: str = config.SIM_DAY) -> None:
        self.house = house
        self.hub = hub or HubClient(house)
        self.day = day
        self.houses: dict[str, HouseInfo] = {}
        self.mandates: dict[str, Mandate] = {}
        self.intents: dict[int, planner.Intent] = {}
        self.remaining_sell: dict[int, float] = {}
        self.remaining_buy: dict[int, float] = {}
        self.block_states: dict[str, str] = {}
        self.planned = False
        self.current_sim_time: datetime | None = None
        self._negotiating_blocks: set[str] = set()
        self.promise_factor = 1.0          # shrinks 10% after each shortfall

        # Load initial street & mandates synchronously from local data
        try:
            self.houses = street.load_houses()
            self.mandates = street.load_mandates()
        except Exception as e:
            log.warning("%s failed to load local street data: %s", self.house, e)

    async def start(self) -> None:
        """Fetch registry & state from hub, then initialize planning if already in progress."""
        try:
            reg = await self.hub.get_registry()
            if "houses" in reg:
                self.houses = {h["id"]: HouseInfo.model_validate(h) for h in reg["houses"]}
        except Exception:
            pass

        try:
            state = await self.hub.get_state()
            if "mandates" in state:
                self.mandates = {m["house"]: Mandate.model_validate(m) for m in state["mandates"]}
            if "block_states" in state:
                self.block_states = state["block_states"]
        except Exception:
            pass

        # If day is already running and tradable blocks are active, forecast and plan
        if not self.planned:
            await self.forecast_and_plan()

        # Check any already OPEN blocks for sell intents
        for b_key, b_state in list(self.block_states.items()):
            if b_state == "OPEN":
                b_ref = blocks.parse_key(b_key)
                rem = self.remaining_sell.get(b_ref.index, 0.0)
                if rem > config.MIN_TRADE_KWH:
                    asyncio.create_task(self.negotiate_sell(b_ref))

    def fallback_forecast(self, house_info: HouseInfo, day: str) -> list[Forecast]:
        """Fallback forecast: profile mean +/- 1.28 sd; solar from the clear-sky roof model, p10/p90 at -/+15%."""
        log.info("%s using fallback forecast", self.house)
        try:
            means, stds = profiles.load_profile(house_info.profile)
        except Exception:
            means = [0.2] * config.BLOCKS_PER_DAY
            stds = [0.04] * config.BLOCKS_PER_DAY

        try:
            clear = solar.roof_kwh_per_block(house_info.roof, solar.clear_sky_frame(day))
        except Exception as e:
            log.warning("%s clear-sky model failed (%s); assuming no solar", self.house, e)
            clear = [0.0] * config.BLOCKS_PER_DAY

        fcs: list[Forecast] = []
        for i in range(config.BLOCKS_PER_DAY):
            s_p50 = round(clear[i], 4)
            s_p10 = round(s_p50 * 0.85, 4)
            s_p90 = round(s_p50 * 1.15, 4)

            m_i = means[i]
            s_i = stds[i]
            use_p50 = round(m_i, 4)
            use_p10 = round(max(0.0, m_i - 1.28 * s_i), 4)
            use_p90 = round(m_i + 1.28 * s_i, 4)

            fcs.append(
                Forecast(
                    house=self.house,  # type: ignore[arg-type]
                    block=BlockRef(day=day, index=i),
                    solar_p10=s_p10,
                    solar_p50=s_p50,
                    solar_p90=s_p90,
                    use_p10=use_p10,
                    use_p50=use_p50,
                    use_p90=use_p90,
                    made_at=datetime.now(config.TZ),
                )
            )
        return fcs

    async def forecast_and_plan(self) -> None:
        """Forecast the day and submit plan windows to hub."""
        me_info = self.houses.get(self.house)
        mandate = self.mandates.get(self.house)
        if not me_info or not mandate:
            return

        forecasts: list[Forecast]
        try:
            weather_data = await self.hub.get_weather()
            df = solar.weather_frame(weather_data)        # needs the 15-min DatetimeIndex
            forecasts = forecaster.forecast_day(me_info, df, self.day)
        except Exception as e:
            log.warning("%s forecaster failed (%s)", self.house, e)
            forecasts = self.fallback_forecast(me_info, self.day)

        intents = planner.plan_day(forecasts, mandate)
        # Blocks already past PLANNED keep what they had (a replan mid-day only moves the future).
        fixed = {blocks.parse_key(k).index for k, s in self.block_states.items() if s != "PLANNED"} if self.planned else set()
        for i, intent in intents.items():
            if i in fixed:
                continue
            self.intents[i] = intent
            side, kwh = intent
            self.remaining_sell.pop(i, None)
            self.remaining_buy.pop(i, None)
            if side == "sell":
                self.remaining_sell[i] = round(kwh * self.promise_factor, 3)
            elif side == "buy":
                self.remaining_buy[i] = kwh

        windows = planner.plan_windows(self.house, self.day, self.intents)
        if windows:
            await self.hub.post_plans(windows)

        self.planned = True
        log.info("%s planned day: %d sell blocks, %d buy blocks",
                 self.house, len(self.remaining_sell), len(self.remaining_buy))

    async def negotiate_sell(self, block_ref: BlockRef) -> None:
        """Haggle with neighbours over A2A for this block."""
        if block_ref.key in self._negotiating_blocks:
            return
        rem = self.remaining_sell.get(block_ref.index, 0.0)
        if rem <= config.MIN_TRADE_KWH:
            return
        self._negotiating_blocks.add(block_ref.key)

        me_info = self.houses.get(self.house)
        my_mandate = self.mandates.get(self.house)
        if not me_info or not my_mandate:
            return

        s_limit = negotiator.seller_limit(my_mandate.min_sell_price, me_info.buyback_rate)
        same_tf = my_mandate.counterparties == "same_transformer"
        candidates = street.neighbours(self.houses, self.house, same_transformer=same_tf)

        async with httpx.AsyncClient(timeout=10.0) as http:
            for neighbour in candidates:
                current_rem = self.remaining_sell.get(block_ref.index, 0.0)
                if current_rem <= config.MIN_TRADE_KWH:
                    break

                # Check gate closure time threshold: before T - 70 min
                if self.current_sim_time:
                    t_70 = blocks.block_start(block_ref) - timedelta(minutes=70)
                    if self.current_sim_time > t_70:
                        log.info("%s reached T - 70m for %s, stopping haggle", self.house, block_ref.key)
                        break

                ask_0 = negotiator.ask_price(0, s_limit)
                expires_at = blocks.gate_close(block_ref)
                nego_id = str(uuid.uuid4())

                first_offer = Offer(
                    offer_id=str(uuid.uuid4()),
                    negotiation_id=nego_id,
                    block=block_ref,
                    side="ask",
                    house=self.house,  # type: ignore[arg-type]
                    to=neighbour.id,
                    kwh=current_rem,
                    price=ask_0,
                    round=0,
                    expires_at=expires_at,
                    nonce=str(uuid.uuid4()),
                )

                sign_res = await self.hub.sign_offer(first_offer)
                if sign_res.get("status") != "signed":
                    log.info("%s sign_offer refused for %s: %s", self.house, neighbour.id, sign_res.get("reason"))
                    continue
                signed_first_offer = Offer.model_validate(sign_res["offer"])

                contract = await negotiate_sale(
                    me=me_info,
                    buyer=neighbour,
                    first_ask=signed_first_offer,
                    hub=self.hub,
                    seller_limit=s_limit,
                    remaining_kwh=current_rem,
                    http=http,
                )
                if contract:
                    self.remaining_sell[block_ref.index] = max(
                        0.0, round(self.remaining_sell[block_ref.index] - contract.kwh, 3)
                    )

    # --- gate closure: leftovers go to the auction -------------------------------------

    async def post_leftovers(self, block_ref: BlockRef) -> None:
        me = self.houses.get(self.house)
        mandate = self.mandates.get(self.house)
        if not me or not mandate:
            return
        i = block_ref.index
        orders = []
        sell = round(self.remaining_sell.get(i, 0.0), 3)
        buy = round(self.remaining_buy.get(i, 0.0), 3)
        if sell > config.MIN_TRADE_KWH:
            orders.append(("ask", sell, negotiator.seller_limit(mandate.min_sell_price, me.buyback_rate)))
        if buy > config.MIN_TRADE_KWH:
            orders.append(("bid", buy, negotiator.buyer_limit(mandate.max_buy_price)))
        for side, kwh, price in orders:
            offer = Offer(offer_id=str(uuid.uuid4()), negotiation_id=f"market-{block_ref.key}", block=block_ref,
                          side=side, house=self.house, to=None, kwh=kwh, price=price, round=0,  # type: ignore[arg-type]
                          expires_at=blocks.block_start(block_ref), nonce=str(uuid.uuid4()))
            signed = await self.hub.sign_offer(offer)
            if signed.get("status") != "signed":
                log.info("%s market %s for %s not signed: %s", self.house, side, block_ref.key, signed.get("reason"))
                continue
            res = await self.hub.post_order(Offer.model_validate(signed["offer"]))
            log.info("%s market %s %.3f kWh @ ₹%.2f for %s: %s %s", self.house, side, kwh, price,
                     block_ref.key, res.get("status"), res.get("reason") or "")

    # --- console attack demo --------------------------------------------------------------

    async def bad_bid(self, price: float = 40.0) -> dict:
        """Bid far above the owner's max for the next OPEN block; the wallet must refuse it."""
        open_blocks = sorted(blocks.parse_key(k).index for k, s in self.block_states.items() if s == "OPEN")
        if not open_blocks:
            log.info("%s bad_bid: no OPEN block", self.house)
            return {"status": "skipped"}
        ref = BlockRef(day=self.day, index=open_blocks[0])
        mandate = self.mandates.get(self.house)
        sellers = [h for h in street.neighbours(self.houses, self.house,
                                                same_transformer=not mandate or mandate.counterparties == "same_transformer")
                   if h.roof is not None]
        offer = Offer(offer_id=str(uuid.uuid4()), negotiation_id=str(uuid.uuid4()), block=ref, side="bid",
                      house=self.house, to=sellers[0].id if sellers else None, kwh=0.5, price=price,  # type: ignore[arg-type]
                      round=0, expires_at=blocks.gate_close(ref), nonce=str(uuid.uuid4()))
        res = await self.hub.sign_offer(offer)
        log.info("%s bad_bid ₹%.2f for %s -> %s: %s", self.house, price, ref.key, res.get("status"), res.get("reason"))
        return res

    def after_settlement(self, s: dict) -> None:
        if s.get("seller") == self.house and float(s.get("shortfall_kwh") or 0) > 0:
            self.promise_factor = round(self.promise_factor * 0.9, 4)
            for i in list(self.remaining_sell):
                if self.block_states.get(BlockRef(day=self.day, index=i).key) in (None, "PLANNED", "OPEN"):
                    self.remaining_sell[i] = round(self.remaining_sell[i] * 0.9, 3)
            log.info("%s shortfall of %.3f kWh in %s; future promises now x%.2f", self.house,
                     float(s["shortfall_kwh"]), s.get("block"), self.promise_factor)

    def reset_day(self) -> None:
        self.intents, self.remaining_sell, self.remaining_buy = {}, {}, {}
        self.block_states = {}
        self.planned = False
        self.promise_factor = 1.0
        self._negotiating_blocks.clear()

    async def on_event(self, event: Event) -> None:
        """Handle incoming hub events from the WebSocket subscription."""
        if event.type == ev.CLOCK_TICK:
            self.current_sim_time = event.sim_time
            if event.data.get("reset"):
                self.reset_day()

        elif event.type == ev.CONSOLE_COMMAND and event.data.get("cmd") == "bad_bid":
            await self.bad_bid(float(event.data.get("price", 40)))

        elif event.type == ev.SETTLEMENT_DONE:
            self.after_settlement(event.data.get("settlement", {}))

        elif event.type == ev.MANDATE_UPDATED and event.house:
            self.mandates[event.house] = Mandate.model_validate(event.data["mandate"])

        elif event.type == ev.HOUSE_UPDATED and event.house:
            self.houses[event.house] = HouseInfo.model_validate(event.data["house"])
            if event.house == self.house and self.planned:
                await self.forecast_and_plan()

        elif event.type == ev.BLOCK_STATE:
            block_key = event.data.get("block")
            state = event.data.get("state")
            if not block_key or not state:
                return

            self.block_states[block_key] = state

            if state == "PLANNED" and not self.planned:
                await self.forecast_and_plan()

            elif state == "OPEN":
                block_ref = blocks.parse_key(block_key)
                if not self.planned:
                    await self.forecast_and_plan()

                rem = self.remaining_sell.get(block_ref.index, 0.0)
                if rem > config.MIN_TRADE_KWH:
                    asyncio.create_task(self.negotiate_sell(block_ref))

            elif state == "GATE_CLOSED":
                asyncio.create_task(self.post_leftovers(blocks.parse_key(block_key)))
