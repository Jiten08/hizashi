// The street's events as plain sentences, newest first. Text only; every number comes from the hub.
import { blockLabel, hhmm, rupees } from "../lib/api";
import type { HubEvent } from "../lib/types";
import type { IconName } from "./ui";
import { Icon } from "./ui";

const name = (h?: string | null) => (h ? `House ${h.slice(1)}` : "The street");

function line(e: HubEvent): { icon: IconName; tone: string; text: string; key: string } | null {
  const d = e.data;
  switch (e.type) {
    case "contract.booked": {
      const c = d.contract;
      return { key: `c${c.contract_id}`, icon: "swap", tone: "text-sun bg-sun-soft",
        text: `${name(c.seller)} → ${name(c.buyer)}: ${c.kwh.toFixed(2)} kWh at ${rupees(c.price)} for ${blockLabel(c.block.index)}${c.route === "auction" ? " (auction)" : ""}` };
    }
    case "settlement.done": {
      const s = d.settlement;
      const short = s.shortfall_kwh >= 0.005 ? `, short ${s.shortfall_kwh.toFixed(2)} kWh${s.outage ? " (outage, no penalty)" : ""}` : "";
      return { key: `s${s.contract_id}`, icon: "check", tone: "text-leaf-ink bg-leaf-soft",
        text: `Settled ${blockLabel(s.block.index)}: ${name(s.seller)} → ${name(s.buyer)} ${s.delivered_kwh.toFixed(2)} kWh${short}` };
    }
    case "wallet.blocked":
      if (d.owner_rule === false) return null;
      return { key: `b${e.sim_time}${e.house}${d.reason}`, icon: "ban", tone: "text-alert bg-alert-soft",
        text: `${name(e.house)}'s wallet blocked it: ${String(d.reason ?? "")}` };
    case "approval.requested":
      return { key: `a${d.approval.approval_id}`, icon: "people", tone: "text-sky bg-sky-soft", text: `${name(e.house)} was asked: ${d.approval.summary}` };
    case "approval.resolved": {
      const a = d.approval;
      const verb = a.status === "approved" ? "approved" : a.status === "declined" ? "declined" : "didn't answer; the agent went ahead with";
      return { key: `r${a.approval_id}`, icon: "people", tone: "text-sky bg-sky-soft", text: `${name(e.house)} ${verb} “${a.summary}”` };
    }
    case "market.cleared":
      if (!d.matches?.length) return null;
      return { key: `m${d.block}`, icon: "swap", tone: "text-ink-2 bg-fill",
        text: `Gate auction for ${blockLabel(d.index)}: ${d.matches.length} match${d.matches.length > 1 ? "es" : ""}` };
    case "sim.event": {
      const ev = d.event;
      const what = { cloud: "Cloud over", ac: "AC switched on at", guests: "Guests at", away: "Nobody home at", outage: "Grid outage on" }[ev.type as string] ?? ev.type;
      return { key: `e${ev.start}${ev.type}${ev.house}`, icon: ev.type === "cloud" ? "cloud" : ev.type === "outage" ? "plug" : "home", tone: "text-ink-2 bg-fill",
        text: `${what} ${ev.house ? name(ev.house) : "the street"} until ${hhmm(ev.end)}` };
    }
    case "grid.outage":
      return d.active ? null : { key: `o${e.sim_time}`, icon: "plug", tone: "text-ink-2 bg-fill", text: "Grid is back" };
    default:
      return null;
  }
}

export function Activity({ events }: { events: HubEvent[] }) {
  const seen = new Set<string>();
  const rows = [];
  for (const e of [...events].reverse()) {
    const l = line(e);
    if (!l || seen.has(l.key)) continue;
    seen.add(l.key);
    rows.push({ ...l, at: e.sim_time });
    if (rows.length >= 40) break;
  }
  if (!rows.length) return <p className="py-6 text-center text-sm text-ink-2">Deals, settlements and blocks appear here as they happen.</p>;
  return (
    <ul className="max-h-[420px] divide-y divide-hair overflow-auto">
      {rows.map((r) => (
        <li key={r.key} className="rise flex items-center gap-3 py-2.5">
          <span className={`inline-flex h-7 w-7 shrink-0 items-center justify-center rounded-full ${r.tone}`}><Icon name={r.icon} className="h-3.5 w-3.5" strokeWidth={2.2} /></span>
          <p className="min-w-0 flex-1 text-sm">{r.text}</p>
          <span className="num font-mono text-xs text-ink-3">{hhmm(r.at)}</span>
        </li>
      ))}
    </ul>
  );
}
