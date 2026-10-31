# Hizashi — build spec for Claude Code

> **How to use (for Jiten):** save this file in the repo as `docs/BUILD_SPEC.md`, then tell Claude Code:
> _"Read docs/BUILD_SPEC.md fully. Do Phase 0 only, then stop and report."_
> Later: _"Do Phase 1"_, or a single task: _"Do task R1.5 from docs/BUILD_SPEC.md"_.

---

## 0. Your role and ground rules

You are building **Hizashi** for Team Enthos at Kodikon 6.0, a 24-hour hackathon. Four people work in parallel: Jiten uses Claude Code (you); Anurag, Prajval and Tezash use Google Antigravity. Your Phase 0 output is the scaffold everyone builds on, so **structure, contracts and stubs matter more than features**.

Rules:

1. **Repo structure first.** Create every folder and file in section 2 before writing logic. Files for later phases get a module docstring, typed function signatures and `raise NotImplementedError("TODO(<task id>, <owner>)")`.
2. **Do only the phase or task you're asked for**, then stop and report (section 12).
3. **`shared/` is the contract.** After Phase 0, do not change anything in `shared/hizashi_shared/` without asking Jiten first.
4. **A2A: don't guess the API.** Use exactly `a2a-sdk[http-server]==1.2.1`. Most examples online are for 0.3 and will not run. Copy the verified sample in section 7.1 verbatim into `agent/examples/negotiation_sample.py`, run it, and build the real agent from it.
5. **No secrets in the repo.** Keys go in `keys/` (git-ignored); API keys in `.env` (git-ignored).
6. **Tests:** pytest for anything with arithmetic or crypto. Run them before reporting.
7. **Git:** if the folder isn't a repo, `git init`. Commit at the end of each phase with a clear message. Do not push unless asked.
8. If something blocks you for more than ~20 minutes (A2A, Tailwind setup, pvlib signatures), stop and tell me what failed and the two options you see. Don't silently swap in a different design.

---

## 1. What Hizashi is (context in 10 lines)

- Karnataka's KERC P2P Regulations 2024 let a home with rooftop solar sell spare power to a neighbour at an agreed price. Almost nobody does, because each 15-minute block needs a promise made an hour ahead, with penalties if a cloud breaks it.
- Hizashi gives **every home an agent** that forecasts, promises safely, and **haggles with neighbours' agents over A2A**, inside limits the owner sets.
- A **Mandate Wallet** in the hub holds each home's signing key. Agents never hold keys; they ask the wallet to sign, and the wallet refuses anything outside the owner's limits ("buy at ₹40" is never sent).
- Hizashi is its own P2P platform: it runs the market, settles each block under KERC 8(g), keeps a hash-chained ledger, and shows each owner **"saved vs BESCOM"**.
- Demo: one laptop, a simulated street of 4 houses, two phones (House 12 and House 14). A simulated day runs at 60× or 300×. Real input: today's Bengaluru weather forecast. Simulated: meters and household use.
- The LLM (Gemini, Groq fallback) is used **only** to turn the owner's sentence into wallet rules. Trading is plain Python.

---

## 2. Repo structure (create this first)

```text
hizashi/
├── AGENTS.md                      # rules for every coding agent (section 10)
├── CLAUDE.md                      # one line: @AGENTS.md
├── README.md                      # setup + run (section 11)
├── docs/
│   ├── BUILD_SPEC.md              # this file
│   └── TASKS.md                   # task IDs, owners, files (section 11)
├── Procfile                       # hub + 4 agents
├── Procfile.demo                  # same + cloudflared tunnel
├── pyproject.toml
├── .env.example
├── .gitignore
├── shared/
│   ├── AGENTS.md
│   └── hizashi_shared/
│       ├── __init__.py
│       ├── models.py              # pydantic models: the contract
│       ├── crypto.py              # canonical JSON + Ed25519 sign/verify
│       ├── blocks.py              # block index <-> time, lifecycle times
│       ├── events.py              # event type names (constants)
│       ├── config.py              # tariffs, fee, thresholds, ports, env loading
│       ├── street.py              # load data/street.json into models
│       ├── solar.py               # pvlib roof output per block (used by hub sim AND agents)
│       └── profiles.py            # load household use profiles
├── hub/
│   ├── AGENTS.md
│   └── hizashi_hub/
│       ├── __init__.py
│       ├── app.py                 # FastAPI app, startup/shutdown, serves web/dist
│       ├── bus.py                 # in-process async event bus
│       ├── ws.py                  # WebSocket endpoint, fan-out by role
│       ├── db.py                  # sqlite3 schema + helpers
│       ├── clock.py               # simulated clock, speed, block lifecycle
│       ├── state.py               # in-memory live state + snapshot for GET /api/state
│       ├── api/
│       │   ├── __init__.py        # include all routers
│       │   ├── state.py           # /api/state, /api/registry, /api/weather
│       │   ├── wallet.py          # /api/wallet/...
│       │   ├── approvals.py       # /api/approvals...
│       │   ├── market.py          # /api/market/...
│       │   ├── ledger.py          # /api/ledger...
│       │   ├── guard.py           # /api/guard/report
│       │   ├── console.py         # /api/console/...
│       │   └── webhooks.py        # /webhooks/twilio
│       ├── sim/
│       │   ├── __init__.py
│       │   ├── weather.py         # Open-Meteo fetch + cache, clear-sky fallback
│       │   ├── pv.py              # actual roof output (uses shared.solar + events)
│       │   ├── load.py            # actual household use (profile + noise + modifiers)
│       │   ├── meters.py          # signed minute readings, per-block totals
│       │   └── events.py          # console events: cloud, outage, ac, guests, away
│       ├── wallet/
│       │   ├── __init__.py
│       │   ├── keystore.py        # load private keys from keys/
│       │   ├── mandate.py         # mandate store + versions
│       │   ├── checks.py          # the ordered checks (section 6.3)
│       │   ├── approvals.py       # plan + offer approvals
│       │   └── signer.py          # sign offers, plans, contracts
│       ├── market/
│       │   ├── __init__.py
│       │   ├── registry.py        # houses, transformers, agent URLs, public keys
│       │   ├── lifecycle.py       # per-block state machine
│       │   ├── orderbook.py       # leftover orders per block
│       │   ├── auction.py         # gate-closure auction (KERC 4(b), average)
│       │   └── booking.py         # verify + book contracts
│       ├── settlement/
│       │   ├── __init__.py
│       │   ├── settle.py          # per-contract settlement (KERC 8(g))
│       │   ├── savings.py         # saved vs BESCOM per house
│       │   └── ledger.py          # hash-chained ledger + verify
│       ├── guard/
│       │   ├── __init__.py
│       │   └── rules.py           # bad sig, impossible reading, wash, collusion, replay
│       ├── notify/
│       │   ├── __init__.py
│       │   └── twilio_wa.py       # WhatsApp approvals out
│       └── llm/
│           ├── __init__.py
│           └── mandate_parser.py  # sentence -> proposed Mandate (Gemini, Groq fallback)
├── agent/
│   ├── AGENTS.md
│   ├── examples/
│   │   └── negotiation_sample.py  # VERIFIED a2a-sdk 1.2.1 sample (section 7.1)
│   └── hizashi_agent/
│       ├── __init__.py
│       ├── __main__.py            # python -m hizashi_agent --house h12 --port 9012
│       ├── card.py                # AgentCard for a house
│       ├── server.py              # FastAPI app + A2A routes
│       ├── executor.py            # A2A server side: answer incoming asks
│       ├── a2a_client.py          # A2A client side: send asks to neighbours
│       ├── hub_client.py          # WS subscribe + REST calls to the hub
│       ├── forecaster.py          # p10/p50/p90 solar + use per block
│       ├── planner.py             # sell / buy / sit out per block + day plan windows
│       ├── negotiator.py          # opening prices, concession, accept rule
│       └── runtime.py             # main loop reacting to block states
├── web/
│   ├── AGENTS.md
│   ├── index.html
│   ├── package.json
│   ├── vite.config.ts             # PWA plugin, dev proxy /api and /ws -> :8000
│   ├── tsconfig.json
│   ├── public/                    # icons (simple sun SVG), manifest assets
│   └── src/
│       ├── main.tsx
│       ├── App.tsx                # routes
│       ├── lib/api.ts             # fetch helpers
│       ├── lib/types.ts           # TS mirrors of shared models + events
│       ├── store/hub.ts           # Zustand store + one reducer per event type
│       ├── hooks/useHub.ts        # snapshot + WebSocket + reconnect
│       ├── pages/Landing.tsx      # pick a house; QR codes for phones
│       ├── pages/Owner.tsx        # /h/:house (tabs: Home, Approvals, Rules, History)
│       ├── pages/Street.tsx       # /street (2D SVG)
│       ├── pages/Street3D.tsx     # /street/3d (later)
│       ├── pages/Console.tsx      # /console
│       └── components/            # SavingsCard, HaggleFeed, BlockCard, ApprovalCard, BlockedCard, HouseSvg, EventLog
├── data/
│   ├── street.json                # houses, transformer, roofs, mandates, public keys
│   ├── profiles/                  # household use profiles (96 blocks each)
│   └── weather/                   # cached forecast JSON
├── keys/                          # private keys (git-ignored)
├── scripts/
│   ├── gen_keys.py                # meter + wallet key pair per house
│   ├── seed.py                    # profiles, street.json pubkeys, fresh DB
│   ├── attack_fake_seller.py
│   ├── attack_bad_bid.py
│   └── attack_collusion.py
└── tests/
    ├── test_crypto.py
    ├── test_blocks.py
    ├── test_negotiator.py
    ├── test_auction.py
    ├── test_wallet_checks.py
    ├── test_settlement.py
    └── test_ledger.py
```

