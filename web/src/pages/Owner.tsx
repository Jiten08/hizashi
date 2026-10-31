/**
 * Owner page — /h/:house
 * Mobile-first, 390px wide, light background, amber accent #d98a04.
 * Tabs: Home (functional) | Approvals / Rules / History (greyed out, "next").
 *
 * Rules from spec:
 * - Display only: never compute prices, savings or settlements.
 * - Unknown event types must be silently ignored (handled in store).
 * - wallet.blocked: use exact copy from spec with numbers from event.data.
 * - Savings: show dash + "coming at Review 2" — do NOT calculate.
 */
import { useState } from "react";
import { Link, useParams } from "react-router-dom";
import {
  BlockCard,
  BlockedCard,
  HaggleFeed,
  SavingsCard,
  SimClock,
  SolarUseStrip,
} from "../components";
import { useHub } from "../hooks/useHub";
import { HOUSES, type BlockState, type Contract, type House, type Offer } from "../lib/types";

const TABS = ["Home", "Approvals", "Rules", "History"] as const;
type Tab = (typeof TABS)[number];

/** Current block: DELIVERING first, then earliest non-SETTLED. */
function currentBlock(blocks: Record<string, BlockState>): [string, number, BlockState] | null {
  const entries = Object.entries(blocks).sort(([a], [b]) => a.localeCompare(b));
  const pick =
    entries.find(([, s]) => s === "DELIVERING") ??
    entries.find(([, s]) => s !== "SETTLED");
  if (!pick) return null;
  const [key, state] = pick;
  return [key, Number(key.split("#")[1]), state];
}

/** Collect all nego offers that belong to the current block. */
function blockOffers(
  negotiations: Record<string, Offer[]>,
  blockKey: string | undefined,
): Offer[] {
  if (!blockKey) return [];
  return Object.values(negotiations)
    .flat()
    .filter((o) => `${o.block.day}#${String(o.block.index).padStart(2, "0")}` === blockKey ||
                   `${o.block.day}#${o.block.index}` === blockKey);
}

/** Find contract for current block. */
function blockDeal(contracts: Contract[], blockKey: string | undefined): Contract | undefined {
  if (!blockKey) return undefined;
  return contracts.find(
    (c) =>
      `${c.block.day}#${String(c.block.index).padStart(2, "0")}` === blockKey ||
      `${c.block.day}#${c.block.index}` === blockKey,
  );
}

/** Promised kWh: from the first plan window covering the current block. */
function promisedKwh(
  plans: Record<string, import("../lib/types").PlanWindow[]>,
  house: House,
  blockIndex: number,
): number | undefined {
  const windows = plans[house] ?? [];
  const w = windows.find((w) => blockIndex >= w.first_index && blockIndex <= w.last_index);
  return w?.kwh;
}

export default function Owner() {
  const { house } = useParams();
  const [tab, setTab] = useState<Tab>("Home");
  const h = (HOUSES as string[]).includes(house ?? "") ? (house as House) : "h12";
  const hub = useHub("owner", h);

  const info = hub.houses[h];
  const current = currentBlock(hub.blocks);
  const [currentKey, currentIndex, currentState] = current ?? [undefined, 0, "PLANNED" as BlockState];
  const saved = hub.savings[h];

  // Meter for this house
  const meterEvent = hub.meters[h];

  // Haggle for current block
  const offers = blockOffers(hub.negotiations, currentKey);
  const deal = blockDeal(hub.contracts, currentKey);

  // Promised kWh from plan windows
  const promised = current ? promisedKwh(hub.plans, h, currentIndex) : undefined;

  // Contracted kWh from the deal (if any)
  const contracted = deal?.kwh;

  // Blocked events for this house (most recent first)
  const blocked = [...hub.blocked].reverse();

  const isDisabled = (t: Tab) => t !== "Home";

  return (
    <div className="mx-auto flex min-h-dvh max-w-[390px] flex-col bg-stone-50">
      {/* ── Header ── */}
      <header className="sticky top-0 z-10 flex items-center justify-between border-b border-stone-200 bg-white/90 px-4 py-3 backdrop-blur">
        <Link to="/" className="flex items-center gap-2">
          <img src="/sun.svg" className="h-7 w-7" alt="" />
          <span className="text-lg font-semibold">{info?.label ?? h}</span>
        </Link>
        <SimClock />
      </header>

      {/* ── Main ── */}
      <main className="flex-1 space-y-4 p-4 pb-28">
        {tab === "Home" && (
          <>
            {/* Savings — dash until Review 2 */}
            <SavingsCard
              savedToday={saved?.saved_today as number | undefined}
              projectedYear={saved?.projected_year as number | undefined}
            />

            {/* Solar + Use */}
            <SolarUseStrip meterEvent={meterEvent} />

            {/* Current block card */}
            {current ? (
              <section>
                <h2 className="mb-2 text-sm font-semibold text-stone-500">Current block</h2>
                <BlockCard
                  index={currentIndex}
                  state={currentState}
                  promised={promised}
                  contracted={contracted}
                />
              </section>
            ) : (
              <p className="text-sm text-stone-500">Waiting for the day to start…</p>
            )}

            {/* Haggle feed */}
            {(offers.length > 0 || deal) && (
              <section>
                <h2 className="mb-2 text-sm font-semibold text-stone-500">Haggling</h2>
                <div className="rounded-2xl border border-stone-200 bg-white p-4 shadow-sm">
                  <HaggleFeed offers={offers} deal={deal} />
                </div>
              </section>
            )}

            {/* Blocked cards — most recent first */}
            {blocked.length > 0 && (
              <section>
                <h2 className="mb-2 text-sm font-semibold text-stone-500">Wallet blocks</h2>
                <div className="space-y-2">
                  {blocked.map((ev, i) => (
                    <BlockedCard key={ev.data?.offer?.offer_id ?? i} event={ev} />
                  ))}
                </div>
              </section>
            )}
          </>
        )}

        {isDisabled(tab) && (
          <div className="rounded-2xl border border-dashed border-stone-300 p-10 text-center text-stone-400">
            <p className="text-base font-medium">{tab}</p>
            <p className="mt-1 text-sm">next</p>
          </div>
        )}
      </main>

      {/* ── Bottom tabs ── */}
      <nav className="fixed inset-x-0 bottom-0 mx-auto flex max-w-[390px] border-t border-stone-200 bg-white pb-[env(safe-area-inset-bottom)]">
        {TABS.map((t) => (
          <button
            key={t}
            onClick={() => setTab(t)}
            disabled={isDisabled(t)}
            className={`flex-1 py-3 text-sm transition-colors ${
              tab === t
                ? "font-semibold text-[#d98a04]"
                : isDisabled(t)
                ? "cursor-not-allowed text-stone-300"
                : "text-stone-500 active:text-[#d98a04]"
            }`}
            title={isDisabled(t) ? "Coming soon" : undefined}
          >
            {t}
          </button>
        ))}
      </nav>

      {/* ── Footer ── */}
      <footer className="pb-20 px-4 pt-2 text-center text-[10px] text-stone-400">
        Weather: real forecast (cached) | Homes and meters: simulated
      </footer>
    </div>
  );
}
