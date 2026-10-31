import { QRCodeSVG } from "qrcode.react";
import { Link } from "react-router-dom";
import { SimClock } from "../components";
import { useHub } from "../hooks/useHub";
import { HOUSES } from "../lib/types";

const PHONES = ["h12", "h14"] as const;

export default function Landing() {
  const hub = useHub("street");
  const base = hub.public_url ?? window.location.origin;
  return (
    <main className="mx-auto max-w-3xl p-6">
      <header className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <img src="/sun.svg" className="h-10 w-10" alt="" />
          <h1 className="text-3xl font-bold">Hizashi</h1>
        </div>
        <SimClock />
      </header>
      <p className="mt-2 text-stone-600">Every home gets an agent that sells spare rooftop solar to neighbours, inside limits the owner sets.</p>

      <h2 className="mt-8 text-sm font-semibold uppercase tracking-wide text-stone-500">Pick a house</h2>
      <div className="mt-2 grid grid-cols-2 gap-3 sm:grid-cols-4">
        {HOUSES.map((h) => (
          <Link key={h} to={`/h/${h}`} className="rounded-2xl bg-white p-4 text-center text-lg font-semibold shadow-sm ring-1 ring-stone-200 hover:ring-sun">
            {hub.houses[h]?.label ?? h}
            <span className="block text-xs font-normal text-stone-500">{hub.houses[h] ? (hub.houses[h].roof ? `${hub.houses[h].roof!.kwp} kWp` : "no solar") : ""}</span>
          </Link>
        ))}
      </div>
      <div className="mt-3 flex gap-3">
        <Link to="/street" className="flex-1 rounded-2xl bg-sun p-4 text-center font-semibold text-white">Street</Link>
        <Link to="/console" className="flex-1 rounded-2xl bg-stone-800 p-4 text-center font-semibold text-white">Console</Link>
      </div>

      <h2 className="mt-8 text-sm font-semibold uppercase tracking-wide text-stone-500">Phones</h2>
      <div className="mt-2 grid grid-cols-2 gap-4">
        {PHONES.map((h) => (
          <div key={h} className="flex flex-col items-center rounded-2xl bg-white p-4 ring-1 ring-stone-200">
            <QRCodeSVG value={`${base}/h/${h}`} size={160} fgColor="#1c1917" />
            <p className="mt-2 font-semibold">{hub.houses[h]?.label ?? h}</p>
            <p className="break-all text-center text-xs text-stone-500">{base}/h/{h}</p>
          </div>
        ))}
      </div>
      {!hub.public_url && <p className="mt-2 text-xs text-stone-500">Set PUBLIC_URL in .env to the tunnel URL so phones can reach the hub.</p>}
    </main>
  );
}
