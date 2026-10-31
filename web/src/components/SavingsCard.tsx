/**
 * SavingsCard — shows "Saved vs BESCOM" from savings.updated events.
 * Spec: do NOT calculate in the browser.
 * Review 1: always show dash + "coming at Review 2".
 */

export function SavingsCard({ savedToday, projectedYear }: { savedToday?: number; projectedYear?: number }) {
  const hasData = savedToday !== undefined;
  return (
    <div className="rounded-2xl bg-amber-50 p-5 ring-1 ring-amber-200">
      <p className="text-sm text-amber-900">Saved today vs BESCOM</p>
      {hasData ? (
        <>
          <p className="mt-1 text-4xl font-bold tabular-nums text-amber-900">
            ₹{savedToday!.toFixed(2)}
          </p>
          {projectedYear !== undefined && (
            <p className="mt-1 text-sm text-amber-800">
              ≈ ₹{projectedYear.toFixed(2)} this year if every day were like today
            </p>
          )}
        </>
      ) : (
        <>
          <p className="mt-1 text-4xl font-bold tabular-nums text-amber-400">₹ —</p>
          <p className="mt-1 text-xs text-amber-700">coming at Review 2</p>
        </>
      )}
    </div>
  );
}
