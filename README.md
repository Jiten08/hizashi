# Hizashi

Every home with rooftop solar gets an AI agent that forecasts surplus, promises safely, and haggles with neighbours over peer-to-peer power trades — all inside limits the owner sets. Built by Team Enthos for Kodikon 6.0.

---

## The Problem

Bengaluru's rooftop solar owners can export surplus power, but BESCOM's buyback rate is ₹1.96–3.89/kWh while the retail tariff is ₹5.80/kWh. Neighbours need that power and would pay more, but no mechanism exists for them to trade directly. Manual coordination is impractical; existing platforms are not real-time and do not operate at the individual-block (15-minute) level.

## The Solution

Hizashi runs a local energy market every 15 minutes. Each house gets an autonomous AI agent. Sellers declare surplus; buyers declare need. Agents negotiate over Google's A2A protocol, the hub matches them and settles the trade, and owners see the outcome on their phone in real time.

**What makes it different:** every agent operates inside a cryptographically enforced mandate — a price floor/ceiling, a kWh cap, and a maximum round count — that the owner sets. No agent can trade outside its mandate, and every meter reading and contract is signed with Ed25519 keys so the ledger cannot be silently edited.

**One trade, start to finish:**

1. At 06:30 (block 26) House 12's solar forecast is 1.4 kWh for the next 15 minutes. The planner works out that 0.8 kWh is spare and safe to promise (stays above its low estimate).
2. Five minutes before the block opens the hub calls a sealed-bid auction. Agent h12 asks ₹4.40/kWh; agent h14 bids ₹4.55.
3. The negotiator runs up to 6 rounds of A2A message exchange. They agree at ₹4.47.
4. The hub writes a signed contract. At block start both meters measure delivery. At block end the ledger records: buyer paid ₹4.47 × 0.8 + ₹0.14 fee; seller received ₹4.47 × 0.8.
5. Both phone apps show the updated "saved today" figure. The street dashboard shows the animated trade arc.

---

## What You Will See in the Demo

**Street dashboard — `http://localhost:8000/`**

- Four houses on transformer T1, each showing live solar output (kW), load (kW), and savings today.
- An animated arc between houses while power is being delivered this block.
- Running totals: deals made, kWh shared, total saved vs BESCOM.
- Speed selector (1×, 60×, 300×) — change it any time.
- **Connect a phone** button — opens a QR sheet, one per house.
- **Controls** link — opens the full console.

**Controls page — `http://localhost:8000/console`**

| Button | What it does |
|---|---|
| Cloud over whole street | Dims all panels for 45 sim-minutes |
| Grid outage · 30 min | Marks outage blocks; no penalties applied |
| House 14 tries a ₹40 bid | Wallet rejects the bid before it reaches the market |
| Per-house: Cloud · 45 min | Dims one house's panel only |
| Per-house: AC on · 2 h | Increases that house's load |
| Per-house: Guests · 3 h | Increases load further |
| Per-house: Away · 4 h | Drops load to standby |
| Verify ledger | Re-hashes every entry; reports "Intact · N entries" or the row that broke |
| Reset the day (same seed) | Rewinds to 05:00, same random seed — result is reproducible |

**Owner phone app — `http://localhost:8000/app/`**

- Today screen: savings, kWh bought/sold, live solar and load gauges.
- Approvals screen: trades the agent flagged for owner sign-off (when a trade exceeds the automatic threshold).
- Rules screen: the owner's mandate (price range, kWh cap, approval threshold). "Rules from a sentence" is a planned Phase 3 feature — not yet built.
- History screen: past blocks with trade details.

---

## Architecture

```
Owners (phones)          Street screen (laptop/projector)
     │  WebSocket /ws?role=owner        │  WebSocket /ws?role=street
     └────────────────┬─────────────────┘
                      │
              ┌───────▼────────┐
              │   Hub :8000    │  FastAPI + uvicorn
              │                │  serves web/dist at /
              │  market        │  serves mobile/dist at /app/
              │  wallet        │  SQLite hizashi.db (WAL)
              │  settlement    │
              │  ledger        │
              │  simulator     │
              └────┬──┬──┬──┬──┘
                   │  │  │  │   A2A JSON-RPC (tasks/send)
        ┌──────────┘  │  │  └──────────┐
        │             │  │             │
   Agent h12    Agent h14  Agent h16   Agent h18
    :9012         :9014      :9016       :9018
```

