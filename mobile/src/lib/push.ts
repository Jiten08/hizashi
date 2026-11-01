// Approval notifications through Web Push: they arrive with the app closed or the phone locked.
// Browsers allow it only on a secure origin (the ngrok https link, or localhost), and an iPhone
// only once the app is on the Home Screen.
import { useCallback, useEffect, useState } from "react";
import { api } from "./api";
import type { House } from "./types";

export type PushStatus = "checking" | "needs-https" | "needs-install" | "unsupported" | "denied" | "off" | "on";

const isIos = () => /iPad|iPhone|iPod/.test(navigator.userAgent) || (navigator.platform === "MacIntel" && navigator.maxTouchPoints > 1);
const standalone = () => matchMedia("(display-mode: standalone)").matches || (navigator as { standalone?: boolean }).standalone === true;

async function registration(): Promise<ServiceWorkerRegistration | null> {
  if (!("serviceWorker" in navigator)) return null;
  // `ready` never settles without a service worker (vite dev server).
  return Promise.race([navigator.serviceWorker.ready, new Promise<null>((r) => setTimeout(() => r(null), 4000))]);
}

function keyBytes(b64: string): Uint8Array<ArrayBuffer> {
  const s = atob((b64 + "=".repeat((4 - (b64.length % 4)) % 4)).replace(/-/g, "+").replace(/_/g, "/"));
  return Uint8Array.from(s, (c) => c.charCodeAt(0));
}

async function status(): Promise<PushStatus> {
  if (!isSecureContext) return "needs-https";
  if (isIos() && !standalone()) return "needs-install";
  if (!("PushManager" in window) || !("Notification" in window)) return "unsupported";
  if (Notification.permission === "denied") return "denied";
  const reg = await registration();
  if (!reg) return "unsupported";
  return (await reg.pushManager.getSubscription()) && Notification.permission === "granted" ? "on" : "off";
}

/** Ask permission (call from a tap), subscribe, and tell the hub which house this phone is for. */
async function enable(house: House): Promise<PushStatus> {
  if ((await Notification.requestPermission()) !== "granted") return Notification.permission === "denied" ? "denied" : "off";
  const reg = await registration();
  if (!reg) return "unsupported";
  const { key } = await api.pushKey();
  let sub = await reg.pushManager.getSubscription();
  // A subscription made with another hub's key can't be reused.
  const current = sub?.options.applicationServerKey;
  if (sub && current && btoa(String.fromCharCode(...new Uint8Array(current))).replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/, "") !== key) {
    await sub.unsubscribe();
    sub = null;
  }
  sub ??= await reg.pushManager.subscribe({ userVisibleOnly: true, applicationServerKey: keyBytes(key) });
  await api.pushSubscribe(house, sub.toJSON());
  return "on";
}

async function disable(house: House): Promise<PushStatus> {
  const sub = await (await registration())?.pushManager.getSubscription();
  if (sub) {
    await api.pushUnsubscribe(house, sub.endpoint).catch(() => {});
    await sub.unsubscribe();
  }
  return "off";
}

/** On app start: re-register an existing subscription for this house (the hub's DB may be new). */
export async function syncPush(house: House): Promise<void> {
  try {
    if ((await status()) !== "on") return;
    await enable(house);
  } catch { /* offline: next start */ }
}

/** The hub decided an approval: drop its notification from the lock screen. */
export function closeNotification(tag: string) {
  registration().then((reg) => reg?.getNotifications({ tag })).then((ns) => ns?.forEach((n) => n.close())).catch(() => {});
}

export function usePush(house: House) {
  const [state, setState] = useState<PushStatus>("checking");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  useEffect(() => { status().then(setState).catch(() => setState("unsupported")); }, []);
  const run = useCallback(async (f: () => Promise<PushStatus | void>) => {
    setBusy(true);
    setError(null);
    try {
      const s = await f();
      if (s) setState(s);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }, []);
  return {
    status: state, busy, error,
    enable: () => run(() => enable(house)),
    disable: () => run(() => disable(house)),
    test: () => run(async () => { const r = await api.pushTest(house); if (!r.sent) throw new Error("No phone is signed up yet."); }),
  };
}

export const PUSH_HELP: Record<PushStatus, string> = {
  checking: "",
  "needs-https": "Notifications need the secure link. Open this app from the https (ngrok) address on the laptop's QR code.",
  "needs-install": "On iPhone: tap Share, then Add to Home Screen, and open Hizashi from there to turn notifications on.",
  unsupported: "This browser can't show notifications from web apps. Try Chrome on Android or Safari on iPhone.",
  denied: "Notifications are blocked for this site. Allow them in your browser's site settings, then come back.",
  off: "Get a notification when your agent needs your OK, even with the phone locked.",
  on: "Your agent's requests arrive here even when the phone is locked.",
};
