// The wallet's limits as iOS steppers (used by onboarding and the Rules tab).
import type { Mandate } from "../lib/types";
import { Stepper } from "./ui";

const money = (v: number) => `₹${v.toFixed(2)}`;

export function MandateSteppers({ m, set, hasSolar }: { m: Mandate; set: (p: Partial<Mandate>) => void; hasSolar: boolean }) {
  return (
    <div>
      {hasSolar && (
        <Stepper label="Never sell below" hint="per unit" value={m.min_sell_price} step={0.1} min={0} max={10}
          onChange={(v) => set({ min_sell_price: v })} format={money} />
      )}
      <Stepper label="Never buy above" hint="BESCOM charges ₹5.80" value={m.max_buy_price} step={0.1} min={0} max={10}
        onChange={(v) => set({ max_buy_price: v })} format={money} />
      <Stepper label="Daily budget" hint="spent on neighbours' power" value={m.daily_budget} step={5} min={0} max={500}
        onChange={(v) => set({ daily_budget: v })} format={(v) => `₹${v.toFixed(0)}`} />
      <Stepper label="Ask me above" hint="bigger buy plans ask first" value={m.approve_above} step={1} min={0} max={200}
        onChange={(v) => set({ approve_above: v })} format={(v) => `₹${v.toFixed(0)}`} last={!hasSolar} />
      {hasSolar && (
        <Stepper label="Max per block" hint="caps a cloud's cost" value={m.max_promise_kwh} step={0.1} min={0.1} max={5}
          onChange={(v) => set({ max_promise_kwh: v })} format={(v) => `${v.toFixed(1)} kWh`} last />
      )}
    </div>
  );
}