### Components

| Component | What it is | Owns | Protocol | Port |
|---|---|---|---|---|
| Hub | FastAPI app | market, wallet, ledger, simulator, WebSocket gateway | HTTP + WebSocket | 8000 |
| Agent (×4) | Per-house FastAPI app | forecast, planner, negotiator | A2A JSON-RPC (HTTP) | 9012/9014/9016/9018 |
| Web | React SPA | street dashboard, console | Built to `web/dist`, served by hub at `/` | — |
| Mobile | React Native / Expo PWA | owner home screen, approvals, rules, history | Built to `mobile/dist`, served by hub at `/app/` | — |
| SQLite | Database | contracts, settlements, ledger hash-chain, approvals | File | — |

### Key Design Decisions

| Decision | Why |
|---|---|
| Ed25519 signing for every meter reading and contract | The ledger hash-chain cannot be silently edited; hub rejects unsigned or wrong-key readings |
| Mandate enforced at wallet layer before auction | Agent cannot commit more than the owner's cap or outside the owner's price range |
| Gate closes 4 blocks (60 min) before block start | Agents have enough wall time to negotiate; avoids last-second races |
| Uniform-price auction (pay-as-bid not used) | All trades in a block clear at the same price; simpler to explain and audit |
| `pvlib` Ineichen model + Open-Meteo weather | Physics-based forecast from real location and irradiance; falls back to clear-sky if network is off |
| SQLite WAL mode | Single-process multi-reader; no external database needed for the demo |
| Honcho Procfile | One command starts hub + all four agents; same on all OSes |

---

## Repository Map

