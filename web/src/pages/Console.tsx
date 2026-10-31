import { useState } from "react";
import { Link } from "react-router-dom";
import { EventLog, SimClock } from "../components";
import { useHub } from "../hooks/useHub";
import { api } from "../lib/api";

const SPEEDS = [1, 60, 300] as const;
// type, house it applies to (null = street-wide)
const EVENTS: [string, string | null][] = [
  ["cloud", "h12"], ["outage", null], ["ac", "h14"], ["guests", "h16"], ["away", "h12"],
  ["bad_bid", "h14"], ["rogue_seller", "h16"], ["collusion", null],
];

export default function Console() {
  const hub = useHub("console");
  const [msg, setMsg] = useState("");

  const run = (label: string, f: () => Promise<unknown>) =>
    f().then((r) => setMsg(`${label}: ${JSON.stringify(r)}`)).catch((e) => setMsg(`${label} failed: ${e.message}`));

  return (
    <main className="mx-auto max-w-5xl space-y-6 p-6">
      <header className="flex items-center justify-between">
        <Link to="/" className="text-2xl font-bold">Hizashi · Console</Link>
        <SimClock />
      </header>

      <section className="flex flex-wrap items-center gap-2">
        <span className="text-sm font-semibold text-stone-500">Speed</span>
        {SPEEDS.map((s) => (
          <button key={s} onClick={() => run(`speed ${s}`, () => api.setSpeed(s))}
            className={`rounded-xl px-4 py-2 font-mono ${hub.speed === s ? "bg-sun text-white" : "bg-white ring-1 ring-stone-300"}`}>
            {s}×
          </button>
        ))}
        <button onClick={() => run("reset", api.reset)} className="ml-4 rounded-xl bg-stone-800 px-4 py-2 text-white">Reset day</button>
        <button onClick={() => run("ledger verify", api.verifyLedger)} className="rounded-xl bg-white px-4 py-2 ring-1 ring-stone-300">Verify ledger</button>
      </section>

      <section className="flex flex-wrap gap-2">
        <span className="w-full text-sm font-semibold text-stone-500">Events (R2.7)</span>
        {EVENTS.map(([type, house]) => (
          <button key={type} onClick={() => run(type, () => api.consoleEvent(type, house ?? undefined, 45))}
            className="rounded-xl bg-white px-3 py-2 text-sm ring-1 ring-stone-300">
            {type}{house ? ` · ${house}` : ""}
          </button>
        ))}
      </section>

      {msg && <p className="font-mono text-xs text-stone-600">{msg}</p>}

      <section>
        <h2 className="mb-2 text-sm font-semibold text-stone-500">Raw events</h2>
        <EventLog events={hub.log} />
      </section>
    </main>
  );
}
