import type { Approval } from "../lib/types";

/** Amber "NEEDS YOUR OK" card with Decline / Approve (R2.5). */
export function ApprovalCard({ approval, onDecide }: {
  approval: Approval; onDecide: (d: "approve" | "decline") => void;
}) {
  return (
    <div className="rounded-2xl bg-amber-50 p-4 ring-1 ring-amber-300">
      <p className="text-xs font-bold tracking-wide text-amber-800">NEEDS YOUR OK</p>
      <p className="mt-1 text-base text-stone-900">{approval.summary}</p>
      <div className="mt-3 flex gap-2">
        <button className="flex-1 rounded-xl border border-stone-300 bg-white py-2" onClick={() => onDecide("decline")}>Decline</button>
        <button className="flex-1 rounded-xl bg-sun py-2 font-semibold text-white" onClick={() => onDecide("approve")}>Approve</button>
      </div>
    </div>
  );
}
