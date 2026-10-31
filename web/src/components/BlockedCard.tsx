/**
 * Red card for wallet.blocked events.
 * Exact copy per user spec:
 *   "BLOCKED - Tried to buy at Rs 40/unit. Your max is Rs 5.50, so it was never sent."
 * Uses numbers from event.data and mandate; does not hardcode.
 */
import type { HubEvent } from "../lib/types";
import { useHubStore } from "../store/hub";

interface BlockedData {
  text?: string;
  reason?: string;
  offer?: { side?: string; price?: number; house?: string };
  tried_price?: number;
  max_buy_price?: number;
  min_sell_price?: number;
}

function fmt(n: number): string {
  return Number.isInteger(n) ? n.toString() : n.toFixed(2);
}

export function BlockedCard({ event }: { event: HubEvent }) {
  const d = (event.data ?? {}) as BlockedData;
  const mandates = useHubStore((s) => s.mandates);

  // If backend provided preformatted text, use it
  if (d.text) {
    return (
      <div className="rounded-2xl bg-red-50 p-4 text-red-900 ring-1 ring-red-200">
        <p className="text-sm font-medium">{d.text}</p>
      </div>
    );
  }

  const house = (event.house ?? d.offer?.house ?? "h14") as import("../lib/types").House;
  const mandate = mandates[house];
  const price = d.tried_price ?? d.offer?.price;
  const maxBuy = d.max_buy_price ?? mandate?.max_buy_price;
  const minSell = d.min_sell_price ?? mandate?.min_sell_price;
  const side = d.offer?.side ?? "bid";

  let body: string;
  if (side === "bid" && price !== undefined && maxBuy !== undefined) {
    body = `BLOCKED - Tried to buy at Rs ${fmt(price)}/unit. Your max is Rs ${fmt(maxBuy)}, so it was never sent.`;
  } else if (side === "ask" && price !== undefined && minSell !== undefined) {
    body = `BLOCKED - Tried to sell at Rs ${fmt(price)}/unit. Your min is Rs ${fmt(minSell)}, so it was never sent.`;
  } else {
    body = `BLOCKED - ${d.reason ?? "Offer blocked by mandate wallet."}`;
  }

  return (
    <div className="rounded-2xl bg-red-50 p-4 text-red-900 ring-1 ring-red-200">
      <p className="text-sm font-medium">{body}</p>
    </div>
  );
}
