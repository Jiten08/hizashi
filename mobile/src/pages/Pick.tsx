// No house yet (opened without a QR link): pick one. Normally the dashboard's QR does this.
import { useEffect, useState } from "react";
import { IconTile } from "../components/ui";
import { api } from "../lib/api";
import type { House, HouseInfo } from "../lib/types";

const HOUSES: House[] = ["h12", "h14", "h16", "h18"];

export default function Pick({ onPick }: { onPick: (h: House) => void }) {
  const [info, setInfo] = useState<Partial<Record<House, HouseInfo>>>({});
  useEffect(() => { api.state().then((s) => setInfo(s.houses)).catch(() => {}); }, []);
  return (
    <main className="mx-auto flex min-h-dvh max-w-[560px] flex-col px-4 pt-[calc(56px+env(safe-area-inset-top))]">
      <div className="flex flex-col items-center text-center">
        <img src="/app/icon-192.png" alt="" className="h-[84px] w-[84px] rounded-[20px] shadow-[0_8px_20px_rgba(255,149,0,0.35)]" />
        <h1 className="t-large mt-4">Hizashi</h1>
        <p className="t-subhead mt-1.5 px-3">Your home's energy agent. Sells spare rooftop power to neighbours, inside limits you set.</p>
      </div>
      <h2 className="t-section mb-[7px] ml-4 mt-9">Which home is this phone for?</h2>
      <div className="overflow-hidden rounded-xl bg-card">
        {HOUSES.map((h, i) => {
          const hi = info[h];
          return (
            <button key={h} onClick={() => onPick(h)} className="flex w-full items-center pl-4 text-left active:bg-[#e5e5ea]">
              <span className="mr-3"><IconTile name={hi && !hi.roof ? "home" : "sun"} bg={hi && !hi.roof ? "var(--color-blue)" : "var(--color-orange)"} /></span>
              <span className={`flex flex-1 items-center py-2.5 pr-4 ${i < HOUSES.length - 1 ? "hairline" : ""}`}>
                <span className="flex-1">
                  <span className="t-body block">{hi?.label ?? `House ${h.slice(1)}`}</span>
                  {hi ? <span className="t-footnote block">{hi.roof ? `${hi.roof.kwp} kWp rooftop solar${hi.subsidized ? " · PM Surya Ghar" : ""}` : "No solar, buys from neighbours"}</span> : null}
                </span>
              </span>
            </button>
          );
        })}
      </div>
      <p className="t-footnote mx-4 mt-2">Tip: scan a house's code on the street dashboard to open it directly.</p>
    </main>
  );
}
