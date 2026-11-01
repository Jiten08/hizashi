import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import App from "./App";
import "./index.css";

// Only this app's own service worker (scope /app/) may stay; drop any left by older builds.
navigator.serviceWorker?.getRegistrations()
  .then((rs) => rs.filter((r) => !new URL(r.scope).pathname.startsWith("/app/")).forEach((r) => r.unregister()))
  .catch(() => {});

// Pick up a new build quickly: check for one whenever the app comes back to the front, and reload
// once when the new service worker takes over, so the phone never sits on an old version.
if (navigator.serviceWorker) {
  const check = () => navigator.serviceWorker.getRegistration("/app/").then((r) => r?.update()).catch(() => {});
  document.addEventListener("visibilitychange", () => { if (document.visibilityState === "visible") check(); });
  setInterval(check, 60_000);
  let had = !!navigator.serviceWorker.controller;
  navigator.serviceWorker.addEventListener("controllerchange", () => {
    if (had) location.reload();
    had = true;
  });
}

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <App />
  </StrictMode>,
);
