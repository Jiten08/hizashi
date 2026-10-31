import { View } from "react-native";
import { ApprovalCard } from "../../components/ApprovalCard";
import { Pill, Row, Screen, Section } from "../../components/ui";
import { hhmm } from "../../lib/format";
import { useHub } from "../../lib/store";
import { C } from "../../lib/theme";

const TONE = {
  approved: { text: "Approved", color: C.greenText, bg: C.greenSoft },
  declined: { text: "Declined", color: C.red, bg: C.redSoft },
  expired: { text: "Went ahead", color: C.label2, bg: C.fill2 },
  pending: { text: "Waiting", color: C.orange, bg: C.orangeSoft },
} as const;

export default function Approvals() {
  const hub = useHub();
  const house = hub.conn!.house;
  const mine = hub.approvals.filter((a) => a.house === house);
  const pending = mine.filter((a) => a.status === "pending");
  const done = mine.filter((a) => a.status !== "pending").reverse();
  return (
    <Screen title="Approvals">
      {pending.length ? pending.map((a) => <ApprovalCard key={a.approval_id} approval={a} />) : (
        <Section footer="Buy plans over your “ask me above” limit show up here first.">
          <Row icon="checkmark" iconBg={C.green} title="Nothing waiting for you" />
        </Section>
      )}
      {done.length ? (
        <Section header="Earlier today">
          {done.map((a, i) => (
            <Row key={a.approval_id} last={i === done.length - 1} title={a.summary} subtitle={`asked ${hhmm(a.created_at)}`}
              accessory={<View style={{ marginLeft: 8 }}><Pill text={TONE[a.status].text} color={TONE[a.status].color} bg={TONE[a.status].bg} /></View>} />
          ))}
        </Section>
      ) : null}
    </Screen>
  );
}