```
hizashi/
├── shared/                 Shared contract layer — used by hub and all agents
│   └── hizashi_shared/
│       ├── config.py       All env vars, ports, tariffs, paths (single source of truth)
│       ├── models.py       Pydantic models: Mandate, Contract, Settlement, HouseInfo, …
│       ├── blocks.py       Block ↔ time arithmetic; TRADABLE = blocks 26–70 (06:30–17:45)
│       ├── crypto.py       Ed25519 sign / verify (PyNaCl)
│       └── solar.py        pvlib clear-sky + Open-Meteo / Google Weather fetch
├── hub/                    The central process — market, wallet, settlement, simulator
│   └── hizashi_hub/
│       ├── app.py          FastAPI lifespan, mounts web/dist and mobile/dist
│       ├── ws.py           WebSocket /ws (roles: owner, street, console, agent)
│       ├── bus.py          In-process asyncio event bus
│       ├── clock.py        SimClock — SIM_SPEED × acceleration, day start 05:00
│       ├── db.py           SQLite schema, init, WAL mode
│       ├── api/            REST endpoints
│       │   ├── state.py    GET /api/state — full hub snapshot for WebSocket clients
│       │   ├── wallet.py   PUT /{house}/mandate; POST /mandate/parse (stub, Phase 3)
│       │   ├── market.py   GET /api/market — open offers
│       │   ├── ledger.py   GET /api/ledger; GET /api/ledger/verify
│       │   ├── console.py  POST /api/console/speed, /reset, /events (cloud/outage/ac/…)
│       │   └── …           houses, approvals, guard
│       ├── market/
│       │   ├── lifecycle.py  Block state machine: OPEN → GATE_CLOSED → AUCTION → SETTLED
│       │   ├── booking.py    Offer registration
│       │   └── auction.py    Uniform-price clearing
│       ├── settlement/
│       │   ├── ledger.py     SHA-256 hash-chain ledger
│       │   ├── settle.py     Settlement engine
│       │   └── savings.py    "Saved vs BESCOM" calculation
│       ├── sim/              Physics-based day simulator
│       │   ├── world.py      Top-level Sim class; 300× headless loop
│       │   ├── meters.py     Ed25519-signed meter readings every sim-minute
│       │   ├── pv.py         PV output with ±5 % noise and cloud-factor dimming
│       │   ├── load.py       Household load profiles
│       │   ├── events.py     Cloud / outage / AC / guests / away / bad_bid events
│       │   └── weather.py    Loads cached weather; fetches Open-Meteo if missing
│       ├── wallet/
│       │   ├── checks.py     8 wallet checks: mandate present, price range, kWh cap, …
│       │   └── keystore.py   Loads meter, wallet, market keys from keys/
│       └── llm/
│           └── mandate_parser.py  Natural-language mandate parser (stub — Phase 3)
├── agent/                  One instance per house
│   └── hizashi_agent/
│       ├── server.py       FastAPI A2A app, lifespan, mounts hub WebSocket client
│       ├── executor.py     A2A task handler
│       ├── runtime.py      Main agent loop — receives hub events, calls planner
│       ├── planner.py      Solar forecast → kWh promise (never exceeds low estimate)
│       ├── negotiator.py   Concession-curve haggling, up to MAX_ROUNDS rounds
│       ├── hub_client.py   WebSocket client — reconnects on drop
│       └── card.py         A2A agent-card builder
├── web/                    Street dashboard and console (React + Vite)
│   ├── src/
│   │   ├── pages/
│   │   │   ├── Dashboard.tsx   Street view, house cards, trade arcs
│   │   │   └── Console.tsx     All demo controls, ledger verify
│   │   ├── components/         Activity, ConnectSheet, HouseSvg, ui primitives
│   │   ├── hooks/useHub.ts     WebSocket subscription, typed hub state
│   │   └── lib/api.ts          REST + WebSocket helpers
│   └── dist/                   Built output (run `npm run build` first)
├── mobile/                 Owner phone app (React Native / Expo SDK 58, PWA)
│   ├── src/app/
│   │   ├── (tabs)/
│   │   │   ├── today.tsx       Savings, kWh gauges, live solar/load
│   │   │   ├── approvals.tsx   Trades awaiting owner sign-off
│   │   │   ├── rules.tsx       Mandate display (edit = Phase 3)
│   │   │   └── history.tsx     Past blocks
│   │   ├── onboarding.tsx      First-run QR scan / manual URL entry
│   │   └── connect.tsx         Re-connect sheet
│   └── dist/                   Built output (run `npm run build` first)
├── data/
│   ├── street.json         House registry with public keys (written by gen_keys.py)
│   ├── weather/
│   │   └── 2026-10-31.json  Cached real-day weather (committed — works offline)
│   └── profiles/           Per-house load profiles
├── keys/                   Ed25519 seeds, one file per key (git-ignored)
├── scripts/
│   ├── gen_keys.py         Generate meter, wallet and market keys; write public keys to street.json
│   ├── seed.py             Populate street.json with house profiles and load shapes
│   ├── preflight.py        Pre-demo health check: Python/Node versions, keys, weather, hub, agents, wallet, WebSocket
│   ├── soak.py             Headless 300× soak test: 8 invariants across 6 weather scenarios and 2 seeds
│   ├── attack_bad_bid.py   Demo script: submits a ₹40 bid to show wallet rejection
│   ├── attack_collusion.py Demo script: collusion attempt
│   └── attack_fake_seller.py  Demo script: unsigned seller attempt
├── tests/                  Pytest suite (84 tests passing)
├── docs/
│   ├── BUILD_SPEC.md       Full technical specification
│   └── TASKS.md            Task tracker and owners
├── Procfile                honcho process definitions (hub + 4 agents)
├── Procfile.demo           Procfile + ngrok tunnel
├── pyproject.toml          Python dependencies and pytest config
├── .env.example            All environment variables with defaults (copy to .env)
├── cloudflared.exe         Cloudflare Tunnel binary for Windows (alternative to ngrok)
├── AGENTS.md               Coding-agent conventions for the whole repo
└── CLAUDE.md               Claude-specific project notes
```

---

## Setup

### Prerequisites

| Tool | Required version | Check |
|---|---|---|
| Python | ≥ 3.12 | `python --version` |
| Node.js | ≥ 20 (22 tested) | `node --version` |
| npm | bundled with Node | `npm --version` |
| Git | any | — |

No external accounts or API keys are needed to run the demo. See [`.env.example`](.env.example) for optional keys (Gemini, Groq, Twilio) that enable Phase 3 features not yet built.

