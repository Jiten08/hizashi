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

Two terminals for the demo (laptop and phones on the same Wi-Fi):

```bash
python -X utf8 -m honcho start          # 1. hub :8000 + the four house agents
cd mobile && npx expo start             # 2. phone app: every phone scans this QR with Expo Go
```

- **Laptop:** http://localhost:8000/ is the street dashboard (desktop demo); `/console` has every control.
- **Phones:** scan Expo's QR (iPhone: Camera app; Android: inside Expo Go). In Hizashi tap
  **Scan house code** and scan a house on the dashboard's **Connect a phone**. Any number of phones.
- First run on Windows: allow Python and Node through the firewall on **private** networks, and
  make sure the Wi-Fi is set to Private.
- Phones on another network (mobile data, a guest Wi-Fi that isolates devices)? Add tunnels:
  `ngrok http 8000` for the hub (detected by itself) and `npx expo start --tunnel ngrok` for the app.

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
