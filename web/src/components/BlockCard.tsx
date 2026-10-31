import { blockLabel } from "../lib/api";
import type { BlockState } from "../lib/types";

export const STATE_STYLE: Record<BlockState, string> = {
  PLANNED: "bg-stone-100 text-stone-500",
  OPEN: "bg-amber-100 text-amber-800",
  GATE_CLOSED: "bg-orange-200 text-orange-900",
  DELIVERING: "bg-sun text-white",
  SETTLED: "bg-emerald-100 text-emerald-800",
};

const STATE_TEXT: Record<BlockState, string> = {
  PLANNED: "Planned",
  OPEN: "Open for deals",
  GATE_CLOSED: "Gate closed",
  DELIVERING: "Delivering now",
  SETTLED: "Settled",
};

/** One block: state, promised and contracted kWh (promised/contracted filled from R1.7). */
export function BlockCard({ index, state, promised, contracted }: {
  index: number; state: BlockState; promised?: number; contracted?: number;
}) {
  return (
    <div className="rounded-2xl border border-stone-200 bg-white p-4 shadow-sm">
      <div className="flex items-center justify-between">
        <span className="text-lg font-semibold">{blockLabel(index)}</span>
        <span className={`rounded-full px-3 py-1 text-xs font-medium ${STATE_STYLE[state]}`}>{STATE_TEXT[state]}</span>
      </div>
      <div className="mt-3 grid grid-cols-2 gap-2 text-sm text-stone-600">
        <div>Promised <b className="text-stone-900">{promised !== undefined ? `${promised.toFixed(2)} kWh` : "—"}</b></div>
        <div>Contracted <b className="text-stone-900">{contracted !== undefined ? `${contracted.toFixed(2)} kWh` : "—"}</b></div>
      </div>
    </div>
  );
}

/** All tradable blocks of the day as small coloured cells. */
export function BlockStrip({ blocks }: { blocks: Record<string, BlockState> }) {
  const entries = Object.entries(blocks).sort(([a], [b]) => a.localeCompare(b));
  if (!entries.length) return <p className="text-sm text-stone-500">Waiting for the market to open…</p>;
  return (
    <div className="grid grid-cols-13 gap-1">
      {entries.map(([key, state]) => {
        const index = Number(key.split("#")[1]);
        return (
          <div key={key} title={`${blockLabel(index)} · ${state}`}
            className={`h-6 rounded text-[9px] leading-6 text-center ${STATE_STYLE[state]}`}>
            {index % 4 === 0 ? String(index / 4).padStart(2, "0") : ""}
          </div>
        );
      })}
    </div>
  );
}
