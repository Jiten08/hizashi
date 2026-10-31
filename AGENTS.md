# Hizashi — rules for every coding agent

Hizashi is Team Enthos's Kodikon 6.0 build. Karnataka's KERC P2P Regulations 2024 let a home with rooftop solar sell spare power to a neighbour at an agreed price, but each 15-minute block needs a promise made an hour ahead, with penalties if a cloud breaks it. Hizashi gives **every home an agent** that forecasts, promises safely and **haggles with neighbours' agents over A2A**, inside limits the owner sets. A **Mandate Wallet** in the hub holds each home's signing key and refuses anything outside the owner's limits. The hub runs the market, settles each block under KERC 8(g), keeps a hash-chained ledger and shows each owner **"saved vs BESCOM"**. Demo: one laptop, a simulated street of 4 houses (h12, h14, h16, h18), two phones. The LLM is used **only** to turn the owner's sentence into wallet rules; trading is plain Python.

Full spec: `docs/BUILD_SPEC.md`. Task list: `docs/TASKS.md`.

## Who are you?

**At the start of a session, if the user hasn't said who they are, ask.** Only edit files in folders they own (table below). **To change anything in `shared/`, stop and ask Jiten.**

| Folder | Owner | Lane |
| --- | --- | --- |
| `shared/hizashi_shared/` (except `crypto.py`, `solar.py`, `profiles.py`) | Jiten | architect |
| `hub/hizashi_hub/wallet/`, `settlement/`, `guard/`, `llm/` | Jiten | trust |
| `agent/`, `hub/hizashi_hub/market/`, `clock.py`, `sim/weather.py`, `sim/pv.py`, `sim/load.py`, `sim/events.py`, `shared/.../solar.py`, `shared/.../profiles.py` | Anurag | market & agents |
| `shared/.../crypto.py`, `hub/hizashi_hub/sim/meters.py`, `notify/`, `scripts/` | Prajval | identity & alerts |
| `web/`, `hub/hizashi_hub/api/`, `ws.py`, `bus.py`, `db.py`, `state.py`, `app.py` | Tezash | screens & integration |

Stubs say who fills them: `raise NotImplementedError("TODO(<task id>, <owner>)")`. Do only the task you were asked for.

## Run

```bash
python -m venv .venv && source .venv/bin/activate     # Windows: .venv\Scripts\activate
pip install -e ".[dev]"
python scripts/gen_keys.py && python scripts/seed.py
pytest
cd web && npm install && npm run build && cd ..
honcho start                      # hub :8000 + agents :9012 :9014 :9016 :9018
```

- Hub: `uvicorn hizashi_hub.app:app --port 8000`. One agent: `python -m hizashi_agent --house h12 --port 9012`.
- Frontend dev: `cd web && npm run dev` (http://localhost:5173, proxies `/api` and `/ws` to :8000).
- Demo with phones: `honcho -f Procfile.demo start` (needs `cloudflared`; set `PUBLIC_URL` in `.env`).

## Test

`pytest` from the repo root. Anything with arithmetic or crypto gets a test. Run tests before you report. Tests for later tasks exist with `pytest.mark.skip(reason="TODO(<task>)")` and the expected numbers already written: remove the skip when you implement the task.

## A2A (read before writing any A2A code)

- Pinned: `a2a-sdk[http-server]==1.2.1`. Most examples online are for 0.3 and will not run.
- Read `agent/examples/negotiation_sample.py` first; it is verified. Copy its imports and patterns.
- Executors **must enqueue a `Task` before any status update** (`new_task(...)` when `context.current_task is None`).
- A2A data parts are protobuf `Value`s: ints come back as floats (`round: 1` → `1.0`). **Re-parse payloads with `Offer.model_validate` / `Contract.model_validate` before verifying signatures**, never verify a raw dict.

## Units and conventions

- Energy: kWh per block. Prices: ₹ per kWh. Money: ₹, round to 2 decimals for display only.
- Time: simulated IST (`Asia/Kolkata`), ISO strings. Block = `day` + `index` 0–95 (48 = 12:00–12:15). Key `"2026-10-31#48"`. Tradable blocks 26–70 (06:30–17:45, when the roofs produce).
- Houses: `"h12" | "h14" | "h16" | "h18"`.
- Hub modules publish through `bus.publish(Event)`; never write to sockets directly.
- Agents never hold private keys; they ask the wallet (`POST /api/wallet/{house}/sign`).
- **Never compute prices, savings or settlements in `web/`.** Screens display hub events and send taps.

## Git

- `git pull --rebase` before every push. Commit only your folders.
- Never commit `keys/`, `.env`, `*.db`.
