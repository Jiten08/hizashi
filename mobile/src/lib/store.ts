// Live hub state for this phone's house: GET /api/state, then /ws events through one reducer
// per type; reconnects on its own. Reducers copy what the hub says, they never compute money.
import { useEffect } from "react";
import { create } from "zustand";
import { api, wsUrl } from "./api";
import { closeNotification } from "./push";
import { EV, type House, type HubEvent, type Snapshot } from "./types";

export interface HubState extends Snapshot {
  loaded: boolean;
  connected: boolean;
  failures: number;
  lastError: string | null;
}

const empty: Snapshot = {
  sim_time: null, speed: 60, running: false, public_url: null,
  houses: {} as Snapshot["houses"], mandates: {} as Snapshot["mandates"],
  blocks: {}, forecasts: {}, plans: {}, negotiations: {}, contracts: [], settlements: [],
  savings: {}, approvals: [], flags: [], outage: null, weather_source: null, recent_events: [],
  live: {}, sim_events: [], blocked: [], auctions: {}, schedules: {},
};

const DAY_RESET: Partial<HubState> = {
  blocks: {}, contracts: [], settlements: [], negotiations: {}, approvals: [], flags: [], blocked: [],
  savings: {}, plans: {}, live: {}, sim_events: [], auctions: {}, outage: null,
};

type Reducer = (s: HubState, e: HubEvent) => Partial<HubState>;

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
  [EV.GUARD_FLAG]: (s, e) => ({ flags: [...s.flags, e.data] }),
  [EV.SCHEDULE_UPDATED]: (s, e) => (e.house ? { schedules: { ...s.schedules, [e.house]: e.data.schedules } } : {}),
};

function upsertApproval(s: HubState, e: HubEvent): Partial<HubState> {
  const a = e.data.approval;
  if (!a) return {};
  return { approvals: [...s.approvals.filter((x) => x.approval_id !== a.approval_id), a] };
}

export const useHubStore = create<HubState>(() => ({ ...empty, loaded: false, connected: false, failures: 0, lastError: null }));

const set = (patch: Partial<HubState>) => useHubStore.setState(patch);

/** Keep a live connection for `house` while mounted. */
export function useHubConnection(house: House | null) {
  useEffect(() => {
    if (!house) return;
    let stopped = false;
    let ws: WebSocket | null = null;
    let timer: ReturnType<typeof setTimeout> | undefined;

    const retry = (err?: unknown) => {
      if (stopped) return;
      const s = useHubStore.getState();
      set({ connected: false, failures: s.failures + 1, lastError: err ? String((err as Error).message ?? err) : s.lastError });
      timer = setTimeout(start, 1500);
    };

    async function start() {
      try {
        const snap = await Promise.race([
          api.state(),
          new Promise<never>((_, reject) => setTimeout(() => reject(new Error("no answer in 8 s")), 8000)),
        ]);
        if (stopped) return;
        set({ ...empty, ...snap, loaded: true, failures: 0, lastError: null });
      } catch (e) {
        retry(e);
        return;
      }
      ws = new WebSocket(wsUrl(house!));
      ws.onopen = () => set({ connected: true });
      ws.onmessage = (m) => {
        const e = JSON.parse(m.data) as HubEvent;
        const patch = reducers[e.type]?.(useHubStore.getState(), e);
        if (patch) set(patch);
        if (e.type === EV.APPROVAL_RESOLVED && e.data.approval) closeNotification(e.data.approval.approval_id);
        if (e.type === EV.CLOCK_TICK && e.data.reset) api.state().then((s) => set({ ...empty, ...s, loaded: true })).catch(() => {});
      };
      ws.onclose = () => retry();
    }

    // Back from the background (phones suspend sockets): reconnect at once.
    const wake = () => { if (document.visibilityState === "visible" && ws?.readyState !== WebSocket.OPEN) { clearTimeout(timer); ws?.close(); start(); } };
    document.addEventListener("visibilitychange", wake);
    start();
    return () => {
      stopped = true;
      clearTimeout(timer);
      document.removeEventListener("visibilitychange", wake);
      if (ws) { ws.onclose = null; ws.close(); }
    };
  }, [house]);
}

// --- which house this phone belongs to ---------------------------------------------------
const KEY = "hizashi.house";
const HOUSES: House[] = ["h12", "h14", "h16", "h18"];

export function savedHouse(): House | null {
  const fromUrl = new URLSearchParams(location.search).get("house");
  if (fromUrl && (HOUSES as string[]).includes(fromUrl)) {
    try { localStorage.setItem(KEY, fromUrl); } catch { /* private mode */ }
    return fromUrl as House;
  }
  try {
    const v = localStorage.getItem(KEY);
    return v && (HOUSES as string[]).includes(v) ? (v as House) : null;
  } catch {
    return null;
  }
}

export function saveHouse(h: House | null) {
  try { if (h) localStorage.setItem(KEY, h); else localStorage.removeItem(KEY); } catch { /* private mode */ }
}
