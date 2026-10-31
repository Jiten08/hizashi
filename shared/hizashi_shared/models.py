"""Pydantic models: the contract between hub, agents and web. Frozen after Phase 0."""
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

House = Literal["h12", "h14", "h16", "h18"]
BlockState = Literal["PLANNED", "OPEN", "GATE_CLOSED", "DELIVERING", "SETTLED"]

HOUSES: tuple[str, ...] = ("h12", "h14", "h16", "h18")
BLOCK_STATES: tuple[str, ...] = ("PLANNED", "OPEN", "GATE_CLOSED", "DELIVERING", "SETTLED")


class BlockRef(BaseModel):
    day: str            # "2026-10-31"
    index: int          # 0..95

    @property
    def key(self) -> str:
        return f"{self.day}#{self.index:02d}"


class Roof(BaseModel):
    kwp: float
    tilt: float
    azimuth: float      # pvlib convention: azimuth 180 = south, 90 = east
    inverter_kw: float


class HouseInfo(BaseModel):
    id: House
    label: str                      # "House 12"
    transformer: str                # "T1"
    roof: Roof | None               # None = no solar
    profile: str                    # household use profile name
    buyback_rate: float | None      # ₹/kWh BESCOM pays this home; None if no solar
    metering: Literal["net", "gross", "none"]
    agent_url: str                  # "http://127.0.0.1:9012/"
    meter_pubkey: str | None = None
    wallet_pubkey: str | None = None
    subsidized: bool | None = None  # PM Surya Ghar subsidy on the rooftop system; None if no solar
    onboarded: bool = False         # the owner confirmed this setup in the app


class Forecast(BaseModel):
    house: House
    block: BlockRef
    solar_p10: float
    solar_p50: float
    solar_p90: float
    use_p10: float
    use_p50: float
    use_p90: float
    made_at: datetime


class Mandate(BaseModel):
    house: House
    version: int = 1
    min_sell_price: float           # never sell below
    max_buy_price: float            # never buy above
    daily_budget: float             # ₹ the agent may spend per day on buys
    max_promise_kwh: float          # per block
    approve_above: float            # ₹; plans or offers worth more need the owner's OK
    counterparties: Literal["same_transformer", "street"] = "same_transformer"
    paused: bool = False


class PlanWindow(BaseModel):        # a run of consecutive blocks with the same side
    plan_id: str
    house: House
    side: Literal["buy", "sell"]
    day: str
    first_index: int
    last_index: int
    kwh: float
    expected_price: float
    expected_value: float           # kwh * expected_price
    status: Literal["auto", "pending", "approved", "declined"] = "auto"
    signature: str | None = None


class Offer(BaseModel):
    offer_id: str
    negotiation_id: str
    block: BlockRef
    side: Literal["ask", "bid"]
    house: House                    # who makes the offer
    to: House | None                # None = market order at gate closure
    kwh: float
    price: float
    round: int
    expires_at: datetime            # the block's gate closure
    nonce: str
    signature: str | None = None    # wallet signature


class Contract(BaseModel):
    contract_id: str
    negotiation_id: str | None
    block: BlockRef
    seller: House
    buyer: House
    kwh: float
    price: float
    route: Literal["haggle", "auction"]
    fee_per_kwh: float = 0.14
    open_access: bool = False
    seller_sig: str | None = None
    buyer_sig: str | None = None
    market_sig: str | None = None


class MeterReading(BaseModel):
    house: House
    ts: datetime                    # simulated minute
    seq: int                        # strictly increasing per meter
    solar_wh: float
    import_wh: float
    export_wh: float
    signature: str | None = None    # meter key


class Settlement(BaseModel):
    contract_id: str
    block: BlockRef
    seller: House | None = None
    buyer: House | None = None
    contracted_kwh: float
    delivered_kwh: float
    shortfall_kwh: float
    price: float
    buyer_pays: float               # (p + F) * q
    seller_net: float               # p*d - s*(R - p)
    seller_penalty: float           # s*(R - p), 0 if outage
    fee: float                      # F * q
    outage: bool


class Approval(BaseModel):
    approval_id: str
    house: House
    kind: Literal["plan", "offer"]
    summary: str                    # "Buy 2.4 kWh from neighbours, 10:00–13:00, for about ₹11.23?"
    ref_id: str                     # plan_id or offer_id
    code: str                       # 4 digits, for WhatsApp replies
    status: Literal["pending", "approved", "declined", "expired"] = "pending"
    created_at: datetime


class Event(BaseModel):
    type: str
    sim_time: datetime
    house: House | None = None      # for owner-scoped filtering
    data: dict = Field(default_factory=dict)
