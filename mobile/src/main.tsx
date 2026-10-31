import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import App from "./App";
import "./index.css";

// Only this app's own service worker (scope /app/) may stay; drop any left by older builds.
navigator.serviceWorker?.getRegistrations()
  .then((rs) => rs.filter((r) => !new URL(r.scope).pathname.startsWith("/app/")).forEach((r) => r.unregister()))
  .catch(() => {});

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <App />
  </StrictMode>,
);
