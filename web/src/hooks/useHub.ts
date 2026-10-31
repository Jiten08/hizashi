// Snapshot + WebSocket + reconnect for the dashboard: GET /api/state -> open /ws?role=street
// -> store.apply(event) for each message -> on close wait 1 s and start over.
import { useEffect } from "react";
import { api, wsUrl } from "../lib/api";
import type { HubEvent, Role } from "../lib/types";
import { useHubStore } from "../store/hub";

export function useHub(role: Role = "street") {
  useEffect(() => {
    let stopped = false;
    let ws: WebSocket | null = null;
    let timer: ReturnType<typeof setTimeout> | undefined;
    const { setSnapshot, setConnected, apply } = useHubStore.getState();

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
      ws = new WebSocket(wsUrl(`role=${role}`));
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
  }, [role]);

  return useHubStore();
}
