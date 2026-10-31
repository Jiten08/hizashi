// "Needs your OK": the hub's plan summary with Decline / Approve.
import { Ionicons } from "@expo/vector-icons";
import * as Haptics from "expo-haptics";
import { useState } from "react";
import { Text, View } from "react-native";
import { hhmm } from "../lib/format";
import { api } from "../lib/store";
import { C, T } from "../lib/theme";
import type { Approval } from "../lib/types";
import { Button, Card } from "./ui";

export function ApprovalCard({ approval }: { approval: Approval }) {
  const [busy, setBusy] = useState<"approve" | "decline" | null>(null);
  const [error, setError] = useState<string | null>(null);
  const decide = async (d: "approve" | "decline") => {
    setBusy(d);
    setError(null);
    try {
      await api().decide(approval.approval_id, d);
      Haptics.notificationAsync(d === "approve" ? Haptics.NotificationFeedbackType.Success : Haptics.NotificationFeedbackType.Warning).catch(() => {});
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(null);
    }
  };
  return (
    <Card style={{ marginTop: 12 }}>
      <View style={{ flexDirection: "row", alignItems: "center", gap: 6 }}>
        <Ionicons name="hand-left" size={15} color={C.orange} />
        <Text style={[T.footnote, { color: C.orange, fontWeight: "600", flex: 1 }]}>NEEDS YOUR OK</Text>
        <Text style={T.caption}>{hhmm(approval.created_at)}</Text>
      </View>
      <Text style={[T.title3, { marginTop: 8 }]}>{approval.summary}</Text>
      <Text style={[T.footnote, { marginTop: 6 }]}>
        If you don't answer before the window opens, your agent goes ahead within your limits.
      </Text>
      {error ? <Text style={[T.footnote, { color: C.red, marginTop: 6 }]}>{error}</Text> : null}
      <View style={{ flexDirection: "row", gap: 10, marginTop: 14 }}>
        <Button title="Decline" kind="gray" style={{ flex: 1 }} onPress={() => decide("decline")} busy={busy === "decline"} disabled={busy !== null} />
        <Button title="Approve" style={{ flex: 1 }} onPress={() => decide("approve")} busy={busy === "approve"} disabled={busy !== null} />
      </View>
    </Card>
  );
}