---

## 3. Tech and versions

- Python ≥ 3.12. One `pyproject.toml` at the root:

```toml
[project]
name = "hizashi"
version = "0.1.0"
requires-python = ">=3.12"
dependencies = [
  "fastapi>=0.115", "uvicorn[standard]>=0.30", "httpx>=0.27", "pydantic>=2.7",
  "a2a-sdk[http-server]==1.2.1",
  "pynacl>=1.5", "pvlib>=0.11", "pandas>=2.2", "numpy>=1.26",
  "python-dotenv>=1.0", "websockets>=12",
  "twilio>=9", "google-genai>=1.0", "groq>=0.11",
]
[project.optional-dependencies]
dev = ["pytest>=8", "pytest-asyncio>=0.23", "honcho>=2"]

[build-system]
requires = ["setuptools>=68"]
build-backend = "setuptools.build_meta"

[tool.setuptools.packages.find]
where = ["shared", "hub", "agent"]

[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["tests"]
```

- Storage: Python's built-in `sqlite3` (no ORM). DB file `hub/hizashi.db`.
- Web: Vite + React + TypeScript, Tailwind (use the current setup for whatever version npm installs; for v4 that's `@tailwindcss/vite`), `vite-plugin-pwa`, `zustand`, `react-router-dom`, `qrcode.react`. Later: `three`, `@react-three/fiber`, `@react-three/drei`.
- Run: `honcho` with `Procfile`. Tunnel: `cloudflared tunnel --url http://localhost:8000` (in `Procfile.demo` only, so a missing cloudflared never breaks dev).

---

## 4. Shared contract (`shared/hizashi_shared/`)

### 4.1 Units and conventions

- Energy: **kWh per block**. Prices: **₹ per kWh**. Money: ₹, rounded to 2 decimals for display only.
- Time: simulated IST (`Asia/Kolkata`), ISO strings. A block = `day` + `index` 0–95 (48 = 12:00–12:15). Key format: `"2026-10-31#48"`.
- Houses: `"h12" | "h14" | "h16" | "h18"`.

### 4.2 `models.py`

```python
from datetime import datetime
from typing import Literal
from pydantic import BaseModel, Field

House = Literal["h12", "h14", "h16", "h18"]
BlockState = Literal["PLANNED", "OPEN", "GATE_CLOSED", "DELIVERING", "SETTLED"]

class BlockRef(BaseModel):
    day: str            # "2026-10-31"
    index: int          # 0..95
    @property
    def key(self) -> str: return f"{self.day}#{self.index:02d}"

class Roof(BaseModel):
    kwp: float; tilt: float; azimuth: float; inverter_kw: float   # pvlib convention: azimuth 180 = south, 90 = east

class HouseInfo(BaseModel):
    id: House
    label: str                      # "House 12"
    transformer: str                # "T1"
    roof: Roof | None               # None = no solar
    profile: str                    # household use profile name
    buyback_rate: float | None      # ₹/kWh BESCOM pays this home; None if no solar
    metering: Literal["net", "gross", "none"]
    agent_url: str                  # "http://127.0.0.1:9012/"
    meter_pubkey: str | None = None
    wallet_pubkey: str | None = None

class Forecast(BaseModel):
    house: House
    block: BlockRef
    solar_p10: float; solar_p50: float; solar_p90: float
    use_p10: float; use_p50: float; use_p90: float
    made_at: datetime

class Mandate(BaseModel):
    house: House
    version: int = 1
    min_sell_price: float           # never sell below
    max_buy_price: float            # never buy above
    daily_budget: float             # ₹ the agent may spend per day on buys
    max_promise_kwh: float          # per block
    approve_above: float            # ₹; plans or offers worth more need the owner's OK
    counterparties: Literal["same_transformer", "street"] = "same_transformer"
    paused: bool = False

class PlanWindow(BaseModel):        # a run of consecutive blocks with the same side
    plan_id: str
    house: House
    side: Literal["buy", "sell"]
    day: str
    first_index: int; last_index: int
    kwh: float
    expected_price: float
    expected_value: float           # kwh * expected_price
    status: Literal["auto", "pending", "approved", "declined"] = "auto"
    signature: str | None = None

class Offer(BaseModel):
    offer_id: str
    negotiation_id: str
    block: BlockRef
    side: Literal["ask", "bid"]
    house: House                    # who makes the offer
    to: House | None                # None = market order at gate closure
    kwh: float
    price: float
    round: int
    expires_at: datetime            # the block's gate closure
    nonce: str
    signature: str | None = None    # wallet signature

class Contract(BaseModel):
    contract_id: str
    negotiation_id: str | None
    block: BlockRef
    seller: House; buyer: House
    kwh: float; price: float
    route: Literal["haggle", "auction"]
    fee_per_kwh: float = 0.14
    open_access: bool = False
    seller_sig: str | None = None
    buyer_sig: str | None = None
    market_sig: str | None = None

class MeterReading(BaseModel):
    house: House
    ts: datetime                    # simulated minute
    seq: int                        # strictly increasing per meter
    solar_wh: float; import_wh: float; export_wh: float
    signature: str | None = None    # meter key

class Settlement(BaseModel):
    contract_id: str
    block: BlockRef
    contracted_kwh: float; delivered_kwh: float; shortfall_kwh: float
    price: float
    buyer_pays: float               # (p + F) * q
    seller_net: float               # p*d - s*(R - p)
    seller_penalty: float           # s*(R - p), 0 if outage
    fee: float                      # F * q
    outage: bool

class Approval(BaseModel):
    approval_id: str
    house: House
    kind: Literal["plan", "offer"]
    summary: str                    # "Buy 2.4 kWh from neighbours, 10:00–13:00, for about ₹11.23?"
    ref_id: str                     # plan_id or offer_id
    code: str                       # 4 digits, for WhatsApp replies
    status: Literal["pending", "approved", "declined", "expired"] = "pending"
    created_at: datetime

class Event(BaseModel):
    type: str
    sim_time: datetime
    house: House | None = None      # for owner-scoped filtering
    data: dict = Field(default_factory=dict)
```

### 4.3 `crypto.py` (Ed25519 via PyNaCl)

```python
import base64, json
from nacl.signing import SigningKey, VerifyKey

SIG_FIELDS = {"signature", "seller_sig", "buyer_sig", "market_sig"}

def canonical(model) -> bytes:
    data = model.model_dump(mode="json", exclude=SIG_FIELDS)
    return json.dumps(data, sort_keys=True, separators=(",", ":")).encode()

def sign(model, key: SigningKey) -> str:
    return base64.b64encode(key.sign(canonical(model)).signature).decode()

def verify(model, sig: str | None, pub_b64: str) -> bool:
    if not sig: return False
    try:
        VerifyKey(base64.b64decode(pub_b64)).verify(canonical(model), base64.b64decode(sig))
        return True
    except Exception:
        return False

def pub_b64(key: SigningKey) -> str: ...
def load_key(path) -> SigningKey: ...      # file holds base64 seed
```

**Critical:** always compute `canonical()` from a **pydantic model**, never from a raw dict that came over A2A. A2A data parts are protobuf `Value`s, so integers come back as floats (`round: 1` → `1.0`), which changes the JSON and breaks the signature. Re-parse with `Offer.model_validate(d)` / `Contract.model_validate(d)` first; pydantic restores the int.

### 4.4 `blocks.py`

- `block_start(ref) -> datetime`, `block_of(dt) -> BlockRef`, `gate_close(ref) = start − 60 min`, `open_time(ref) = max(day_start, start − 120 min)`, `settle_time(ref) = start + 15 min`.
- `TRADABLE = range(24, 76)` (06:00–18:45). Other blocks never open.
- Constants from config: `DAY_START = 05:00`, `DAY_END = 19:00`.

### 4.5 `events.py` (string constants)

`clock.tick`, `block.state`, `forecast.updated`, `plan.updated`, `meter.reading`, `nego.offer`, `nego.result`, `wallet.blocked`, `approval.requested`, `approval.resolved`, `contract.booked`, `market.cleared`, `settlement.done`, `savings.updated`, `guard.flag`, `grid.outage`, `console.command`, `mandate.updated`.

### 4.6 `config.py`

Loads `.env` with python-dotenv. Defaults:

| Name                                                                                                          | Default                 | Meaning                                           |
| ------------------------------------------------------------------------------------------------------------- | ----------------------- | ------------------------------------------------- |
| `SIM_DAY`                                                                                                     | `2026-10-31`            | simulated date                                    |
| `SIM_SPEED`                                                                                                   | `60`                    | 1, 60 or 300                                      |
| `SIM_SEED`                                                                                                    | `31`                    | all randomness seeded                             |
| `LAT`, `LON`, `ALT`                                                                                           | `12.93`, `77.55`, `900` | Bengaluru (Banashankari)                          |
| `RETAIL_ENERGY_CHARGE` (R)                                                                                    | `5.80`                  | buyer's BESCOM price                              |
| `FEE_PER_KWH` (F)                                                                                             | `0.14`                  | provider fee, paid by the buyer (KERC 8(e), 8(h)) |
| `MIN_TRADE_KWH`                                                                                               | `0.05`                  | below this, sit out                               |
| `SELLER_OPEN_DISCOUNT`                                                                                        | `0.40`                  | seller opens at R − 0.40                          |
| `BUYER_OPEN_PRICE`                                                                                            | `4.00`                  | buyer opens here                                  |
| `MAX_ROUNDS`                                                                                                  | `6`                     | rounds 0..5                                       |
| `CONCESSION_BETA`                                                                                             | `1.0`                   | 1 = even steps                                    |
| `EXPECTED_P2P_PRICE`                                                                                          | `4.68`                  | for plan approval estimates                       |
| `NEGOTIATION_ROUND_DELAY_MS`                                                                                  | `700`                   | real ms between rounds, so humans can watch       |
| `HUB_URL`                                                                                                     | `http://127.0.0.1:8000` |                                                   |
| `PUBLIC_URL`                                                                                                  | empty                   | tunnel URL for QR codes and Twilio                |
| `AGENT_TOKEN_H12..H18`                                                                                        | `dev-h12` …             | bearer tokens agents use for their wallet         |
| `GEMINI_API_KEY`, `GROQ_API_KEY`                                                                              | empty                   | Phase 3                                           |
| `TWILIO_ACCOUNT_SID`, `TWILIO_AUTH_TOKEN`, `TWILIO_WHATSAPP_FROM`, `OWNER_WHATSAPP_H12`, `OWNER_WHATSAPP_H14` | empty                   | Phase 3                                           |

### 4.7 `solar.py` (shared by hub sim and agents)

`roof_kwh_per_block(roof: Roof, weather: pd.DataFrame) -> list[float]` (96 values):

- `weather` has a 15-min `DatetimeIndex` (Asia/Kolkata) with columns `ghi`, `dni`, `dhi`, `temp_air`, `cloud_cover`.
- `pvlib.location.Location(LAT, LON, tz, ALT)` → `get_solarposition` → `pvlib.irradiance.get_total_irradiance(tilt, azimuth, zenith, azimuth, dni, ghi, dhi)` → cell temperature (`pvlib.temperature.sapm_cell` or a simple NOCT model) → `pvlib.pvsystem.pvwatts_dc` → `pvlib.inverter.pvwatts` (clip at inverter_kw) → kW × 0.25 h = kWh per block. **Check the signatures in the installed pvlib version**; parameter names changed across versions.
- Roof `None` → all zeros.

### 4.8 `profiles.py`

`load_profile(name) -> tuple[list[float], list[float]]` = (mean kWh per block, std kWh per block), 96 each, from `data/profiles/<name>.json` (`{"name", "source", "mean": [...], "std": [...]}`). Later a real eMARC CSV can replace a file without code changes.

---

## 5. Street data and demo defaults

`data/street.json` (written by `scripts/seed.py`; pubkeys filled by `gen_keys.py`):

| House | Label    | Transformer | Roof (kWp, tilt, azimuth, inverter kW) | Profile            | Buyback ₹                    | Metering | Agent URL |
| ----- | -------- | ----------- | -------------------------------------- | ------------------ | ---------------------------- | -------- | --------- |
| h12   | House 12 | T1          | 5.0, 13, 180, 5.0                      | `couple_away_day`  | 3.89                         | net      | :9012     |
| h14   | House 14 | T1          | none                                   | `wfh_ac`           | —                            | none     | :9014     |
| h16   | House 16 | T1          | 3.0, 15, 90 (east), 3.0                | `family_medium`    | 2.14 (PM Surya Ghar, 2–3 kW) | net      | :9016     |
| h18   | House 18 | T1          | 2.0, 13, 180, 2.0                      | `heavy_appliances` | 1.96 (PM Surya Ghar, ≤ 2 kW) | net      | :9018     |

Demo mandates:

| House | min_sell | max_buy | daily_budget | max_promise_kwh | approve_above |
| ----- | -------- | ------- | ------------ | --------------- | ------------- |
| h12   | 4.20     | 5.50    | 50           | 1.0             | 10            |
| h14   | 4.20     | 5.50    | 50           | 1.0             | 10            |
| h16   | 3.80     | 5.40    | 50           | 1.0             | 25            |
| h18   | 3.50     | 5.40    | 60           | 1.0             | 25            |

With these numbers the H12–H14 haggle reproduces the deck: asks 5.40, 5.16, 4.92, 4.68; bids 4.00, 4.30, 4.60; deal at **₹4.68 in round 3**. Keep `tests/test_negotiator.py` asserting exactly this.

Household profiles (`scripts/seed.py` generates them; label `"source": "synthetic, shaped after Prayas eMARC load curves"`). Mean kWh per block, std = 20% of mean:

| Profile                  | Night (00–06) | Morning peak (06:30–08:30) | Day (10–17)       | Evening peak (18:30–22:00) |
| ------------------------ | ------------- | -------------------------- | ----------------- | -------------------------- |
| `couple_away_day` (h12)  | 0.05          | 0.25                       | 0.12–0.16         | 0.35                       |
| `wfh_ac` (h14)           | 0.10          | 0.25                       | 0.30 (AC ~1.2 kW) | 0.40                       |
| `family_medium` (h16)    | 0.06          | 0.30                       | 0.18              | 0.40                       |
| `heavy_appliances` (h18) | 0.08          | 0.30                       | 0.28–0.35         | 0.45                       |

Smooth the transitions (no cliffs).

---

## 6. Hub (`hub/hizashi_hub/`)

### 6.1 Core

- `app.py`: FastAPI app. On startup: load config + street, open DB, load keys and mandates, fetch/cache weather, start the clock task. Mount routers under `/api`, WebSocket at `/ws`, Twilio webhook at `/webhooks/twilio`. Serve `web/dist` at `/` with SPA fallback (unknown non-`/api` paths return `index.html`). CORS open for dev.
- `bus.py`: `publish(event: Event)` and `subscribe() -> asyncio.Queue`. Every module publishes through it. The gateway, state, settlement and guard subscribe.
- `ws.py`: `/ws?role=owner&house=h14 | role=street | role=console | role=agent&house=h12&token=...`. Fan-out filter: owners get events where `event.house` is theirs or `None`; street and console get everything except per-minute meter readings of all houses (send meter readings at most once per simulated 5 minutes per house to screens); agents get `clock.tick`, `block.state`, `market.cleared`, `approval.resolved`, `console.command` for their house, and their own `meter.reading`. Reject agent sockets with a wrong token.
- `state.py`: holds the live snapshot (clock, speed, houses, mandates, current block states, last forecasts, open negotiations, contracts today, settlements, savings, approvals, flags, outage). `GET /api/state` returns it in one JSON.
- `clock.py`: async loop. Each tick = one simulated minute; real sleep = `60 / speed` seconds. Day 05:00 → 19:00, then stop (console can reset). On each tick: ask `sim` for the minute's readings, publish `clock.tick`, and move blocks through the lifecycle (6.2). `set_speed()`, `reset()` (same seed → same day).

### 6.2 Block lifecycle (`market/lifecycle.py`)

| State         | When                          | Action                                                                                                                                     |
| ------------- | ----------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------ |
| `PLANNED`     | day start                     | agents forecast and post day plans                                                                                                         |
| `OPEN`        | `max(day_start, T − 120 min)` | wallets accept offers for this block                                                                                                       |
| `GATE_CLOSED` | T − 60 min                    | wallets refuse new offers; agents post leftover market orders within 1 sim minute; then run the auction (6.4); schedule frozen (KERC 6(7)) |
| `DELIVERING`  | T                             | meters stream into this block                                                                                                              |
| `SETTLED`     | T + 15 min                    | settle every contract (6.5)                                                                                                                |

Outage overlapping a block sets `outage=True` on it (no penalties, KERC 5(c)(iii)). Publish `block.state` on every change.

### 6.3 Wallet (`wallet/`)

Endpoints (bearer token = that house's agent token):

- `POST /api/wallet/{house}/sign` body `{"kind": "offer", "offer": {...}}` or `{"kind": "contract", "contract": {...}}` → `{"status": "signed", "offer"|"contract": {...}}` | `{"status": "pending", "approval_id": "..."}` | `{"status": "refused", "reason": "..."}`.
- `POST /api/wallet/{house}/plans` body `{"windows": [PlanWindow, ...]}` → each window `auto` (value ≤ approve_above), or `pending` with an approval created.

Offer checks, **in order**; the first failure refuses:

1. Token matches `house`, and `offer.house == house`.
2. Mandate not paused.
3. Block is `OPEN` and `expires_at` ≤ gate closure.
4. Ask: `price ≥ min_sell_price`. Bid: `price ≤ max_buy_price`.
5. `kwh ≤ max_promise_kwh`.
6. Counterparty allowed: with `same_transformer`, `to` must be on the same transformer (market orders allowed).
7. Bids: today's committed buy spending + `kwh × price` ≤ `daily_budget`.
8. Approval: if the block belongs to a plan window with status `pending` or `declined` → refuse ("waiting for your OK" / "you declined this window"). If not covered by an `approved`/`auto` window and `kwh × price > approve_above` → create an offer approval, return `pending`.
9. Sign with the house's wallet key; store the offer; publish `nego.offer` (house = offerer, plus a copy for the `to` house).

Every refusal publishes `wallet.blocked` with `{reason, offer}` scoped to that house. Phone text format: **"BLOCKED · Tried to buy at ₹40/unit. Your max is ₹5.50, so it was never sent."**

Contract checks: same token/house check; this house is the seller or buyer; the terms (block, kWh, price, seller, buyer) equal an offer **signed in this negotiation by either side** (look up stored offers by `negotiation_id`, verify that signature); and the terms pass this house's checks 2–7. Then add `seller_sig` or `buyer_sig`.

Plan approval summary format (deck): **"Buy 2.4 kWh from neighbours, 10:00–13:00, for about ₹11.23?"** Approve/decline via `POST /api/approvals/{id}` `{"decision": "approve"|"decline", "channel": "app"|"whatsapp"}` → publish `approval.resolved`.

Mandates: `GET /api/wallet/{house}/mandate`, `PUT /api/wallet/{house}/mandate` (new version, ledger entry, `mandate.updated`), `POST /api/wallet/{house}/mandate/parse` `{text}` → proposed Mandate, not applied (Phase 3).

### 6.4 Market

- `booking.py`, `POST /api/market/contracts`: verify `seller_sig` and `buyer_sig` against registry pubkeys, block still `OPEN`, seller ≠ buyer, guard checks pass → set `open_access` (different transformers), add `market_sig` (market key from `keys/market.key`), store, ledger entry, publish `contract.booked` (scoped copies to seller and buyer).
- `POST /api/market/orders`: signed `Offer` with `to=None`, only while the block is `GATE_CLOSED` and before the auction runs.
- `auction.py` (KERC 4(b), average price):

```python
def clear(asks, bids):
    asks = sorted(asks, key=lambda o: (o.price, o.offer_id))
    bids = sorted(bids, key=lambda o: (-o.price, o.offer_id))
    matches = []
    while asks and bids and bids[0].price >= asks[0].price:
        a, b = asks[0], bids[0]
        q = round(min(a.kwh, b.kwh), 3)
        price = round((a.price + b.price) / 2, 2)
        matches.append((a, b, q, price))
        a.kwh -= q; b.kwh -= q
        if a.kwh < 0.01: asks.pop(0)
        if b.kwh < 0.01: bids.pop(0)
    return matches   # unsold asks -> BESCOM at buyback; unmet bids -> BESCOM at R
```

Run per transformer first, then across transformers with `open_access=True`. Each match becomes a `Contract(route="auction")` signed by the market (wallets already signed the orders). Publish `market.cleared`.

### 6.5 Settlement (KERC 8(g))

At `SETTLED`, per contract: the seller's metered export in the block is shared across its contracts in proportion to size; `d = min(share, q)`, `s = q − d`.

- `buyer_pays = (p + F) × q` (buyer pays the pledged quantity even if it used less, 8(g)(iv); extra use is bought from BESCOM at R, no penalty, 8(g)(v)).
- `seller_penalty = s × (R − p)`, or 0 if the block had an outage (5(c)(iii)).
- `seller_net = p × d − seller_penalty`.
- Extra export beyond contracts → BESCOM at the seller's buyback (8(g)(ii)).

Savings vs BESCOM (`savings.py`), per house per day:

- Buyer: `Σ q × (R − p − F)`.
- Seller: `Σ [d × (p − B) − s × (R − p)]`.
- Also `projected_year = saved_today × 300` (label in UI: "if the year had 300 days like today"). Publish `savings.updated`.

Test: deck block 0.20 kWh at ₹4.68 → buyer saves ₹0.196, seller gains ₹0.158.

### 6.6 Ledger

Table `ledger(seq, ts, kind, ref_id, payload, prev_hash, hash)`; first `prev_hash = "0"*64`;

```python
def entry_hash(prev_hash, seq, ts, kind, ref_id, payload) -> str:
    body = json.dumps([prev_hash, seq, ts, kind, ref_id, payload], separators=(",", ":"))
    return hashlib.sha256(body.encode()).hexdigest()
```

Entries: contract booked, settlement, mandate change, approval decision, guard flag. `GET /api/ledger?house=` and `GET /api/ledger/verify` → `{"ok": true}` or `{"ok": false, "broken_at": seq}`.

### 6.7 DB schema (`db.py`)

Tables: `houses`, `mandates(house, version, json, created_at)`, `plans(plan_id, house, json, status)`, `offers(offer_id, negotiation_id, block_key, house, to_house, side, kwh, price, round, status, reason, json, created_at)`, `approvals(approval_id, house, kind, ref_id, code, status, channel, summary, created_at, decided_at)`, `contracts(contract_id, block_key, seller, buyer, kwh, price, route, status, json)`, `block_meter(house, block_key, solar_kwh, import_kwh, export_kwh, outage)`, `settlements(contract_id, json)`, `flags(id, ts, kind, houses, detail)`, `ledger(...)`. `scripts/seed.py` recreates the DB.

### 6.8 Simulation

- `weather.py`: Open-Meteo forecast for `SIM_DAY`: `https://api.open-meteo.com/v1/forecast?latitude=..&longitude=..&hourly=shortwave_radiation,direct_normal_irradiance,diffuse_radiation,temperature_2m,cloud_cover&timezone=Asia%2FKolkata&start_date=..&end_date=..`. Hourly radiation is the **mean of the preceding hour**: shift each value to (hour − 30 min) before interpolating to 15-min. Rename to `ghi`, `dni`, `dhi`, `temp_air`, `cloud_cover`. Cache to `data/weather/<date>.json`; use the cache if present. If offline: pvlib clear-sky (Ineichen) scaled by 0.85, `cloud_cover=20`, flagged `"source": "clear-sky fallback"`. `GET /api/weather` returns the 96-block frame + source.
- `pv.py`: actual output = `shared.solar` on the same weather × cloud factor from console events (e.g. cloud over h12 → 0.3 for 45 sim minutes) × seeded noise (±5%), per minute.
- `load.py`: actual use = profile mean (interpolated to minutes) + seeded noise (std from profile) + modifiers: AC on (h14) +1.0 kW; Guests ×1.4; Away ×0.4.
- `meters.py`: per minute per house: `export = max(solar − use, 0)`, `import = max(use − solar, 0)`, sign with the meter key, increment `seq`, publish `meter.reading` (house-scoped), add to `block_meter`. During an outage: solar 0, export 0, import 0.
- `events.py`: console events with start/end in sim time.

### 6.9 Console, guard, notify, LLM

- `POST /api/console/events` `{"type": "cloud"|"outage"|"ac"|"guests"|"away"|"bad_bid"|"rogue_seller"|"collusion", "house"?: "h12", "minutes"?: 45}`; `POST /api/console/speed` `{"speed": 1|60|300}`; `POST /api/console/reset`. `bad_bid` publishes `console.command` to h14's agent `{"cmd": "bad_bid", "price": 40}`.
- `POST /api/guard/report` (agent token) `{"kind", "detail"}` → `guard.flag`.
- Guard rules (Phase 3): bad signature, impossible reading (solar at night, export > inverter), wash trade (self or both ways in one block), price coordination (2+ sellers identical asks for 4+ blocks in a row, KERC 5(a)(ii)), replay (seen `nonce`/`seq`).
- Twilio (Phase 3): on `approval.requested` for a house with `OWNER_WHATSAPP_<H>`, send the summary + "Reply YES 4821 or NO 4821". Webhook parses the reply and resolves the approval.
- LLM (Phase 3): Gemini with the `Mandate` JSON schema as required output; validate with pydantic; Groq fallback; on failure keep the current mandate.

### 6.10 REST summary

| Method + path                                                   | Caller             |
| --------------------------------------------------------------- | ------------------ |
| `GET /api/state`                                                | screens            |
| `GET /api/registry`                                             | agents, screens    |
| `GET /api/weather`                                              | agents             |
| `POST /api/wallet/{house}/sign`                                 | agent              |
| `POST /api/wallet/{house}/plans`                                | agent              |
| `GET/PUT /api/wallet/{house}/mandate`, `POST .../mandate/parse` | owner app          |
| `GET /api/approvals?house=`, `POST /api/approvals/{id}`         | owner app          |
| `POST /api/market/orders`, `POST /api/market/contracts`         | agent              |
| `GET /api/ledger?house=`, `GET /api/ledger/verify`              | owner app, console |
| `POST /api/guard/report`                                        | agent              |
| `POST /api/console/events`, `/speed`, `/reset`                  | console            |
| `POST /webhooks/twilio`                                         | Twilio             |

---

## 7. Home agent (`agent/hizashi_agent/`)

### 7.1 Verified A2A sample — copy verbatim to `agent/examples/negotiation_sample.py`

Verified on a2a-sdk 1.2.1: the client sends asks on one task; the server answers with bids in `INPUT_REQUIRED` and accepts at ₹4.68, completing the task. Two traps it already handles: **the executor must enqueue a `Task` before any status update**, and data parts return numbers as floats.

```python
"""Minimal two-party haggle over A2A, verified against a2a-sdk[http-server]==1.2.1.

Run the server:  python agent/examples/negotiation_sample.py serve
Run the client:  python agent/examples/negotiation_sample.py ask
"""
import asyncio
import sys
import uuid

import httpx
import uvicorn
from fastapi import FastAPI

from a2a.client import ClientConfig, create_client
from a2a.helpers import get_data_parts, new_data_message, new_data_part, new_task
from a2a.server.agent_execution import AgentExecutor, RequestContext
from a2a.server.events import EventQueue
from a2a.server.request_handlers import DefaultRequestHandler
from a2a.server.routes import (
    add_a2a_routes_to_fastapi,
    create_agent_card_routes,
    create_jsonrpc_routes,
)
from a2a.server.tasks import InMemoryTaskStore, TaskUpdater
from a2a.types import (
    AgentCapabilities,
    AgentCard,
    AgentInterface,
    AgentSkill,
    Message,
    Role,
    SendMessageRequest,
    TaskState,
)

PORT = 9099
URL = f"http://127.0.0.1:{PORT}/"
BUYER_LIMIT = 4.70


def card() -> AgentCard:
    return AgentCard(
        name="Hizashi agent · House 14",
        description="Buys spare rooftop solar for House 14",
        version="0.1.0",
        supported_interfaces=[
            AgentInterface(url=URL, protocol_binding="JSONRPC", protocol_version="1.0")
        ],
        capabilities=AgentCapabilities(streaming=False),
        default_input_modes=["application/json"],
        default_output_modes=["application/json"],
        skills=[
            AgentSkill(
                id="trade_block",
                name="Trade energy for one 15-minute block",
                description="Replies to an ask with a bid, an accept or a refusal",
                tags=["energy", "p2p"],
            )
        ],
    )


class BuyerExecutor(AgentExecutor):
    async def execute(self, context: RequestContext, event_queue: EventQueue) -> None:
        # A new negotiation: the executor must enqueue a Task before any status update.
        if context.current_task is None:
            await event_queue.enqueue_event(
                new_task(
                    context.task_id,
                    context.context_id,
                    TaskState.TASK_STATE_SUBMITTED,
                    history=[context.message],
                )
            )
        updater = TaskUpdater(event_queue, context.task_id, context.context_id)
        data = get_data_parts(context.message.parts)
        ask = data[0] if data else {}
        price = float(ask.get("price", 99))
        rnd = int(ask.get("round", 0))
        if price <= BUYER_LIMIT:
            reply = {"type": "accept", "price": price, "round": rnd}
            await updater.complete(self._msg(reply, context))
        else:
            bid = round(4.00 + 0.27 * rnd, 2)
            reply = {"type": "bid", "price": bid, "round": rnd}
            await updater.requires_input(self._msg(reply, context))

    async def cancel(self, context: RequestContext, event_queue: EventQueue) -> None:
        updater = TaskUpdater(event_queue, context.task_id, context.context_id)
        await updater.cancel()

    @staticmethod
    def _msg(data: dict, context: RequestContext) -> Message:
        return new_data_message(
            data, context_id=context.context_id, task_id=context.task_id, role=Role.ROLE_AGENT
        )


def build_app() -> FastAPI:
    agent_card = card()
    handler = DefaultRequestHandler(
        agent_executor=BuyerExecutor(),
        task_store=InMemoryTaskStore(),
        agent_card=agent_card,
    )
    app = FastAPI()
    add_a2a_routes_to_fastapi(
        app,
        agent_card_routes=create_agent_card_routes(agent_card),
        jsonrpc_routes=create_jsonrpc_routes(handler, rpc_url="/"),
    )
    return app


async def seller() -> None:
    async with httpx.AsyncClient(timeout=10) as http:
        client = await create_client(
            URL, client_config=ClientConfig(streaming=False, httpx_client=http)
        )
        task_id, context_id = "", ""
        for rnd, ask_price in enumerate([5.40, 5.16, 4.92, 4.68]):
            msg = Message(
                message_id=str(uuid.uuid4()),
                role=Role.ROLE_USER,
                parts=[new_data_part({"type": "ask", "price": ask_price, "round": rnd})],
                task_id=task_id,
                context_id=context_id,
            )
            async for resp in client.send_message(SendMessageRequest(message=msg)):
                task = resp.task if resp.HasField("task") else None
                if task is None:
                    print("non-task response:", resp)
                    continue
                task_id, context_id = task.id, task.context_id
                state = TaskState.Name(task.status.state)
                reply = get_data_parts(task.status.message.parts)
                print(f"round {rnd}: ask {ask_price:.2f} -> {state} {reply}")
                if task.status.state == TaskState.TASK_STATE_COMPLETED:
                    return


if __name__ == "__main__":
    if sys.argv[1:] == ["serve"]:
        uvicorn.run(build_app(), host="127.0.0.1", port=PORT, log_level="warning")
    else:
        asyncio.run(seller())
```

Expected client output:

```text
round 0: ask 5.40 -> TASK_STATE_INPUT_REQUIRED [{'price': 4.0, 'type': 'bid', 'round': 0.0}]
round 1: ask 5.16 -> TASK_STATE_INPUT_REQUIRED [{'price': 4.27, 'type': 'bid', 'round': 1.0}]
round 2: ask 4.92 -> TASK_STATE_INPUT_REQUIRED [{'price': 4.54, 'type': 'bid', 'round': 2.0}]
round 3: ask 4.68 -> TASK_STATE_COMPLETED [{'price': 4.68, 'type': 'accept', 'round': 3.0}]
```

### 7.2 Agent process

`python -m hizashi_agent --house h12 --port 9012`:

1. Load config, street, mandate (from hub `GET /api/state` or `/api/registry`).
2. Start the A2A server (FastAPI + `add_a2a_routes_to_fastapi`, JSON-RPC at `/`) with the house's card: name `"Hizashi agent · House 12"`, description, skill `trade_block`, interface URL from street.json.
3. Connect to the hub WebSocket as `role=agent` with retry/backoff (the hub may start later).
4. React to block states (7.6).

### 7.3 Negotiation protocol (one negotiation = one A2A task)

Data part payloads:

- Seller → buyer: `{"type": "ask", "offer": <signed Offer as model_dump(mode="json")>}`
- Buyer → seller: `{"type": "bid", "offer": ...}` (task → `INPUT_REQUIRED`), `{"type": "accept", "contract": <Contract with buyer_sig>}` (task → `COMPLETED`), or `{"type": "refuse", "reason": "..."}` (task → `REJECTED` or `FAILED`).
- Seller → buyer (accepting a bid): `{"type": "accept", "contract": <Contract with seller_sig>}`; buyer countersigns via its wallet, books via `POST /api/market/contracts`, replies `{"type": "booked", "contract_id": ...}` and completes.

Rules:

- **The side that receives an accept countersigns and books.**
- Always re-parse incoming payloads with `Offer.model_validate` / `Contract.model_validate` and verify signatures with the registry pubkey of the claimed house **before** acting. Bad signature → refuse + `POST /api/guard/report`.
- Buyer refuses at once if it has no buy intent for that block, the seller is on another transformer (with `same_transformer`), or the block isn't `OPEN`.
- A seller asks neighbours on its transformer one by one in registry order until its promised kWh is sold. Buyer bids for `min(ask kWh, its remaining need)`.
- Stop after `MAX_ROUNDS`, at gate closure, or on refuse. Wait `NEGOTIATION_ROUND_DELAY_MS` between rounds.

### 7.4 Forecaster and planner

- Solar p50 = `shared.solar` on the hub's forecast weather. Uncertainty `u = 0.10 + 0.40 × cloud_cover/100`; `p10 = p50 × (1 − u)`, `p90 = p50 × (1 + u)`.
- Use: from the profile, `p50 = mean`, `p10 = mean − 1.28 σ` (≥ 0), `p90 = mean + 1.28 σ`, with Away/Guests/AC modifiers when the owner sets them.
- Plan per block: `spare_low = solar_p10 − use_p90`. Sell if `spare_low > MIN_TRADE_KWH` → `min(spare_low, max_promise_kwh)`. Buy if `use_p10 > solar_p50` → `use_p10 − solar_p50`. Else sit out.
- Day plan windows: group consecutive buy (or sell) blocks; `expected_value = kwh × EXPECTED_P2P_PRICE`; post to `/api/wallet/{house}/plans` at `PLANNED`. Publish nothing yourself; the hub publishes `plan.updated`.
- During the day (Phase 3, N6): after each settled block, `ratio = actual_last_hour / forecast_last_hour` clamped to [0.5, 1.5]; scale forecasts for blocks still `OPEN`/`PLANNED`; replan; if a sell intent shrinks below what's contracted, buy cover.

### 7.5 Negotiator (`negotiator.py`)

```text
seller_open  = R − SELLER_OPEN_DISCOUNT            (5.40)
seller_limit = max(min_sell_price, buyback + 0.10)
buyer_open   = BUYER_OPEN_PRICE                     (4.00)
buyer_limit  = min(max_buy_price, R − F)

ask(r) = seller_open − (seller_open − seller_limit) × (r / (MAX_ROUNDS−1)) ** (1/β)
bid(r) = buyer_open  + (buyer_limit − buyer_open)  × (r / (MAX_ROUNDS−1)) ** (1/β)

Accept the other side's latest price as soon as it's at least as good as your own next offer.
```

Round 2 decimals. `tests/test_negotiator.py` must reproduce: H12 (min_sell 4.20, buyback 3.89) vs H14 (max_buy 5.50) → asks 5.40, 5.16, 4.92, 4.68; bids 4.00, 4.30, 4.60; buyer accepts **4.68 in round 3**.

### 7.6 Runtime by block state

| State         | Agent does                                                                              |
| ------------- | --------------------------------------------------------------------------------------- |
| `PLANNED`     | forecast the day, post plan windows                                                     |
| `OPEN`        | sellers start negotiations (7.3); buyers answer                                         |
| `GATE_CLOSED` | post leftover kWh (unsold sell / unmet buy) as a signed market order at its limit price |
| `DELIVERING`  | read own meter; Phase 3 corrections                                                     |
| `SETTLED`     | read results; after a shortfall, shrink future promises by 10%                          |

Console command `bad_bid` (h14): build a bid at ₹40 for the next `OPEN` block and ask the wallet to sign it (it will be refused; that's the demo).

---

## 8. Web (`web/`)

- One React PWA. **Screens only display hub events and send taps; they never compute prices, savings or settlements.**
- `vite.config.ts`: dev proxy `/api` and `/ws` → `http://127.0.0.1:8000` (with `ws: true`); `vite-plugin-pwa` with manifest name "Hizashi", theme colour amber `#d98a04`, a simple sun SVG icon.
- `useHub(role, house?)`: `GET /api/state` into the Zustand store → open `/ws?...` → `store.apply(event)` (one reducer per event type) → on close wait 1 s and start over.
- Routes:
  - `/` Landing: four house buttons + Street + Console; QR codes for `PUBLIC_URL + /h/h12` and `/h/h14`.
  - `/h/:house` Owner app, mobile-first, bottom tabs:
    - **Home**: big "Saved today vs BESCOM ₹X" (+ "≈ ₹Y this year if every day were like today"); live solar kW and use kW; current block card (state, promised, contracted); haggle feed (Ask ₹5.40 → Bid ₹4.00 → … → Deal 0.20 kWh at ₹4.68); red **BLOCKED** cards; amber **NEEDS YOUR OK** card with Decline / Approve.
    - **Approvals**: pending + history.
    - **Rules**: mandate fields (editable → PUT); text box for a sentence → parse → show proposal → Save (Phase 3).
    - **History**: ledger entries for this house.
    - Away / Guests toggles (Phase 3).
  - `/street` (laptop): SVG street of four houses; roof glow by solar kW; "spare/short" label; a line per live trade with kWh and price; outage dims everything; guard flags as toasts; sim clock + speed in the corner.
  - `/street/3d` (Phase 3): React Three Fiber; same store; Kenney City Kit models if present in `web/public/models`, else boxes.
  - `/console`: buttons for every console event (per house where relevant), speed 1/60/300, reset, ledger verify, and a raw event log.
- Visual: clean, light background, amber accent (sun), large numbers, ₹ everywhere. Copy the deck's phrasing for cards.

---

## 9. Scripts

- `gen_keys.py`: for each house, a meter key and a wallet key; plus `keys/market.key`. Write base64 seeds to `keys/<house>.meter.key`, `keys/<house>.wallet.key`; write public keys into `data/street.json`. Idempotent (`--force` to regenerate).
- `seed.py`: write `data/street.json` (section 5, keeps existing pubkeys), the four profiles, default mandates; recreate `hub/hizashi.db`.
- Attack scripts (Phase 2/3): `attack_bad_bid.py` posts the console `bad_bid` event; `attack_fake_seller.py` sends an A2A ask to h14 signed with a random key claiming to be h16; `attack_collusion.py` makes h16 and h18 post identical asks for 4 blocks.

---

## 10. AGENTS.md files (write these in Phase 0)

**Root `AGENTS.md`** (keep under ~150 lines):

- One-paragraph project summary (section 1).
- How to run (section 11) and how to test (`pytest`).
- **Ownership table** (below). Rule: "At the start of a session, if the user hasn't said who they are, ask. Only edit files in folders they own. To change anything in `shared/`, stop and ask Jiten."
- A2A rule: pinned `a2a-sdk[http-server]==1.2.1`; read `agent/examples/negotiation_sample.py` before writing A2A code; executors must enqueue a Task first; re-parse payloads with pydantic before verifying signatures.
- Units and conventions (4.1). Never compute prices or savings in `web/`.
- Git: `git pull --rebase` before every push; commit only your folders; never commit `keys/`, `.env`, `*.db`.

| Folder                                                                                                                                                          | Owner   | Lane                  |
| --------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------- | --------------------- |
| `shared/hizashi_shared/` (except `crypto.py`, `solar.py`, `profiles.py`)                                                                                        | Jiten   | architect             |
| `hub/hizashi_hub/wallet/`, `settlement/`, `guard/`, `llm/`                                                                                                      | Jiten   | trust                 |
| `agent/`, `hub/hizashi_hub/market/`, `clock.py`, `sim/weather.py`, `sim/pv.py`, `sim/load.py`, `sim/events.py`, `shared/.../solar.py`, `shared/.../profiles.py` | Anurag  | market & agents       |
| `shared/.../crypto.py`, `hub/hizashi_hub/sim/meters.py`, `notify/`, `scripts/`                                                                                  | Prajval | identity & alerts     |
| `web/`, `hub/hizashi_hub/api/`, `ws.py`, `bus.py`, `db.py`, `state.py`, `app.py`                                                                                | Tezash  | screens & integration |

**`shared/AGENTS.md`**: "Frozen contract. Read-only unless you are Jiten. If you need a field, ask."

**`hub/AGENTS.md`**: module map (section 6.1 list), the event bus rule ("publish through `bus.publish`, never write to sockets directly"), and the wallet rule ("nothing outside `wallet/` touches private keys").

**`agent/AGENTS.md`**: the A2A traps (7.1), the negotiation protocol (7.3), "agents never hold keys; ask the wallet".

**`web/AGENTS.md`**: display-only rule, `useHub` pattern, mobile-first owner app, phrasing from the deck.

**`CLAUDE.md`**: `@AGENTS.md`

---

## 11. README, Procfiles, env, TASKS.md

`README.md` run steps:

```bash
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
python scripts/gen_keys.py && python scripts/seed.py
pytest
cd web && npm install && npm run build && cd ..
honcho start                      # hub :8000 + agents :9012 :9014 :9016 :9018
# demo with phones: honcho -f Procfile.demo start  (needs cloudflared)
# frontend dev: cd web && npm run dev  (http://localhost:5173)
```

`Procfile`:

```text
hub: uvicorn hizashi_hub.app:app --host 0.0.0.0 --port 8000
h12: python -m hizashi_agent --house h12 --port 9012
h14: python -m hizashi_agent --house h14 --port 9014
h16: python -m hizashi_agent --house h16 --port 9016
h18: python -m hizashi_agent --house h18 --port 9018
```

`Procfile.demo`: the same plus `tunnel: cloudflared tunnel --url http://localhost:8000`.

`.env.example`: every variable in 4.6 with its default (secrets empty). `.gitignore`: `.venv/`, `__pycache__/`, `.env`, `keys/`, `hub/*.db`, `web/node_modules/`, `web/dist/`, `data/weather/*.json`.

`docs/TASKS.md`: the task IDs below with the files each touches and an empty Owner column.

---

## 12. Phases

Each phase ends with: tests pass, `honcho start` runs clean, commit, and a report.

### Phase 0 — scaffold (now, for Review 0)

Tasks R0.1–R0.7. Build:

1. The full tree in section 2, every file present (stubs where later).
2. `pyproject.toml`, `.env.example`, `.gitignore`, `Procfile`, `Procfile.demo`, README, all `AGENTS.md`, `CLAUDE.md`, `docs/TASKS.md`.
3. `shared/`: `models.py`, `crypto.py`, `blocks.py`, `events.py`, `config.py`, `street.py`, `profiles.py` **fully implemented**; `solar.py` implemented if pvlib signatures check out quickly, else stub.
4. `scripts/gen_keys.py`, `scripts/seed.py` working.
5. Hub: `app.py`, `bus.py`, `ws.py`, `state.py`, `db.py` (schema), `clock.py` (ticks, speed, reset, block lifecycle events), `api/state.py`, `api/console.py` (speed + reset only). Everything else stubbed.
6. Agent: `agent/examples/negotiation_sample.py` (verbatim, run it), `__main__.py`, `card.py`, `server.py` serving the card + a stub executor that politely refuses (`{"type": "refuse", "reason": "not trading yet"}`), `hub_client.py` connecting to the WebSocket with retry and logging block states.
7. Web: Vite app, routes, `useHub`, store, Landing with QR codes, Owner page showing the sim clock and block states live, Console with speed/reset and a raw event log. Build output served by the hub.
8. Tests: `test_crypto.py` (sign/verify; tampered field fails; int→float round trip through a dict then `model_validate` still verifies), `test_blocks.py`, and **`test_negotiator.py` with the deck numbers** (implement the pure functions in `negotiator.py` now; they have no dependencies).

Done when:

- `pytest` passes.
- `honcho start` → `curl localhost:8000/api/state` returns the snapshot; `curl localhost:90{12,14,16,18}/.well-known/agent-card.json` returns four cards.
- The sample prints the four expected rounds.
- `http://localhost:8000/h/h12` shows the sim clock ticking and block states changing; `/console` changes speed.

### Phase 1 — two phones haggle (Review 1, Sat 2:30 PM)

R1.1 wallet sign endpoint with checks 1–6 · R1.2 weather fetch + cache · R1.3 forecaster (`solar.py`, profiles) · R1.4 planner · R1.5 negotiator over A2A (protocol 7.3) · R1.6 contract signing + booking · R1.7 Owner Home screen: haggle feed, live block card, solar/use.

Done when, at 60×, `/h/h12` and `/h/h14` show H12 and H14 haggling block by block, deals at ~₹4.68, `contract.booked` on both phones.

### Phase 2 — a full day runs (Review 2, Sat 8:30 PM)

R2.1 auction · R2.2 signed meters · R2.3 settlement + savings · R2.4 ledger + verify · R2.5 plan/offer approvals (wallet check 7–8) + Approve card · R2.6 2D street · R2.7 console events (cloud, AC, speed, reset) with sim reacting · R2.8 savings + history screens · R2.9 `bad_bid` blocked and shown · R2.10 full day end to end.

Done when a full day at 300× finishes with settlements, a ledger that verifies, "saved today" on both phones, the ₹40 bid blocked on the phone, and House 14's 10:00–13:00 window asking for approval.

### Phase 3 — overnight polish (freeze 6 AM)

N1 WhatsApp approvals · N2 guard rules · N3 attack scripts · N4 mandate parser + Rules screen · N5 outage handling · N6 mid-day correction · N7 Away/Guests · N8 3D street · N9 backup video (manual) · N10 stage deck (manual).

### Report format (after every phase or task)

1. What now runs, with the exact commands to see it.
2. What's stubbed and which task ID fills it.
3. Any deviation from this spec and why.
4. Anything a teammate must know before pulling.
