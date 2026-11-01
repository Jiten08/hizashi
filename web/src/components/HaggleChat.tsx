// The latest A2A haggle as an offer log: who, ask or bid, kWh, price, round, and the deal.
// Every figure is the hub's (the wallet signed the offers).
import { useHubStore } from "../store/hub";
import { blockLabel, rupees } from "../lib/api";
import type { Offer } from "../lib/types";

const short = (h?: string | null) => (h ? `H${h.slice(1)}` : "");

export function HaggleChat() {
  const negotiations = useHubStore((s) => s.negotiations);
  const contracts = useHubStore((s) => s.contracts);
  const latest = Object.values(negotiations).filter((os) => os[0]?.to != null).at(-1) ?? [];
  const offers: Offer[] = [...latest].sort((a, b) => a.round - b.round || (a.side === "ask" ? -1 : 1));
  if (!offers.length) return <p className="text-sm text-ink-2">No haggling yet.</p>;
  const deal = contracts.find((c) => c.negotiation_id === offers[0].negotiation_id);
  return (
    <div className="num text-[13px]">
      <p className="mb-2 text-xs text-ink-2">{blockLabel(offers[0].block.index)}</p>
      <ul className="space-y-1">
        {offers.slice(-8).map((o) => (
          <li key={o.offer_id} className="flex items-baseline gap-2">
            <span className="w-6 text-[11px] text-ink-3">R{o.round + 1}</span>
            <span className={`w-24 whitespace-nowrap font-semibold ${o.side === "ask" ? "text-sun-ink" : "text-sky"}`}>
              {short(o.house)} {o.side === "ask" ? "ask" : "bid"} →{short(o.to)}
            </span>
            <span className="text-ink-2">{o.kwh.toFixed(2)} kWh</span>
            <span className="ml-auto font-semibold text-ink">{rupees(o.price)}</span>
          </li>
        ))}
      </ul>
      {deal && (
        <p className="mt-2 rounded-lg bg-leaf-soft px-2.5 py-1.5 font-semibold text-leaf-ink">
          Deal {short(deal.seller)}→{short(deal.buyer)} · {deal.kwh.toFixed(2)} kWh · {rupees(deal.price)}
        </p>
      )}
    </div>
  );
}
