import { hhmm } from "../lib/api";
import { useHubStore } from "../store/hub";

export function SimClock({ className = "" }: { className?: string }) {
  const { sim_time, speed, running, connected } = useHubStore();
  return (
    <div className={`flex items-center gap-2 ${className}`}>
      <span className={`h-2 w-2 rounded-full ${connected ? "bg-emerald-500" : "bg-red-500"}`} title={connected ? "live" : "reconnecting"} />
      <span className="font-mono text-lg tabular-nums">{hhmm(sim_time)}</span>
      <span className="rounded bg-stone-100 px-1.5 text-xs text-stone-600">{running ? `${speed}×` : "paused"}</span>
    </div>
  );
}
