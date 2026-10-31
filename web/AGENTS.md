# web/ — one React PWA (Vite + TS + Tailwind v4 + Zustand)

Run: `npm install`, then `npm run dev` (http://localhost:5173, proxies `/api` and `/ws` to the hub on :8000) or `npm run build` (the hub serves `web/dist` at http://localhost:8000).

## Display-only rule

**Screens only display hub events and send taps; they never compute prices, savings or settlements.** If a number isn't in an event or the snapshot, ask for it to be added in the hub.

## The useHub pattern

`useHub(role, house?)` in `src/hooks/useHub.ts`: `GET /api/state` into the Zustand store → open `/ws?role=...` → `store.apply(event)` → on close wait 1 s and start over. Each event type has one reducer in `src/store/hub.ts`; add a reducer there instead of handling events inside components. Types mirror the Python models in `src/lib/types.ts`; keep them in sync with `shared/hizashi_shared/models.py`.

## Screens

- `/` Landing: house buttons, Street, Console, QR codes for `PUBLIC_URL/h/h12` and `/h/h14`.
- `/h/:house` Owner app, **mobile-first**, bottom tabs Home / Approvals / Rules / History.
- `/street` laptop SVG street; `/street/3d` (Phase 3); `/console` demo controls + raw event log.

## Look and phrasing

Clean, light background, amber accent `#d98a04` (`bg-sun`, `text-sun`), large numbers, ₹ everywhere. Copy the deck's phrasing:

- "Saved today vs BESCOM ₹X" and "≈ ₹Y this year if every day were like today"
- Haggle feed: "Ask ₹5.40 → Bid ₹4.00 → … → Deal 0.20 kWh at ₹4.68"
- Red card: "BLOCKED · Tried to buy at ₹40/unit. Your max is ₹5.50, so it was never sent."
- Amber card: "NEEDS YOUR OK" — "Buy 2.4 kWh from neighbours, 10:00–13:00, for about ₹11.23?" with Decline / Approve
