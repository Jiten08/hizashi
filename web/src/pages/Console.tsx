// /console: demo controls — speed, reset, sim events per house, the ₹40 attack, ledger verify, raw log.
import { Button, Card, Chip, toast } from "@heroui/react";
import { useState } from "react";
import { Link } from "react-router-dom";
import { EventLog } from "../components/EventLog";
import { ClockChip, Icon, type IconName, SunMark } from "../components/ui";
import { useHub } from "../hooks/useHub";
import { api } from "../lib/api";
import { HOUSES, type House } from "../lib/types";

const SPEEDS = [1, 60, 300] as const;
const PER_HOUSE: { type: string; label: string; icon: IconName; minutes: number }[] = [
  { type: "cloud", label: "Cloud 45 min", icon: "cloud", minutes: 45 },
  { type: "ac", label: "AC on 2 h", icon: "bolt", minutes: 120 },
  { type: "guests", label: "Guests 3 h", icon: "home", minutes: 180 },
  { type: "away", label: "Away 4 h", icon: "clock", minutes: 240 },
];

export default function Console() {
  const hub = useHub("console");
  const [verify, setVerify] = useState<{ ok: boolean; broken_at?: number; entries?: number } | null>(null);
  const run = async (what: string, fn: () => Promise<unknown>) => {
    try {
      await fn();
      toast.success(what);
    } catch (e) {
      toast.danger(what, { description: (e as Error).message });
    }
  };
  const ev = (type: string, house?: House, minutes?: number) =>
    run(`${type}${house ? ` · ${hub.houses[house]?.label ?? house}` : ""}`, () => api.consoleEvent(type, house, minutes));

  return (
    <div className="mx-auto max-w-6xl space-y-4 p-6">
      <header className="flex items-center justify-between">
        <Link to="/" className="flex items-center gap-3">
          <SunMark className="h-10 w-10" />
          <div>
            <h1 className="text-2xl font-bold">Console</h1>
            <p className="text-sm text-stone-500">Drive the simulated day. Every button goes through the hub.</p>
          </div>
        </Link>
        <ClockChip />
      </header>

      <div className="grid gap-4 lg:grid-cols-3">
        <Card>
          <Card.Header className="px-4 pt-4"><Card.Title>Clock</Card.Title><Card.Description>One tick is one simulated minute.</Card.Description></Card.Header>
          <Card.Content className="gap-3 p-4">
            <div className="grid grid-cols-3 gap-2">
              {SPEEDS.map((s) => (
                <Button key={s} variant={hub.speed === s ? "primary" : "secondary"} onPress={() => run(`speed ${s}×`, () => api.setSpeed(s))}>{s}×</Button>
              ))}
            </div>
            <Button variant="danger-soft" onPress={() => run("day reset", api.reset)}>Reset the day (same seed)</Button>
          </Card.Content>
        </Card>

        <Card>
          <Card.Header className="px-4 pt-4"><Card.Title>Street events</Card.Title><Card.Description>Hit everyone at once.</Card.Description></Card.Header>
          <Card.Content className="gap-2 p-4">
            <Button variant="secondary" onPress={() => ev("cloud", undefined, 45)}><Icon name="cloud" className="h-4 w-4" /> Cloud over the street</Button>
            <Button variant="secondary" onPress={() => ev("outage", undefined, 30)}><Icon name="plug" className="h-4 w-4" /> Grid outage 30 min</Button>
            <Button variant="danger" onPress={() => ev("bad_bid", "h14")}><Icon name="ban" className="h-4 w-4" /> House 14 tries a ₹40 bid</Button>
          </Card.Content>
        </Card>

        <Card>
          <Card.Header className="px-4 pt-4"><Card.Title>Ledger</Card.Title><Card.Description>Re-hash every entry from the first.</Card.Description></Card.Header>
          <Card.Content className="gap-3 p-4">
            <Button variant="primary" onPress={async () => setVerify(await api.verifyLedger())}><Icon name="chain" className="h-4 w-4" /> Verify ledger</Button>
            {verify && (verify.ok
              ? <Chip color="success" variant="soft">intact · {verify.entries} entries</Chip>
              : <Chip color="danger" variant="soft">broken at #{verify.broken_at}</Chip>)}
          </Card.Content>
        </Card>
      </div>

      <Card>
        <Card.Header className="px-4 pt-4"><Card.Title>Per house</Card.Title></Card.Header>
        <Card.Content className="p-4">
          <div className="grid gap-3 md:grid-cols-4">
            {HOUSES.map((h) => (
              <div key={h} className="space-y-2 rounded-2xl bg-stone-50 p-3">
                <div className="flex items-center justify-between">
                  <p className="font-semibold">{hub.houses[h]?.label ?? h}</p>
                  <Link to={`/h/${h}`} className="text-xs text-sun underline">open app</Link>
                </div>
                {PER_HOUSE.filter((a) => a.type !== "cloud" || hub.houses[h]?.roof).map((a) => (
                  <Button key={a.type} size="sm" variant="tertiary" fullWidth onPress={() => ev(a.type, h, a.minutes)}>
                    <Icon name={a.icon} className="h-3.5 w-3.5" /> {a.label}
                  </Button>
                ))}
              </div>
            ))}
          </div>
        </Card.Content>
      </Card>

      <Card>
        <Card.Header className="px-4 pt-4"><Card.Title>Event log</Card.Title></Card.Header>
        <Card.Content className="p-4"><EventLog events={hub.log} /></Card.Content>
      </Card>
    </div>
  );
}
