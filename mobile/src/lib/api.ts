// REST calls to the hub. The phone only sends taps; the hub computes every price and saving.
import type {
  Approval, ApprovalRow, House, LedgerEntry, Mandate, SetupBody, SetupResult, Snapshot,
} from "./types";

// ngrok's free tier shows a warning page to browsers unless this header is sent.
const HEADERS = { "ngrok-skip-browser-warning": "1" };

export class Api {
  constructor(public hub: string) {}

  private async req<T>(method: string, path: string, body?: unknown): Promise<T> {
    const res = await fetch(`${this.hub}${path}`, {
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

  state = () => this.req<Snapshot>("GET", "/api/state");
  decide = (id: string, decision: "approve" | "decline") =>
    this.req<Approval>("POST", `/api/approvals/${id}`, { decision, channel: "app" });
  approvals = (house: House) => this.req<ApprovalRow[]>("GET", `/api/approvals?house=${house}`);
  ledger = (house: House) => this.req<LedgerEntry[]>("GET", `/api/ledger?house=${house}`);
  verify = () => this.req<{ ok: boolean; broken_at?: number; entries?: number }>("GET", "/api/ledger/verify");
  putMandate = (house: House, m: Mandate) => this.req<Mandate>("PUT", `/api/wallet/${house}/mandate`, m);
  setup = (house: House, body: SetupBody) => this.req<SetupResult>("POST", `/api/houses/${house}/setup`, body);

  wsUrl(house: House): string {
    return `${this.hub.replace(/^http/, "ws")}/ws?role=owner&house=${house}`;
  }
}

/** Accepts the dashboard's QR payload: JSON {"hub","house"} or hizashi://connect?hub=..&house=.. */
export function parseConnect(text: string): { hub: string; house: House } | null {
  const clean = (hub: string) => hub.trim().replace(/\/+$/, "");
  const ok = (h: string): h is House => ["h12", "h14", "h16", "h18"].includes(h);
  try {
    const j = JSON.parse(text);
    if (j?.hub && ok(j.house)) return { hub: clean(j.hub), house: j.house };
  } catch { /* not json */ }
  const m = text.match(/[?&]hub=([^&]+).*?[?&]house=(h1[2468])/) ?? text.match(/[?&]house=(h1[2468]).*?[?&]hub=([^&]+)/);
  if (m) {
    const [hub, house] = m[1].startsWith("h1") ? [m[2], m[1]] : [m[1], m[2]];
    if (ok(house)) return { hub: clean(decodeURIComponent(hub)), house };
  }
  return null;
}
