// Fetch helpers. Screens only send taps; the hub computes everything.
import type { House, LedgerEntry, Snapshot } from "./types";

async function req<T>(method: string, path: string, body?: unknown): Promise<T> {
  const res = await fetch(path, {
    method,
    headers: body === undefined ? undefined : { "Content-Type": "application/json" },
    body: body === undefined ? undefined : JSON.stringify(body),
  });
  if (!res.ok) {
    let detail = "";
    try { detail = (await res.json()).detail ?? ""; } catch { /* not json */ }
    throw new Error(detail || `${method} ${path} -> ${res.status}`);
  }
  return res.json() as Promise<T>;
}

export const api = {
  state: () => req<Snapshot>("GET", "/api/state"),
  setSpeed: (speed: 1 | 60 | 300) => req<{ speed: number }>("POST", "/api/console/speed", { speed }),
  reset: () => req<{ sim_time: string }>("POST", "/api/console/reset"),
  nextDay: () => req<{ sim_time: string; day: string }>("POST", "/api/console/reset", { next_day: true }),
  startOver: () => req<{ sim_time: string; day: string }>("POST", "/api/console/reset", { start_over: true }),
  consoleEvent: (type: string, house?: string, minutes?: number) =>
    req("POST", "/api/console/events", { type, house, minutes }),
  decide: (approvalId: string, decision: "approve" | "decline") =>
    req("POST", `/api/approvals/${approvalId}`, { decision, channel: "app" }),
  verifyLedger: () => req<{ ok: boolean; broken_at?: number; entries?: number }>("GET", "/api/ledger/verify"),
  ledger: (house?: House) => req<LedgerEntry[]>("GET", `/api/ledger${house ? `?house=${house}` : ""}`),
  connect: () => req<{ hub: string | null; houses: { house: House; label: string; url: string | null }[] }>("GET", "/api/connect"),
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
export const kwh = (x: number, d = 2) => `${x.toFixed(d)} kWh`;

/** Block key "2026-10-31#48" -> index 48. */
export const blockIndex = (key: string) => Number(key.split("#")[1]);

/** Same key format as the hub: day#NN. */
export const blockKey = (b: { day: string; index: number }) => `${b.day}#${String(b.index).padStart(2, "0")}`;

/** "10:00–13:00" for a plan window. */
export function windowLabel(first: number, last: number): string {
  const f = (m: number) => `${String(Math.floor(m / 60)).padStart(2, "0")}:${String(m % 60).padStart(2, "0")}`;
  return `${f(first * 15)}–${f(last * 15 + 15)}`;
}
