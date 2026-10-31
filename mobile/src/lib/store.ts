// Live hub state for one house: GET /api/state, then /ws events through one reducer per type.
// Tiny external store (useSyncExternalStore) so screens re-render on every applied event.
import AsyncStorage from "@react-native-async-storage/async-storage";
import { useSyncExternalStore } from "react";
import { Api } from "./api";
import { EV, type House, type HubEvent, type Snapshot } from "./types";

export interface Connection { hub: string; house: House }

export interface HubState extends Snapshot {
  loaded: boolean;
  connected: boolean;
  conn: Connection | null;
  ready: boolean;              // saved connection read from storage
}

const empty: Snapshot = {
  sim_time: null, speed: 60, running: false, public_url: null,
  houses: {} as Snapshot["houses"], mandates: {} as Snapshot["mandates"],
  blocks: {}, forecasts: {}, plans: {}, negotiations: {}, contracts: [], settlements: [],
  savings: {}, approvals: [], flags: [], outage: null, weather_source: null, recent_events: [],
  live: {}, sim_events: [], blocked: [], auctions: {},
};

let state: HubState = { ...empty, loaded: false, connected: false, conn: null, ready: false };
const listeners = new Set<() => void>();

function set(patch: Partial<HubState>) {
  state = { ...state, ...patch };
  listeners.forEach((l) => l());
}

export function useHub(): HubState {
  return useSyncExternalStore((l) => { listeners.add(l); return () => listeners.delete(l); }, () => state);
}

export const getHub = () => state;
export const api = () => new Api(state.conn?.hub ?? "");

type Reducer = (s: HubState, e: HubEvent) => Partial<HubState>;

const DAY_RESET: Partial<HubState> = {
  blocks: {}, contracts: [], settlements: [], negotiations: {}, approvals: [], flags: [], blocked: [],
  savings: {}, plans: {}, live: {}, sim_events: [], auctions: {}, outage: null,
};

const reducers: Record<string, Reducer> = {
  [EV.CLOCK_TICK]: (s, e) => ({
    sim_time: e.sim_time, speed: e.data.speed ?? s.speed, running: e.data.running ?? s.running,
    ...(e.data.reset ? DAY_RESET : {}),
  }),
  [EV.BLOCK_STATE]: (s, e) => ({ blocks: { ...s.blocks, [e.data.block]: e.data.state } }),
  [EV.METER_READING]: (s, e) => (e.house
    ? { live: { ...s.live, [e.house]: { solar_kw: e.data.solar_kw ?? 0, use_kw: e.data.use_kw ?? 0, ts: e.sim_time, outage: !!e.data.outage } } }
    : {}),
  [EV.PLAN_UPDATED]: (s, e) => (e.house ? { plans: { ...s.plans, [e.house]: e.data.windows } } : {}),
  [EV.NEGO_OFFER]: (s, e) => {
    const o = e.data.offer;
    if (!o?.negotiation_id) return {};
    const prev = s.negotiations[o.negotiation_id] ?? [];
    if (prev.some((x) => x.offer_id === o.offer_id)) return {};
    return { negotiations: { ...s.negotiations, [o.negotiation_id]: [...prev, o] } };
  },
  [EV.WALLET_BLOCKED]: (s, e) => ({ blocked: [...s.blocked, { house: e.house!, sim_time: e.sim_time, ...e.data }].slice(-30) }),
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
  [EV.GRID_OUTAGE]: (_s, e) => ({ outage: e.data.active ? e.data : null }),
  [EV.SIM_EVENT]: (s, e) => ({ sim_events: [...s.sim_events, e.data.event] }),
  [EV.MANDATE_UPDATED]: (s, e) => (e.house ? { mandates: { ...s.mandates, [e.house]: e.data.mandate } } : {}),
  [EV.HOUSE_UPDATED]: (s, e) => (e.house ? { houses: { ...s.houses, [e.house]: e.data.house } } : {}),
};

function upsertApproval(s: HubState, e: HubEvent): Partial<HubState> {
  const a = e.data.approval;
  if (!a) return {};
  return { approvals: [...s.approvals.filter((x) => x.approval_id !== a.approval_id), a] };
}

// --- connection ------------------------------------------------------------------------

const KEY = "hizashi.connection";
let ws: WebSocket | null = null;
let timer: ReturnType<typeof setTimeout> | undefined;
let generation = 0;

export async function loadConnection(): Promise<void> {
  try {
    const raw = await AsyncStorage.getItem(KEY);
    const conn = raw ? (JSON.parse(raw) as Connection) : null;
    set({ conn, ready: true });
    if (conn) start();
  } catch {
    set({ ready: true });
  }
}

export async function connect(conn: Connection): Promise<void> {
  await AsyncStorage.setItem(KEY, JSON.stringify(conn));
  set({ ...empty, conn, loaded: false, connected: false });
  start();
}

export async function disconnect(): Promise<void> {
  stop();
  await AsyncStorage.removeItem(KEY);
  set({ ...empty, conn: null, loaded: false, connected: false });
}

function stop() {
  generation++;
  clearTimeout(timer);
  if (ws) { ws.onclose = null; ws.close(); ws = null; }
}

function start() {
  stop();
  const gen = generation;
  const conn = state.conn;
  if (!conn) return;
  const client = new Api(conn.hub);
  const retry = () => {
    if (gen !== generation) return;
    set({ connected: false });
    timer = setTimeout(start, 1500);
  };
  client.state().then((snap) => {
    if (gen !== generation) return;
    set({ ...empty, ...snap, loaded: true });
    // React Native's WebSocket takes headers as a third argument; the header keeps ngrok's
    // browser warning page out of the way.
    ws = new (WebSocket as any)(client.wsUrl(conn.house), undefined, { headers: { "ngrok-skip-browser-warning": "1" } }) as WebSocket;
    ws.onopen = () => set({ connected: true });
    ws.onmessage = (m) => {
      const e = JSON.parse(String(m.data)) as HubEvent;
      const patch = reducers[e.type]?.(state, e);
      if (patch) set(patch);
      if (e.type === EV.CLOCK_TICK && e.data.reset) client.state().then((s) => set({ ...empty, ...s, loaded: true })).catch(() => {});
    };
    ws.onclose = retry;
    ws.onerror = () => ws?.close();
  }).catch(retry);
}
