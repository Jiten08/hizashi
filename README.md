# Hizashi

Every home with rooftop solar gets an agent that forecasts, promises safely and haggles with neighbours' agents over A2A, inside limits the owner sets. Built by Team Enthos for Kodikon 6.0 on the KERC P2P Regulations 2024.

## Setup and run

Needs Python ≥ 3.12 and Node ≥ 20. Phones need only a browser.

```bash
python -m venv .venv && source .venv/bin/activate     # Windows: .venv\Scripts\activate
pip install -e ".[dev]"
python scripts/gen_keys.py && python scripts/seed.py
pytest
cd web && npm install && npm run build && cd ..        # street dashboard (laptop)
cd mobile && npm install && npm run build && cd ..     # owner phone app (PWA)
```

Run the demo:

```bash
python -X utf8 -m honcho start          # hub :8000 + the four house agents (+ an ngrok tunnel, see below)
```

- **Laptop:** http://localhost:8000/ is the street dashboard; `/console` has every control.
- **Phones:** on the dashboard click **Connect a phone** and scan a house with the phone's camera. It opens
  `…/app/?house=h14` in the browser. Add it to the Home Screen for a full-screen app. Any number of phones.
- The hub starts `ngrok http 8000` itself when ngrok is installed, so the QR codes work from any network
  (the first visit shows ngrok's notice once, tap **Visit Site**). `AUTO_NGROK=0` in `.env` turns it off;
  the QR codes then use the laptop's Wi-Fi address (allow Python through Windows Firewall on private networks).
- **Notifications** (Rules → Notifications, or the card on Approvals): the phone is pinged when its agent
  needs an OK, even locked, with Approve / Decline on Android. Browsers allow this only over https, so open
  the app through the ngrok link; on iPhone add it to the Home Screen first. The hub needs internet to reach
  the push services. Keys are made on first use in `keys/vapid.pem`.
- **Away / Guests** (Today → At home): the owner plans time away or guests for today or tomorrow, and the agent
  re-plans. Tomorrow's plans take effect when the console's **Start the next day** moves the sim on a date.
- Developing the phone app: `cd mobile && npm run dev` (http://localhost:5174/app/, proxies to the hub).

Copy `.env.example` to `.env` to change defaults (sim day, speed, tariff, tokens, API keys). No API keys are needed to run.

## Check it works

```bash
curl localhost:8000/api/state
curl localhost:8000/api/connect                     # what the phone QR codes carry
curl localhost:9012/.well-known/agent-card.json      # also 9014, 9016, 9018
```

A2A sample (two terminals): `python agent/examples/negotiation_sample.py serve`, then `python agent/examples/negotiation_sample.py ask`.

## Layout

`shared/` the contract (models, crypto, block time, config) · `hub/` market, wallet, settlement, sim, WebSocket gateway · `agent/` one A2A agent per house · `web/` desktop street dashboard (React) · `mobile/` the owner's phone app (PWA, served at /app/) · `scripts/` keys, seed, attack demos · `tests/`.

Spec: [docs/BUILD_SPEC.md](docs/BUILD_SPEC.md). Tasks and owners: [docs/TASKS.md](docs/TASKS.md). Rules for coding agents: [AGENTS.md](AGENTS.md).
