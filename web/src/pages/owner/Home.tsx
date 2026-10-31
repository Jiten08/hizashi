// Home tab: savings, live power, what needs the owner, the live block, the latest haggle, today's deals.
import { Button } from "@heroui/react";
import { ApprovalCard } from "../../components/ApprovalCard";
import { BlockCard } from "../../components/BlockCard";
import { BlockedCard } from "../../components/BlockedCard";
import { HaggleFeed } from "../../components/HaggleFeed";
import { PlanStrip } from "../../components/PlanStrip";
import { SavingsCard } from "../../components/SavingsCard";
import { SolarUseStrip } from "../../components/SolarUseStrip";
import { TradeList } from "../../components/TradeList";
import { Empty, Icon, SectionTitle } from "../../components/ui";
import { blockIndex } from "../../lib/api";
import type { BlockState, House, Offer } from "../../lib/types";
import { useHubStore } from "../../store/hub";

function currentBlock(blocks: Record<string, BlockState>): [number, BlockState] | null {
  const entries = Object.entries(blocks).sort(([a], [b]) => a.localeCompare(b));
  const pick = entries.find(([, s]) => s === "DELIVERING") ?? entries.find(([, s]) => s === "OPEN")
    ?? entries.find(([, s]) => s !== "SETTLED") ?? entries.at(-1);
  return pick ? [blockIndex(pick[0]), pick[1]] : null;
}

function latestHaggle(negotiations: Record<string, Offer[]>, house: House): Offer[] {
  // Market orders (to = null) go to the auction, not a haggle.
  const mine = Object.values(negotiations).filter((os) => os[0]?.to != null && os.some((o) => o.house === house || o.to === house));
  return mine.at(-1) ?? [];
}

export default function Home({ house, onOpenApprovals }: { house: House; onOpenApprovals: () => void }) {
  const s = useHubStore();
  const info = s.houses[house];
  const pending = s.approvals.filter((a) => a.house === house && a.status === "pending");
  const blocked = s.blocked.filter((b) => b.house === house && b.owner_rule !== false).slice(-2).reverse();
  const current = currentBlock(s.blocks);
  const haggle = latestHaggle(s.negotiations, house);
  const deal = haggle.length ? s.contracts.find((c) => c.negotiation_id === haggle[0].negotiation_id) : undefined;
  const plans = s.plans[house] ?? [];

  return (
    <>
      <SavingsCard savings={s.savings[house]} hasSolar={!!info?.roof} />
      <SolarUseStrip live={s.live[house]} hasSolar={!!info?.roof} />

      {s.outage && (
        <div className="flex items-center gap-2 rounded-2xl bg-stone-800 px-4 py-3 text-sm text-white">
          <Icon name="plug" className="h-4 w-4" /> Grid outage — no penalties for blocks it touches (KERC 5(c)(iii)).
        </div>
      )}

      {pending.length > 0 && (
        <section className="space-y-2">
          <ApprovalCard approval={pending[0]} />
          {pending.length > 1 && (
            <Button variant="ghost" fullWidth onPress={onOpenApprovals}>
              {pending.length - 1} more waiting for you <Icon name="arrow" className="h-4 w-4" />
            </Button>
          )}
        </section>
      )}

      {blocked.map((b, i) => <BlockedCard key={`${b.sim_time}-${i}`} text={b.text} reason={b.reason} at={b.sim_time} />)}

      {current ? (
        <section>
          <SectionTitle>Live block</SectionTitle>
          <BlockCard index={current[0]} state={current[1]} house={house} contracts={s.contracts} settlements={s.settlements} />
        </section>
      ) : (
        <Empty icon="clock" title="The day hasn't started">Trading opens at 05:00 for the first blocks of the day.</Empty>
      )}

      {haggle.length > 0 && (
        <section>
          <SectionTitle>Latest haggle</SectionTitle>
          <HaggleFeed offers={haggle} deal={deal} house={house} />
        </section>
      )}

      {plans.length > 0 && (
        <section>
          <SectionTitle>Today's plan</SectionTitle>
          <PlanStrip windows={plans} />
        </section>
      )}

      <section>
        <SectionTitle>Today's deals</SectionTitle>
        <TradeList house={house} contracts={s.contracts} settlements={s.settlements} />
      </section>
    </>
  );
}
