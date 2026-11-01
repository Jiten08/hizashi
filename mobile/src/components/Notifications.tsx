// Approval notifications: the switch on Rules, and a nudge on Approvals while they're off.
import { useEffect, useState } from "react";
import { api } from "../lib/api";
import { PUSH_HELP, usePush } from "../lib/push";
import type { House } from "../lib/types";
import { Button, Card, Icon, Row, Section, Toggle } from "./ui";

export function NotificationsSection({ house }: { house: House }) {
  const p = usePush(house);
  if (p.status === "checking") return null;
  const can = p.status === "on" || p.status === "off";
  return (
    <Section header="Notifications" footer={p.error ?? PUSH_HELP[p.status]}>
      <Row icon="bell" iconBg="var(--color-red)" title="When your OK is needed" last={p.status !== "on"}
        accessory={can ? <Toggle on={p.status === "on"} label="Approval notifications"
          onChange={(on) => (on ? p.enable() : p.disable())} /> : <span className="t-body text-label-2">Off</span>} />
      {p.status === "on" && <Row title={<span className="text-orange">{p.busy ? "Sending…" : "Send a test notification"}</span>} onClick={p.test} />}
      <TestApproval house={house} pushOn={p.status === "on"} />
    </Section>
  );
}

const TEST_DELAY = 10;

/** A real approval request in 10 s: lock the phone and it should light up with Approve / Decline. */
function TestApproval({ house, pushOn }: { house: House; pushOn: boolean }) {
  const [left, setLeft] = useState<number | null>(null);
  const [note, setNote] = useState<string | null>(null);
  useEffect(() => {
    if (left === null || left <= 0) return;
    const t = setTimeout(() => setLeft(left - 1), 1000);
    return () => clearTimeout(t);
  }, [left]);
  const start = async () => {
    setNote(null);
    try {
      const r = await api.testApproval(house, TEST_DELAY);
      setLeft(r.delay);
      setNote(r.subscribed ? "Lock your phone now. The request arrives as a notification." :
        "This phone isn't signed up for notifications, so the request will only show in Approvals.");
    } catch (e) {
      setNote((e as Error).message);
    }
  };
  const title = left && left > 0 ? `Arriving in ${left} s…` : left === 0 ? "Sent: check the lock screen / Approvals" : "Send a test approval in 10 s";
  return (
    <Row last title={<span className="text-orange">{title}</span>}
      subtitle={note ?? (pushOn ? "A real request for your OK: approve or decline it from the notification." : undefined)}
      onClick={left && left > 0 ? undefined : start} />
  );
}

export function PushPrompt({ house }: { house: House }) {
  const p = usePush(house);
  if (p.status !== "off") return null;
  return (
    <Card className="rise mt-3">
      <div className="flex items-start gap-3">
        <Icon name="bell" className="mt-0.5 h-6 w-6 shrink-0 text-orange" strokeWidth={2} />
        <div className="flex-1">
          <p className="t-headline">Get asked on your lock screen</p>
          <p className="t-footnote mt-0.5">{PUSH_HELP.off}</p>
          {p.error && <p className="t-footnote mt-1 !text-red">{p.error}</p>}
        </div>
      </div>
      <Button className="mt-3 w-full" onClick={p.enable} busy={p.busy}>Turn on notifications</Button>
    </Card>
  );
}
