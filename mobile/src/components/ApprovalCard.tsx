// "Needs your OK": the hub's plan summary with Decline / Approve.
import { useState } from "react";
import { api } from "../lib/api";
import { hhmm } from "../lib/format";
import type { Approval } from "../lib/types";
import { Button, Card, Icon } from "./ui";

export function ApprovalCard({ approval }: { approval: Approval }) {
  const [busy, setBusy] = useState<"approve" | "decline" | null>(null);
  const [error, setError] = useState<string | null>(null);
  const decide = async (d: "approve" | "decline") => {
    setBusy(d);
    setError(null);
    try {
      await api.decide(approval.approval_id, d);
      navigator.vibrate?.(15);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(null);
    }
  };
  return (
    <Card className="rise mt-3">
      <div className="flex items-center gap-1.5">
        <Icon name="hand" className="h-4 w-4 text-orange" strokeWidth={2.2} />
        <span className="t-footnote flex-1 font-semibold text-orange">NEEDS YOUR OK</span>
        <span className="t-caption">{hhmm(approval.created_at)}</span>
      </div>
      <p className="t-title3 mt-2">{approval.summary}</p>
      <p className="t-footnote mt-1.5">If you don't answer before the window opens, your agent goes ahead within your limits.</p>
      {error && <p className="t-footnote mt-1.5 text-red">{error}</p>}
      <div className="mt-3.5 grid grid-cols-2 gap-2.5">
        <Button kind="gray" onClick={() => decide("decline")} busy={busy === "decline"} disabled={busy !== null}>Decline</Button>
        <Button onClick={() => decide("approve")} busy={busy === "approve"} disabled={busy !== null}>Approve</Button>
      </div>
    </Card>
  );
}
