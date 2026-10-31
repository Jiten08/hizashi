/** Red card from wallet.blocked: "BLOCKED · Tried to buy at ₹40/unit. Your max is ₹5.50, so it was never sent." (R2.9) */
export function BlockedCard({ text }: { text: string }) {
  return (
    <div className="rounded-2xl bg-red-50 p-4 text-red-900 ring-1 ring-red-200">
      <p className="text-xs font-bold tracking-wide">BLOCKED</p>
      <p className="mt-1 text-sm">{text}</p>
    </div>
  );
}
