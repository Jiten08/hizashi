// Raw hub events, newest first (console).
import { hhmm } from "../lib/api";
import type { HubEvent } from "../lib/types";

const TONE: Record<string, string> = {
  "wallet.blocked": "text-red-600",
  "contract.booked": "text-emerald-700",
  "settlement.done": "text-emerald-700",
  "approval.requested": "text-amber-700",
  "market.cleared": "text-sky-700",
  "grid.outage": "text-stone-900 font-semibold",
};

export function EventLog({ events }: { events: HubEvent[] }) {
  const rows = [...events].reverse().slice(0, 200);
  if (!rows.length) return <p className="text-sm text-stone-500">No events yet.</p>;
  return (
    <ol className="max-h-[28rem] space-y-0.5 overflow-auto font-mono text-xs">
      {rows.map((e, i) => (
        <li key={i} className="flex gap-3 border-b border-stone-100 py-1">
          <span className="text-stone-400">{hhmm(e.sim_time)}</span>
          <span className={`w-40 shrink-0 ${TONE[e.type] ?? "text-stone-700"}`}>{e.type}</span>
          <span className="w-10 shrink-0 text-stone-500">{e.house ?? "—"}</span>
          <span className="truncate text-stone-500">{JSON.stringify(e.data)}</span>
        </li>
      ))}
    </ol>
  );
}
