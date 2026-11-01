/**
 * The desktop demo: the street of four homes, live trades, each home at a glance, and the
 * day's activity. Owners use the phone app; this screen is for the laptop / projector.
 * Every figure comes from the hub.
 */
import { useEffect, useRef, useState } from "react";
import { Link } from "react-router-dom";
import { Activity } from "../components/Activity";
import { ConnectSheet } from "../components/ConnectSheet";
import { HaggleChat } from "../components/HaggleChat";
import { HouseSvg } from "../components/HouseSvg";
import { Button, Card, Clock, Icon, Logo, Segmented, toast } from "../components/ui";
import { useHub } from "../hooks/useHub";
import { TONE_CLASS, useHappening } from "../lib/happening";
import { useHubStore } from "../store/hub";
import { api, blockIndex, blockKey, blockLabel, rupees } from "../lib/api";
import { HOUSES, type House } from "../lib/types";

const X = [140, 380, 620, 860];
const Y = 190;
const SPEEDS = [1, 60, 300] as const;

export default function Dashboard() {
  const hub = useHub("street");
  const [connectOpen, setConnectOpen] = useState(false);
  const delivering = Object.entries(hub.blocks).find(([, s]) => s === "DELIVERING")?.[0];
  const now = hub.sim_time ? Date.parse(hub.sim_time) : 0;
  const clouded = new Set(hub.sim_events
    .filter((e) => e.type === "cloud" && Date.parse(e.start) <= now && Date.parse(e.end) > now)
    .flatMap((e) => (e.house ? [e.house] : HOUSES)));
  const live = delivering ? hub.contracts.filter((c) => blockKey(c.block) === delivering) : [];
  const shared = hub.contracts.reduce((a, c) => a + c.kwh, 0);
  const saved = HOUSES.reduce((a, h) => a + (hub.savings[h]?.saved_today ?? 0), 0);
  const outage = !!hub.outage;
  const { outageUntil } = useHappening();

  const seen = useRef(-1);
  useEffect(() => {
    const fresh = seen.current < 0 ? [] : hub.blocked.slice(seen.current).filter((b) => b.owner_rule !== false);
    seen.current = hub.blocked.length;
    for (const b of fresh) toast(`House ${b.house.slice(1)}: blocked by its wallet`, String(b.reason ?? ""), "bad");
  }, [hub.blocked.length]);

  const seenFlags = useRef(-1);
  useEffect(() => {
    const fresh = seenFlags.current < 0 ? [] : hub.flags.slice(seenFlags.current);
    seenFlags.current = hub.flags.length;
    for (const f of fresh) toast(`Guard · ${f.title ?? "flag"}`, String(f.text ?? ""), "bad");
  }, [hub.flags.length]);

  return (
    <div className="mx-auto max-w-[1440px] px-8 pb-10 pt-6">
      <header className="flex items-center gap-4">
        <Logo />
        <div className="flex-1">
          <h1 className="text-[22px] font-semibold leading-tight tracking-tight">Hizashi</h1>
          <p className="text-[13px] text-ink-2">Street demo · four homes on transformer T1 · KERC P2P 2024</p>
        </div>
        <Clock />
        <Segmented value={hub.speed} onChange={(s) => api.setSpeed(s as 1 | 60 | 300).catch(() => {})}
          options={SPEEDS.map((s) => ({ value: s, label: `${s}×` }))} />
        <Button icon="qr" kind="tinted" onClick={() => setConnectOpen(true)}>Connect a phone</Button>
        <Link to="/street/3d"><Button icon="sun" kind="tinted">3D street</Button></Link>
        <Link to="/console"><Button icon="sliders">Controls</Button></Link>
      </header>

      <div className="mt-6 grid grid-cols-12 gap-5">
        <Card className={`col-span-8 overflow-hidden p-0 transition ${outage ? "grayscale" : ""}`}>
          <div className="flex items-center justify-between px-5 pt-4">
            <h2 className="text-[15px] font-semibold">The street</h2>
            <span className="text-[13px] text-ink-2">
              {outage ? `Grid outage${outageUntil ? ` until ${outageUntil}` : ""} · no neighbour trades, no penalties` : delivering ? `Power flowing for ${blockLabel(blockIndex(delivering))}` : "Waiting for the first block"}
            </span>
          </div>
          <svg viewBox="0 0 1000 380" className="w-full">
            <defs>
              <radialGradient id="sunGlow"><stop offset="0%" stopColor="#ffcc00" stopOpacity="0.9" /><stop offset="100%" stopColor="#ff9500" stopOpacity="0" /></radialGradient>
            </defs>
            <rect x="0" y="318" width="1000" height="62" fill="#ececf0" />
            <line x1="0" y1="350" x2="1000" y2="350" stroke="#fff" strokeWidth="3" strokeDasharray="24 18" />
            <line x1="30" y1="290" x2="970" y2="290" stroke="#c7c7cc" strokeWidth="1.5" strokeDasharray="2 5" />
            <g transform="translate(30 290)">
              <rect x="-14" y="-28" width="28" height="28" rx="6" fill="#3a3a3c" />
              <text x="0" y="-9" textAnchor="middle" fill="#fff" style={{ fontSize: 11, fontWeight: 700 }}>T1</text>
            </g>
            {!outage && live.map((c) => {
              const a = X[HOUSES.indexOf(c.seller)], b = X[HOUSES.indexOf(c.buyer)];
              const mid = (a + b) / 2, lift = 60 + Math.abs(b - a) * 0.12;
              return (
                <g key={c.contract_id}>
                  <path d={`M ${a} ${Y - 30} Q ${mid} ${Y - 30 - lift} ${b} ${Y - 30}`} fill="none" stroke="#ff9500" strokeWidth="3" strokeLinecap="round" strokeDasharray="7 7">
                    <animate attributeName="stroke-dashoffset" from="28" to="0" dur="0.9s" repeatCount="indefinite" />
                  </path>
                  <g transform={`translate(${mid} ${Y - 30 - lift / 2 - 14})`}>
                    <rect x="-56" y="-13" width="112" height="24" rx="12" fill="#fff" stroke="rgba(0,0,0,0.08)" />
                    <text x="0" y="4" textAnchor="middle" fill="#9a5b00" style={{ fontSize: 12, fontWeight: 600 }}>{c.kwh.toFixed(2)} kWh · {rupees(c.price)}</text>
                  </g>
                </g>
              );
            })}
            {HOUSES.map((h, i) => {
              const info = hub.houses[h];
              const l = hub.live[h];
              return <HouseSvg key={h} x={X[i]} y={Y} label={info?.label ?? h} hasSolar={!!info?.roof} outage={outage}
                glow={info?.roof && l ? l.solar_kw / info.roof.kwp : 0} cloud={clouded.has(h)} spareKw={l ? l.solar_kw - l.use_kw : null} />;
            })}
          </svg>
        </Card>

        <div className="col-span-4 flex flex-col gap-5">
          <Card title="Today on the street">
            <div className="grid grid-cols-3 gap-3">
              <Big value={String(hub.contracts.length)} label="deals" />
              <Big value={shared.toFixed(1)} label="kWh shared" />
              <Big value={rupees(saved)} label="saved vs BESCOM" tone="text-leaf-ink" />
            </div>
          </Card>
          <Card title="Power changing hands now" className="flex-1">
            {live.length ? (
              <ul className="space-y-2.5">
                {live.map((c) => (
                  <li key={c.contract_id} className="flex items-center justify-between text-sm">
                    <span>{hub.houses[c.seller]?.label} <span className="text-ink-3">→</span> {hub.houses[c.buyer]?.label}</span>
                    <span className="num font-medium">{c.kwh.toFixed(2)} kWh · {rupees(c.price)}</span>
                  </li>
                ))}
              </ul>
            ) : <p className="text-sm text-ink-2">No trades in this block.</p>}
          </Card>
        </div>

        {HOUSES.map((h) => <HouseCard key={h} house={h} />)}

        <Card title="Activity" className="col-span-5"><Activity events={hub.log} /></Card>
        <Card title="A2A haggle" className="col-span-4"><HaggleChat /></Card>
        <Card title="Try it" className="col-span-3">
          <div className="grid gap-2">
            <Button icon="cloud" onClick={() => run("Cloud over House 12", () => api.consoleEvent("cloud", "h12", 45))}>Cloud over House 12 (45 min)</Button>
            <Button icon="bolt" onClick={() => run("AC on at House 14", () => api.consoleEvent("ac", "h14", 120))}>AC on at House 14 (2 h)</Button>
            <Button icon="plug" onClick={() => run("Grid outage", () => api.consoleEvent("outage", undefined, 30))}>Grid outage (30 min)</Button>
            <Button icon="ban" kind="danger" onClick={() => run("House 14 tries a ₹40 bid", () => api.consoleEvent("bad_bid", "h14"))}>House 14 tries a ₹40 bid</Button>
            <Button icon="reset" onClick={() => run("Day reset", api.reset)}>Reset the day</Button>
          </div>
        </Card>
      </div>
      {connectOpen && <ConnectSheet onClose={() => setConnectOpen(false)} />}
    </div>
  );
}

