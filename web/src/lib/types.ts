// TS mirrors of shared/hizashi_shared/models.py and events.py. Keep in sync with shared/.

export type House = "h12" | "h14" | "h16" | "h18";
export const HOUSES: House[] = ["h12", "h14", "h16", "h18"];
export type BlockState = "PLANNED" | "OPEN" | "GATE_CLOSED" | "DELIVERING" | "SETTLED";

export interface BlockRef { day: string; index: number }

export interface Roof { kwp: number; tilt: number; azimuth: number; inverter_kw: number }

export interface HouseInfo {
  id: House;
  label: string;
  transformer: string;
  roof: Roof | null;
  profile: string;
  buyback_rate: number | null;
  metering: "net" | "gross" | "none";
  agent_url: string;
  meter_pubkey: string | null;
  wallet_pubkey: string | null;
  subsidized?: boolean | null;
  onboarded?: boolean;
}

export interface Forecast {
  house: House; block: BlockRef;
  solar_p10: number; solar_p50: number; solar_p90: number;
  use_p10: number; use_p50: number; use_p90: number;
  made_at: string;
}

export interface Mandate {
  house: House;
  version: number;
  min_sell_price: number;
  max_buy_price: number;
  daily_budget: number;
  max_promise_kwh: number;
  approve_above: number;
  counterparties: "same_transformer" | "street";
  paused: boolean;
}

export interface PlanWindow {
  plan_id: string; house: House; side: "buy" | "sell"; day: string;
  first_index: number; last_index: number;
  kwh: number; expected_price: number; expected_value: number;
  status: "auto" | "pending" | "approved" | "declined" | "expired";
  signature: string | null;
}

export interface Offer {
  offer_id: string; negotiation_id: string; block: BlockRef;
  side: "ask" | "bid"; house: House; to: House | null;
  kwh: number; price: number; round: number;
  expires_at: string; nonce: string; signature: string | null;
}

export interface Contract {
  contract_id: string; negotiation_id: string | null; block: BlockRef;
  seller: House; buyer: House; kwh: number; price: number;
  route: "haggle" | "auction"; fee_per_kwh: number; open_access: boolean;
  seller_sig: string | null; buyer_sig: string | null; market_sig: string | null;
}

export interface MeterReading {
  house: House; ts: string; seq: number;
  solar_wh: number; import_wh: number; export_wh: number; signature: string | null;
}

export interface Settlement {
  contract_id: string; block: BlockRef; seller: House | null; buyer: House | null;
  contracted_kwh: number; delivered_kwh: number; shortfall_kwh: number;
  price: number; buyer_pays: number; seller_net: number; seller_penalty: number;
  fee: number; outage: boolean;
}

export interface Approval {
  approval_id: string; house: House; kind: "plan" | "offer";
  summary: string; ref_id: string; code: string;
  status: "pending" | "approved" | "declined" | "expired";
  created_at: string;
}

export interface ApprovalRow extends Approval { channel: string | null; decided_at: string | null }

export interface Savings {
  house: House; day: string;
  saved_today: number; projected_year: number; as_buyer: number; as_seller: number;
  bought_kwh: number; paid: number; sold_kwh: number; delivered_kwh: number; shortfall_kwh: number;
  earned: number; penalties: number; trades: number;
}

export interface Live { solar_kw: number; use_kw: number; ts: string; outage: boolean }

export interface SimEvent { type: string; house: House | null; start: string; end: string }

export interface LedgerEntry {
  seq: number; ts: string; kind: string; ref_id: string;
  payload: Record<string, any>; prev_hash: string; hash: string;
}

export interface Tariffs {
  retail: number; fee: number; expected_p2p_price: number;
  buyback: { unsubsidized: number; subsidized_upto_2kw: number; subsidized_above_2kw: number };
}

export interface SetupBody {
  has_solar: boolean; kwp: number; facing: "south" | "east" | "west" | "north";
  subsidized: boolean; metering: "net" | "gross"; preview?: boolean;
}

export interface SetupResult {
  house: HouseInfo; clear_day_kwh: number; mandate: Mandate; tariffs: Tariffs; saved: boolean;
}

/** What an agent said with one of its offers (screens only). */
export interface HubEvent<T = Record<string, any>> {
  type: string;
  sim_time: string;
  house: House | null;
  data: T;
}

/** GET /api/state */
export interface Snapshot {
  sim_time: string | null;
  speed: number;
  running: boolean;
  public_url: string | null;
  houses: Record<House, HouseInfo>;
  mandates: Record<House, Mandate>;
  blocks: Record<string, BlockState>;
  forecasts: Record<string, Forecast[]>;
  plans: Record<string, PlanWindow[]>;
  negotiations: Record<string, Offer[]>;
  contracts: (Contract & { settled?: boolean })[];
  settlements: Settlement[];
  savings: Record<string, Savings>;
  approvals: Approval[];
  flags: Record<string, any>[];
  outage: Record<string, any> | null;
  weather_source: string | null;
  recent_events: HubEvent[];
  live: Record<string, Live>;
  sim_events: SimEvent[];
  blocked: (Record<string, any> & { house: House })[];
  auctions: Record<string, Record<string, any>>;
  sun: { azimuth: number; elevation: number } | null;
}

export const EV = {
  CLOCK_TICK: "clock.tick",
  BLOCK_STATE: "block.state",
  FORECAST_UPDATED: "forecast.updated",
  PLAN_UPDATED: "plan.updated",
  METER_READING: "meter.reading",
  NEGO_OFFER: "nego.offer",
  NEGO_RESULT: "nego.result",
  WALLET_BLOCKED: "wallet.blocked",
  APPROVAL_REQUESTED: "approval.requested",
  APPROVAL_RESOLVED: "approval.resolved",
  CONTRACT_BOOKED: "contract.booked",
  MARKET_CLEARED: "market.cleared",
  SETTLEMENT_DONE: "settlement.done",
  SAVINGS_UPDATED: "savings.updated",
  GUARD_FLAG: "guard.flag",
  GRID_OUTAGE: "grid.outage",
  CONSOLE_COMMAND: "console.command",
  MANDATE_UPDATED: "mandate.updated",
  SIM_EVENT: "sim.event",
  HOUSE_UPDATED: "house.updated",
} as const;

export type Role = "owner" | "street" | "console";
