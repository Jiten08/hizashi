// History tab: this house's ledger entries (hash-chained in the hub) and a verify button.
import { Button, Card, Chip, Spinner } from "@heroui/react";
import { useEffect, useState } from "react";
import { Empty, Icon, type IconName, SectionTitle } from "../../components/ui";
import { api, blockLabel, hhmm, rupees } from "../../lib/api";
import type { House, LedgerEntry } from "../../lib/types";
import { useHubStore } from "../../store/hub";

const name = (h?: string) => (h ? h.replace("h", "House ") : "");

function describe(e: LedgerEntry, house: House): { icon: IconName; title: string; detail: string } {
  const p = e.payload;
  switch (e.kind) {
    case "contract.booked": {
      const selling = p.seller === house;
      return {
        icon: selling ? "sun" : "home",
        title: `${selling ? "Sold" : "Bought"} ${p.kwh.toFixed(2)} kWh ${selling ? "to" : "from"} ${name(selling ? p.buyer : p.seller)}`,
        detail: `${blockLabel(p.block.index)} · ${rupees(p.price)}/unit · ${p.route}`,
      };
    }
    case "settlement": {
      const selling = p.seller === house;
      const money = selling ? `you got ${rupees(p.seller_net)}` : `you paid ${rupees(p.buyer_pays)}`;
      const short = p.shortfall_kwh > 0 ? ` · short ${p.shortfall_kwh.toFixed(2)} kWh${p.outage ? " (outage, no penalty)" : ""}` : "";
      return { icon: "check", title: `Settled ${blockLabel(p.block.index)}`, detail: `${p.delivered_kwh.toFixed(2)} of ${p.contracted_kwh.toFixed(2)} kWh delivered · ${money}${short}` };
    }
    case "mandate":
      return { icon: "sliders", title: `Rules changed (v${p.version})`, detail: `sell ≥ ${rupees(p.min_sell_price)} · buy ≤ ${rupees(p.max_buy_price)} · budget ${rupees(p.daily_budget)}` };
    case "approval":
      return { icon: "hand", title: `${p.decision === "approved" ? "Approved" : "Declined"} via ${p.channel}`, detail: p.summary };
    default:
      return { icon: "shield", title: e.kind, detail: e.ref_id };
  }
}

export default function History({ house }: { house: House }) {
  const settled = useHubStore((s) => s.settlements.length + s.contracts.length);
  const [entries, setEntries] = useState<LedgerEntry[] | null>(null);
  const [verify, setVerify] = useState<{ ok: boolean; broken_at?: number; entries?: number } | null>(null);
  const [checking, setChecking] = useState(false);

  useEffect(() => {
    api.ledger(house).then(setEntries).catch(() => setEntries([]));
  }, [house, settled]);

  const check = async () => {
    setChecking(true);
    try { setVerify(await api.verifyLedger()); } finally { setChecking(false); }
  };

  return (
    <>
      <Card className="bg-ink text-white">
        <Card.Content className="gap-3 p-4">
          <div className="flex items-center gap-3">
            <span className="inline-flex h-10 w-10 items-center justify-center rounded-xl bg-white/10"><Icon name="chain" /></span>
            <div className="flex-1">
              <p className="font-semibold">Tamper-evident ledger</p>
              <p className="text-sm text-white/70">Every deal, settlement and rule change is chained by SHA-256.</p>
            </div>
          </div>
          <div className="flex items-center gap-3">
            <Button variant="primary" onPress={check} isDisabled={checking}>{checking ? <Spinner size="sm" /> : "Verify the chain"}</Button>
            {verify && (verify.ok
              ? <Chip color="success" variant="primary">intact · {verify.entries} entries</Chip>
              : <Chip color="danger" variant="primary">broken at #{verify.broken_at}</Chip>)}
          </div>
        </Card.Content>
      </Card>

      <SectionTitle>Your entries</SectionTitle>
      {entries === null ? <div className="flex justify-center py-8"><Spinner /></div>
        : entries.length === 0 ? <Empty icon="list" title="Nothing recorded yet">Deals and settlements land here as they happen.</Empty>
        : (
          <Card>
            <Card.Content className="p-0">
              <ul className="divide-y divide-stone-100">
                {entries.map((e) => {
                  const d = describe(e, house);
                  return (
                    <li key={e.seq} className="flex gap-3 px-4 py-3">
                      <span className="mt-0.5 inline-flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-stone-100 text-stone-600">
                        <Icon name={d.icon} className="h-4 w-4" />
                      </span>
                      <div className="min-w-0 flex-1">
                        <p className="text-sm font-medium">{d.title}</p>
                        <p className="text-xs text-stone-500">{d.detail}</p>
                        <p className="mt-0.5 font-mono text-[10px] text-stone-400">#{e.seq} · {hhmm(e.ts)} · {e.hash.slice(0, 12)}…</p>
                      </div>
                    </li>
                  );
                })}
              </ul>
            </Card.Content>
          </Card>
        )}
    </>
  );
}
