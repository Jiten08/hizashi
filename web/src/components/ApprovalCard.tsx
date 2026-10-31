// Amber "NEEDS YOUR OK" card: the hub's plan summary with Decline / Approve.
import { Button, Card, Chip } from "@heroui/react";
import { useState } from "react";
import { api, hhmm } from "../lib/api";
import type { Approval } from "../lib/types";
import { Icon } from "./ui";

export function ApprovalCard({ approval }: { approval: Approval }) {
  const [busy, setBusy] = useState<"approve" | "decline" | null>(null);
  const [error, setError] = useState<string | null>(null);
  const decide = async (d: "approve" | "decline") => {
    setBusy(d);
    setError(null);
    try {
      await api.decide(approval.approval_id, d);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(null);
    }
  };
  return (
    <Card className="pop-in border border-amber-300 bg-gradient-to-b from-amber-50 to-white shadow-md shadow-amber-500/10">
      <Card.Content className="gap-3 p-4">
        <div className="flex items-center justify-between">
          <Chip size="sm" color="warning" variant="primary">
            <Icon name="hand" className="h-3.5 w-3.5" /> Needs your OK
          </Chip>
          <span className="text-xs text-stone-500">code {approval.code} · {hhmm(approval.created_at)}</span>
        </div>
        <p className="text-lg font-semibold leading-snug">{approval.summary}</p>
        <p className="text-xs text-stone-500">
          Your agent won't buy in this window until you decide. Over your “ask me above” limit.
        </p>
        {error && <p className="text-sm text-red-600">{error}</p>}
        <div className="grid grid-cols-2 gap-2">
          <Button variant="secondary" size="lg" onPress={() => decide("decline")} isDisabled={busy !== null}>
            Decline
          </Button>
          <Button variant="primary" size="lg" onPress={() => decide("approve")} isDisabled={busy !== null}>
            <Icon name="check" className="h-4 w-4" strokeWidth={2.4} /> Approve
          </Button>
        </div>
      </Card.Content>
    </Card>
  );
}
