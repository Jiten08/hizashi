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
import math
import uuid

import httpx

from hizashi_shared import blocks, config, events as ev, profiles, street
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
        """Fallback forecast: profile mean +/- 1.28 sd, solar bell curve peaking at 12:15."""
        log.info("%s using fallback forecast", self.house)
        try:
            means, stds = profiles.load_profile(house_info.profile)
        except Exception:
            means = [0.2] * config.BLOCKS_PER_DAY
            stds = [0.04] * config.BLOCKS_PER_DAY

        kwp = house_info.roof.kwp if house_info.roof else 0.0
        peak_solar = 0.8 * kwp * 0.25  # kWh per block peak

        fcs: list[Forecast] = []
        for i in range(config.BLOCKS_PER_DAY):
            # Solar bell curve peaking at block 49 (12:15)
            if house_info.roof and 24 <= i <= 74:
                angle = (i - 49) / 25.0 * (math.pi / 2.0)
                s_p50 = round(peak_solar * (math.cos(angle) ** 2), 4)
                s_p10 = round(s_p50 * 0.85, 4)
                s_p90 = round(s_p50 * 1.15, 4)
            else:
                s_p10 = s_p50 = s_p90 = 0.0

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
            # If weather dataframe can be built, pass to forecaster
            import pandas as pd
            df = pd.DataFrame(weather_data.get("blocks", []))
            forecasts = forecaster.forecast_day(me_info, df, self.day)
        except Exception:
            forecasts = self.fallback_forecast(me_info, self.day)

        self.intents = planner.plan_day(forecasts, mandate)
        self.remaining_sell = {i: kwh for i, (side, kwh) in self.intents.items() if side == "sell"}
        self.remaining_buy = {i: kwh for i, (side, kwh) in self.intents.items() if side == "buy"}

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

    async def on_event(self, event: Event) -> None:
        """Handle incoming hub events from the WebSocket subscription."""
        if event.type == ev.CLOCK_TICK:
            self.current_sim_time = event.sim_time

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
