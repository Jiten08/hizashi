// The agent's day plan: one chip per window, coloured by the owner's decision.
import { Card, Chip } from "@heroui/react";
import { windowLabel } from "../lib/api";
import type { PlanWindow } from "../lib/types";

const STATUS = {
  auto: { color: "default", label: "auto" },
  pending: { color: "warning", label: "needs OK" },
  approved: { color: "success", label: "approved" },
  declined: { color: "danger", label: "declined" },
  expired: { color: "default", label: "not approved" },
} as const;

export function PlanStrip({ windows }: { windows: PlanWindow[] }) {
  if (!windows.length) return null;
  return (
    <Card>
      <Card.Content className="gap-2 p-4">
        <ul className="space-y-2">
          {windows.map((w) => (
            <li key={w.plan_id} className="flex items-center gap-3 text-sm">
              <span className={`h-2 w-2 shrink-0 rounded-full ${w.side === "sell" ? "bg-sun" : "bg-sky-500"}`} />
              <span className="num w-24 text-stone-500">{windowLabel(w.first_index, w.last_index)}</span>
              <span className="flex-1 font-medium">
                {w.side === "sell" ? "Sell" : "Buy"} {w.kwh.toFixed(w.kwh < 1 ? 2 : 1)} kWh
                <span className="num font-normal text-stone-500"> · ~₹{w.expected_value.toFixed(2)}</span>
              </span>
              <Chip size="sm" variant="soft" color={STATUS[w.status].color}>{STATUS[w.status].label}</Chip>
            </li>
          ))}
        </ul>
      </Card.Content>
    </Card>
  );
}
