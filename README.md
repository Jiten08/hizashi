# Hizashi

Every home with rooftop solar gets an agent that forecasts, promises safely and haggles with neighbours' agents over A2A, inside limits the owner sets. Built by Team Enthos for Kodikon 6.0 on the KERC P2P Regulations 2024.

## Setup and run

Needs Python ≥ 3.12 and Node ≥ 20.

```bash
python -m venv .venv && source .venv/bin/activate     # Windows: .venv\Scripts\activate
pip install -e ".[dev]"
python scripts/gen_keys.py && python scripts/seed.py
pytest
cd web && npm install && npm run build && cd ..
honcho start                      # hub :8000 + agents :9012 :9014 :9016 :9018
# demo with phones: honcho -f Procfile.demo start  (needs cloudflared)
# frontend dev: cd web && npm run dev  (http://localhost:5173)
```

Copy `.env.example` to `.env` to change defaults (sim day, speed, tariff, tokens, API keys).

## Check it works

```bash
curl localhost:8000/api/state
curl localhost:9012/.well-known/agent-card.json      # also 9014, 9016, 9018
```

- http://localhost:8000/ — landing page with QR codes for the phones
- http://localhost:8000/h/h12 — owner app (sim clock + block states live)
- http://localhost:8000/console — speed 1/60/300, reset, raw event log
- http://localhost:8000/docs — hub API

A2A sample (two terminals): `python agent/examples/negotiation_sample.py serve`, then `python agent/examples/negotiation_sample.py ask`.

## Layout

`shared/` the contract (models, crypto, block time, config) · `hub/` market, wallet, settlement, sim, WebSocket gateway · `agent/` one A2A agent per house · `web/` React PWA · `scripts/` keys, seed, attack demos · `tests/`.

Spec: [docs/BUILD_SPEC.md](docs/BUILD_SPEC.md). Tasks and owners: [docs/TASKS.md](docs/TASKS.md). Rules for coding agents: [AGENTS.md](AGENTS.md).
