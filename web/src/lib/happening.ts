// What is going on right now, for the screens to show the moment a console button is pressed:
// active cloud / AC / guests / away / outage, the owner's OK on a deal (asking, approved, declined),
// a deal that broke an owner's rule, guard flags and a blacklisted impostor. All read straight from hub
// events; nothing is computed here but "is it still on".
import { useMemo } from "react";
import { hhmm } from "./api";
import { HOUSES, type House } from "./types";
import { useHubStore } from "../store/hub";

export type Tone = "cloud" | "load" | "alert" | "ok" | "info";
// street: shown on every house (a street-wide cloud); house: that house only; none: the Now list only.
export interface Happening { key: string; house: House | null; label: string; tone: Tone; scope: "house" | "street" | "none" }

const RECENT_MIN = 30;          // a decision, refusal or flag stays on screen this long (sim minutes)
const LABEL: Record<string, string> = { cloud: "Cloud", ac: "AC on", guests: "Guests", away: "Away", outage: "Grid outage" };
const TONE: Record<string, Tone> = { cloud: "cloud", ac: "load", guests: "load", away: "load", outage: "alert" };

export function useHappening(): {
  all: Happening[]; byHouse: Record<House, Happening[]>; outageUntil: string | null; dayOver: boolean;
  impostor: { claimed: string; price: number } | null;
} {
  const simTime = useHubStore((s) => s.sim_time);
  const running = useHubStore((s) => s.running);
  const simEvents = useHubStore((s) => s.sim_events);
  const blocked = useHubStore((s) => s.blocked);
  const approvals = useHubStore((s) => s.approvals);
  const flags = useHubStore((s) => s.flags);
  return useMemo(() => {
    const now = simTime ? Date.parse(simTime) : 0;
    const recent = (ts: string | null | undefined) => !!ts && now - Date.parse(ts) >= 0 && now - Date.parse(ts) <= RECENT_MIN * 60_000;
    const all: Happening[] = [];
    let outageUntil: string | null = null;
    let impostor: { claimed: string; price: number } | null = null;

    simEvents.forEach((e, i) => {
      if (Date.parse(e.start) > now || Date.parse(e.end) <= now) return;
      if (e.type === "outage") outageUntil = hhmm(e.end);
      all.push({ key: `ev${i}`, house: e.house, label: `${LABEL[e.type] ?? e.type} until ${hhmm(e.end)}`,
        tone: TONE[e.type] ?? "info", scope: e.house ? "house" : e.type === "outage" ? "none" : "street" });
    });

    // The owner's OK: one chip per house, the latest approval's state.
    for (const h of HOUSES) {
      const a = [...approvals].reverse().find((x) => x.house === h) as (typeof approvals[number] & { decided_at?: string | null }) | undefined;
      if (!a) continue;
      if (a.status === "pending") all.push({ key: `ok${h}`, house: h, tone: "info", scope: "house", label: "Asking the owner…" });
      else if (recent(a.decided_at ?? a.created_at)) {
        all.push({ key: `ok${h}`, house: h, scope: "house",
          tone: a.status === "approved" ? "ok" : "alert",
          label: a.status === "approved" ? "✓ Owner approved" : a.status === "declined" ? "✗ Owner declined" : "✗ Owner didn't answer" });
      }
    }

    // A deal that broke one of the owner's rules: one chip per house, the latest.
    for (const h of HOUSES) {
      const b = [...blocked].reverse().find((x) => x.house === h && x.owner_rule);
      if (b && recent(b.sim_time)) all.push({ key: `bl${h}`, house: h, tone: "alert", scope: "house", label: "✗ Outside the owner's rules" });
    }

    flags.forEach((f, i) => {
      if (!recent(f.ts)) return;
      if (f.kind === "impostor") {
        impostor = { claimed: String(f.detail?.claimed ?? ""), price: Number(f.detail?.price ?? 0) };
        all.push({ key: `fl${i}`, house: null, tone: "alert", scope: "none",
          label: `Impostor “House ${String(f.detail?.claimed ?? "").slice(1)}” at ₹${Number(f.detail?.price ?? 0).toFixed(2)} blacklisted` });
        return;
      }
      for (const h of f.houses ?? []) all.push({ key: `fl${i}${h}`, house: h as House, tone: "alert", scope: "house", label: String(f.title ?? "Guard flag") });
    });

    const byHouse = Object.fromEntries(HOUSES.map((h) => [h, all.filter((x) => x.house === h || x.scope === "street")])) as Record<House, Happening[]>;
    const dayOver = !!simTime && !running && hhmm(simTime) >= "19:00";
    return { all, byHouse, outageUntil, dayOver, impostor };
  }, [simTime, running, simEvents, blocked, approvals, flags]);
}

export const TONE_CLASS: Record<Tone, string> = {
  cloud: "bg-[#e5e7eb] text-[#374151]",
  load: "bg-sky-soft text-sky",
  alert: "bg-alert text-white",
  ok: "bg-leaf text-white",
  info: "bg-white/90 text-ink-2",
};
