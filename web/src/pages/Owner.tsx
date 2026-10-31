/**
 * Owner app — /h/:house. Mobile first. First visit (house not onboarded) shows the setup
 * flow; afterwards: Home / Approvals / Rules / History bottom tabs.
 * Display only: prices, savings and settlements all come from hub events.
 */
import { Spinner } from "@heroui/react";
import { useState } from "react";
import { Link, useParams } from "react-router-dom";
import { ClockChip, Icon, type IconName, SunMark } from "../components/ui";
import { useHub } from "../hooks/useHub";
import { HOUSES, type House } from "../lib/types";
import Onboarding from "./Onboarding";
import Approvals from "./owner/Approvals";
import History from "./owner/History";
import Home from "./owner/Home";
import Rules from "./owner/Rules";

const TABS: { id: Tab; label: string; icon: IconName }[] = [
  { id: "home", label: "Home", icon: "home" },
  { id: "approvals", label: "Approvals", icon: "inbox" },
  { id: "rules", label: "Rules", icon: "sliders" },
  { id: "history", label: "History", icon: "list" },
];
type Tab = "home" | "approvals" | "rules" | "history";

export default function Owner() {
  const { house } = useParams();
  const h = (HOUSES as string[]).includes(house ?? "") ? (house as House) : "h12";
  const hub = useHub("owner", h);
  const [tab, setTab] = useState<Tab>("home");
  const [editingSetup, setEditingSetup] = useState(false);
  const info = hub.houses[h];
  const pending = hub.approvals.filter((a) => a.house === h && a.status === "pending").length;

  if (!hub.loaded || !info) {
    return (
      <div className="flex min-h-dvh items-center justify-center">
        <Spinner size="lg" />
      </div>
    );
  }
  if (!info.onboarded || editingSetup) {
    return <Onboarding house={h} info={info} mandate={hub.mandates[h]} onDone={() => setEditingSetup(false)}
      onCancel={info.onboarded ? () => setEditingSetup(false) : undefined} />;
  }

  return (
    <div className="mx-auto flex min-h-dvh max-w-md flex-col">
      <header className="sticky top-0 z-20 flex items-center justify-between border-b border-black/5 bg-[var(--background)]/85 px-4 py-3 backdrop-blur-md">
        <Link to="/" className="flex items-center gap-2.5">
          <SunMark className="h-8 w-8" />
          <span className="leading-tight">
            <span className="block text-base font-semibold">{info.label}</span>
            <span className="block text-xs text-stone-500">
              {info.roof ? `${info.roof.kwp} kWp${info.subsidized ? " · PM Surya Ghar" : ""}` : "No solar · buyer"}
            </span>
          </span>
        </Link>
        <ClockChip />
      </header>

      <main className="flex-1 space-y-3 px-4 pb-28 pt-4">
        {tab === "home" && <Home house={h} onOpenApprovals={() => setTab("approvals")} />}
        {tab === "approvals" && <Approvals house={h} />}
        {tab === "rules" && <Rules house={h} onEditSetup={() => setEditingSetup(true)} />}
        {tab === "history" && <History house={h} />}
        <p className="pt-4 text-center text-[11px] text-stone-400">
          Weather: {hub.weather_source ?? "—"} · homes and meters simulated
        </p>
      </main>

      <nav className="fixed inset-x-0 bottom-0 z-20 mx-auto max-w-md border-t border-black/5 bg-white/95 pb-[env(safe-area-inset-bottom)] backdrop-blur-md">
        <ul className="grid grid-cols-4">
          {TABS.map((t) => {
            const active = tab === t.id;
            return (
              <li key={t.id}>
                <button onClick={() => setTab(t.id)} aria-current={active ? "page" : undefined}
                  className={`relative flex w-full flex-col items-center gap-0.5 py-2.5 text-[11px] font-medium transition-colors ${active ? "text-sun" : "text-stone-500 hover:text-stone-800"}`}>
                  <Icon name={t.icon} className="h-5 w-5" strokeWidth={active ? 2.2 : 1.8} />
                  {t.label}
                  {t.id === "approvals" && pending > 0 && (
                    <span className="absolute right-[calc(50%-20px)] top-1.5 inline-flex h-4 min-w-4 items-center justify-center rounded-full bg-red-500 px-1 text-[10px] font-bold text-white">
                      {pending}
                    </span>
                  )}
                </button>
              </li>
            );
          })}
        </ul>
      </nav>
    </div>
  );
}
