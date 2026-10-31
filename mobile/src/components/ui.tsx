// iOS-style building blocks for the phone PWA: large-title screens, inset grouped sections,
// rows, buttons, rings, steppers, a segmented control and a switch.
import type { ReactNode } from "react";

const PATHS: Record<string, ReactNode> = {
  sun: (<><circle cx="12" cy="12" r="4.2" /><path d="M12 2.5v2.2M12 19.3v2.2M4.6 4.6l1.6 1.6M17.8 17.8l1.6 1.6M2.5 12h2.2M19.3 12h2.2M4.6 19.4l1.6-1.6M17.8 6.2l1.6-1.6" /></>),
  home: (<><path d="M3.5 10.5 12 3.5l8.5 7" /><path d="M5.5 9v11h13V9" /></>),
  check: <path d="M5 12.5 10 17.5 19 7" />,
  checkCircle: (<><circle cx="12" cy="12" r="9" /><path d="m8 12.5 3 3 5-6" /></>),
  sliders: <path d="M4 20v-6M4 10V4M12 20v-8M12 8V4M20 20v-4M20 12V4M1.5 14h5M9.5 8h5M17.5 16h5" />,
  clock: (<><circle cx="12" cy="12" r="9" /><path d="M12 7v5l3 2" /></>),
  hand: <path d="M18 11V6a2 2 0 0 0-4 0v5M14 10V4a2 2 0 0 0-4 0v6M10 10.5V6a2 2 0 0 0-4 0v8a8 8 0 0 0 16 0v-3a2 2 0 0 0-4 0" />,
  shield: (<><path d="M12 21.5s8-3.8 8-9.8V5l-8-3-8 3v6.7c0 6 8 9.8 8 9.8z" /><path d="m8.5 12 2.5 2.5 4.5-5" /></>),
  swap: <path d="M7 7h12l-3-3M17 17H5l3 3" />,
  trend: <path d="M3 17 9 11l4 4 8-8M15 7h6v6" />,
  ribbon: (<><circle cx="12" cy="9" r="5.5" /><path d="m8.5 13.5-2 7.5 5.5-3 5.5 3-2-7.5" /></>),
  cash: (<><rect x="2.5" y="6" width="19" height="12" rx="2" /><circle cx="12" cy="12" r="2.5" /></>),
  link: <path d="M9.5 16.5H7a4.5 4.5 0 0 1 0-9h2.5M14.5 7.5H17a4.5 4.5 0 0 1 0 9h-2.5M8.5 12h7" />,
  chevron: <path d="m9 5 7 7-7 7" />,
  back: <path d="m15 5-7 7 7 7" />,
  plus: <path d="M12 5v14M5 12h14" />,
  minus: <path d="M5 12h14" />,
  doc: (<><path d="M14 3H7a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V8z" /><path d="M14 3v5h5" /></>),
};
export type IconName = keyof typeof PATHS;

export function Icon({ name, className = "h-5 w-5", strokeWidth = 1.9 }: { name: IconName; className?: string; strokeWidth?: number }) {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={strokeWidth} strokeLinecap="round"
      strokeLinejoin="round" className={className} aria-hidden="true">{PATHS[name]}</svg>
  );
}

export function IconTile({ name, bg, size = 29 }: { name: IconName; bg: string; size?: number }) {
  return (
    <span className="inline-flex shrink-0 items-center justify-center text-white"
      style={{ width: size, height: size, borderRadius: size * 0.24, background: bg }}>
      <Icon name={name} className="h-[62%] w-[62%]" strokeWidth={2.2} />
    </span>
  );
}

export function Screen({ title, subtitle, children }: { title: string; subtitle?: ReactNode; children: ReactNode }) {
  return (
    <main className="mx-auto max-w-[560px] px-4 pb-[calc(96px+env(safe-area-inset-bottom))] pt-[calc(14px+env(safe-area-inset-top))]">
      {subtitle ? <p className="t-footnote font-semibold">{subtitle}</p> : null}
      <h1 className="t-large mb-1">{title}</h1>
      {children}
    </main>
  );
}

export function Section({ header, footer, children, className = "" }: { header?: string; footer?: ReactNode; children: ReactNode; className?: string }) {
  return (
    <section className={`mt-[22px] ${className}`}>
      {header ? <h2 className="t-section mb-[7px] ml-4">{header}</h2> : null}
      <div className="overflow-hidden rounded-xl bg-card">{children}</div>
      {footer ? <p className="t-footnote mx-4 mt-[7px]">{footer}</p> : null}
    </section>
  );
}

export function Card({ children, className = "" }: { children: ReactNode; className?: string }) {
  return <div className={`rounded-xl bg-card p-4 ${className}`}>{children}</div>;
}

export function Row({ icon, iconBg = "var(--color-orange)", title, subtitle, value, valueClass = "", onClick, chevron, last, accessory }: {
  icon?: IconName; iconBg?: string; title: ReactNode; subtitle?: ReactNode; value?: ReactNode; valueClass?: string;
  onClick?: () => void; chevron?: boolean; last?: boolean; accessory?: ReactNode;
}) {
  const Tag = onClick ? "button" : "div";
  return (
    <Tag onClick={onClick} className={`flex w-full items-center pl-4 text-left ${onClick ? "active:bg-[#e5e5ea]" : ""}`}>
      {icon ? <span className="mr-3"><IconTile name={icon} bg={iconBg} /></span> : null}
      <span className={`flex min-h-11 flex-1 items-center pr-4 ${last ? "" : "hairline"}`}>
        <span className={`min-w-0 flex-1 ${subtitle ? "py-[9px]" : "py-[11px]"}`}>
          <span className="t-body block">{title}</span>
          {subtitle ? <span className="t-footnote mt-px block whitespace-pre-line">{subtitle}</span> : null}
        </span>
        {value !== undefined ? <span className={`t-body num ml-2 text-right text-label-2 ${valueClass}`}>{value}</span> : null}
        {accessory}
        {chevron ? <Icon name="chevron" className="ml-1.5 h-4 w-4 text-label-3" strokeWidth={2.4} /> : null}
      </span>
    </Tag>
  );
}

