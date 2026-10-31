import { Link } from "react-router-dom";
import { BlockStrip, HouseSvg, SimClock } from "../components";
import { useHub } from "../hooks/useHub";
import { HOUSES } from "../lib/types";

/** Laptop street view. Phase 0: the four houses + clock; glow, trades and flags in R2.6. */
export default function Street() {
  const hub = useHub("street");
  return (
    <main className="mx-auto max-w-5xl p-6">
      <header className="flex items-center justify-between">
        <Link to="/" className="text-2xl font-bold">Hizashi · Street</Link>
        <SimClock />
      </header>
      <svg viewBox="0 0 480 160" className="mt-6 w-full rounded-2xl bg-white ring-1 ring-stone-200">
        <rect x="0" y="120" width="480" height="40" fill="#e7e5e4" />
        {HOUSES.map((h, i) => (
          <HouseSvg key={h} x={15 + i * 115} label={hub.houses[h]?.label ?? h}
            solar={!!hub.houses[h]?.roof} dim={!!hub.outage} />
        ))}
      </svg>
      <section className="mt-6">
        <BlockStrip blocks={hub.blocks} />
      </section>
    </main>
  );
}
