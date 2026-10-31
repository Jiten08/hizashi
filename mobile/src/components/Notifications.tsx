// Approval notifications: the switch on Rules, and a nudge on Approvals while they're off.
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
      {p.status === "on" && <Row title={<span className="text-orange">{p.busy ? "Sending…" : "Send a test notification"}</span>} onClick={p.test} last />}
    </Section>
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
