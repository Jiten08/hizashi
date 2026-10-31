import { rupees } from "../lib/api";

/** "Saved today vs BESCOM ₹X" — values come from savings.updated (R2.3/R2.8). */
export function SavingsCard({ savedToday, projectedYear }: { savedToday?: number; projectedYear?: number }) {
  return (
    <div className="rounded-2xl bg-amber-50 p-5 ring-1 ring-amber-200">
      <p className="text-sm text-amber-900">Saved today vs BESCOM</p>
      <p className="mt-1 text-4xl font-bold tabular-nums text-amber-900">{savedToday !== undefined ? rupees(savedToday) : "₹—"}</p>
      {projectedYear !== undefined && (
        <p className="mt-1 text-sm text-amber-800">≈ {rupees(projectedYear)} this year if every day were like today</p>
      )}
    </div>
  );
}
