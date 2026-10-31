// The latest haggle as a chat: each offer an agent made, its price, and what it said.
// Prices and lines come from the hub (the wallet signed the offers; agents wrote the lines).
import { useHub } from "../hooks/useHub";
import { blockLabel, rupees } from "../lib/api";
import type { Offer } from "../lib/types";

const name = (h?: string | null) => (h ? `House ${h.slice(1)}` : "");

export function HaggleChat() {
  const hub = useHub("street");
  // The newest neighbour-to-neighbour haggle, preferring one the agents have talked in.
  const all = Object.values(hub.negotiations).filter((os) => os[0]?.to != null);
  const talked = all.filter((os) => os.some((o) => hub.notes[o.offer_id]));
  const offers: Offer[] = [...(talked.at(-1) ?? all.at(-1) ?? [])].sort((a, b) => a.round - b.round || (a.side === "ask" ? -1 : 1));
  if (!offers.length) return <p className="text-sm text-ink-2">The agents haven't started haggling yet.</p>;
  const seller = offers[0].side === "ask" ? offers[0].house : offers[0].to;
  const deal = hub.contracts.find((c) => c.negotiation_id === offers[0].negotiation_id);
  return (
    <div>
      <p className="mb-3 text-xs text-ink-2">{name(seller)} selling · {blockLabel(offers[0].block.index)}</p>
      <ul className="space-y-2">
        {offers.slice(-6).map((o) => {
          const note = hub.notes[o.offer_id];
          const mine = o.side === "ask";
          return (
            <li key={o.offer_id} className={`flex ${mine ? "justify-start" : "justify-end"}`}>
              <div className={`max-w-[88%] rounded-2xl px-3 py-2 ${mine ? "rounded-bl-md bg-sun-soft" : "rounded-br-md bg-sky-soft"}`}>
                <p className="flex items-baseline gap-2 text-[11px] font-semibold">
                  <span className={mine ? "text-sun-ink" : "text-sky"}>{name(o.house)} · {mine ? "ask" : "bid"}</span>
                  <span className="num text-ink">{rupees(o.price)}</span>
                  {note?.source === "gemini" && <span className="font-medium text-ink-3">Gemini</span>}
                </p>
                <p className="mt-0.5 text-[13px] leading-snug text-ink">{note ? note.text : <span className="text-ink-3">…</span>}</p>
              </div>
            </li>
          );
        })}
      </ul>
      {deal && (
        <p className="mt-3 rounded-xl bg-leaf-soft px-3 py-2 text-center text-[13px] font-semibold text-leaf-ink">
          Deal · {deal.kwh.toFixed(2)} kWh at {rupees(deal.price)}
        </p>
      )}
    </div>
  );
}
