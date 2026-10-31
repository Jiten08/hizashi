// Web Push for approvals, imported by the generated service worker (vite.config.ts importScripts).
// The hub sends {title, body, tag, url, approval_id?, quiet?}. A pending approval gets Approve /
// Decline buttons (Android; iPhone shows none, a tap opens the app); its outcome later replaces
// it quietly under the same tag.
const HEADERS = { "Content-Type": "application/json", "ngrok-skip-browser-warning": "1" };

self.addEventListener("push", (event) => {
  let d = {};
  try { d = event.data ? event.data.json() : {}; } catch { d = { body: event.data ? event.data.text() : "" }; }
  const options = {
    body: d.body || "",
    tag: d.tag || "hizashi",
    data: d,
    icon: "/app/icon-192.png",
    badge: "/app/icon-192.png",
    renotify: !d.quiet,
    silent: !!d.quiet,
    requireInteraction: !!d.approval_id,
  };
  if (d.approval_id) {
    options.actions = [{ action: "approve", title: "Approve" }, { action: "decline", title: "Decline" }];
    options.vibrate = [80, 40, 80];
  }
  event.waitUntil(self.registration.showNotification(d.title || "Hizashi", options));
});

self.addEventListener("notificationclick", (event) => {
  const n = event.notification;
  const d = n.data || {};
  n.close();
  if (d.approval_id && (event.action === "approve" || event.action === "decline")) {
    event.waitUntil(decide(d, event.action));
  } else {
    event.waitUntil(openApp(d.url || "/app/"));
  }
});

async function decide(d, decision) {
  let title, body;
  try {
    const r = await fetch(`/api/approvals/${d.approval_id}`, {
      method: "POST", headers: HEADERS, body: JSON.stringify({ decision, channel: "app" }),
    });
    if (r.ok) {
      title = decision === "approve" ? "Approved" : "Declined";
      body = d.body;
    } else {
      title = "Not changed";
      body = (await r.json().catch(() => ({}))).detail || `The hub said ${r.status}.`;
    }
  } catch {
    title = "Couldn't reach your street";
    body = "Open Hizashi to answer.";
  }
  await self.registration.showNotification(title, {
    body, tag: d.tag, data: { url: d.url }, icon: "/app/icon-192.png", badge: "/app/icon-192.png", silent: true,
  });
}

async function openApp(url) {
  const wins = await self.clients.matchAll({ type: "window", includeUncontrolled: true });
  for (const w of wins) {
    if (new URL(w.url).pathname.startsWith("/app/")) {
      await w.focus();
      w.postMessage({ type: "open", url });
      return;
    }
  }
  await self.clients.openWindow(url);
}
