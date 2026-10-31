// "Connect a phone": one QR per house for the Hizashi phone app (it scans {"hub", "house"}).
import { QRCodeSVG } from "qrcode.react";
import { useEffect, useState } from "react";
import { api } from "../lib/api";
import type { House } from "../lib/types";
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

  return (
    <div className="fixed inset-0 z-40 flex items-center justify-center bg-black/25 p-6 backdrop-blur-sm" onClick={onClose}>
      <div className="rise card w-full max-w-4xl p-7" onClick={(e) => e.stopPropagation()}>
        <div className="flex items-start justify-between">
          <div>
            <h2 className="text-2xl font-semibold tracking-tight">Connect a phone</h2>
            <p className="mt-1 text-[15px] text-ink-2">Open the Hizashi app, tap <b className="text-ink">Scan house code</b>, and point it at a house.</p>
          </div>
          <button onClick={onClose} className="rounded-full bg-fill p-2 text-ink-2 hover:text-ink" aria-label="Close"><Icon name="close" className="h-4 w-4" /></button>
        </div>

        {hub ? (
          <>
            <div className="mt-6 grid grid-cols-4 gap-4">
              {(info?.houses ?? []).map((h) => (
                <div key={h.house} className="flex flex-col items-center rounded-2xl bg-canvas p-4">
                  <QRCodeSVG value={JSON.stringify({ hub, house: h.house as House })} size={168} fgColor="#1d1d1f" bgColor="transparent" />
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
          <li className="rounded-2xl bg-canvas p-4"><b className="block text-ink">1 · Get Expo Go</b>Free from the App Store or Play Store.</li>
          <li className="rounded-2xl bg-canvas p-4"><b className="block text-ink">2 · Open the app</b>Scan the Expo code printed by <span className="font-mono">npx expo start</span> in <span className="font-mono">mobile/</span> (same Wi-Fi).</li>
          <li className="rounded-2xl bg-canvas p-4"><b className="block text-ink">3 · Pick your house</b>In Hizashi, scan one of the codes above.</li>
        </ol>
      </div>
    </div>
  );
}
