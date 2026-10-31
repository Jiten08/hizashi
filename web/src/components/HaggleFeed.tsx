/**
 * HaggleFeed — renders the haggle sequence inline.
 * Format: Ask Rs 5.40 -> Bid Rs 4.00 -> ... -> Deal 0.20 kWh at Rs 4.68
 *
 * Built from nego.offer events and contract.booked.
 * Does NOT rely on nego.result existing.
 */
import type { Contract, Offer } from "../lib/types";

export function HaggleFeed({ offers, deal }: { offers: Offer[]; deal?: Contract }) {
  if (!offers.length && !deal) return <p className="text-sm text-stone-500">No haggling yet.</p>;

  // Sort by round then by side (ask before bid in same round)
  const sorted = [...offers].sort((a, b) =>
    a.round !== b.round ? a.round - b.round : a.side === "ask" ? -1 : 1,
  );

  return (
    <div className="flex flex-wrap items-center gap-1.5 text-sm leading-loose">
      {sorted.map((o, i) => (
        <span key={o.offer_id} className="inline-flex items-center gap-1.5">
          {i > 0 && <span className="text-stone-400">→</span>}
          <span
            className={
              o.side === "ask"
                ? "rounded-md bg-amber-100 px-2 py-0.5 font-medium text-amber-900"
                : "rounded-md bg-sky-100 px-2 py-0.5 font-medium text-sky-900"
            }
          >
            {o.side === "ask" ? "Ask" : "Bid"} Rs {o.price.toFixed(2)}
          </span>
        </span>
      ))}
      {deal && (
        <span className="inline-flex items-center gap-1.5">
          {sorted.length > 0 && <span className="text-stone-400">→</span>}
          <span className="rounded-md bg-emerald-100 px-2 py-0.5 font-semibold text-emerald-900">
            Deal {deal.kwh.toFixed(2)} kWh at Rs {deal.price.toFixed(2)}
          </span>
        </span>
      )}
    </div>
  );
}
