/**
 * SolarUseStrip — live solar kW and household use kW from the latest meter.reading.
 *
 * Spec: readings carry watt-hours per simulated minute.
 *   kW = wh * 60 / 1000
 *
 * Layout: two stat cells side by side, amber for solar, sky-blue for use.
 */
import type { HubEvent } from "../lib/types";

function whToKw(wh: number): number {
  return (wh * 60) / 1000;
}

interface Props {
  meterEvent?: HubEvent; // latest meter.reading for this house
}

export function SolarUseStrip({ meterEvent }: Props) {
  const d = meterEvent?.data as
    | { solar_wh?: number; import_wh?: number; export_wh?: number }
    | undefined;

  const solarKw = d?.solar_wh !== undefined ? whToKw(d.solar_wh) : null;
  // import_wh is grid import; use = solar - export + import
  const useKw =
    d?.solar_wh !== undefined && d?.import_wh !== undefined && d?.export_wh !== undefined
      ? whToKw(d.solar_wh - d.export_wh + d.import_wh)
      : null;

  const fmt = (v: number | null) =>
    v !== null ? `${v.toFixed(2)} kW` : "— kW";

  return (
    <div className="grid grid-cols-2 gap-3">
      <div className="rounded-2xl bg-amber-50 p-4 ring-1 ring-amber-200">
        <p className="text-xs font-medium text-amber-700 uppercase tracking-wide">☀ Solar</p>
        <p className="mt-1 text-3xl font-bold tabular-nums text-amber-900">{fmt(solarKw)}</p>
      </div>
      <div className="rounded-2xl bg-sky-50 p-4 ring-1 ring-sky-200">
        <p className="text-xs font-medium text-sky-700 uppercase tracking-wide">⚡ Use</p>
        <p className="mt-1 text-3xl font-bold tabular-nums text-sky-900">{fmt(useKw)}</p>
      </div>
    </div>
  );
}

