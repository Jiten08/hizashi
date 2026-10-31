// Display helpers only (no prices or savings are computed here).
export const rupees = (x: number) => `₹${x.toFixed(2)}`;
export const kwh = (x: number) => `${x.toFixed(x < 1 ? 2 : 1)} kWh`;

const pad = (n: number) => String(n).padStart(2, "0");
const hm = (minutes: number) => `${pad(Math.floor(minutes / 60))}:${pad(minutes % 60)}`;

export const blockLabel = (index: number) => `${hm(index * 15)}–${hm(index * 15 + 15)}`;
export const windowLabel = (first: number, last: number) => `${hm(first * 15)}–${hm(last * 15 + 15)}`;
export const blockIndex = (key: string) => Number(key.split("#")[1]);
export const houseName = (h?: string | null) => (h ? `House ${h.slice(1)}` : "");

/** "12:00" from an ISO sim time; the hub's time is IST and carries its offset. */
export function hhmm(iso?: string | null): string {
  const m = iso?.match(/T(\d\d):(\d\d)/);
  return m ? `${m[1]}:${m[2]}` : "--:--";
}