### 1. Clone and create a virtual environment

```bash
git clone <repo-url>
cd hizashi

python -m venv .venv
# Windows:
.venv\Scripts\activate
# macOS / Linux:
source .venv/bin/activate
```

### 2. Install Python packages

```bash
# from hizashi/
pip install -e ".[dev]"
```

This installs `hizashi_shared`, `hizashi_hub`, and `hizashi_agent` as editable packages, plus `honcho`, `pytest`, and `pytest-asyncio`.

### 3. Generate keys and seed data

```bash
# from hizashi/
python scripts/gen_keys.py
python scripts/seed.py
```

`gen_keys.py` writes 9 Ed25519 seed files to `keys/` (git-ignored) and updates the public keys in `data/street.json`. It is idempotent — run with `--force` to regenerate all keys.

### 4. Configure environment variables

```bash
copy .env.example .env      # Windows
cp .env.example .env        # macOS / Linux
```

The defaults in `.env.example` work without editing. Key variables:

| Variable | Default | What it does |
|---|---|---|
| `SIM_DAY` | `2026-10-31` | The simulated date (weather cache already committed for this date) |
| `SIM_SPEED` | `60` | Simulation speed on startup (1×, 60×, or 300×) |
| `SIM_SEED` | `31` | Random seed — same seed gives same result |
| `RETAIL_ENERGY_CHARGE` | `5.80` | BESCOM retail rate ₹/kWh used for savings calculation |
| `FEE_PER_KWH` | `0.14` | Hub fee ₹/kWh (14 paise) added on top of agreed price |
| `EXPECTED_P2P_PRICE` | `4.68` | Mid-point agents aim for |
| `PUBLIC_URL` | _(empty)_ | Fixed public URL for phones; leave empty and the hub detects a running ngrok automatically |
| `AGENT_TOKEN_H12` … `H18` | `dev-h12` … | Tokens agents use to authenticate with the hub WebSocket |
| `PYTHONUTF8` | `1` | Required on Windows so honcho can print ₹ symbols correctly |

### 5. Build the frontends

```bash
# Street dashboard (from hizashi/web/)
cd web
npm install
npm run build
cd ..

# Owner phone app (from hizashi/mobile/)
cd mobile
npm install
npm run build
cd ..
```

Built output lands in `web/dist/` and `mobile/dist/`. The hub serves them statically.

### 6. Start everything

**Simplest — one command:**

```bash
# from hizashi/, with .venv active
python -X utf8 -m honcho start
```

This starts five processes defined in `Procfile`:

| Process | Command | Port |
|---|---|---|
| hub | `uvicorn hizashi_hub.app:app --host 0.0.0.0 --port 8000` | 8000 |
| h12 | `python -m hizashi_agent --house h12 --port 9012` | 9012 |
| h14 | `python -m hizashi_agent --house h14 --port 9014` | 9014 |
| h16 | `python -m hizashi_agent --house h16 --port 9016` | 9016 |
| h18 | `python -m hizashi_agent --house h18 --port 9018` | 9018 |

**With ngrok tunnel for phones on a different network:**

```bash
python -X utf8 -m honcho start -f Procfile.demo
```

This also starts `ngrok http 8000`. The hub detects the public URL automatically; no extra config needed.

**Alternatively, with Cloudflare Tunnel (Windows, no ngrok account needed):**

```bash
# terminal 1
python -X utf8 -m honcho start

# terminal 2
.\cloudflared.exe tunnel --url http://localhost:8000
```

**Individual components (separate terminals, from `hizashi/`):**

```bash
# Terminal 1 — hub
uvicorn hizashi_hub.app:app --host 0.0.0.0 --port 8000

# Terminal 2 — agents
python -m hizashi_agent --house h12 --port 9012
python -m hizashi_agent --house h14 --port 9014
python -m hizashi_agent --house h16 --port 9016
python -m hizashi_agent --house h18 --port 9018
```

### 7. Open the app

| URL | What it is |
|---|---|
| `http://localhost:8000/` | Street dashboard (laptop / projector) |
| `http://localhost:8000/console` | Demo controls |
| `http://localhost:8000/app/` | Owner phone app (open on phone browser) |
| `http://localhost:8000/api/state` | Raw hub state (JSON) |
| `http://localhost:9012/.well-known/agent-card.json` | Agent h12 A2A card |

