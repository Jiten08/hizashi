// History: this house's hash-chained ledger entries, and a button that re-checks the whole chain.
import { useCallback, useEffect, useState } from "react";
import { Text } from "react-native";
import { Button, Pill, Row, Screen, Section, type IconName } from "../../components/ui";
import { blockLabel, hhmm, houseName, rupees } from "../../lib/format";
import { api, useHub } from "../../lib/store";
import { C, T } from "../../lib/theme";
import type { House, LedgerEntry } from "../../lib/types";

function describe(e: LedgerEntry, house: House): { icon: IconName; bg: string; title: string; detail: string } {
  const p = e.payload;
  switch (e.kind) {
    case "contract.booked": {
      const selling = p.seller === house;
      return { icon: selling ? "sunny" : "home", bg: selling ? C.orange : C.blue,
        title: `${selling ? "Sold" : "Bought"} ${p.kwh.toFixed(2)} kWh ${selling ? "to" : "from"} ${houseName(selling ? p.buyer : p.seller)}`,
        detail: `${blockLabel(p.block.index)} · ${rupees(p.price)}/unit · ${p.route}` };
    }
    case "settlement": {
      const selling = p.seller === house;
      const short = p.shortfall_kwh >= 0.005 ? ` · short ${p.shortfall_kwh.toFixed(2)} kWh${p.outage ? " (outage)" : ""}` : "";
      return { icon: "checkmark", bg: C.green, title: `Settled ${blockLabel(p.block.index)}`,
        detail: `${selling ? `got ${rupees(p.seller_net)}` : `paid ${rupees(p.buyer_pays)}`}${short}` };
    }
    case "mandate":
      return { icon: "options", bg: C.indigo, title: `Limits changed (v${p.version})`,
        detail: `sell ≥ ${rupees(p.min_sell_price)} · buy ≤ ${rupees(p.max_buy_price)} · budget ${rupees(p.daily_budget)}` };
    case "approval":
      return { icon: "hand-left", bg: C.orange, title: String(p.decision).replace(/^\w/, (c) => c.toUpperCase()), detail: p.summary };
    default:
      return { icon: "document-text", bg: "#8E8E93", title: e.kind, detail: e.ref_id };
  }
}

export default function History() {
  const hub = useHub();
  const house = hub.conn!.house;
  const [entries, setEntries] = useState<LedgerEntry[] | null>(null);
  const [verify, setVerify] = useState<{ ok: boolean; broken_at?: number; entries?: number } | null>(null);
  const [busy, setBusy] = useState(false);
  const load = useCallback(() => { api().ledger(house).then(setEntries).catch(() => setEntries([])); }, [house]);
  useEffect(load, [load, hub.settlements.length, hub.contracts.length]);

  return (
    <Screen title="History" onRefresh={load}>
      <Section footer="Every deal, settlement and rule change is chained with SHA-256, so an edited record shows up.">
        <Row icon="link" iconBg="#1C1C1E" title="Tamper-evident ledger"
          accessory={verify ? <Pill text={verify.ok ? `Intact · ${verify.entries}` : `Broken at #${verify.broken_at}`}
            color={verify.ok ? C.greenText : C.red} bg={verify.ok ? C.greenSoft : C.redSoft} /> : undefined} last />
      </Section>
      <Button title="Verify the chain" kind="tinted" style={{ marginTop: 10 }} busy={busy}
        onPress={async () => { setBusy(true); try { setVerify(await api().verify()); } finally { setBusy(false); } }} />

      <Section header="Your entries">
        {entries === null ? <Row title="Loading…" last /> : entries.length === 0 ? <Row title="Nothing recorded yet" last /> :
          entries.slice(0, 80).map((e, i, all) => {
            const d = describe(e, house);
            return <Row key={e.seq} icon={d.icon} iconBg={d.bg} title={d.title} subtitle={`${d.detail}\n#${e.seq} · ${hhmm(e.ts)} · ${e.hash.slice(0, 10)}…`} last={i === all.length - 1} />;
          })}
      </Section>
      <Text style={[T.caption, { textAlign: "center", marginTop: 10 }]}>Pull down to refresh</Text>
    </Screen>
  );
}
