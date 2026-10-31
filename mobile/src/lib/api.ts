// REST calls to the hub. The app is served by the hub at /app/, so every path is same-origin.
// The phone only sends taps; the hub computes every price and saving.
import type { Approval, ApprovalRow, House, LedgerEntry, Mandate, MandateProposal, Schedule, SetupBody, SetupResult, Snapshot } from "./types";

// ngrok's free tier puts a warning page in front of browsers unless this header is sent.
const HEADERS = { "ngrok-skip-browser-warning": "1" };

async function req<T>(method: string, path: string, body?: unknown): Promise<T> {
  const res = await fetch(path, {
    method,
    headers: body === undefined ? HEADERS : { ...HEADERS, "Content-Type": "application/json" },
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
  decide: (id: string, decision: "approve" | "decline") => req<Approval>("POST", `/api/approvals/${id}`, { decision, channel: "app" }),
  approvals: (house: House) => req<ApprovalRow[]>("GET", `/api/approvals?house=${house}`),
  ledger: (house: House) => req<LedgerEntry[]>("GET", `/api/ledger?house=${house}`),
  verify: () => req<{ ok: boolean; broken_at?: number; entries?: number }>("GET", "/api/ledger/verify"),
  putMandate: (house: House, m: Mandate) => req<Mandate>("PUT", `/api/wallet/${house}/mandate`, m),
  parseMandate: (house: House, text: string) => req<MandateProposal>("POST", `/api/wallet/${house}/mandate/parse`, { text }),
  setup: (house: House, body: SetupBody) => req<SetupResult>("POST", `/api/houses/${house}/setup`, body),
  addSchedule: (house: House, body: { kind: Schedule["kind"]; day: string; start: string; end: string }) =>
    req<Schedule>("POST", `/api/schedules/${house}`, body),
  removeSchedule: (house: House, id: string) => req<{ status: string }>("DELETE", `/api/schedules/${house}/${id}`),
  pushKey: () => req<{ key: string }>("GET", "/api/push/key"),
  pushSubscribe: (house: House, sub: PushSubscriptionJSON) => req<{ status: string }>("POST", `/api/push/${house}`, sub),
  pushUnsubscribe: (house: House, endpoint: string) => req<{ status: string }>("DELETE", `/api/push/${house}`, { endpoint }),
  pushTest: (house: House) => req<{ sent: number }>("POST", `/api/push/${house}/test`),
};

export function wsUrl(house: House): string {
  const proto = location.protocol === "https:" ? "wss:" : "ws:";
  return `${proto}//${location.host}/ws?role=owner&house=${house}`;
}
