// Ask ₹5.40 → Bid ₹4.00 → … → Deal 0.20 kWh at ₹4.68, built from nego.offer + contract.booked.
import { Card } from "@heroui/react";
import { blockLabel } from "../lib/api";
import type { Contract, House, Offer } from "../lib/types";
import { Icon } from "./ui";

export function HaggleFeed({ offers, deal, house }: { offers: Offer[]; deal?: Contract; house: House }) {
  const sorted = [...offers].sort((a, b) => (a.round !== b.round ? a.round - b.round : a.side === "ask" ? -1 : 1));
  const first = sorted[0];
  if (!first) return null;
  const other = first.house === house ? first.to : first.house;
  return (
    <Card>
      <Card.Content className="gap-3 p-4">
        <div className="flex items-center justify-between text-sm">
          <span className="flex items-center gap-1.5 font-medium">
            <Icon name="hand" className="h-4 w-4 text-sun" />
            {first.side === "ask" && first.house === house ? "Selling to" : "Buying from"} {other?.replace("h", "House ")}
          </span>
          <span className="num text-stone-500">{blockLabel(first.block.index)} · {first.kwh.toFixed(2)} kWh</span>
        </div>
        <ol className="flex flex-wrap items-center gap-1.5">
          {sorted.map((o, i) => (
            <li key={o.offer_id} className="pop-in flex items-center gap-1.5">
              {i > 0 && <span className="text-stone-300">→</span>}
              <span className={`num rounded-lg px-2 py-1 text-sm font-medium ${o.side === "ask" ? "bg-amber-50 text-amber-900 ring-1 ring-amber-200" : "bg-sky-50 text-sky-900 ring-1 ring-sky-200"}`}>
                {o.side === "ask" ? "Ask" : "Bid"} ₹{o.price.toFixed(2)}
              </span>
            </li>
          ))}
          {deal && (
            <li className="pop-in flex items-center gap-1.5">
              <span className="text-stone-300">→</span>
              <span className="num inline-flex items-center gap-1 rounded-lg bg-emerald-600 px-2 py-1 text-sm font-semibold text-white">
                <Icon name="check" className="h-3.5 w-3.5" strokeWidth={2.6} /> Deal {deal.kwh.toFixed(2)} kWh at ₹{deal.price.toFixed(2)}
              </span>
            </li>
          )}
        </ol>
      </Card.Content>
    </Card>
  );
}
