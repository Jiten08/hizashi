// Today: saved vs BESCOM, live power rings, what needs the owner, the live block, the latest
// haggle, today's deals, and the owner's away / guests plans. Every figure comes from the hub.
import { ApprovalCard } from "../components/ApprovalCard";
import { HomePlans } from "../components/HomePlans";
import { Card, Icon, Pill, Ring, Row, Screen, Section } from "../components/ui";
import { blockIndex, blockLabel, hhmm, houseName, kwh, rupees } from "../lib/format";
import { useHubStore } from "../lib/store";
import type { BlockState, House, Offer } from "../lib/types";

const STEPS: { state: BlockState; label: string }[] = [
  { state: "PLANNED", label: "Planned" }, { state: "OPEN", label: "Deals" }, { state: "GATE_CLOSED", label: "Locked" },
  { state: "DELIVERING", label: "Live" }, { state: "SETTLED", label: "Settled" },
];

export default function Today({ house }: { house: House }) {
  const hub = useHubStore();
  const info = hub.houses[house];
  const sv = hub.savings[house];
  const live = hub.live[house];
  const pending = hub.approvals.filter((a) => a.house === house && a.status === "pending");
  const blocked = hub.blocked.filter((b) => b.house === house && b.owner_rule !== false).slice(-1);
  const flag = hub.flags.filter((f) => (f.houses ?? []).includes(house)).at(-1);

  const entries = Object.entries(hub.blocks).sort(([a], [b]) => a.localeCompare(b));
  const cur = entries.find(([, s]) => s === "DELIVERING") ?? entries.find(([, s]) => s === "OPEN") ?? entries.find(([, s]) => s !== "SETTLED") ?? entries.at(-1);
  const curIndex = cur ? blockIndex(cur[0]) : null;
  const curStep = cur ? STEPS.findIndex((s) => s.state === cur[1]) : -1;
  const inBlock = hub.contracts.filter((c) => c.block.index === curIndex && (c.seller === house || c.buyer === house));

  const haggle: Offer[] = Object.values(hub.negotiations).filter((os) => os[0]?.to != null && os.some((o) => o.house === house || o.to === house)).at(-1) ?? [];
  const deal = haggle.length ? hub.contracts.find((c) => c.negotiation_id === haggle[0].negotiation_id) : undefined;
  const deals = hub.contracts.filter((c) => c.seller === house || c.buyer === house).sort((a, b) => b.block.index - a.block.index).slice(0, 20);

  const solar = live?.solar_kw ?? 0;
  const use = live?.use_kw ?? 0;
  const net = solar - use;
  const scale = Math.max(info?.roof?.kwp ?? 0, 3);

  return (
    <Screen title="Today" subtitle={`${houseName(house).toUpperCase()} · ${hhmm(hub.sim_time)}${hub.connected ? "" : " · OFFLINE"}`}>
      <Card className="mt-3">
        <p className="t-footnote font-semibold">SAVED VS BESCOM</p>
        <p className="num mt-0.5 text-[52px] font-bold leading-[60px] tracking-[-1px] text-green-ink">{rupees(sv?.saved_today ?? 0)}</p>
        <p className="t-subhead">
          {sv && sv.projected_year > 0
            ? `≈ ₹${Math.round(sv.projected_year).toLocaleString("en-IN")} a year at today's pace`
            : info?.roof ? "Your first deal settles 15 minutes after its block." : "You save on every unit bought from a neighbour."}
        </p>
        {sv && sv.trades > 0 && (
          <div className="mt-3.5 grid grid-cols-3 border-t-[0.5px] border-sep pt-3">
            <Mini label="Sold" value={kwh(sv.sold_kwh)} />
            <Mini label="Bought" value={kwh(sv.bought_kwh)} />
            <Mini label="Trades" value={String(sv.trades)} />
          </div>
        )}
      </Card>

      <Card className="mt-3 flex items-center gap-[18px]">
        <Ring size={96} stroke={11} progress={solar / scale} color="var(--color-orange)">
          <Ring size={70} stroke={11} progress={use / scale} color="var(--color-blue)" />
        </Ring>
        <div className="flex flex-1 flex-col gap-1.5">
          <Legend color="bg-orange" label="Solar" value={info?.roof ? `${solar.toFixed(2)} kW` : "none"} />
          <Legend color="bg-blue" label="Using" value={`${use.toFixed(2)} kW`} />
          <p className={`t-footnote font-semibold ${live?.outage ? "" : net >= 0.05 ? "!text-green-ink" : net <= -0.05 ? "!text-blue" : ""}`}>
            {live?.outage ? "Grid outage" : !live ? "Waiting for the meter…" : net >= 0.05 ? `${net.toFixed(2)} kW spare for neighbours` : net <= -0.05 ? `${(-net).toFixed(2)} kW short` : "Balanced"}
          </p>
        </div>
      </Card>

      {pending[0] && <ApprovalCard approval={pending[0]} />}

      {blocked.map((b, i) => (
        <div key={i} className="rise mt-3 flex gap-2.5 rounded-xl bg-red-soft p-3.5">
          <Icon name="shield" className="h-5 w-5 shrink-0 text-red" strokeWidth={2} />
          <div>
            <p className="t-headline text-red">Blocked by your wallet</p>
            <p className="t-subhead mt-0.5 !text-label">{String(b.text ?? b.reason ?? "").replace(/^BLOCKED · /, "")}</p>
          </div>
        </div>
      ))}

      {flag && (
        <div className="rise mt-3 flex gap-2.5 rounded-xl bg-red-soft p-3.5">
          <Icon name="shield" className="h-5 w-5 shrink-0 text-red" strokeWidth={2} />
          <div>
            <p className="t-headline text-red">Street guard · {String(flag.title ?? "flag")}</p>
            <p className="t-subhead mt-0.5 !text-label">{String(flag.text ?? "")}</p>
          </div>
        </div>
      )}

      {curIndex !== null && (
        <Section header="Now">
          <div className="p-4">
            <div className="flex items-baseline justify-between">
              <span className="t-title2 num">{blockLabel(curIndex)}</span>
              <Pill className={cur?.[1] === "DELIVERING" ? "bg-orange-soft text-orange" : "bg-fill text-label-2"}>{STEPS[curStep]?.label}</Pill>
            </div>
            <div className="mt-3 grid grid-cols-5 gap-1">
              {STEPS.map((s, i) => (
                <div key={s.state}>
                  <div className={`h-1 rounded-sm ${i < curStep ? "bg-orange/50" : i === curStep ? "bg-orange" : "bg-fill"}`} />
                  <p className={`mt-1 text-[10px] ${i === curStep ? "text-label" : "text-label-3"}`}>{s.label}</p>
                </div>
              ))}
            </div>
          </div>
          {inBlock.map((c, i) => (
            <Row key={c.contract_id} last={i === inBlock.length - 1}
              title={c.seller === house ? `Selling to ${houseName(c.buyer)}` : `Buying from ${houseName(c.seller)}`}
              value={`${kwh(c.kwh)} · ${rupees(c.price)}`} />
          ))}
        </Section>
      )}

      {haggle.length > 0 && (
        <Section header="Latest haggle">
          <div className="p-4">
            <p className="t-subhead">
              {haggle[0].house === house ? "Selling to" : "Buying from"} {houseName(haggle[0].house === house ? haggle[0].to : haggle[0].house)} · {blockLabel(haggle[0].block.index)}
            </p>
            <div className="mt-2.5 flex flex-wrap gap-1.5">
              {[...haggle].sort((a, b) => a.round - b.round || (a.side === "ask" ? -1 : 1)).map((o) => (
                <Pill key={o.offer_id} className={o.side === "ask" ? "bg-orange-soft text-orange-ink" : "bg-blue-soft text-blue"}>
                  {o.side === "ask" ? "Ask" : "Bid"} {rupees(o.price)}
                </Pill>
              ))}
              {deal && <Pill className="bg-green text-white">✓ Deal {kwh(deal.kwh)} at {rupees(deal.price)}</Pill>}
            </div>
            {haggle.filter((o) => hub.notes[o.offer_id]).slice(-3).map((o) => (
              <p key={o.offer_id} className="t-footnote mt-2">
                <span className={`font-semibold ${o.side === "ask" ? "text-orange-ink" : "text-blue"}`}>{o.house === house ? "Your agent" : houseName(o.house)}:</span>{" "}
                <span className="!text-label">{hub.notes[o.offer_id].text}</span>
              </p>
            ))}
          </div>
        </Section>
      )}

      <HomePlans house={house} />

      <Section header="Today's deals" footer={deals.length ? undefined : "Deals your agent books show up here."}>
        {deals.length ? deals.map((c, i) => {
          const selling = c.seller === house;
          const st = hub.settlements.find((x) => x.contract_id === c.contract_id);
          return (
            <Row key={c.contract_id} last={i === deals.length - 1}
              icon={selling ? "sun" : "home"} iconBg={selling ? "var(--color-orange)" : "var(--color-blue)"}
              title={`${selling ? "Sold to" : "Bought from"} ${houseName(selling ? c.buyer : c.seller)}`}
              subtitle={`${blockLabel(c.block.index)} · ${c.route === "auction" ? "auction" : "haggled"}${st ? (st.shortfall_kwh >= 0.005 ? ` · short ${st.shortfall_kwh.toFixed(2)} kWh` : " · settled") : ""}`}
              accessory={<span className="ml-2 text-right"><span className="t-headline num block">{kwh(c.kwh)}</span><span className="t-footnote num block">{rupees(c.price)}</span></span>} />
          );
        }) : <Row title="No deals yet" last />}
      </Section>
    </Screen>
  );
}

function Mini({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <p className="t-caption">{label}</p>
      <p className="t-headline num">{value}</p>
    </div>
  );
}

function Legend({ color, label, value }: { color: string; label: string; value: string }) {
  return (
    <div className="flex items-center gap-2">
      <span className={`h-2.5 w-2.5 rounded-full ${color}`} />
      <span className="t-subhead flex-1">{label}</span>
      <span className="t-headline num">{value}</span>
    </div>
  );
}
