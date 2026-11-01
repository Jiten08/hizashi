// What is going on right now, for the screens to show the moment a console button is pressed:
// the active cloud / AC / guests / away / outage events, recent wallet refusals, price-fixing and
// guard flags. All read straight from hub events; nothing is computed here but "is it still on".
import { useMemo } from "react";
import { hhmm } from "./api";
import { HOUSES, type House } from "./types";
import { useHubStore } from "../store/hub";

export type Tone = "cloud" | "load" | "alert" | "info";
export interface Happening { key: string; house: House | null; label: string; tone: Tone }

const RECENT_MIN = 30;          // a wallet refusal or flag stays on screen this long (sim minutes)
const COLLUDE_MIN = 90;         // the collusion demo holds the price for six blocks
const LABEL: Record<string, string> = { cloud: "Cloud", ac: "AC on", guests: "Guests", away: "Away", outage: "Grid outage" };
const TONE: Record<string, Tone> = { cloud: "cloud", ac: "load", guests: "load", away: "load", outage: "alert" };

export function useHappening(): { all: Happening[]; byHouse: Record<House, Happening[]>; outageUntil: string | null; dayOver: boolean } {
  const simTime = useHubStore((s) => s.sim_time);
  const running = useHubStore((s) => s.running);
  const simEvents = useHubStore((s) => s.sim_events);
  const blocked = useHubStore((s) => s.blocked);
  const flags = useHubStore((s) => s.flags);
  const log = useHubStore((s) => s.log);
  return useMemo(() => {
    const now = simTime ? Date.parse(simTime) : 0;
    const recent = (ts: string | undefined, minutes: number) => !!ts && now - Date.parse(ts) >= 0 && now - Date.parse(ts) <= minutes * 60_000;
    const all: Happening[] = [];
    let outageUntil: string | null = null;
    simEvents.forEach((e, i) => {
      if (Date.parse(e.start) > now || Date.parse(e.end) <= now) return;
      if (e.type === "outage") outageUntil = hhmm(e.end);
      all.push({ key: `ev${i}`, house: e.house, label: `${LABEL[e.type] ?? e.type} until ${hhmm(e.end)}`, tone: TONE[e.type] ?? "info" });
    });
    blocked.forEach((b, i) => {
      if (!recent(b.sim_time, RECENT_MIN) || String(b.reason ?? "").startsWith("Grid outage")) return;
      const o = b.offer as { side?: string; price?: number } | undefined;
      all.push({ key: `bl${i}`, house: b.house as House, tone: "alert",
        label: o?.price != null ? `Wallet refused ₹${o.price.toFixed(2)} ${o.side ?? ""}`.trim() : "Wallet refused" });
    });
    log.forEach((e, i) => {
      if (e.type !== "console.command" || e.data?.cmd !== "collude" || !e.house || !recent(e.sim_time, COLLUDE_MIN)) return;
      all.push({ key: `co${i}`, house: e.house as House, tone: "alert", label: `Holding ₹${Number(e.data.price).toFixed(2)}` });
    });
    flags.forEach((f, i) => {
      if (!recent(f.ts, RECENT_MIN)) return;
      for (const h of f.houses ?? []) all.push({ key: `fl${i}${h}`, house: h as House, tone: "alert", label: String(f.title ?? "Guard flag") });
    });
    const byHouse = Object.fromEntries(HOUSES.map((h) => [h, all.filter((x) => x.house === h || x.house === null)])) as Record<House, Happening[]>;
    const dayOver = !!simTime && !running && hhmm(simTime) >= "19:00";
    return { all, byHouse, outageUntil, dayOver };
  }, [simTime, running, simEvents, blocked, flags, log]);
}

export const TONE_CLASS: Record<Tone, string> = {
  cloud: "bg-[#e5e7eb] text-[#374151]",
  load: "bg-sky-soft text-sky",
  alert: "bg-alert text-white",
  info: "bg-white/90 text-ink-2",
};
