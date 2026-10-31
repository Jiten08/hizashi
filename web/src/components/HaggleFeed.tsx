import { rupees } from "../lib/api";
import type { Contract, Offer } from "../lib/types";

/** Ask ₹5.40 → Bid ₹4.00 → … → Deal 0.20 kWh at ₹4.68. Filled from nego.offer / contract.booked (R1.7). */
export function HaggleFeed({ offers, deal }: { offers: Offer[]; deal?: Contract }) {
  if (!offers.length) return <p className="text-sm text-stone-500">No haggling yet.</p>;
  return (
    <div className="flex flex-wrap items-center gap-1 text-sm">
      {offers.map((o, i) => (
        <span key={o.offer_id} className="flex items-center gap-1">
          {i > 0 && <span className="text-stone-400">→</span>}
          <span className={o.side === "ask" ? "text-amber-700" : "text-sky-700"}>
            {o.side === "ask" ? "Ask" : "Bid"} {rupees(o.price)}
          </span>
        </span>
      ))}
      {deal && <span className="font-semibold text-emerald-700">→ Deal {deal.kwh.toFixed(2)} kWh at {rupees(deal.price)}</span>}
    </div>
  );
}
