# Tasks

Fill in the Owner column when you take a task. Stubs in the code say `TODO(<task id>, <folder owner>)`. Paths are relative to `hub/hizashi_hub/`, `agent/hizashi_agent/`, `shared/hizashi_shared/` or the repo root as shown.

## Phase 0 — scaffold (Review 0)

| ID | Task | Files | Owner | Status |
| --- | --- | --- | --- | --- |
| R0.1 | Repo tree, pyproject, env, Procfiles, README, AGENTS.md, TASKS.md | all of section 2 | Jiten | done |
| R0.2 | Shared contract | `shared/hizashi_shared/*` | Jiten | done |
| R0.3 | Keys + seed scripts | `scripts/gen_keys.py`, `scripts/seed.py` | Jiten | done |
| R0.4 | Hub core: app, bus, ws, state, db schema, clock, `/api/state`, console speed/reset | `app.py`, `bus.py`, `ws.py`, `state.py`, `db.py`, `clock.py`, `api/state.py`, `api/console.py` | Jiten | done |
| R0.5 | Agent skeleton: A2A sample, card, server, refusing executor, hub WS client | `agent/examples/negotiation_sample.py`, `__main__.py`, `card.py`, `server.py`, `executor.py`, `hub_client.py` | Jiten | done |
| R0.6 | Web shell: routes, useHub, store, Landing + QR, Owner clock/blocks, Console | `web/` | Jiten | done |
| R0.7 | Tests: crypto, blocks, negotiator (deck numbers) | `tests/test_crypto.py`, `tests/test_blocks.py`, `tests/test_negotiator.py`, `agent/.../negotiator.py` | Jiten | done |

## Phase 1 — two phones haggle (Review 1, Sat 2:30 PM)

| ID | Task | Files | Owner | Status |
| --- | --- | --- | --- | --- |
| R1.1 | Wallet sign endpoint with checks 1–6 | `wallet/checks.py`, `wallet/signer.py`, `wallet/keystore.py`, `wallet/mandate.py`, `api/wallet.py`, `tests/test_wallet_checks.py` | | done |
| R1.2 | Weather fetch + cache (+ clear-sky fallback), `GET /api/weather` | `sim/weather.py`, `api/state.py`, `app.py` | | done |
| R1.3 | Forecaster (`solar.py`, profiles) | `agent/.../forecaster.py`, `shared/.../solar.py`, `shared/.../profiles.py`, `agent/.../hub_client.py` | | done |
| R1.4 | Planner (intents + plan windows) | `agent/.../planner.py`, `agent/.../hub_client.py` | | done |
| R1.5 | Negotiator over A2A (protocol 7.3) | `agent/.../a2a_client.py`, `agent/.../executor.py`, `agent/.../runtime.py`, `agent/.../negotiator.py` | | done |
| R1.6 | Contract signing + booking | `wallet/checks.py`, `wallet/signer.py`, `market/booking.py`, `market/registry.py`, `api/market.py`, `agent/.../hub_client.py` | | done |
| R1.7 | Owner Home: haggle feed, live block card, solar/use | `web/src/pages/Owner.tsx`, `web/src/components/HaggleFeed.tsx`, `BlockCard.tsx`, `web/src/store/hub.ts` | | done |

## Phase 2 — a full day runs (Review 2, Sat 8:30 PM)

| ID | Task | Files | Owner | Status |
| --- | --- | --- | --- | --- |
| R2.1 | Gate-closure auction (per transformer, then open access) + market orders | `market/auction.py`, `market/orderbook.py`, `market/lifecycle.py`, `api/market.py`, `tests/test_auction.py` | | done |
| R2.2 | Signed meters (pv + load sim, per-block totals) | `sim/meters.py`, `sim/pv.py`, `sim/load.py`, `wallet/keystore.py`, `clock.py` hook | | done |
| R2.3 | Settlement + savings | `settlement/settle.py`, `settlement/savings.py`, `tests/test_settlement.py` | | done |
| R2.4 | Ledger + verify | `settlement/ledger.py`, `api/ledger.py`, `tests/test_ledger.py` | | done |
| R2.5 | Plan/offer approvals (wallet checks 7–8) + Approve card | `wallet/approvals.py`, `wallet/checks.py`, `api/wallet.py`, `api/approvals.py`, `web/src/components/ApprovalCard.tsx` | | done |
| R2.6 | 2D street | `web/src/pages/Street.tsx`, `web/src/components/HouseSvg.tsx` | | done |
| R2.7 | Console events (cloud, AC, speed, reset) with sim reacting | `sim/events.py`, `api/console.py`, `web/src/pages/Console.tsx` | | done |
| R2.8 | Savings + history screens, mandate GET/PUT | `web/src/pages/Owner.tsx`, `web/src/components/SavingsCard.tsx`, `api/wallet.py`, `wallet/mandate.py` | | done |
| R2.9 | `bad_bid` blocked and shown | `agent/.../runtime.py`, `wallet/checks.py`, `web/src/components/BlockedCard.tsx`, `scripts/attack_bad_bid.py` | | done |
| R2.10 | Full day end to end at 300× | all | | done |

## Phase 3 — overnight polish (freeze 6 AM)

| ID | Task | Files | Owner |
| --- | --- | --- | --- |
| N1 | WhatsApp approvals | `notify/twilio_wa.py`, `api/webhooks.py` | |
| N2 | Guard rules | `guard/rules.py`, `api/guard.py`, `market/booking.py` | |
| N3 | Attack scripts | `scripts/attack_fake_seller.py`, `scripts/attack_collusion.py` | |
| N4 | Mandate parser + Rules screen | `llm/mandate_parser.py`, `api/wallet.py`, `web/src/pages/Owner.tsx` | |
| N5 | Outage handling | `sim/events.py`, `sim/meters.py`, `clock.py`, `settlement/settle.py` | |
| N6 | Mid-day correction | `agent/.../forecaster.py`, `agent/.../planner.py`, `agent/.../runtime.py` | |
| N7 | Away / Guests | `sim/load.py`, `agent/.../forecaster.py`, `web/src/pages/Owner.tsx` | |
| N8 | 3D street | `web/src/pages/Street3D.tsx` | |
| N9 | Backup video (manual) | — | |
| N10 | Stage deck (manual) | — | |
