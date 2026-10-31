import { hhmm } from "../lib/api";
import type { HubEvent } from "../lib/types";

/** Raw event log, newest first. */
export function EventLog({ events, max = 200 }: { events: HubEvent[]; max?: number }) {
  const rows = events.slice(-max).reverse();
  return (
    <div className="max-h-[60vh] overflow-auto rounded-xl border border-stone-200 bg-white font-mono text-xs">
      {rows.length === 0 && <p className="p-3 text-stone-400">No events yet.</p>}
      {rows.map((e, i) => (
        <div key={rows.length - i} className="flex gap-2 border-b border-stone-100 px-3 py-1">
          <span className="text-stone-400">{hhmm(e.sim_time)}</span>
          <span className="w-32 shrink-0 font-semibold text-amber-700">{e.type}</span>
          <span className="w-8 shrink-0 text-stone-500">{e.house ?? ""}</span>
          <span className="truncate text-stone-700">{JSON.stringify(e.data)}</span>
        </div>
      ))}
    </div>
  );
}
