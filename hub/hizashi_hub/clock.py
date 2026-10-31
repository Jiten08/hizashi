"""Simulated clock: one tick = one simulated minute, real sleep = 60 / speed seconds.

The day runs 05:00 -> 19:00 and then stops (console can reset; same seed -> same day).
Each tick publishes `clock.tick` and a `block.state` event for every tradable block
whose lifecycle state changed (section 6.2).

Hooks for later tasks: `on_minute` callbacks (sim meters, R2.2) run before the tick is
published; `on_block_state` callbacks (auction, settlement, R2.1/R2.3) run after each
block.state event.
"""
import asyncio
import logging
from collections.abc import Awaitable, Callable
from datetime import datetime, timedelta

from hizashi_shared import blocks, config
from hizashi_shared import events as ev
from hizashi_shared.models import BlockRef, Event

from . import bus

log = logging.getLogger("hizashi.clock")

MinuteHook = Callable[[datetime], Awaitable[None] | None]
BlockHook = Callable[[BlockRef, str | None, str], Awaitable[None] | None]


class SimClock:
    def __init__(self, day: str = config.SIM_DAY, speed: int = config.SIM_SPEED) -> None:
        self.day = day
        self.speed = speed
        self.now = blocks.day_start(day)
        self.block_states: dict[str, str] = {}
        self.running = False
        self.on_minute: list[MinuteHook] = []
        self.on_block_state: list[BlockHook] = []
        self._task: asyncio.Task | None = None
        self._wake = asyncio.Event()

    # --- control -------------------------------------------------------------

    def start(self) -> None:
        if self._task is None or self._task.done():
            self._task = asyncio.create_task(self._run(), name="clock")

    async def stop(self) -> None:
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None
        self.running = False

    def set_speed(self, speed: int) -> None:
        if speed not in config.ALLOWED_SPEEDS:
            raise ValueError(f"speed must be one of {config.ALLOWED_SPEEDS}")
        self.speed = speed
        self._wake.set()        # cut the current sleep short
        self._publish_tick()

    async def reset(self) -> None:
        await self.stop()
        self.now = blocks.day_start(self.day)
        self.block_states = {}
        self._publish_tick(reset=True)
        self.start()

    # --- loop ----------------------------------------------------------------

    @property
    def finished(self) -> bool:
        return self.now >= blocks.day_end(self.day)

    async def _run(self) -> None:
        self.running = True
        try:
            if not self.block_states:
                self._publish_tick()
                await self._advance_blocks()
            while not self.finished:
                await self._sleep(60 / self.speed)
                self.now += timedelta(minutes=1)
                for hook in self.on_minute:
                    await _maybe_await(hook(self.now))
                self._publish_tick()
                await self._advance_blocks()
        finally:
            self.running = False
            self._publish_tick()
        log.info("simulated day finished at %s", self.now)

    async def _sleep(self, seconds: float) -> None:
        self._wake.clear()
        try:
            await asyncio.wait_for(self._wake.wait(), timeout=seconds)
        except TimeoutError:
            pass

    def _publish_tick(self, reset: bool = False) -> None:
        data = {
            "speed": self.speed,
            "running": self.running and not self.finished,
            "block": blocks.block_of(self.now).key,
        }
        if reset:
            data["reset"] = True
        bus.publish(Event(type=ev.CLOCK_TICK, sim_time=self.now, data=data))

    async def _advance_blocks(self) -> None:
        for ref in blocks.tradable_blocks(self.day):
            new = blocks.state_at(ref, self.now)
            old = self.block_states.get(ref.key)
            if new is None or new == old:
                continue
            self.block_states[ref.key] = new
            bus.publish(Event(
                type=ev.BLOCK_STATE, sim_time=self.now,
                data={"block": ref.key, "index": ref.index, "state": new, "prev": old,
                      "outage": False},  # outage flag: R2/N5
            ))
            for hook in self.on_block_state:
                await _maybe_await(hook(ref, old, new))


async def _maybe_await(result) -> None:
    if asyncio.iscoroutine(result):
        await result


_clock: SimClock | None = None


def init(day: str = config.SIM_DAY, speed: int = config.SIM_SPEED) -> SimClock:
    global _clock
    _clock = SimClock(day, speed)
    return _clock


def get() -> SimClock:
    if _clock is None:
        raise RuntimeError("clock not initialised")
    return _clock
