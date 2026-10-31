# agent/ — one home agent per house

Run: `python -m hizashi_agent --house h12 --port 9012`. Card: `http://localhost:9012/.well-known/agent-card.json`.

**Agents never hold keys; ask the wallet** (`POST /api/wallet/{house}/sign`). Trading is plain Python, no LLM.

## A2A traps (a2a-sdk[http-server]==1.2.1)

- Start from `examples/negotiation_sample.py` (verified: `python agent/examples/negotiation_sample.py serve`, then `... ask`). Online examples are mostly 0.3 and will not run.
- The executor **must enqueue a `Task` before any status update** (see `executor.py`).
- Data parts return numbers as floats (`round: 3` → `3.0`). Re-parse with `Offer.model_validate(d)` / `Contract.model_validate(d)` and only then verify signatures against the registry pubkey of the claimed house.
- Carry `task_id` / `context_id` across rounds on the client side; one negotiation = one A2A task.

## Negotiation protocol (spec 7.3)

- Seller → buyer: `{"type": "ask", "offer": <signed Offer, model_dump(mode="json")>}`.
- Buyer → seller: `{"type": "bid", "offer": ...}` (task → `INPUT_REQUIRED`), `{"type": "accept", "contract": <Contract with buyer_sig>}` (→ `COMPLETED`), or `{"type": "refuse", "reason": "..."}` (→ `REJECTED`/`FAILED`).
- Seller accepting a bid: `{"type": "accept", "contract": <Contract with seller_sig>}`; buyer countersigns via its wallet, books via `POST /api/market/contracts`, replies `{"type": "booked", "contract_id": ...}` and completes.
- **The side that receives an accept countersigns and books.**
- Bad signature → refuse + `POST /api/guard/report`.
- Buyer refuses at once if it has no buy intent for that block, the seller is on another transformer (with `same_transformer`), or the block isn't `OPEN`.
- Seller asks neighbours on its transformer one by one in registry order until its promised kWh is sold; buyer bids for `min(ask kWh, remaining need)`.
- Stop after `MAX_ROUNDS`, at gate closure, or on refuse. Wait `NEGOTIATION_ROUND_DELAY_MS` between rounds.

## Files

| File | What |
| --- | --- |
| `__main__.py` | CLI entry |
| `card.py` | `AgentCard` for a house |
| `server.py` | FastAPI app + A2A routes + hub client task |
| `executor.py` | answers incoming asks (Phase 0: refuses "not trading yet") |
| `a2a_client.py` | sends asks to neighbours |
| `hub_client.py` | WS subscribe with backoff + REST calls |
| `forecaster.py` | p10/p50/p90 solar + use per block |
| `planner.py` | sell / buy / sit out + plan windows |
| `negotiator.py` | prices, concession curve, accept rule (pure, tested in `tests/test_negotiator.py`) |
| `runtime.py` | reacts to block states |
