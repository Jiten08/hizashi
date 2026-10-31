# Hizashi

Every home with rooftop solar gets an agent that forecasts, promises safely and haggles with neighbours' agents over A2A, inside limits the owner sets. Built by Team Enthos for Kodikon 6.0 on the KERC P2P Regulations 2024.

## Setup and run

Needs Python ≥ 3.12, Node ≥ 20, and on the phone the free **Expo Go** app.

```bash
python -m venv .venv && source .venv/bin/activate     # Windows: .venv\Scripts\activate
pip install -e ".[dev]"
python scripts/gen_keys.py && python scripts/seed.py
pytest
cd web && npm install && npm run build && cd ..
cd mobile && npm install && cd ..
```

Three terminals for the demo:

```bash
python -X utf8 -m honcho start          # 1. hub :8000 + the four house agents
ngrok http 8000                         # 2. phones reach the hub (the hub detects the URL itself)
cd mobile && npx expo start --tunnel ngrok   # 3. phone app: scan its QR with Expo Go
```

- **Laptop:** http://localhost:8000/ is the street dashboard (desktop demo); `/console` has every control.
- **Phone:** in the Hizashi app tap **Scan house code** and scan a house on the dashboard's **Connect a phone**.
- Same Wi-Fi only? Skip ngrok and `--tunnel`, open the dashboard via the laptop's IP (http://192.168.x.x:8000).

Copy `.env.example` to `.env` to change defaults (sim day, speed, tariff, tokens, API keys). No API keys are needed to run.

## Check it works

```bash
curl localhost:8000/api/state
curl localhost:8000/api/connect                     # what the phone QR codes carry
curl localhost:9012/.well-known/agent-card.json      # also 9014, 9016, 9018
```

A2A sample (two terminals): `python agent/examples/negotiation_sample.py serve`, then `python agent/examples/negotiation_sample.py ask`.

## Layout

`shared/` the contract (models, crypto, block time, config) · `hub/` market, wallet, settlement, sim, WebSocket gateway · `agent/` one A2A agent per house · `web/` desktop street dashboard (React) · `mobile/` the owner's phone app (Expo / React Native) · `scripts/` keys, seed, attack demos · `tests/`.

Spec: [docs/BUILD_SPEC.md](docs/BUILD_SPEC.md). Tasks and owners: [docs/TASKS.md](docs/TASKS.md). Rules for coding agents: [AGENTS.md](AGENTS.md).