**Connecting a phone:**

- **Same Wi-Fi as laptop:** Go to `http://<laptop-ip>:8000/` on the phone, or use the QR code from the dashboard. Windows Firewall must allow Python on private networks.
- **Different network / public Wi-Fi:** Use ngrok or cloudflared (see above). The hub exposes the tunnel URL via `/api/connect`; the QR code on the dashboard carries it automatically.
- Scan the house-specific QR code and the phone app opens pre-connected to that house.

### 8. Verify it works

```bash
# Hub responds
curl http://localhost:8000/api/state

# Agent cards respond
curl http://localhost:9012/.well-known/agent-card.json
curl http://localhost:9014/.well-known/agent-card.json
curl http://localhost:9016/.well-known/agent-card.json
curl http://localhost:9018/.well-known/agent-card.json

# Phone connect payload
curl http://localhost:8000/api/connect
```

Expected: all return JSON. `/api/state` includes `"clock"`, `"houses"`, `"contracts"`, `"savings"` keys.

---

## Running the Simulation

The simulation replays `SIM_DAY` (`2026-10-31`) starting at 05:00. Weather is loaded from `data/weather/2026-10-31.json` (committed — works with no internet).

**Speed:** 1× is real-time. 60× runs a full day in ~14 minutes. 300× runs it in ~3 minutes. Change speed any time from the dashboard header or the Controls page. Allowed values: 1, 60, 300.

**Reset:** "Reset the day (same seed)" rewinds to 05:00 and replays from scratch with the same `SIM_SEED`. The result is deterministic.

**Demo buttons (Controls page):**

| Event | Duration | What to watch |
|---|---|---|
| Cloud over whole street | 45 sim-min | All house glows dim; fewer trades for those blocks |
| Cloud over one house | 45 sim-min | That house's solar drops; it switches from seller to buyer |
| Grid outage | 30 sim-min | Outage badge appears; no penalties for those blocks |
| AC on at a house | 2 sim-h | Load rises; spare kW shrinks; agent bids as buyer |
| Guests | 3 sim-h | Same as AC but larger load spike |
| Away | 4 sim-h | Load drops; house sells more |
| House 14 tries a ₹40 bid | instant | Wallet check rejects it before it reaches the market; shown in the activity log |
| Verify ledger | instant | Rehashes every entry; "Intact" = chain intact |

**Sequencing events:** buttons can be clicked in any order while the day runs. Each event is additive. Use "Reset the day" to get back to a clean state.

---

## Tests and Checks

### Unit tests

```bash
# from hizashi/, with .venv active
python -m pytest tests/ -q --tb=short \
  --ignore=tests/test_run_direct.py \
  --ignore=tests/test_weather_solar.py
```

Expected: **84 passed** (last verified: 2026-11-01).

`test_run_direct.py` starts a live server and requires a free port; `test_weather_solar.py` makes real HTTP calls to Open-Meteo. Both are excluded from the standard CI run.

### Frontend build

```bash
# from hizashi/web/
npm run build
```

Expected: Vite prints `✓ built in ~2.7s`, PWA precaches 6 entries.

```bash
# from hizashi/mobile/
npx tsc --noEmit
```

Expected: 0 errors.

### Pre-demo preflight

```bash
# from hizashi/, with hub + agents running
python -X utf8 scripts/preflight.py
```

Checks: Python ≥ 3.12, Node ≥ 20, pytest, npm build, keys present and not in git, weather cache, hub `/api/state`, all four agent cards, wallet signs a valid ask and refuses a ₹40 bid, WebSocket accepts owner role and rejects a wrong token.

### Soak test

```bash
# from hizashi/, with .venv active (does NOT need hub running)
python -X utf8 scripts/soak.py
```

Runs the full simulated day headless at 300× under 6 weather scenarios × 2 seeds. Checks 8 invariants per block and per day. Writes results to `docs/soak_results.md`.

---

## What Is Real, Simulated, and Planned

### Real (runs on actual hardware / code)

