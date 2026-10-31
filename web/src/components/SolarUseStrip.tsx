// Live solar and use from the hub's latest meter.reading for this house.
import type { Live } from "../lib/types";
import { Icon } from "./ui";

export function SolarUseStrip({ live, hasSolar }: { live?: Live; hasSolar: boolean }) {
  const solar = live?.solar_kw ?? 0;
  const use = live?.use_kw ?? 0;
  const net = solar - use;
  const fmt = (v: number) => (live ? v.toFixed(2) : "—");
  return (
    <div className="grid grid-cols-3 gap-2">
      <Cell icon="sun" label="Solar" value={hasSolar ? fmt(solar) : "—"} unit="kW" tone="bg-sun-soft text-amber-900" />
      <Cell icon="home" label="Use" value={fmt(use)} unit="kW" tone="bg-white text-ink" />
      <Cell icon={net >= 0 ? "arrow" : "bolt"} label={live?.outage ? "Outage" : net >= 0 ? "Spare" : "From grid"}
        value={live ? Math.abs(net).toFixed(2) : "—"} unit="kW"
        tone={live?.outage ? "bg-stone-200 text-stone-600" : net >= 0 ? "bg-emerald-50 text-emerald-900" : "bg-sky-50 text-sky-900"} />
    </div>
  );
}

function Cell({ icon, label, value, unit, tone }: { icon: "sun" | "home" | "arrow" | "bolt"; label: string; value: string; unit: string; tone: string }) {
  return (
    <div className={`rounded-2xl p-3 ring-1 ring-black/5 ${tone}`}>
      <p className="flex items-center gap-1 text-[11px] font-semibold uppercase tracking-wide opacity-70">
        <Icon name={icon} className="h-3.5 w-3.5" /> {label}
      </p>
      <p className="num mt-1 text-xl font-bold">{value}<span className="ml-0.5 text-xs font-medium opacity-60">{unit}</span></p>
    </div>
  );
}
