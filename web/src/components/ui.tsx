// Dashboard building blocks: icons, buttons, segmented control, clock, cards, toasts.
import { type ReactNode, useEffect, useState } from "react";
import { hhmm } from "../lib/api";
import { useHubStore } from "../store/hub";

const PATHS: Record<string, ReactNode> = {
  sun: (<><circle cx="12" cy="12" r="4.2" /><path d="M12 2.5v2.2M12 19.3v2.2M4.6 4.6l1.6 1.6M17.8 17.8l1.6 1.6M2.5 12h2.2M19.3 12h2.2M4.6 19.4l1.6-1.6M17.8 6.2l1.6-1.6" /></>),
  bolt: <path d="M13 2.5 4.5 13.5h6.5l-1 8 8.5-11h-6.5z" />,
  home: (<><path d="M3.5 10.5 12 3.5l8.5 7" /><path d="M5.5 9v11h13V9" /></>),
  cloud: <path d="M17.5 19H8a5.5 5.5 0 1 1 5.3-7.2A4.2 4.2 0 1 1 17.5 19z" />,
  plug: <path d="M9 2.5v5M15 2.5v5M6 7.5h12V11a6 6 0 0 1-12 0zM12 17v4.5" />,
  ban: (<><circle cx="12" cy="12" r="8.5" /><path d="m6 6 12 12" /></>),
  qr: (<><rect x="3.5" y="3.5" width="6.5" height="6.5" rx="1" /><rect x="14" y="3.5" width="6.5" height="6.5" rx="1" /><rect x="3.5" y="14" width="6.5" height="6.5" rx="1" /><path d="M14 14h2.5v2.5H14zM18 18h2.5v2.5H18zM18 14h2.5M14 18v2.5" /></>),
  sliders: <path d="M4 20v-6M4 10V4M12 20v-8M12 8V4M20 20v-4M20 12V4M1.5 14h5M9.5 8h5M17.5 16h5" />,
  chain: <path d="M9.5 16.5H7a4.5 4.5 0 0 1 0-9h2.5M14.5 7.5H17a4.5 4.5 0 0 1 0 9h-2.5M8.5 12h7" />,
  reset: <path d="M4 12a8 8 0 1 0 2.4-5.7M4 4v4h4" />,
  close: <path d="M6 6l12 12M18 6 6 18" />,
  arrow: <path d="M5 12h14M13 6l6 6-6 6" />,
  check: <path d="M5 12.5 10 17.5 19 7" />,
  swap: <path d="M7 7h12l-3-3M17 17H5l3 3" />,
  people: (<><circle cx="9" cy="8" r="3.5" /><path d="M2.5 20a6.5 6.5 0 0 1 13 0M16 4.6a3.5 3.5 0 0 1 0 6.8M21.5 20a6.5 6.5 0 0 0-4-6" /></>),
};
export type IconName = keyof typeof PATHS;

export function Icon({ name, className = "h-5 w-5", strokeWidth = 1.8 }: { name: IconName; className?: string; strokeWidth?: number }) {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={strokeWidth} strokeLinecap="round"
      strokeLinejoin="round" className={className} aria-hidden="true">{PATHS[name]}</svg>
  );
}

export function Logo() {
  return (
    <span className="inline-flex h-9 w-9 items-center justify-center rounded-[10px] bg-sun text-white shadow-[0_4px_12px_rgba(255,149,0,0.35)]">
      <Icon name="sun" className="h-5 w-5" strokeWidth={2.2} />
    </span>
  );
}

type Kind = "filled" | "tinted" | "gray" | "danger";
const KIND: Record<Kind, string> = {
  filled: "bg-sun text-white hover:brightness-105",
  tinted: "bg-sun-soft text-sun-ink hover:bg-[#ffe9c2]",
  gray: "bg-fill text-ink hover:bg-[rgba(120,120,128,0.18)]",
  danger: "bg-alert-soft text-alert hover:bg-[#ffdcda]",
};

