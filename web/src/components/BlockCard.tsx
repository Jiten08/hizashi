// The live block: where it is in its lifecycle and what this house has contracted in it.
import { Card, Chip } from "@heroui/react";
import { blockLabel, kwh, rupees } from "../lib/api";
import type { BlockState, Contract, House, Settlement } from "../lib/types";

const STEPS: { state: BlockState; label: string }[] = [
  { state: "PLANNED", label: "Planned" },
  { state: "OPEN", label: "Deals" },
  { state: "GATE_CLOSED", label: "Gate" },
  { state: "DELIVERING", label: "Live" },
  { state: "SETTLED", label: "Settled" },
];

const HINT: Record<BlockState, string> = {
  PLANNED: "Your agent has a plan for this block.",
  OPEN: "Agents are haggling. Deals close an hour before the block.",
  GATE_CLOSED: "Schedule frozen; leftovers go to the street auction.",
  DELIVERING: "Power is flowing now. Meters are signing every minute.",
  SETTLED: "Settled under KERC 8(g).",
};

export function BlockCard({ index, state, house, contracts, settlements }: {
  index: number; state: BlockState; house: House; contracts: Contract[]; settlements: Settlement[];
}) {
  const at = STEPS.findIndex((s) => s.state === state);
  const mine = contracts.filter((c) => c.block.index === index && (c.seller === house || c.buyer === house));
  return (
    <Card>
      <Card.Content className="gap-3 p-4">
        <div className="flex items-center justify-between">
          <div>
            <p className="text-xs font-medium uppercase tracking-wide text-stone-500">Now</p>
            <p className="num text-xl font-semibold">{blockLabel(index)}</p>
          </div>
          <Chip size="sm" variant="soft" color={state === "DELIVERING" ? "accent" : state === "SETTLED" ? "success" : "default"}>
            {STEPS[at]?.label ?? state}
          </Chip>
        </div>
        <ol className="grid grid-cols-5 gap-1" aria-label="Block lifecycle">
          {STEPS.map((s, i) => (
            <li key={s.state} className="flex flex-col gap-1">
              <span className={`h-1.5 rounded-full ${i < at ? "bg-sun/60" : i === at ? "bg-sun" : "bg-stone-200"}`} />
              <span className={`text-[10px] ${i === at ? "font-semibold text-ink" : "text-stone-400"}`}>{s.label}</span>
            </li>
          ))}
        </ol>
        <p className="text-sm text-stone-600">{HINT[state]}</p>
        {mine.length > 0 && (
          <ul className="divide-y divide-stone-100 rounded-xl bg-stone-50 px-3">
            {mine.map((c) => {
              const s = settlements.find((x) => x.contract_id === c.contract_id);
              const selling = c.seller === house;
              return (
                <li key={c.contract_id} className="flex items-center justify-between py-2 text-sm">
                  <span>{selling ? "Selling to" : "Buying from"} <b>{(selling ? c.buyer : c.seller).replace("h", "House ")}</b></span>
                  <span className="num font-medium">
                    {kwh(c.kwh)} · {rupees(c.price)}
                    {s && s.shortfall_kwh > 0 && <span className="ml-1 text-red-600">short {s.shortfall_kwh.toFixed(2)}</span>}
                  </span>
                </li>
              );
            })}
          </ul>
        )}
      </Card.Content>
    </Card>
  );
}
