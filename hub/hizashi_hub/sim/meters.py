"""Signed minute meter readings and per-block totals (section 6.8).

export = max(solar - use, 0), import = max(use - solar, 0); sign with the meter key,
increment seq, publish meter.reading (house-scoped), add to block_meter.
During an outage: solar 0, export 0, import 0.
"""
from datetime import datetime

from hizashi_shared.models import MeterReading


class Meters:
    def __init__(self, pv, load, conn) -> None:
        raise NotImplementedError("TODO(R2.2, Prajval)")

    async def on_minute(self, minute: datetime) -> list[MeterReading]:
        """Clock on_minute hook: one signed reading per house."""
        raise NotImplementedError("TODO(R2.2, Prajval)")

    def block_totals(self, house: str, block_key: str) -> dict:
        raise NotImplementedError("TODO(R2.2, Prajval)")