type Kind = "filled" | "tinted" | "gray" | "plain" | "danger";
export function Button({ children, onClick, kind = "filled", disabled, busy, className = "" }: {
  children: ReactNode; onClick?: () => void; kind?: Kind; disabled?: boolean; busy?: boolean; className?: string;
}) {
  const k = {
    filled: "bg-orange text-white",
    tinted: "bg-orange-soft text-orange-ink",
    gray: "bg-fill text-label",
    plain: "bg-transparent text-orange",
    danger: "bg-transparent text-red",
  }[kind];
  return (
    <button onClick={onClick} disabled={disabled || busy}
      className={`t-headline inline-flex h-[50px] items-center justify-center gap-1.5 rounded-[14px] px-4 transition active:opacity-70 disabled:opacity-40 ${k} ${className}`}>
      {busy ? <span className="h-5 w-5 animate-spin rounded-full border-2 border-current border-t-transparent" /> : children}
    </button>
  );
}

export function Pill({ children, className = "bg-fill text-label-2" }: { children: ReactNode; className?: string }) {
  return <span className={`inline-flex items-center rounded-full px-2 py-[3px] text-xs font-semibold ${className}`}>{children}</span>;
}

/** Apple Fitness-style ring. progress 0..1 (clamped). */
export function Ring({ size, stroke, progress, color, children }: { size: number; stroke: number; progress: number; color: string; children?: ReactNode }) {
  const r = (size - stroke) / 2;
  const c = 2 * Math.PI * r;
  const p = Math.max(0, Math.min(1, progress));
  return (
    <span className="relative inline-flex items-center justify-center" style={{ width: size, height: size }}>
      <svg width={size} height={size} className="absolute inset-0 -rotate-90">
        <circle cx={size / 2} cy={size / 2} r={r} stroke={color} strokeOpacity={0.18} strokeWidth={stroke} fill="none" />
        <circle cx={size / 2} cy={size / 2} r={r} stroke={color} strokeWidth={stroke} fill="none" strokeLinecap="round"
          strokeDasharray={`${c * p} ${c}`} style={{ transition: "stroke-dasharray 0.6s ease" }} />
      </svg>
      {children}
    </span>
  );
}

export function Stepper({ label, hint, value, onChange, step, min = 0, max = 999, format, last }: {
  label: string; hint?: string; value: number; onChange: (v: number) => void; step: number; min?: number; max?: number;
  format: (v: number) => string; last?: boolean;
}) {
  const bump = (d: number) => {
    const v = Math.round((value + d) * 100) / 100;
    if (v >= min - 1e-9 && v <= max + 1e-9) onChange(v);
  };
  return (
    <div className="flex items-center pl-4">
      <div className={`flex min-h-11 flex-1 items-center py-2.5 pr-4 ${last ? "" : "hairline"}`}>
        <div className="min-w-0 flex-1 pr-2">
          <p className="t-body">{label}</p>
          {hint ? <p className="t-footnote">{hint}</p> : null}
        </div>
        <span className="t-headline num mr-2.5 min-w-16 text-right">{format(value)}</span>
        <span className="flex h-8 items-center rounded-[9px] bg-fill">
          <button aria-label={`Less ${label}`} onClick={() => bump(-step)} className="flex h-8 w-[46px] items-center justify-center active:opacity-50"><Icon name="minus" className="h-5 w-5" strokeWidth={2.2} /></button>
          <span className="h-[18px] w-px bg-label-3" />
          <button aria-label={`More ${label}`} onClick={() => bump(step)} className="flex h-8 w-[46px] items-center justify-center active:opacity-50"><Icon name="plus" className="h-5 w-5" strokeWidth={2.2} /></button>
        </span>
      </div>
    </div>
  );
}

export function Segmented<T extends string>({ options, value, onChange }: { options: { value: T; label: string }[]; value: T; onChange: (v: T) => void }) {
  return (
    <div className="flex rounded-[9px] bg-fill p-0.5">
      {options.map((o) => (
        <button key={o.value} onClick={() => onChange(o.value)}
          className={`h-[30px] flex-1 rounded-[7px] text-[13px] transition ${o.value === value ? "bg-white font-semibold shadow-[0_2px_4px_rgba(0,0,0,0.12)]" : "font-medium"}`}>
          {o.label}
        </button>
      ))}
    </div>
  );
}

export function Toggle({ on, onChange, label }: { on: boolean; onChange: (v: boolean) => void; label: string }) {
  return (
    <button role="switch" aria-checked={on} aria-label={label} onClick={() => onChange(!on)}
      className={`relative h-[31px] w-[51px] shrink-0 rounded-full transition-colors ${on ? "bg-green" : "bg-[#e9e9ea]"}`}>
      <span className={`absolute top-[2px] h-[27px] w-[27px] rounded-full bg-white shadow-[0_3px_8px_rgba(0,0,0,0.15),0_1px_1px_rgba(0,0,0,0.16)] transition-all ${on ? "left-[22px]" : "left-[2px]"}`} />
    </button>
  );
}

export function Spinner() {
  return <span className="inline-block h-6 w-6 animate-spin rounded-full border-[2.5px] border-label-3 border-t-label-2" />;
}
