// The owner's phone app for one house. Which house comes from the QR link (?house=h14) and is
// remembered on the phone. First visit runs onboarding; then four tabs. A notification tap opens
// a tab through ?tab= (or a message from the service worker when the app is already open).
import { useEffect, useState } from "react";
import { Button, Icon, type IconName, Spinner } from "./components/ui";
import { syncPush } from "./lib/push";
import { saveHouse, savedHouse, useHubConnection, useHubStore } from "./lib/store";
import type { House } from "./lib/types";
import Approvals from "./pages/Approvals";
import History from "./pages/History";
import Onboarding from "./pages/Onboarding";
import Pick from "./pages/Pick";
import Rules from "./pages/Rules";
import Today from "./pages/Today";

type Tab = "today" | "approvals" | "rules" | "history";
const TABS: { id: Tab; label: string; icon: IconName }[] = [
  { id: "today", label: "Today", icon: "sun" },
  { id: "approvals", label: "Approvals", icon: "checkCircle" },
  { id: "rules", label: "Rules", icon: "sliders" },
  { id: "history", label: "History", icon: "clock" },
];

const tabFrom = (url: string): Tab | null => {
  const t = new URL(url, location.origin).searchParams.get("tab");
  return TABS.some((x) => x.id === t) ? (t as Tab) : null;
};

export default function App() {
  const [house, setHouse] = useState<House | null>(savedHouse);
  const [tab, setTab] = useState<Tab>(() => tabFrom(location.href) ?? "today");
  const [editingSetup, setEditingSetup] = useState(false);
  useHubConnection(house);
  const hub = useHubStore();

  useEffect(() => { if (house) syncPush(house); }, [house]);
  useEffect(() => {
    const onMessage = (m: MessageEvent) => {
      const t = m.data?.type === "open" ? tabFrom(m.data.url) : null;
      if (t) { setEditingSetup(false); setTab(t); window.scrollTo(0, 0); }
    };
    navigator.serviceWorker?.addEventListener("message", onMessage);
    return () => navigator.serviceWorker?.removeEventListener("message", onMessage);
  }, []);

  const choose = (h: House | null) => {
    saveHouse(h);
    setHouse(h);
    setTab("today");
    history.replaceState(null, "", "/app/");
  };

  if (!house) return <Pick onPick={choose} />;
  const info = hub.houses[house];

  if (!hub.loaded || !info) {
    const stuck = hub.failures >= 3;
    return (
      <div className="flex min-h-dvh flex-col items-center justify-center gap-3 px-8 text-center">
        {!stuck && <Spinner />}
        <p className="t-title3">{stuck ? "Can't reach your street" : "Reaching your street…"}</p>
        {stuck && (
          <p className="t-footnote">
            The laptop running Hizashi isn't answering. Check that the hub (and ngrok, if you use it) is still running.
            {hub.lastError ? ` (${hub.lastError})` : ""} Still trying every couple of seconds.
          </p>
        )}
        <Button kind="plain" onClick={() => choose(null)}>Choose a different house</Button>
      </div>
    );
  }

  if (!info.onboarded || editingSetup) {
    return <Onboarding house={house} info={info} mandate={hub.mandates[house]}
      onDone={() => { setEditingSetup(false); setTab("today"); }}
      onCancel={info.onboarded ? () => setEditingSetup(false) : undefined} />;
  }

  const pending = hub.approvals.filter((a) => a.house === house && a.status === "pending").length;
  return (
    <>
      {tab === "today" && <Today house={house} />}
      {tab === "approvals" && <Approvals house={house} />}
      {tab === "rules" && <Rules house={house} onEditSetup={() => setEditingSetup(true)} onSwitchHouse={() => choose(null)} />}
      {tab === "history" && <History house={house} />}
      <nav className="fixed inset-x-0 bottom-0 z-20 border-t-[0.5px] border-sep bg-[rgba(249,249,249,0.94)] pb-[env(safe-area-inset-bottom)] backdrop-blur-xl">
        <ul className="mx-auto grid max-w-[560px] grid-cols-4">
          {TABS.map((t) => {
            const on = tab === t.id;
            return (
              <li key={t.id}>
                <button onClick={() => { setTab(t.id); window.scrollTo(0, 0); }} aria-current={on ? "page" : undefined}
                  className={`relative flex w-full flex-col items-center gap-0.5 pb-1 pt-1.5 text-[10px] font-medium ${on ? "text-orange" : "text-[#8e8e93]"}`}>
                  <Icon name={t.icon} className="h-[26px] w-[26px]" strokeWidth={on ? 2.2 : 1.7} />
                  {t.label}
                  {t.id === "approvals" && pending > 0 && (
                    <span className="absolute left-[calc(50%+6px)] top-0.5 inline-flex h-[18px] min-w-[18px] items-center justify-center rounded-full bg-red px-1 text-[11px] font-semibold text-white">{pending}</span>
                  )}
                </button>
              </li>
            );
          })}
        </ul>
      </nav>
    </>
  );
}