export function Button({ children, onClick, kind = "gray", icon, small, className = "", disabled }: {
  children: ReactNode; onClick?: () => void; kind?: Kind; icon?: IconName; small?: boolean; className?: string; disabled?: boolean;
}) {
  return (
    <button onClick={onClick} disabled={disabled}
      className={`inline-flex items-center justify-center gap-1.5 rounded-full font-medium transition active:scale-[0.98] disabled:opacity-40 ${small ? "h-8 px-3 text-[13px]" : "h-10 px-4 text-sm"} ${KIND[kind]} ${className}`}>
      {icon && <Icon name={icon} className={small ? "h-3.5 w-3.5" : "h-4 w-4"} />}
      {children}
    </button>
  );
}

export function Segmented<T extends string | number>({ options, value, onChange }: { options: { value: T; label: string }[]; value: T; onChange: (v: T) => void }) {
  return (
    <div className="inline-flex rounded-[9px] bg-fill p-0.5">
      {options.map((o) => (
        <button key={String(o.value)} onClick={() => onChange(o.value)}
          className={`h-7 min-w-12 rounded-[7px] px-3 text-[13px] transition ${o.value === value ? "bg-white font-semibold shadow-[0_1px_3px_rgba(0,0,0,0.12)]" : "text-ink-2 hover:text-ink"}`}>
          {o.label}
        </button>
      ))}
    </div>
  );
}

export function Clock() {
  const { sim_time, connected, running } = useHubStore();
  return (
    <div className="flex items-center gap-2 rounded-full bg-card px-3 py-1.5 shadow-[0_1px_2px_rgba(0,0,0,0.06)]">
      <span className={`h-2 w-2 rounded-full ${connected ? (running ? "bg-leaf" : "bg-ink-3") : "animate-pulse bg-alert"}`} />
      <span className="num font-mono text-[15px] font-semibold">{hhmm(sim_time)}</span>
      <span className="text-xs text-ink-2">{connected ? (running ? "IST · simulated" : "day over") : "reconnecting"}</span>
    </div>
  );
}

export function Card({ title, action, children, className = "" }: { title?: string; action?: ReactNode; children: ReactNode; className?: string }) {
  return (
    <section className={`card p-5 ${className}`}>
      {(title || action) && (
        <div className="mb-3 flex items-center justify-between">
          {title && <h2 className="text-[15px] font-semibold">{title}</h2>}
          {action}
        </div>
      )}
      {children}
    </section>
  );
}

// --- toasts -------------------------------------------------------------------------------
type Toast = { id: number; title: string; body?: string; tone: "ok" | "bad" | "info" };
let push: (t: Omit<Toast, "id">) => void = () => {};
export const toast = (title: string, body?: string, tone: Toast["tone"] = "info") => push({ title, body, tone });

/** Toasts float in the middle of the screen, see-through and click-through, so nothing behind them is
 *  ever blocked. A repeat of the same title replaces the old one instead of stacking. */
export function Toaster() {
  const [items, setItems] = useState<Toast[]>([]);
  useEffect(() => {
    let n = 0;
    push = (t) => {
      const id = ++n;
      setItems((xs) => [...xs.filter((x) => x.title !== t.title).slice(-2), { ...t, id }]);
      setTimeout(() => setItems((xs) => xs.filter((x) => x.id !== id)), 3500);
    };
  }, []);
  const dot = { ok: "bg-leaf", bad: "bg-alert", info: "bg-sun" };
  return (
    <div className="pointer-events-none fixed left-1/2 top-1/2 z-50 flex w-[min(420px,90vw)] -translate-x-1/2 -translate-y-1/2 flex-col items-center gap-2">
      {items.map((t) => (
        <div key={t.id} className="rise flex max-w-full gap-2.5 rounded-2xl bg-white/55 px-4 py-2.5 shadow-sm backdrop-blur-md">
          <span className={`mt-1.5 h-2 w-2 shrink-0 rounded-full ${dot[t.tone]}`} />
          <div className="min-w-0">
            <p className="text-sm font-semibold">{t.title}</p>
            {t.body && <p className="line-clamp-2 text-[12px] text-ink-2">{t.body}</p>}
          </div>
        </div>
      ))}
    </div>
  );
}
