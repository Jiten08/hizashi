// "At home": the owner tells the agent they'll be away, or have guests, today or tomorrow.
// The hub stores it and the agent re-forecasts; this screen only lists plans and sends taps.
import { useState } from "react";
import { api } from "../lib/api";
import { hhmm } from "../lib/format";
import { useHubStore } from "../lib/store";
import type { House, Schedule } from "../lib/types";
import { Button, Icon, Pill, Row, Section, Segmented } from "./ui";

type Kind = Schedule["kind"];
type When = "today" | "tomorrow";

const KIND: Record<Kind, { label: string; icon: "suitcase" | "people"; color: string; start: number; end: number }> = {
  away: { label: "Away", icon: "suitcase", color: "var(--color-blue)", start: 9 * 4, end: 18 * 4 },
  guests: { label: "Guests", icon: "people", color: "var(--color-indigo)", start: 11 * 4, end: 15 * 4 },
};

const pad = (n: number) => String(n).padStart(2, "0");
const quarter = (q: number) => `${pad(Math.floor(q / 4))}:${pad((q % 4) * 15)}`;     // 36 -> "09:00"
const dayAfter = (day: string) => new Date(Date.parse(`${day}T00:00:00Z`) + 86_400_000).toISOString().slice(0, 10);

/** "09:00–18:00", with a midnight end shown as 24:00. */
function span(s: Schedule) {
  const end = s.end.slice(0, 10) > s.start.slice(0, 10) && hhmm(s.end) === "00:00" ? "24:00" : hhmm(s.end);
  return `${hhmm(s.start)}–${end}`;
}

export function HomePlans({ house }: { house: House }) {
  const simTime = useHubStore((s) => s.sim_time);
  const all = useHubStore((s) => s.schedules[house]);
  const [adding, setAdding] = useState(false);
  const [removing, setRemoving] = useState<string | null>(null);
  if (!simTime) return null;
  const today = simTime.slice(0, 10);
  const now = Date.parse(simTime);
  const plans = (all ?? []).filter((s) => Date.parse(s.end) > now);
  const dayLabel = (s: Schedule) => (s.start.slice(0, 10) === today ? "Today" : s.start.slice(0, 10) === dayAfter(today) ? "Tomorrow" : s.start.slice(0, 10));

  const remove = async (id: string) => {
    setRemoving(id);
    try { await api.removeSchedule(house, id); } catch { /* the list stays as the hub says */ } finally { setRemoving(null); }
  };

  return (
    <>
      <Section header="At home" footer="Your agent plans around these: away means less use, so more to sell; guests mean more use. Changes reach the blocks that haven't opened yet (about 2 hours ahead).">
        {plans.map((s) => {
          const on = Date.parse(s.start) <= now;
          return (
            <Row key={s.schedule_id} icon={KIND[s.kind].icon} iconBg={KIND[s.kind].color} title={KIND[s.kind].label}
              subtitle={`${dayLabel(s)} · ${span(s)}`}
              accessory={<span className="ml-2 flex items-center gap-2">
                {on && <Pill className="bg-green-soft text-green-ink">Now</Pill>}
                <button aria-label="Remove" disabled={removing === s.schedule_id} onClick={() => remove(s.schedule_id)}
                  className="flex h-8 w-8 items-center justify-center rounded-full bg-fill text-label-2 active:opacity-50 disabled:opacity-40">
                  <Icon name="close" className="h-4 w-4" strokeWidth={2.4} />
                </button>
              </span>} />
          );
        })}
        <Row title={<span className="text-orange">Plan time away or guests</span>} icon="plus" iconBg="var(--color-orange)"
          onClick={() => setAdding(true)} last />
      </Section>
      {adding && <AddPlan house={house} today={today} nowQuarter={Math.floor((Date.parse(simTime) - Date.parse(`${today}T00:00:00+05:30`)) / 900_000)}
        onClose={() => setAdding(false)} />}
    </>
  );
}

function AddPlan({ house, today, nowQuarter, onClose }: { house: House; today: string; nowQuarter: number; onClose: () => void }) {
  const [kind, setKind] = useState<Kind>("away");
  const [when, setWhen] = useState<When>(nowQuarter >= 23 * 4 ? "tomorrow" : "today");
  const first = when === "today" ? nowQuarter : 0;
  const defaults = (k: Kind, w: When) => {
    const lo = w === "today" ? nowQuarter : 0;
    const start = Math.max(KIND[k].start, lo);
    return { start, end: Math.max(KIND[k].end, Math.min(start + 4, 96)) };
  };
  const [range, setRange] = useState(() => defaults("away", when));
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const pick = (k: Kind, w: When) => { setKind(k); setWhen(w); setRange(defaults(k, w)); setError(null); };
  const save = async () => {
    setBusy(true);
    setError(null);
    try {
      await api.addSchedule(house, { kind, day: when === "today" ? today : dayAfter(today), start: quarter(range.start), end: quarter(range.end) });
      navigator.vibrate?.(15);
      onClose();
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  };

  const starts = Array.from({ length: 96 - first }, (_, i) => first + i);
  const ends = Array.from({ length: 96 - range.start }, (_, i) => range.start + 1 + i);
  return (
    <div className="fixed inset-0 z-30 flex items-end bg-black/30" onClick={onClose}>
      <div className="rise mx-auto w-full max-w-[560px] rounded-t-[14px] bg-bg px-4 pb-[calc(20px+env(safe-area-inset-bottom))] pt-3"
        onClick={(e) => e.stopPropagation()}>
        <div className="mx-auto mb-3 h-[5px] w-9 rounded-full bg-label-3" />
        <div className="flex items-center">
          <h2 className="t-title3 flex-1">Plan your day</h2>
          <button onClick={onClose} className="t-body text-orange">Cancel</button>
        </div>
        <div className="mt-4 grid gap-2.5">
          <Segmented value={kind} onChange={(k) => pick(k, when)}
            options={[{ value: "away", label: "I'll be away" }, { value: "guests", label: "Guests coming" }]} />
          <Segmented value={when} onChange={(w) => pick(kind, w)}
            options={[{ value: "today", label: "Today" }, { value: "tomorrow", label: "Tomorrow" }]} />
        </div>
        <Section>
          <TimeRow label="From" value={range.start} options={starts}
            onChange={(v) => setRange({ start: v, end: Math.max(range.end, v + 1) })} />
          <TimeRow label="Until" value={range.end} options={ends} onChange={(v) => setRange({ ...range, end: v })} last />
        </Section>
        {error && <p className="t-footnote mx-4 mt-2 !text-red">{error}</p>}
        <Button className="mt-4 w-full" onClick={save} busy={busy}>Save</Button>
      </div>
    </div>
  );
}

function TimeRow({ label, value, options, onChange, last }: { label: string; value: number; options: number[]; onChange: (v: number) => void; last?: boolean }) {
  return (
    <label className="flex items-center pl-4">
      <span className={`flex min-h-11 flex-1 items-center pr-4 ${last ? "" : "hairline"}`}>
        <span className="t-body flex-1">{label}</span>
        <select value={value} onChange={(e) => onChange(Number(e.target.value))}
          className="t-body num rounded-lg bg-fill px-2.5 py-1 text-label">
          {options.map((q) => <option key={q} value={q}>{quarter(q)}</option>)}
        </select>
      </span>
    </label>
  );
}
