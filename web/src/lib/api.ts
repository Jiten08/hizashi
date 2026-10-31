// Fetch helpers. Screens only send taps; the hub computes everything.
import type { Snapshot } from "./types";

async function req<T>(method: string, path: string, body?: unknown): Promise<T> {
  const res = await fetch(path, {
    method,
    headers: body === undefined ? undefined : { "Content-Type": "application/json" },
    body: body === undefined ? undefined : JSON.stringify(body),
  });
  if (!res.ok) throw new Error(`${method} ${path} -> ${res.status}`);
  return res.json() as Promise<T>;
}

export const api = {
  state: () => req<Snapshot>("GET", "/api/state"),
  setSpeed: (speed: 1 | 60 | 300) => req<{ speed: number }>("POST", "/api/console/speed", { speed }),
  reset: () => req<{ sim_time: string }>("POST", "/api/console/reset"),
  consoleEvent: (type: string, house?: string, minutes?: number) =>
    req("POST", "/api/console/events", { type, house, minutes }),
  decide: (approvalId: string, decision: "approve" | "decline") =>
    req("POST", `/api/approvals/${approvalId}`, { decision, channel: "app" }),
  verifyLedger: () => req<{ ok: boolean; broken_at?: number }>("GET", "/api/ledger/verify"),
};

export function wsUrl(query: string): string {
  const proto = location.protocol === "https:" ? "wss:" : "ws:";
  return `${proto}//${location.host}/ws?${query}`;
}

/** "12:00" from an ISO sim time, shown in IST whatever the phone's zone. */
export function hhmm(iso: string | null): string {
  if (!iso) return "--:--";
  return new Date(iso).toLocaleTimeString("en-IN", {
    hour: "2-digit", minute: "2-digit", hour12: false, timeZone: "Asia/Kolkata",
  });
}

/** "12:00–12:15" for a block index. */
export function blockLabel(index: number): string {
  const f = (m: number) => `${String(Math.floor(m / 60)).padStart(2, "0")}:${String(m % 60).padStart(2, "0")}`;
  return `${f(index * 15)}–${f(index * 15 + 15)}`;
}

export const rupees = (x: number) => `₹${x.toFixed(2)}`;
