/**
 * SimClock — shows the simulated time, speed, and a connection badge.
 * Badge states:
 *   • mock (amber)       — ?mock=1
 *   • live (green)       — WS connected
 *   • reconnecting (red) — WS closed / connecting
 */
import { hhmm } from "../lib/api";
import { useHubStore } from "../store/hub";

export function SimClock({ className = "" }: { className?: string }) {
  const { sim_time, speed, running, connected, mock } = useHubStore();

  const badge = mock
    ? { label: "mock", dot: "bg-amber-400", text: "text-amber-700" }
    : connected
    ? { label: "live", dot: "bg-emerald-500", text: "text-emerald-700" }
    : { label: "reconnecting", dot: "bg-red-500 animate-pulse", text: "text-red-600" };

  return (
    <div className={`flex items-center gap-2 ${className}`}>
      {/* connection badge */}
      <span
        className={`flex items-center gap-1 rounded-full border px-2 py-0.5 text-xs font-medium ${badge.text} border-current`}
        title={badge.label}
      >
        <span className={`h-1.5 w-1.5 rounded-full ${badge.dot}`} />
        {badge.label}
      </span>
      <span className="font-mono text-lg tabular-nums">{hhmm(sim_time)}</span>
      <span className="rounded bg-stone-100 px-1.5 text-xs text-stone-600">
        {running ? `${speed}×` : "paused"}
      </span>
    </div>
  );
}
