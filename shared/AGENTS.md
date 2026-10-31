# shared/ — the contract

**Frozen contract. Read-only unless you are Jiten. If you need a field, ask.**

Exceptions by owner (see root `AGENTS.md`): `crypto.py` is Prajval's, `solar.py` and `profiles.py` are Anurag's. Even they must not change a function signature or a model without asking Jiten, because the hub, every agent and `web/src/lib/types.ts` depend on it.

| File | What |
| --- | --- |
| `models.py` | pydantic models: `BlockRef`, `HouseInfo`, `Mandate`, `PlanWindow`, `Offer`, `Contract`, `MeterReading`, `Settlement`, `Approval`, `Event` |
| `crypto.py` | `canonical(model)`, `sign`, `verify`, `pub_b64`, `load_key`; Ed25519 via PyNaCl; signature fields are excluded from the canonical JSON |
| `blocks.py` | `block_start`, `block_of`, `gate_close`, `open_time`, `settle_time`, `state_at`, `TRADABLE` |
| `events.py` | event type names (`clock.tick`, `block.state`, ...) |
| `config.py` | `.env` + defaults: tariff R, fee F, thresholds, ports, agent tokens, paths |
| `street.py` | load `data/street.json` into `HouseInfo` / `Mandate` |
| `solar.py` | `roof_kwh_per_block(roof, weather)` with pvlib (hub sim and agents use the same code) |
| `profiles.py` | `load_profile(name)` → (mean, std), 96 blocks each |

Rules: always `canonical()` a pydantic model, never a raw dict. When a model changes (with Jiten's OK), update `web/src/lib/types.ts` in the same commit.
