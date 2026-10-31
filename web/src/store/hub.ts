// Zustand store: the snapshot from GET /api/state, then one reducer per event type.
// Reducers only copy what the hub says; they never compute prices or savings.
import { create } from "zustand";
import { EV, type HubEvent, type Snapshot } from "../lib/types";

const LOG_SIZE = 300;

export interface HubStore extends Snapshot {
  loaded: boolean;
  connected: boolean;
  log: HubEvent[];
  setSnapshot: (s: Snapshot) => void;
  setConnected: (c: boolean) => void;
  apply: (e: HubEvent) => void;
}

export const emptySnapshot: Snapshot = {
  sim_time: null, speed: 60, running: false, public_url: null,
  houses: {} as Snapshot["houses"], mandates: {} as Snapshot["mandates"],
  blocks: {}, forecasts: {}, plans: {}, negotiations: {}, contracts: [], settlements: [],
  savings: {}, approvals: [], flags: [], outage: null, weather_source: null, recent_events: [],
  live: {}, sim_events: [], blocked: [], auctions: {}, notes: {}, sun: null,
};

const DAY_RESET: Partial<HubStore> = {
  blocks: {}, contracts: [], settlements: [], negotiations: {}, approvals: [], flags: [], blocked: [],
  savings: {}, plans: {}, live: {}, sim_events: [], auctions: {}, outage: null, log: [], notes: {},
};

type Reducer = (s: HubStore, e: HubEvent) => Partial<HubStore>;

const reducers: Record<string, Reducer> = {
  [EV.CLOCK_TICK]: (s, e) => ({
    sim_time: e.sim_time,
    speed: e.data.speed ?? s.speed,
    running: e.data.running ?? s.running,
    sun: e.data.sun ?? s.sun,
    ...(e.data.reset ? DAY_RESET : {}),
  }),
  [EV.BLOCK_STATE]: (s, e) => ({ blocks: { ...s.blocks, [e.data.block]: e.data.state } }),
  [EV.METER_READING]: (s, e) =>
    e.house
      ? { live: { ...s.live, [e.house]: { solar_kw: e.data.solar_kw ?? 0, use_kw: e.data.use_kw ?? 0, ts: e.sim_time, outage: !!e.data.outage } } }
      : {},
  [EV.FORECAST_UPDATED]: (s, e) => (e.house ? { forecasts: { ...s.forecasts, [e.house]: e.data.forecasts } } : {}),
  [EV.NEGO_NOTE]: (s, e) => (e.data.note ? { notes: { ...s.notes, [e.data.note.offer_id]: e.data.note } } : {}),
  [EV.PLAN_UPDATED]: (s, e) => (e.house ? { plans: { ...s.plans, [e.house]: e.data.windows } } : {}),
  [EV.NEGO_OFFER]: (s, e) => {
    const o = e.data.offer;
    if (!o?.negotiation_id) return {};
    const prev = s.negotiations[o.negotiation_id] ?? [];
    if (prev.some((x) => x.offer_id === o.offer_id)) return {};
    return { negotiations: { ...s.negotiations, [o.negotiation_id]: [...prev, o] } };
  },
  [EV.WALLET_BLOCKED]: (s, e) => ({
    blocked: [...s.blocked, { house: e.house!, sim_time: e.sim_time, ...e.data }].slice(-50),
  }),
  [EV.APPROVAL_REQUESTED]: (s, e) => upsertApproval(s, e),
  [EV.APPROVAL_RESOLVED]: (s, e) => upsertApproval(s, e),
  [EV.CONTRACT_BOOKED]: (s, e) => {
    const c = e.data.contract;
    if (!c || s.contracts.some((x) => x.contract_id === c.contract_id)) return {};
    return { contracts: [...s.contracts, c] };
  },
  [EV.SETTLEMENT_DONE]: (s, e) => {
    const st = e.data.settlement;
    if (!st || s.settlements.some((x) => x.contract_id === st.contract_id)) return {};
    return {
      settlements: [...s.settlements, st],
      contracts: s.contracts.map((c) => (c.contract_id === st.contract_id ? { ...c, settled: true } : c)),
    };
  },
  [EV.SAVINGS_UPDATED]: (s, e) => (e.house ? { savings: { ...s.savings, [e.house]: e.data as any } } : {}),
  [EV.MARKET_CLEARED]: (s, e) => ({ auctions: { ...s.auctions, [e.data.block]: e.data } }),
  [EV.GUARD_FLAG]: (s, e) => ({ flags: [...s.flags, e.data] }),
  [EV.GRID_OUTAGE]: (_s, e) => ({ outage: e.data.active ? e.data : null }),
  [EV.SIM_EVENT]: (s, e) => ({ sim_events: [...s.sim_events, e.data.event] }),
  [EV.MANDATE_UPDATED]: (s, e) => (e.house ? { mandates: { ...s.mandates, [e.house]: e.data.mandate } } : {}),
  [EV.HOUSE_UPDATED]: (s, e) => (e.house ? { houses: { ...s.houses, [e.house]: e.data.house } } : {}),
};

function upsertApproval(s: HubStore, e: HubEvent): Partial<HubStore> {
  const a = e.data.approval;
  if (!a) return {};
  return { approvals: [...s.approvals.filter((x) => x.approval_id !== a.approval_id), a] };
}

export const useHubStore = create<HubStore>((set) => ({
  ...emptySnapshot,
  loaded: false,
  connected: false,
  log: [],
  setSnapshot: (snap) => set({ ...emptySnapshot, ...snap, loaded: true, log: snap.recent_events ?? [] }),
  setConnected: (connected) => set({ connected }),
  apply: (e) =>
    set((s) => {
      // Unknown event types are ignored, not crashed.
      const patch = reducers[e.type]?.(s, e) ?? {};
      const quiet = e.type === EV.CLOCK_TICK || e.type === EV.METER_READING;
      const log = quiet ? patch.log ?? s.log : [...(patch.log ?? s.log), e].slice(-LOG_SIZE);
      return { ...patch, log };
    }),
}));