- Ed25519 key generation and signing (`scripts/gen_keys.py`, `shared/hizashi_shared/crypto.py`)
- Wallet mandate enforcement — 8 checks before any offer is accepted
- A2A negotiation protocol between agents (JSON-RPC over HTTP, concession-curve haggling)
- Uniform-price auction and settlement engine
- SHA-256 ledger hash-chain — verified by the "Verify ledger" button
- `pvlib` Ineichen clear-sky solar model with ±5 % noise
- Open-Meteo weather fetch (falls back to committed cache when offline)
- All four React and React Native UIs (street dashboard, console, phone app)

### Simulated (physics-based, not from real meters)

- Meter readings — generated by `hub/hizashi_hub/sim/meters.py` using `pvlib` + load profiles; signed with Ed25519 keys so the signing path is real, but the kWh numbers are from the simulator, not physical hardware
- Household load profiles — synthetic curves in `data/profiles/`
- Weather events (cloud, outage) — injected via console buttons

### Planned / Not Yet Built

- **Mandate parser** (`hub/hizashi_hub/llm/mandate_parser.py`) — natural language → mandate (e.g. "sell up to 2 kWh above ₹4"). The POST `/api/wallet/{house}/mandate/parse` endpoint raises `NotImplementedError`. The phone app shows "Rules from a sentence → Soon".
- **3D street view** — mentioned in the spec; no code exists.
- **WhatsApp alerts** (Twilio) — env vars present; code not built.
- **Physical meter hardware** — the demo uses the simulator.

---

## Troubleshooting

**Hub starts but phones can't connect.**
The phone and the laptop must be on the same Wi-Fi, or you must use a tunnel. On Windows, open "Windows Defender Firewall → Allow an app" and add Python for Private networks. Then open `http://<laptop-local-ip>:8000/app/` on the phone.

**`honcho: command not found` / `python -m honcho` fails.**
Install dev dependencies: `pip install -e ".[dev]"`. Then use `python -m honcho start`.

**`UnicodeEncodeError` when hub starts on Windows.**
Add `PYTHONUTF8=1` to your `.env`, or prefix every command with `python -X utf8`.

**`keys/*.key` missing — hub crashes at startup.**
Run `python scripts/gen_keys.py` from `hizashi/`. The `keys/` directory is git-ignored and must be created on every fresh clone.

**`data/street.json` has empty public keys.**
`gen_keys.py` must run *before* the hub starts. Run it again: `python scripts/gen_keys.py`.

**Agents start but stay disconnected from hub.**
The hub must be fully started (port 8000 listening) before agents try to connect. With honcho they all start together; the hub lifespan usually wins. If not, start the hub first in one terminal, then run the agents.

**`npm run build` fails in `mobile/`.**
Run `npm install` first from `hizashi/mobile/`. Node ≥ 20 is required; the project uses Expo SDK 58 (React Native 0.88).

**Phone app shows a loading spinner indefinitely.**
Check that the hub is running and the phone can reach it. Try opening `http://<hub-ip>:8000/api/state` in the phone browser; if that loads, re-scan the QR code.

**`asyncio.run()` hangs in the sandbox / CI.**
The async integration tests (`test_run_direct.py`, `test_weather_solar.py`) need a real async event loop. Exclude them from automated runs: `pytest --ignore=tests/test_run_direct.py --ignore=tests/test_weather_solar.py`.

---

## Limitations and Next Steps

- Meter readings are simulated; a real deployment needs hardware meters with embedded Ed25519 keys.
- The mandate parser (natural-language rules) is a stub; it requires a Gemini or Groq API key and is not built.
- The clearing price rule is uniform price; pay-as-bid is mentioned in some earlier notes but is not implemented.
- Only four houses are modelled; scaling to a larger street requires testing the auction and settlement under load.
- WhatsApp notifications (Twilio) are wired in config but the notification code is not built.
- The 3D street visualisation is planned but does not exist yet.

---

## Docs

- Full technical spec: [`docs/BUILD_SPEC.md`](docs/BUILD_SPEC.md)
- Task tracker: [`docs/TASKS.md`](docs/TASKS.md)
- Coding-agent conventions: [`AGENTS.md`](AGENTS.md)
