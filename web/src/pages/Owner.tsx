import { useState } from "react";
import { Link, useParams } from "react-router-dom";
import { BlockCard, BlockStrip, EventLog, SavingsCard, SimClock } from "../components";
import { useHub } from "../hooks/useHub";
import { HOUSES, type BlockState, type House } from "../lib/types";

const TABS = ["Home", "Approvals", "Rules", "History"] as const;
type Tab = (typeof TABS)[number];

/** Current block worth showing: the one delivering now, else the next one in play. */
function currentBlock(blocks: Record<string, BlockState>): [number, BlockState] | null {
  const entries = Object.entries(blocks).sort(([a], [b]) => a.localeCompare(b));
  const pick = entries.find(([, s]) => s === "DELIVERING") ?? entries.find(([, s]) => s !== "SETTLED");
  return pick ? [Number(pick[0].split("#")[1]), pick[1]] : null;
}

export default function Owner() {
  const { house } = useParams();
  const [tab, setTab] = useState<Tab>("Home");
  const h = (HOUSES as string[]).includes(house ?? "") ? (house as House) : "h12";
  const hub = useHub("owner", h);
  const info = hub.houses[h];
  const current = currentBlock(hub.blocks);
  const saved = hub.savings[h];

  return (
    <div className="mx-auto flex min-h-dvh max-w-md flex-col">
      <header className="sticky top-0 z-10 flex items-center justify-between border-b border-stone-200 bg-white/90 px-4 py-3 backdrop-blur">
        <Link to="/" className="flex items-center gap-2">
          <img src="/sun.svg" className="h-7 w-7" alt="" />
          <span className="text-lg font-semibold">{info?.label ?? h}</span>
        </Link>
        <SimClock />
      </header>

      <main className="flex-1 space-y-4 p-4 pb-24">
        {tab === "Home" && (
          <>
            <SavingsCard savedToday={saved?.saved_today} projectedYear={saved?.projected_year} />
            {current ? <BlockCard index={current[0]} state={current[1]} /> : <p className="text-stone-500">Waiting for the day to start…</p>}
            <section>
              <h2 className="mb-2 text-sm font-semibold text-stone-500">Today's blocks</h2>
              <BlockStrip blocks={hub.blocks} />
            </section>
            <section>
              <h2 className="mb-2 text-sm font-semibold text-stone-500">Latest</h2>
              <EventLog events={hub.log.filter((e) => e.type !== "block.state")} max={30} />
            </section>
          </>
        )}
        {tab === "Approvals" && <Placeholder task="R2.5" text="Plans and offers that need your OK show up here." />}
        {tab === "Rules" && (
          <section className="rounded-2xl bg-white p-4 ring-1 ring-stone-200">
            <h2 className="font-semibold">Your rules</h2>
            {hub.mandates[h] ? (
              <dl className="mt-2 grid grid-cols-2 gap-y-1 text-sm">
                <dt className="text-stone-500">Never sell below</dt><dd>₹{hub.mandates[h].min_sell_price.toFixed(2)}</dd>
                <dt className="text-stone-500">Never buy above</dt><dd>₹{hub.mandates[h].max_buy_price.toFixed(2)}</dd>
                <dt className="text-stone-500">Daily budget</dt><dd>₹{hub.mandates[h].daily_budget.toFixed(2)}</dd>
                <dt className="text-stone-500">Max promise / block</dt><dd>{hub.mandates[h].max_promise_kwh} kWh</dd>
                <dt className="text-stone-500">Ask me above</dt><dd>₹{hub.mandates[h].approve_above.toFixed(2)}</dd>
              </dl>
            ) : <p className="text-sm text-stone-500">Loading…</p>}
            <p className="mt-3 text-xs text-stone-400">Editing comes in R2.8; plain-English rules in N4.</p>
          </section>
        )}
        {tab === "History" && <Placeholder task="R2.8" text="Your ledger entries will be listed here." />}
      </main>

      <nav className="fixed inset-x-0 bottom-0 mx-auto flex max-w-md border-t border-stone-200 bg-white pb-[env(safe-area-inset-bottom)]">
        {TABS.map((t) => (
          <button key={t} onClick={() => setTab(t)}
            className={`flex-1 py-3 text-sm ${tab === t ? "font-semibold text-sun" : "text-stone-500"}`}>
            {t}
          </button>
        ))}
      </nav>
    </div>
  );
}

function Placeholder({ task, text }: { task: string; text: string }) {
  return (
    <div className="rounded-2xl border border-dashed border-stone-300 p-6 text-center text-stone-500">
      <p>{text}</p>
      <p className="mt-1 text-xs">({task})</p>
    </div>
  );
}
