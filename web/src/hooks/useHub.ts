// Snapshot + WebSocket + reconnect: GET /api/state -> open /ws -> store.apply(event)
// for each message -> on close wait 1 s and start over.
//
// If ?mock=1 is in the URL, skip the backend entirely and play the scripted
// mock stream from src/mock/events.ts. The connection badge shows "mock".
import { useEffect } from "react";
import { api, wsUrl } from "../lib/api";
import { playMock } from "../mock/events";
import type { House, HubEvent, Role } from "../lib/types";
import { useHubStore } from "../store/hub";

function isMockMode(): boolean {
  return new URLSearchParams(window.location.search).get("mock") === "1";
}

export function useHub(role: Role, house?: House) {
  useEffect(() => {
    let stopped = false;
    const { setSnapshot, setConnected, setMock, apply } = useHubStore.getState();

    if (isMockMode()) {
      // ── mock mode ────────────────────────────────────────────────────────
      setMock(true);
      setConnected(false);
      // Inject a minimal snapshot so the page renders immediately
      setSnapshot({
        sim_time: null,
        speed: 60,
        running: true,
        public_url: null,
        houses: {
          h12: {
            id: "h12", label: "House 12", transformer: "T1",
            roof: { kwp: 5.0, tilt: 13, azimuth: 180, inverter_kw: 5.0 },
            profile: "couple_away_day", buyback_rate: 3.89,
            metering: "net", agent_url: "http://127.0.0.1:9012/",
            meter_pubkey: null, wallet_pubkey: null,
          },
          h14: {
            id: "h14", label: "House 14", transformer: "T1",
            roof: null, profile: "wfh_ac", buyback_rate: null,
            metering: "none", agent_url: "http://127.0.0.1:9014/",
            meter_pubkey: null, wallet_pubkey: null,
          },
          h16: {
            id: "h16", label: "House 16", transformer: "T1",
            roof: { kwp: 3.0, tilt: 15, azimuth: 90, inverter_kw: 3.0 },
            profile: "family_medium", buyback_rate: 2.14,
            metering: "net", agent_url: "http://127.0.0.1:9016/",
            meter_pubkey: null, wallet_pubkey: null,
          },
          h18: {
            id: "h18", label: "House 18", transformer: "T1",
            roof: { kwp: 2.0, tilt: 13, azimuth: 180, inverter_kw: 2.0 },
            profile: "heavy_appliances", buyback_rate: 1.96,
            metering: "net", agent_url: "http://127.0.0.1:9018/",
            meter_pubkey: null, wallet_pubkey: null,
          },
        },
        mandates: {
          h12: { house: "h12", version: 1, min_sell_price: 4.20, max_buy_price: 5.50, daily_budget: 50, max_promise_kwh: 1.0, approve_above: 10, counterparties: "same_transformer", paused: false },
          h14: { house: "h14", version: 1, min_sell_price: 4.20, max_buy_price: 5.50, daily_budget: 50, max_promise_kwh: 1.0, approve_above: 10, counterparties: "same_transformer", paused: false },
          h16: { house: "h16", version: 1, min_sell_price: 3.80, max_buy_price: 5.40, daily_budget: 50, max_promise_kwh: 1.0, approve_above: 25, counterparties: "same_transformer", paused: false },
          h18: { house: "h18", version: 1, min_sell_price: 3.50, max_buy_price: 5.40, daily_budget: 60, max_promise_kwh: 1.0, approve_above: 25, counterparties: "same_transformer", paused: false },
        },
        blocks: {},
        forecasts: {},
        plans: {},
        negotiations: {},
        contracts: [],
        settlements: [],
        savings: {},
        approvals: [],
        flags: [],
        outage: null,
        weather_source: null,
        recent_events: [],
      });

      const cancel = playMock(house ?? "h12", (e: HubEvent) => {
        if (!stopped) apply(e);
      });
      return () => {
        stopped = true;
        cancel();
      };
    }

    // ── live mode ──────────────────────────────────────────────────────────
    setMock(false);
    let ws: WebSocket | null = null;
    let timer: ReturnType<typeof setTimeout> | undefined;

    const retry = () => {
      setConnected(false);
      if (!stopped) timer = setTimeout(start, 1000);
    };

    async function start() {
      try {
        setSnapshot(await api.state());
      } catch {
        retry();
        return;
      }
      if (stopped) return;
      const q = new URLSearchParams({ role, ...(house ? { house } : {}) });
      ws = new WebSocket(wsUrl(q.toString()));
      ws.onopen = () => setConnected(true);
      ws.onmessage = (m) => {
        const e = JSON.parse(m.data) as HubEvent;
        apply(e);
        if (e.type === "clock.tick" && e.data.reset) api.state().then(setSnapshot).catch(() => {});
      };
      ws.onclose = retry;
    }

    start();
    return () => {
      stopped = true;
      clearTimeout(timer);
      if (ws) {
        ws.onclose = null;
        ws.close();
      }
    };
  }, [role, house]);

  return useHubStore();
}
