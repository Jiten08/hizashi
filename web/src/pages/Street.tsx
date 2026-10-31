/**
 * /street (laptop): the four houses, roofs glowing with live solar, spare/short labels,
 * a line per trade in the block that's delivering now, outage dims everything,
 * wallet blocks and guard flags as toasts. All figures come from the hub.
 */
import { Card, Chip, toast } from "@heroui/react";
import { useEffect, useRef } from "react";
import { Link } from "react-router-dom";
import { HouseSvg } from "../components/HouseSvg";
import { ClockChip, Icon, SunMark } from "../components/ui";
import { useHub } from "../hooks/useHub";
import { blockIndex, blockLabel, rupees } from "../lib/api";
import { HOUSES } from "../lib/types";

const X = [150, 390, 630, 870];
const Y = 200;

export default function Street() {
  const hub = useHub("street");
  const delivering = Object.entries(hub.blocks).find(([, s]) => s === "DELIVERING")?.[0];
  const now = hub.sim_time ? new Date(hub.sim_time).getTime() : 0;
  const clouded = new Set(hub.sim_events.filter((e) => e.type === "cloud" && new Date(e.start).getTime() <= now && new Date(e.end).getTime() > now)
    .flatMap((e) => (e.house ? [e.house] : HOUSES)));
  const live = delivering ? hub.contracts.filter((c) => `${c.block.day}#${String(c.block.index).padStart(2, "0")}` === delivering) : [];
  const today = hub.contracts.length;
  const shared = hub.contracts.reduce((a, c) => a + c.kwh, 0);
  const outage = !!hub.outage;

  const seen = useRef(0);
  useEffect(() => {
    const fresh = hub.blocked.slice(seen.current).filter((b) => b.owner_rule !== false);
    seen.current = hub.blocked.length;
    for (const b of fresh) toast.danger(`${b.house.replace("h", "House ")}: blocked`, { description: (b.text ?? b.reason ?? "").replace(/^BLOCKED · /, "") });
  }, [hub.blocked.length]);
  const flagsSeen = useRef(0);
  useEffect(() => {
    for (const f of hub.flags.slice(flagsSeen.current)) toast.warning(`Guard: ${f.kind ?? "flag"}`, { description: JSON.stringify(f.detail ?? f) });
    flagsSeen.current = hub.flags.length;
  }, [hub.flags.length]);

  return (
    <div className="mx-auto flex min-h-dvh max-w-6xl flex-col gap-4 p-6">
      <header className="flex items-center justify-between">
        <Link to="/" className="flex items-center gap-3">
          <SunMark className="h-10 w-10" />
          <div>
            <h1 className="text-2xl font-bold">Hizashi Street</h1>
            <p className="text-sm text-stone-500">Four homes on transformer T1 · {delivering ? `delivering ${blockLabel(blockIndex(delivering))}` : "waiting for the first block"}</p>
          </div>
        </Link>
        <div className="flex items-center gap-2">
          {outage && <Chip color="danger" variant="primary"><Icon name="plug" className="h-3.5 w-3.5" /> Grid outage</Chip>}
          <ClockChip />
        </div>
      </header>

      <Card className={`overflow-hidden transition ${outage ? "grayscale" : ""}`}>
        <Card.Content className="p-0">
          <svg viewBox="0 0 1020 400" className="w-full bg-gradient-to-b from-sky-50 to-[var(--background)]">
            <rect x="0" y="330" width="1020" height="70" fill="#e7e5e4" />
            <line x1="0" y1="365" x2="1020" y2="365" stroke="#fff" strokeWidth="3" strokeDasharray="22 18" />
            <line x1="40" y1="300" x2="980" y2="300" stroke="#a8a29e" strokeWidth="2" strokeDasharray="3 5" />
            <g transform="translate(40 300)">
              <rect x="-16" y="-34" width="32" height="34" rx="4" fill="#57534e" />
              <text x="0" y="-12" textAnchor="middle" className="fill-white text-[11px] font-bold">T1</text>
            </g>
            {live.map((c) => {
              const a = X[HOUSES.indexOf(c.seller)], b = X[HOUSES.indexOf(c.buyer)];
              const mid = (a + b) / 2, lift = 70 + Math.abs(b - a) * 0.12;
              return (
                <g key={c.contract_id}>
                  <path d={`M ${a} ${Y - 30} Q ${mid} ${Y - 30 - lift} ${b} ${Y - 30}`} fill="none" stroke="#d98a04" strokeWidth="3.5" strokeLinecap="round" strokeDasharray="8 7">
                    <animate attributeName="stroke-dashoffset" from="30" to="0" dur="0.9s" repeatCount="indefinite" />
                  </path>
                  <g transform={`translate(${mid} ${Y - 30 - lift / 2 - 14})`}>
                    <rect x="-58" y="-13" width="116" height="24" rx="12" fill="#fff" stroke="#fcd34d" />
                    <text x="0" y="4" textAnchor="middle" className="num fill-amber-900 text-[12px] font-semibold">{c.kwh.toFixed(2)} kWh · {rupees(c.price)}</text>
                  </g>
                </g>
              );
            })}
            {HOUSES.map((h, i) => {
              const info = hub.houses[h];
              const l = hub.live[h];
              return (
                <HouseSvg key={h} x={X[i]} y={Y} label={info?.label ?? h} hasSolar={!!info?.roof} outage={outage}
                  glow={info?.roof && l ? l.solar_kw / info.roof.kwp : 0} cloud={clouded.has(h)}
                  spareKw={l ? l.solar_kw - l.use_kw : null} />
              );
            })}
          </svg>
        </Card.Content>
      </Card>

      <div className="grid gap-4 md:grid-cols-[1fr_1fr_1.2fr]">
        <Card>
          <Card.Header className="px-4 pt-4"><Card.Title>Today on the street</Card.Title></Card.Header>
          <Card.Content className="grid grid-cols-2 gap-3 p-4">
            <div><p className="num text-3xl font-bold">{today}</p><p className="text-sm text-stone-500">deals</p></div>
            <div><p className="num text-3xl font-bold">{shared.toFixed(1)}</p><p className="text-sm text-stone-500">kWh shared</p></div>
          </Card.Content>
        </Card>
        <Card>
          <Card.Header className="px-4 pt-4"><Card.Title>Saved vs BESCOM</Card.Title></Card.Header>
          <Card.Content className="space-y-2 p-4">
            {HOUSES.map((h) => (
              <div key={h} className="flex items-center justify-between text-sm">
                <span>{hub.houses[h]?.label ?? h}</span>
                <span className="num font-semibold">{rupees(hub.savings[h]?.saved_today ?? 0)}</span>
              </div>
            ))}
          </Card.Content>
        </Card>
        <Card>
          <Card.Header className="px-4 pt-4"><Card.Title>Live trades</Card.Title></Card.Header>
          <Card.Content className="p-4">
            {live.length ? (
              <ul className="space-y-2 text-sm">
                {live.map((c) => (
                  <li key={c.contract_id} className="flex items-center justify-between">
                    <span>{hub.houses[c.seller]?.label} → {hub.houses[c.buyer]?.label}</span>
                    <span className="num font-medium">{c.kwh.toFixed(2)} kWh · {rupees(c.price)}{c.route === "auction" && <Chip size="sm" variant="soft" className="ml-2">auction</Chip>}</span>
                  </li>
                ))}
              </ul>
            ) : <p className="text-sm text-stone-500">No power changing hands in this block.</p>}
          </Card.Content>
        </Card>
      </div>
    </div>
  );
}
