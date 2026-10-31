// / : pick a house, open the street or the console, scan a phone in.
import { Card, Chip } from "@heroui/react";
import { QRCodeSVG } from "qrcode.react";
import { Link } from "react-router-dom";
import { ClockChip, Icon, SunMark } from "../components/ui";
import { useHub } from "../hooks/useHub";
import { HOUSES } from "../lib/types";

const PHONES = ["h12", "h14"] as const;

export default function Landing() {
  const hub = useHub("street");
  const base = hub.public_url ?? window.location.origin;
  return (
    <main className="mx-auto max-w-5xl px-6 py-8">
      <header className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <SunMark className="h-11 w-11" />
          <div>
            <h1 className="text-3xl font-bold tracking-tight">Hizashi</h1>
            <p className="text-sm text-stone-500">Neighbour-to-neighbour solar under KERC P2P 2024</p>
          </div>
        </div>
        <ClockChip />
      </header>

      <p className="mt-6 max-w-2xl text-lg text-stone-600">
        Every home gets an agent that sells spare rooftop solar to the neighbours, or buys theirs, inside limits the owner sets.
        A wallet in the hub refuses anything outside those limits.
      </p>

      <section className="mt-8">
        <h2 className="mb-3 text-[13px] font-semibold uppercase tracking-wider text-stone-500">Homes on the street</h2>
        <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
          {HOUSES.map((h) => {
            const info = hub.houses[h];
            const saved = hub.savings[h]?.saved_today;
            return (
              <Link key={h} to={`/h/${h}`} className="group">
                <Card className="h-full transition group-hover:-translate-y-0.5 group-hover:shadow-lg">
                  <Card.Content className="gap-2 p-4">
                    <div className="flex items-center justify-between">
                      <span className={`inline-flex h-10 w-10 items-center justify-center rounded-xl ${info?.roof ? "bg-sun-soft text-amber-700" : "bg-sky-50 text-sky-700"}`}>
                        <Icon name={info?.roof ? "sun" : "home"} />
                      </span>
                      {info && !info.onboarded && <Chip size="sm" variant="soft" color="warning">set up</Chip>}
                    </div>
                    <p className="text-lg font-semibold">{info?.label ?? h}</p>
                    <p className="text-sm text-stone-500">
                      {info ? (info.roof ? `${info.roof.kwp} kWp${info.subsidized ? " · subsidised" : ""}` : "No solar · buyer") : "…"}
                    </p>
                    {saved !== undefined && <p className="num text-sm font-medium text-emerald-700">saved ₹{saved.toFixed(2)} today</p>}
                  </Card.Content>
                </Card>
              </Link>
            );
          })}
        </div>
        <div className="mt-3 grid gap-3 sm:grid-cols-2">
          <Link to="/street" className="flex items-center justify-between rounded-2xl bg-sun px-5 py-4 font-semibold text-white shadow-sm shadow-amber-600/20 transition hover:brightness-105">
            <span className="flex items-center gap-2"><Icon name="grid" /> Street view</span><Icon name="arrow" />
          </Link>
          <Link to="/console" className="flex items-center justify-between rounded-2xl bg-ink px-5 py-4 font-semibold text-white transition hover:bg-stone-800">
            <span className="flex items-center gap-2"><Icon name="sliders" /> Console</span><Icon name="arrow" />
          </Link>
        </div>
      </section>

      <section className="mt-10">
        <h2 className="mb-3 text-[13px] font-semibold uppercase tracking-wider text-stone-500">Scan a phone in</h2>
        <div className="grid gap-4 sm:grid-cols-2">
          {PHONES.map((h) => (
            <Card key={h}>
              <Card.Content className="flex-row items-center gap-5 p-5">
                <div className="rounded-xl bg-white p-2 ring-1 ring-black/5">
                  <QRCodeSVG value={`${base}/h/${h}`} size={132} fgColor="#1c1917" />
                </div>
                <div className="min-w-0">
                  <p className="text-lg font-semibold">{hub.houses[h]?.label ?? h}</p>
                  <p className="text-sm text-stone-500">{hub.houses[h]?.roof ? "Seller with rooftop solar" : "Buyer, no solar"}</p>
                  <p className="mt-2 break-all font-mono text-xs text-stone-400">{base}/h/{h}</p>
                </div>
              </Card.Content>
            </Card>
          ))}
        </div>
        {!hub.public_url && <p className="mt-3 text-xs text-stone-500">Set PUBLIC_URL in .env to the tunnel URL so phones can reach the hub.</p>}
      </section>
    </main>
  );
}
