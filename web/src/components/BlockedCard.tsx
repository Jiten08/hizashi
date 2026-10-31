// Red card for wallet.blocked: the hub's sentence as it is ("BLOCKED · Tried to buy at ₹40...").
import { Alert } from "@heroui/react";
import { hhmm } from "../lib/api";

export function BlockedCard({ text, reason, at }: { text?: string; reason?: string; at?: string }) {
  const body = (text ?? reason ?? "").replace(/^BLOCKED · /, "");
  return (
    <Alert status="danger" className="pop-in">
      <Alert.Indicator />
      <Alert.Content>
        <Alert.Title>Blocked by your wallet{at ? ` · ${hhmm(at)}` : ""}</Alert.Title>
        <Alert.Description>{body}</Alert.Description>
      </Alert.Content>
    </Alert>
  );
}
