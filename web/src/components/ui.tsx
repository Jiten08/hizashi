// Small shared pieces: icons (inline, lucide-style strokes), the sim clock chip, section titles.
import { Chip } from "@heroui/react";
import type { ReactNode } from "react";
import { hhmm } from "../lib/api";
import { useHubStore } from "../store/hub";

const PATHS: Record<string, ReactNode> = {
  sun: (<><circle cx="12" cy="12" r="4" /><path d="M12 2v2M12 20v2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4M2 12h2M20 12h2M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4" /></>),
  bolt: <path d="M13 2 4 14h7l-1 8 9-12h-7z" />,
  home: (<><path d="m3 10 9-7 9 7" /><path d="M5 9v11h14V9" /><path d="M10 20v-6h4v6" /></>),
  check: <path d="M20 6 9 17l-5-5" />,
  x: <path d="M18 6 6 18M6 6l12 12" />,
  shield: (<><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" /><path d="m9 12 2 2 4-4" /></>),
  ban: (<><circle cx="12" cy="12" r="9" /><path d="m5.6 5.6 12.8 12.8" /></>),
  clock: (<><circle cx="12" cy="12" r="9" /><path d="M12 7v5l3 2" /></>),
  list: <path d="M8 6h13M8 12h13M8 18h13M3 6h.01M3 12h.01M3 18h.01" />,
  sliders: <path d="M4 21v-7M4 10V3M12 21v-9M12 8V3M20 21v-5M20 12V3M1 14h6M9 8h6M17 16h6" />,
  inbox: (<><path d="M22 12h-6l-2 3h-4l-2-3H2" /><path d="M5.5 5h13L22 12v6a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2v-6z" /></>),
  arrow: <path d="M5 12h14M13 6l6 6-6 6" />,
  back: <path d="M19 12H5M11 18l-6-6 6-6" />,
  plug: <path d="M9 2v6M15 2v6M6 8h12v4a6 6 0 0 1-12 0zM12 18v4" />,
  cloud: <path d="M17.5 19H8a6 6 0 1 1 5.7-7.9A4.5 4.5 0 1 1 17.5 19z" />,
  grid: (<><path d="M4 21 12 3l8 18" /><path d="M7 14h10M6 18h12M9 9h6" /></>),
  link: <path d="M10 14a5 5 0 0 0 7 0l3-3a5 5 0 0 0-7-7l-1 1M14 10a5 5 0 0 0-7 0l-3 3a5 5 0 0 0 7 7l1-1" />,
  chain: <path d="M9 17H7A5 5 0 0 1 7 7h2M15 7h2a5 5 0 1 1 0 10h-2M8 12h8" />,
  hand: <path d="M18 11V6a2 2 0 0 0-4 0v5M14 10V4a2 2 0 0 0-4 0v6M10 10.5V6a2 2 0 0 0-4 0v8a8 8 0 0 0 16 0v-3a2 2 0 0 0-4 0" />,
  rupee: <path d="M6 3h12M6 8h12M6 13l8.5 8M6 13h3c6.7 0 6.7-10 0-10" />,
  sparkle: <path d="M12 3v4M12 17v4M3 12h4M17 12h4M6 6l2.5 2.5M15.5 15.5 18 18M6 18l2.5-2.5M15.5 8.5 18 6" />,
  pause: <path d="M10 4H6v16h4zM18 4h-4v16h4z" />,
  wifi: <path d="M5 13a10 10 0 0 1 14 0M8.5 16.5a5 5 0 0 1 7 0M2 9.5a15 15 0 0 1 20 0M12 20h.01" />,
};

export type IconName = keyof typeof PATHS;

export function Icon({ name, className = "h-5 w-5", strokeWidth = 1.8 }: { name: IconName; className?: string; strokeWidth?: number }) {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={strokeWidth}
      strokeLinecap="round" strokeLinejoin="round" className={className} aria-hidden="true">
      {PATHS[name]}
    </svg>
  );
}

export function SunMark({ className = "h-8 w-8" }: { className?: string }) {
  return (
    <span className={`relative inline-flex items-center justify-center rounded-xl bg-sun text-white shadow-sm ${className}`}>
      <Icon name="sun" className="h-[60%] w-[60%]" strokeWidth={2.2} />
    </span>
  );
}

/** Sim time, speed and the connection state. */
export function ClockChip({ compact = false }: { compact?: boolean }) {
  const { sim_time, speed, running, connected, mock } = useHubStore();
  const state = mock ? "mock" : connected ? "live" : "offline";
  const dot = mock ? "bg-amber-400" : connected ? "bg-emerald-500" : "bg-red-500 animate-pulse";
  return (
    <div className="flex items-center gap-2" title={state}>
      <span className="inline-flex items-center gap-1.5 rounded-full border border-black/5 bg-white px-2.5 py-1 shadow-sm">
        <span className={`h-1.5 w-1.5 rounded-full ${dot}`} />
        <span className="num font-mono text-sm font-semibold">{hhmm(sim_time)}</span>
        {!compact && <span className="text-xs text-stone-500">{running ? `${speed}×` : "paused"}</span>}
      </span>
      {!compact && state !== "live" && (
        <Chip size="sm" variant="soft" color={mock ? "warning" : "danger"}>{state}</Chip>
      )}
    </div>
  );
}

export function SectionTitle({ children, action }: { children: ReactNode; action?: ReactNode }) {
  return (
    <div className="mb-2 mt-1 flex items-center justify-between px-1">
      <h2 className="text-[13px] font-semibold uppercase tracking-wider text-stone-500">{children}</h2>
      {action}
    </div>
  );
}

export function Stat({ label, value, icon, tone = "default", sub }: {
  label: string; value: ReactNode; icon?: IconName; tone?: "sun" | "grid" | "default"; sub?: ReactNode;
}) {
  const tones = {
    sun: "bg-sun-soft text-amber-900",
    grid: "bg-sky-50 text-sky-900",
    default: "bg-white text-ink",
  } as const;
  return (
    <div className={`rounded-2xl p-4 ring-1 ring-black/5 ${tones[tone]}`}>
      <p className="flex items-center gap-1.5 text-xs font-medium uppercase tracking-wide opacity-75">
        {icon && <Icon name={icon} className="h-3.5 w-3.5" />} {label}
      </p>
      <p className="num mt-1 text-2xl font-bold">{value}</p>
      {sub && <p className="mt-0.5 text-xs opacity-70">{sub}</p>}
    </div>
  );
}

export function Empty({ icon, title, children }: { icon: IconName; title: string; children?: ReactNode }) {
  return (
    <div className="flex flex-col items-center rounded-2xl border border-dashed border-stone-300 bg-white/50 px-6 py-10 text-center">
      <span className="mb-3 inline-flex h-11 w-11 items-center justify-center rounded-full bg-stone-100 text-stone-500">
        <Icon name={icon} />
      </span>
      <p className="font-medium text-stone-700">{title}</p>
      {children && <p className="mt-1 text-sm text-stone-500">{children}</p>}
    </div>
  );
}
