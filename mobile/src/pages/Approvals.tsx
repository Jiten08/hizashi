import { ApprovalCard } from "../components/ApprovalCard";
import { Pill, Row, Screen, Section } from "../components/ui";
import { hhmm } from "../lib/format";
import { useHubStore } from "../lib/store";
import type { House } from "../lib/types";

const TONE = {
  approved: { text: "Approved", cls: "bg-green-soft text-green-ink" },
  declined: { text: "Declined", cls: "bg-red-soft text-red" },
  expired: { text: "Went ahead", cls: "bg-fill text-label-2" },
  pending: { text: "Waiting", cls: "bg-orange-soft text-orange" },
} as const;

export default function Approvals({ house }: { house: House }) {
  const all = useHubStore((s) => s.approvals);
  const mine = all.filter((a) => a.house === house);
  const pending = mine.filter((a) => a.status === "pending");
  const done = mine.filter((a) => a.status !== "pending").reverse();
  return (
    <Screen title="Approvals">
      {pending.length ? pending.map((a) => <ApprovalCard key={a.approval_id} approval={a} />) : (
        <Section footer="Buy plans over your “ask me above” limit show up here first.">
          <Row icon="check" iconBg="var(--color-green)" title="Nothing waiting for you" last />
        </Section>
      )}
      {done.length > 0 && (
        <Section header="Earlier today">
          {done.map((a, i) => (
            <Row key={a.approval_id} last={i === done.length - 1} title={a.summary} subtitle={`asked ${hhmm(a.created_at)}`}
              accessory={<span className="ml-2"><Pill className={TONE[a.status].cls}>{TONE[a.status].text}</Pill></span>} />
          ))}
        </Section>
      )}
    </Screen>
  );
}
