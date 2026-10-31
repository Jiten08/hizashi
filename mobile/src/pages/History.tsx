// History: this house's hash-chained ledger entries, and a button that re-checks the whole chain.
import { useCallback, useEffect, useState } from "react";
import { Button, type IconName, Pill, Row, Screen, Section } from "../components/ui";
import { api } from "../lib/api";
import { blockLabel, hhmm, houseName, rupees } from "../lib/format";
import { useHubStore } from "../lib/store";
import type { House, LedgerEntry } from "../lib/types";

function describe(e: LedgerEntry, house: House): { icon: IconName; bg: string; title: string; detail: string } {
  const p = e.payload;
  switch (e.kind) {
    case "contract.booked": {
      const selling = p.seller === house;
      return { icon: selling ? "sun" : "home", bg: selling ? "var(--color-orange)" : "var(--color-blue)",
        title: `${selling ? "Sold" : "Bought"} ${p.kwh.toFixed(2)} kWh ${selling ? "to" : "from"} ${houseName(selling ? p.buyer : p.seller)}`,
        detail: `${blockLabel(p.block.index)} · ${rupees(p.price)}/unit · ${p.route}` };
    }
    case "settlement": {
      const selling = p.seller === house;
      const short = p.shortfall_kwh >= 0.005 ? ` · short ${p.shortfall_kwh.toFixed(2)} kWh${p.outage ? " (outage)" : ""}` : "";
      return { icon: "check", bg: "var(--color-green)", title: `Settled ${blockLabel(p.block.index)}`,
        detail: `${selling ? `got ${rupees(p.seller_net)}` : `paid ${rupees(p.buyer_pays)}`}${short}` };
    }
    case "mandate":
      return { icon: "sliders", bg: "var(--color-indigo)", title: `Limits changed (v${p.version})`,
        detail: `sell ≥ ${rupees(p.min_sell_price)} · buy ≤ ${rupees(p.max_buy_price)} · budget ${rupees(p.daily_budget)}` };
    case "approval":
      return { icon: "hand", bg: "var(--color-orange)", title: String(p.decision).replace(/^\w/, (c) => c.toUpperCase()), detail: p.summary };
    default:
      return { icon: "doc", bg: "#8e8e93", title: e.kind, detail: e.ref_id };
  }
}

export default function History({ house }: { house: House }) {
  const changes = useHubStore((s) => s.settlements.length + s.contracts.length);
  const [entries, setEntries] = useState<LedgerEntry[] | null>(null);
  const [verify, setVerify] = useState<{ ok: boolean; broken_at?: number; entries?: number } | null>(null);
  const [busy, setBusy] = useState(false);
  const load = useCallback(() => { api.ledger(house).then(setEntries).catch(() => setEntries([])); }, [house]);
  useEffect(load, [load, changes]);

  return (
    <Screen title="History">
      <Section footer="Every deal, settlement and rule change is chained with SHA-256, so an edited record shows up.">
        <Row icon="link" iconBg="#1c1c1e" title="Tamper-evident ledger" last
          accessory={verify ? <Pill className={verify.ok ? "bg-green-soft text-green-ink" : "bg-red-soft text-red"}>{verify.ok ? `Intact · ${verify.entries}` : `Broken at #${verify.broken_at}`}</Pill> : undefined} />
      </Section>
      <Button kind="tinted" className="mt-2.5 w-full" busy={busy}
        onClick={async () => { setBusy(true); try { setVerify(await api.verify()); } finally { setBusy(false); } }}>
        Verify the chain
      </Button>

      <Section header="Your entries">
        {entries === null ? <Row title="Loading…" last /> : entries.length === 0 ? <Row title="Nothing recorded yet" last /> :
          entries.slice(0, 80).map((e, i, all) => {
            const d = describe(e, house);
            return <Row key={e.seq} icon={d.icon} iconBg={d.bg} title={d.title} subtitle={`${d.detail}\n#${e.seq} · ${hhmm(e.ts)} · ${e.hash.slice(0, 10)}…`} last={i === all.length - 1} />;
          })}
      </Section>
    </Screen>
  );
}
