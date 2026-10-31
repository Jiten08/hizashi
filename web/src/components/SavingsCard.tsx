// "Saved today vs BESCOM ₹X" — every number here comes from the hub's savings.updated.
import { Card } from "@heroui/react";
import type { Savings } from "../lib/types";
import { Icon } from "./ui";

export function SavingsCard({ savings, hasSolar }: { savings?: Savings; hasSolar: boolean }) {
  const saved = savings?.saved_today;
  return (
    <Card className="relative overflow-hidden border-0 bg-gradient-to-br from-[#f6b73c] via-[#e79a12] to-[#c97a00] text-white shadow-lg shadow-amber-600/20">
      <div className="sun-glow pointer-events-none absolute -right-16 -top-16 h-56 w-56 rounded-full bg-yellow-200/40 blur-2xl" />
      <Card.Content className="relative gap-1 p-5">
        <p className="flex items-center gap-1.5 text-sm font-medium text-white/85">
          <Icon name="sparkle" className="h-4 w-4" /> Saved today vs BESCOM
        </p>
        <p className="num text-5xl font-bold leading-tight">{saved === undefined ? "₹0.00" : `₹${saved.toFixed(2)}`}</p>
        <p className="text-sm text-white/85">
          {savings && savings.projected_year > 0
            ? <>≈ ₹{savings.projected_year.toLocaleString("en-IN", { maximumFractionDigits: 0 })} a year if the year had 300 days like today</>
            : hasSolar ? "Your first deal settles 15 minutes after its block." : "You save every time you buy from a neighbour instead of BESCOM."}
        </p>
        {savings && savings.trades > 0 && (
          <div className="mt-3 grid grid-cols-3 gap-2 rounded-xl bg-black/10 p-2.5 text-center text-xs">
            <div><p className="num text-base font-semibold">{savings.sold_kwh.toFixed(2)}</p><p className="text-white/75">kWh sold</p></div>
            <div><p className="num text-base font-semibold">{savings.bought_kwh.toFixed(2)}</p><p className="text-white/75">kWh bought</p></div>
            <div><p className="num text-base font-semibold">{savings.trades}</p><p className="text-white/75">trades</p></div>
          </div>
        )}
      </Card.Content>
    </Card>
  );
}
