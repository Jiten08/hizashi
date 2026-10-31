# hub/ — market, wallet, settlement, sim, screens gateway

Run: `uvicorn hizashi_hub.app:app --port 8000`. API docs at http://localhost:8000/docs.

## Rules

- **Event bus:** publish through `bus.publish(Event(...))`, never write to sockets directly. `ws.py` fans events out by role; `state.py` keeps the snapshot for `GET /api/state`.
- **Wallet:** nothing outside `wallet/` touches private keys. Other modules ask `wallet.signer`; the market signs with `keys/market.key` through `wallet.keystore.market_key()`.
- Storage is plain `sqlite3` via `db.py` (no ORM). `scripts/seed.py` recreates `hub/hizashi.db`.
- Routes in `api/` stay thin: parse, call the module, return. Logic lives in `wallet/`, `market/`, `settlement/`, `guard/`.

## Module map

| Module | What |
| --- | --- |
| `app.py` | FastAPI app; startup loads street, DB, mandates, starts state + clock; serves `web/dist` with SPA fallback |
| `bus.py` | in-process async event bus: `publish(event)`, `subscribe() -> asyncio.Queue` |
| `ws.py` | `/ws?role=owner&house=h14 \| street \| console \| agent&house=h12&token=...` |
| `db.py` | schema + helpers |
| `clock.py` | simulated clock (1 tick = 1 sim minute, sleep 60/speed s), 05:00→19:00, `set_speed`, `reset`, publishes `clock.tick` and `block.state`; hooks `on_minute` (meters) and `on_block_state` (auction, settlement) |
| `state.py` | live snapshot |
| `api/` | REST routes (`state`, `wallet`, `approvals`, `market`, `ledger`, `guard`, `console`, `webhooks`) |
| `sim/` | `weather` (Open-Meteo + cache + clear-sky fallback), `pv`, `load`, `meters`, `events` |
| `wallet/` | `keystore`, `mandate`, `checks` (ordered, section 6.3), `approvals`, `signer` |
| `market/` | `registry`, `lifecycle`, `orderbook`, `auction` (KERC 4(b)), `booking` |
| `settlement/` | `settle` (KERC 8(g)), `savings`, `ledger` (hash chain) |
| `guard/` | `rules` |
| `notify/` | `twilio_wa` |
| `llm/` | `mandate_parser` (Gemini, Groq fallback) |

Block lifecycle (computed by `hizashi_shared.blocks.state_at`, published by the clock): `PLANNED` at day start → `OPEN` at max(05:00, T−120) → `GATE_CLOSED` at T−60 → `DELIVERING` at T → `SETTLED` at T+15.
