// /console: every demo control — speed, reset, street and per-house events, the ₹40 attack,
// ledger verify — plus the raw event log.
import { useState } from "react";
import { Link } from "react-router-dom";
import { EventLog } from "../components/EventLog";
import { Button, Card, Clock, Icon, type IconName, Logo, Segmented, toast } from "../components/ui";
import { useHub } from "../hooks/useHub";
import { api } from "../lib/api";
import { HOUSES, type House } from "../lib/types";

const PER_HOUSE: { type: string; label: string; icon: IconName; minutes: number; solarOnly?: boolean }[] = [
  { type: "cloud", label: "Cloud · 45 min", icon: "cloud", minutes: 45, solarOnly: true },
  { type: "ac", label: "AC on · 2 h", icon: "bolt", minutes: 120 },
  { type: "guests", label: "Guests · 3 h", icon: "people", minutes: 180 },
  { type: "away", label: "Away · 4 h", icon: "home", minutes: 240 },
];

export default function Console() {
  const hub = useHub("console");
  const [verify, setVerify] = useState<{ ok: boolean; broken_at?: number; entries?: number } | null>(null);
  const run = async (what: string, fn: () => Promise<unknown>) => {
    try { await fn(); toast(what, undefined, "ok"); } catch (e) { toast(what, (e as Error).message, "bad"); }
  };
  const ev = (type: string, house?: House, minutes?: number) =>
    run(`${type}${house ? ` · House ${house.slice(1)}` : ""}`, () => api.consoleEvent(type, house, minutes));

  return (
    <div className="mx-auto max-w-[1440px] px-8 pb-10 pt-6">
      <header className="flex items-center gap-4">
        <Link to="/" className="flex items-center gap-4">
          <Logo />
          <div>
            <h1 className="text-[22px] font-semibold leading-tight tracking-tight">Controls</h1>
            <p className="text-[13px] text-ink-2">Drive the simulated day. Every button goes through the hub.</p>
          </div>
        </Link>
        <div className="flex-1" />
        <Clock />
        <Link to="/"><Button icon="arrow">Back to the street</Button></Link>
      </header>

      <div className="mt-6 grid grid-cols-3 gap-5">
        <Card title="Clock">
          <div className="flex items-center justify-between">
            <span className="text-sm text-ink-2">Speed (one tick = one sim minute)</span>
            <Segmented value={hub.speed} onChange={(s) => run(`Speed ${s}×`, () => api.setSpeed(s as 1 | 60 | 300))}
              options={[1, 60, 300].map((s) => ({ value: s, label: `${s}×` }))} />
          </div>
          <Button icon="reset" kind="danger" className="mt-4 w-full" onClick={() => run("Day reset", api.reset)}>Reset the day (same seed)</Button>
        </Card>
        <Card title="Street events">
          <div className="grid gap-2">
            <Button icon="cloud" onClick={() => ev("cloud", undefined, 45)}>Cloud over the whole street</Button>
            <Button icon="plug" onClick={() => ev("outage", undefined, 30)}>Grid outage · 30 min</Button>
            <Button icon="ban" kind="danger" onClick={() => ev("bad_bid", "h14")}>House 14 tries a ₹40 bid</Button>
          </div>
        </Card>
        <Card title="Ledger">
          <p className="text-sm text-ink-2">Re-hash every entry from the first; an edited row breaks the chain.</p>
          <div className="mt-4 flex items-center gap-3">
            <Button icon="chain" kind="filled" onClick={async () => setVerify(await api.verifyLedger())}>Verify</Button>
            {verify && (
              <span className={`rounded-full px-3 py-1 text-[13px] font-semibold ${verify.ok ? "bg-leaf-soft text-leaf-ink" : "bg-alert-soft text-alert"}`}>
                {verify.ok ? `Intact · ${verify.entries} entries` : `Broken at #${verify.broken_at}`}
              </span>
            )}
          </div>
        </Card>
      </div>

      <div className="mt-5 grid grid-cols-4 gap-5">
        {HOUSES.map((h) => (
          <Card key={h} title={hub.houses[h]?.label ?? h}>
            <div className="grid gap-2">
              {PER_HOUSE.filter((a) => !a.solarOnly || hub.houses[h]?.roof).map((a) => (
                <Button key={a.type} small icon={a.icon} onClick={() => ev(a.type, h, a.minutes)}>{a.label}</Button>
              ))}
            </div>
          </Card>
        ))}
      </div>

      <Card title="Event log" className="mt-5" action={<span className="flex items-center gap-1 text-xs text-ink-2"><Icon name="chain" className="h-3.5 w-3.5" /> raw hub events</span>}>
        <EventLog events={hub.log} />
      </Card>
    </div>
  );
}
