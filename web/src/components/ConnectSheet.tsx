// "Connect a phone": one QR per house; each is a link to the phone app for that house (/app/?house=h14).
import { QRCodeSVG } from "qrcode.react";
import { useEffect, useState } from "react";
import { api } from "../lib/api";
import { Icon } from "./ui";

type ConnectInfo = Awaited<ReturnType<typeof api.connect>>;

export function ConnectSheet({ onClose }: { onClose: () => void }) {
  const [info, setInfo] = useState<ConnectInfo | null>(null);
  useEffect(() => {
    const load = () => api.connect().then(setInfo).catch(() => {});
    load();
    const t = setInterval(load, 5000);           // picks the tunnel up as soon as ngrok starts
    return () => clearInterval(t);
  }, []);
  const local = ["localhost", "127.0.0.1"].includes(location.hostname);
  const hub = info?.hub ?? (local ? null : location.origin);
  const link = (house: string) => `${hub}/app/?house=${house}`;

  return (
    <div className="fixed inset-0 z-40 flex items-center justify-center bg-black/25 p-6 backdrop-blur-sm" onClick={onClose}>
      <div className="rise card w-full max-w-4xl p-7" onClick={(e) => e.stopPropagation()}>
        <div className="flex items-start justify-between">
          <div>
            <h2 className="text-2xl font-semibold tracking-tight">Connect a phone</h2>
            <p className="mt-1 text-[15px] text-ink-2">Point the phone's camera at a house. Hizashi opens in the browser, no install needed.</p>
          </div>
          <button onClick={onClose} className="rounded-full bg-fill p-2 text-ink-2 hover:text-ink" aria-label="Close"><Icon name="close" className="h-4 w-4" /></button>
        </div>

        {hub ? (
          <>
            <div className="mt-6 grid grid-cols-4 gap-4">
              {(info?.houses ?? []).map((h) => (
                <div key={h.house} className="flex flex-col items-center rounded-2xl bg-canvas p-4">
                  <QRCodeSVG value={link(h.house)} size={168} fgColor="#1d1d1f" bgColor="transparent" />
                  <p className="mt-3 font-semibold">{h.label}</p>
                </div>
              ))}
            </div>
            <p className="mt-5 text-[13px] text-ink-2">Phones reach the hub at <span className="font-mono text-ink">{hub}</span>{hub.startsWith("http://") ? " (same Wi-Fi only)" : ""}</p>
          </>
        ) : (
          <div className="mt-6 rounded-2xl bg-sun-soft p-5 text-[15px] text-sun-ink">
            <p className="font-semibold">This laptop isn't on a network phones can reach.</p>
            <p className="mt-1">Join the same Wi-Fi as the phones, or run <span className="font-mono">ngrok http 8000</span>. The codes appear here by themselves.</p>
          </div>
        )}

        <ol className="mt-6 grid grid-cols-3 gap-4 text-[13px] text-ink-2">
          <li className="rounded-2xl bg-canvas p-4"><b className="block text-ink">1 · Scan</b>With the normal camera app. Any number of phones, one house each.</li>
          <li className="rounded-2xl bg-canvas p-4"><b className="block text-ink">2 · Set up</b>The first visit walks the owner through solar, subsidy and limits.</li>
          <li className="rounded-2xl bg-canvas p-4"><b className="block text-ink">3 · Add to Home Screen</b>Safari: Share → Add to Home Screen. Chrome: menu → Install app.</li>
        </ol>
      </div>
    </div>
  );
}
