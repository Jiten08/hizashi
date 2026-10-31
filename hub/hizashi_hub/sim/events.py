"""Console events with start/end in sim time: cloud, outage, ac, guests, away."""
from datetime import datetime

from pydantic import BaseModel


class SimEvent(BaseModel):
    type: str
    house: str | None
    start: datetime
    end: datetime


class SimEvents:
    def add(self, type_: str, house: str | None, start: datetime, minutes: int) -> SimEvent:
        raise NotImplementedError("TODO(R2.7, Anurag)")

    def active(self, minute: datetime, type_: str | None = None, house: str | None = None) -> list[SimEvent]:
        raise NotImplementedError("TODO(R2.7, Anurag)")

    def cloud_factor(self, house: str, minute: datetime) -> float:
        """0.3 under a console cloud, else 1.0."""
        raise NotImplementedError("TODO(R2.7, Anurag)")