async function run(what: string, fn: () => Promise<unknown>) {
  try {
    await fn();
    toast(what, undefined, "ok");
  } catch (e) {
    toast(what, (e as Error).message, "bad");
  }
}

function Big({ value, label, tone = "" }: { value: string; label: string; tone?: string }) {
  return (
    <div>
      <p className={`num text-[26px] font-semibold leading-tight tracking-tight ${tone}`}>{value}</p>
      <p className="text-xs text-ink-2">{label}</p>
    </div>
  );
}

function HouseCard({ house }: { house: House }) {
  const hub = useHubStore();      // the page's useHub owns the socket
  const info = hub.houses[house];
  const l = hub.live[house];
  const sv = hub.savings[house];
  const net = l ? l.solar_kw - l.use_kw : 0;
  const role = !l ? "—" : net >= 0.05 ? "Spare power" : net <= -0.05 ? "Needs power" : "Balanced";
  const pending = hub.approvals.some((a) => a.house === house && a.status === "pending");
  const chips = useHappening().byHouse[house];
  return (
    <Card className="col-span-3">
      <div className="flex items-start justify-between">
        <div>
          <p className="text-[15px] font-semibold">{info?.label ?? house}</p>
          <p className="text-xs text-ink-2">
            {info?.roof ? `${info.roof.kwp} kWp solar${info.subsidized ? " · PM Surya Ghar" : ""}` : "No solar"}
          </p>
        </div>
        {pending && <span className="rounded-full bg-sky-soft px-2 py-0.5 text-[11px] font-semibold text-sky">asking owner</span>}
      </div>
      {chips.length > 0 && (
        <div className="mt-2 flex flex-wrap gap-1">
          {chips.map((x) => <span key={x.key} className={`rounded-full px-2 py-0.5 text-[11px] font-semibold ${TONE_CLASS[x.tone]}`}>{x.label}</span>)}
        </div>
      )}
      <div className="mt-4 flex items-end justify-between">
        <div>
          <p className={`num text-[28px] font-semibold leading-none tracking-tight ${(sv?.saved_today ?? 0) > 0 ? "text-leaf-ink" : ""}`}>{rupees(sv?.saved_today ?? 0)}</p>
          <p className="mt-1 text-xs text-ink-2">saved today</p>
        </div>
        <div className="text-right text-xs text-ink-2">
          <p>sold <span className="num font-medium text-ink">{(sv?.sold_kwh ?? 0).toFixed(2)}</span> kWh</p>
          <p>bought <span className="num font-medium text-ink">{(sv?.bought_kwh ?? 0).toFixed(2)}</span> kWh</p>
        </div>
      </div>
      <div className="mt-4 grid grid-cols-2 gap-2 border-t border-hair pt-3 text-xs">
        <p className="flex items-center gap-1.5 text-ink-2"><Icon name="sun" className="h-3.5 w-3.5 text-sun" /> <span className="num font-medium text-ink">{(l?.solar_kw ?? 0).toFixed(2)}</span> kW</p>
        <p className="flex items-center gap-1.5 text-ink-2"><Icon name="home" className="h-3.5 w-3.5 text-sky" /> <span className="num font-medium text-ink">{(l?.use_kw ?? 0).toFixed(2)}</span> kW</p>
        <p className={`col-span-2 font-medium ${net >= 0.05 ? "text-leaf-ink" : net <= -0.05 ? "text-sky" : "text-ink-2"}`}>{role}{l && Math.abs(net) >= 0.05 ? ` · ${Math.abs(net).toFixed(2)} kW` : ""}</p>
      </div>
    </Card>
  );
}
