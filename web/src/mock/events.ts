/**
 * Scripted mock event stream for /h/:house?mock=1.
 * Simulates one block: H12 (seller) haggles with H14 (buyer),
 * reaching a deal, then a wallet.blocked fires.
 *
 * Event shape: { type, sim_time, house, data } — matches models.Event exactly.
 *
 * kW conversion note: meter.reading carries solar_wh / import_wh / export_wh
 * per simulated minute. UI converts: kW = wh * 60 / 1000.
 *
 * Keep working to the end — this is the demo fallback if the hub is down.
 */

import type { HubEvent } from "../lib/types";

const DAY = "2026-10-31";
const NEG = "neg-mock-001";
const BLK = { day: DAY, index: 48 }; // 12:00–12:15
function iso(hh: number, mm: number) {
  return `${DAY}T${String(hh).padStart(2, "0")}:${String(mm).padStart(2, "0")}:00+05:30`;
}
function offerId(r: number, side: "ask" | "bid") {
  return `off-${side}-r${r}`;
}

/** Returns the full scripted sequence. Call once; replay with index. */
export function makeMockScript(house: string): { delay: number; event: HubEvent }[] {
  const h = (house === "h14" ? "h14" : "h12") as "h12" | "h14";
  const script: { delay: number; event: HubEvent }[] = [];
  let t = 0;

  function push(delay: number, ev: HubEvent) {
    t += delay;
    script.push({ delay: t, event: ev });
  }

  // ── clock.tick (initial) ─────────────────────────────────────────────────
  push(0, {
    type: "clock.tick",
    sim_time: iso(10, 0),
    house: null,
    data: { speed: 60, running: true },
  });

  // ── block.state: PLANNED ─────────────────────────────────────────────────
  push(400, {
    type: "block.state",
    sim_time: iso(10, 0),
    house: null,
    data: { block: `${DAY}#48`, state: "PLANNED" },
  });

  // ── clock ticks ──────────────────────────────────────────────────────────
  for (let m = 1; m <= 5; m++) {
    push(500, {
      type: "clock.tick",
      sim_time: iso(10, m),
      house: null,
      data: { speed: 60, running: true },
    });
  }

  // ── forecast.updated ─────────────────────────────────────────────────────
  push(300, {
    type: "forecast.updated",
    sim_time: iso(10, 5),
    house: h,
    data: {
      forecasts: [
        {
          house: h,
          block: BLK,
          solar_p10: 0.18, solar_p50: 0.22, solar_p90: 0.26,
          use_p10: 0.05, use_p50: 0.07, use_p90: 0.09,
          made_at: iso(10, 5),
        },
      ],
    },
  });

  // ── plan.updated ─────────────────────────────────────────────────────────
  push(200, {
    type: "plan.updated",
    sim_time: iso(10, 6),
    house: h,
    data: {
      windows: [
        {
          plan_id: "plan-mock-001",
          house: h,
          side: h === "h12" ? "sell" : "buy",
          day: DAY,
          first_index: 48,
          last_index: 52,
          kwh: 0.20,
          expected_price: 4.68,
          expected_value: 0.936,
          status: "auto",
          signature: null,
        },
      ],
    },
  });

  // ── block.state: OPEN ────────────────────────────────────────────────────
  push(600, {
    type: "block.state",
    sim_time: iso(10, 7),
    house: null,
    data: { block: `${DAY}#48`, state: "OPEN" },
  });

  // ── meter.reading ────────────────────────────────────────────────────────
  // solar_wh=33 wh/min → 33*60/1000 = 1.98 kW solar
  // import_wh=0, export_wh=25 wh/min → 25*60/1000 = 1.50 kW export
  push(800, {
    type: "meter.reading",
    sim_time: iso(10, 8),
    house: h,
    data: {
      house: h,
      ts: iso(10, 8),
      seq: 1,
      solar_wh: 33,
      import_wh: 0,
      export_wh: 25,
      signature: null,
    },
  });

  // ── nego.offer rounds ────────────────────────────────────────────────────
  // Round 0: Ask 5.40 (h12), Bid 4.00 (h14)
  push(900, {
    type: "nego.offer",
    sim_time: iso(10, 9),
    house: h,
    data: {
      offer: {
        offer_id: offerId(0, "ask"),
        negotiation_id: NEG,
        block: BLK,
        side: "ask",
        house: "h12",
        to: "h14",
        kwh: 0.20,
        price: 5.40,
        round: 0,
        expires_at: `${DAY}T11:00:00+05:30`,
        nonce: "n-ask-0",
        signature: null,
      },
    },
  });
  push(800, {
    type: "nego.offer",
    sim_time: iso(10, 9),
    house: h,
    data: {
      offer: {
        offer_id: offerId(0, "bid"),
        negotiation_id: NEG,
        block: BLK,
        side: "bid",
        house: "h14",
        to: "h12",
        kwh: 0.20,
        price: 4.00,
        round: 0,
        expires_at: `${DAY}T11:00:00+05:30`,
        nonce: "n-bid-0",
        signature: null,
      },
    },
  });

  // Round 1: Ask 5.16, Bid 4.30
  push(900, {
    type: "nego.offer",
    sim_time: iso(10, 10),
    house: h,
    data: {
      offer: {
        offer_id: offerId(1, "ask"),
        negotiation_id: NEG,
        block: BLK,
        side: "ask",
        house: "h12",
        to: "h14",
        kwh: 0.20,
        price: 5.16,
        round: 1,
        expires_at: `${DAY}T11:00:00+05:30`,
        nonce: "n-ask-1",
        signature: null,
      },
    },
  });
  push(800, {
    type: "nego.offer",
    sim_time: iso(10, 10),
    house: h,
    data: {
      offer: {
        offer_id: offerId(1, "bid"),
        negotiation_id: NEG,
        block: BLK,
        side: "bid",
        house: "h14",
        to: "h12",
        kwh: 0.20,
        price: 4.30,
        round: 1,
        expires_at: `${DAY}T11:00:00+05:30`,
        nonce: "n-bid-1",
        signature: null,
      },
    },
  });

  // Round 2: Ask 4.92, Bid 4.60
  push(900, {
    type: "nego.offer",
    sim_time: iso(10, 11),
    house: h,
    data: {
      offer: {
        offer_id: offerId(2, "ask"),
        negotiation_id: NEG,
        block: BLK,
        side: "ask",
        house: "h12",
        to: "h14",
        kwh: 0.20,
        price: 4.92,
        round: 2,
        expires_at: `${DAY}T11:00:00+05:30`,
        nonce: "n-ask-2",
        signature: null,
      },
    },
  });
  push(800, {
    type: "nego.offer",
    sim_time: iso(10, 11),
    house: h,
    data: {
      offer: {
        offer_id: offerId(2, "bid"),
        negotiation_id: NEG,
        block: BLK,
        side: "bid",
        house: "h14",
        to: "h12",
        kwh: 0.20,
        price: 4.60,
        round: 2,
        expires_at: `${DAY}T11:00:00+05:30`,
        nonce: "n-bid-2",
        signature: null,
      },
    },
  });

  // Round 3: Ask 4.68 — buyer accepts (bid 4.60 ≥ ask 4.68 fails, but buyer accepts 4.68)
  push(900, {
    type: "nego.offer",
    sim_time: iso(10, 12),
    house: h,
    data: {
      offer: {
        offer_id: offerId(3, "ask"),
        negotiation_id: NEG,
        block: BLK,
        side: "ask",
        house: "h12",
        to: "h14",
        kwh: 0.20,
        price: 4.68,
        round: 3,
        expires_at: `${DAY}T11:00:00+05:30`,
        nonce: "n-ask-3",
        signature: null,
      },
    },
  });

  // ── contract.booked — deal at ₹4.68 ──────────────────────────────────────
  push(700, {
    type: "contract.booked",
    sim_time: iso(10, 12),
    house: h,
    data: {
      contract: {
        contract_id: "ctr-mock-001",
        negotiation_id: NEG,
        block: BLK,
        seller: "h12",
        buyer: "h14",
        kwh: 0.20,
        price: 4.68,
        route: "haggle",
        fee_per_kwh: 0.14,
        open_access: false,
        seller_sig: null,
        buyer_sig: null,
        market_sig: null,
      },
    },
  });

  // ── wallet.blocked (demo: h14 agent tried ₹40, wallet refused) ────────────
  push(1200, {
    type: "wallet.blocked",
    sim_time: iso(10, 13),
    house: h,
    data: {
      reason: "price exceeds max_buy_price",
      offer: {
        offer_id: "off-bad-bid",
        negotiation_id: "neg-bad-001",
        block: BLK,
        side: "bid",
        house: "h14",
        to: "h12",
        kwh: 0.20,
        price: 40.0,
        round: 0,
        expires_at: `${DAY}T11:00:00+05:30`,
        nonce: "n-bad-0",
        signature: null,
      },
      tried_price: 40.0,
      max_buy_price: 5.50,
    },
  });

  // ── block.state: GATE_CLOSED ─────────────────────────────────────────────
  push(1000, {
    type: "block.state",
    sim_time: iso(10, 15),
    house: null,
    data: { block: `${DAY}#48`, state: "GATE_CLOSED" },
  });

  // ── continue ticking ─────────────────────────────────────────────────────
  for (let m = 16; m <= 20; m++) {
    push(500, {
      type: "clock.tick",
      sim_time: iso(10, m),
      house: null,
      data: { speed: 60, running: true },
    });
    push(0, {
      type: "meter.reading",
      sim_time: iso(10, m),
      house: h,
      data: {
        house: h,
        ts: iso(10, m),
        seq: m - 7,
        solar_wh: 35,
        import_wh: 0,
        export_wh: 27,
        signature: null,
      },
    });
  }

  // ── block.state: DELIVERING ──────────────────────────────────────────────
  push(400, {
    type: "block.state",
    sim_time: iso(12, 0),
    house: null,
    data: { block: `${DAY}#48`, state: "DELIVERING" },
  });

  // keep ticking every 600ms
  for (let m = 1; m <= 10; m++) {
    push(600, {
      type: "clock.tick",
      sim_time: iso(12, m),
      house: null,
      data: { speed: 60, running: true },
    });
  }

  return script;
}

/**
 * Plays the mock script into a callback, simulating real-time delivery.
 * Returns a cancel function.
 */
export function playMock(
  house: string,
  onEvent: (e: HubEvent) => void,
): () => void {
  const script = makeMockScript(house);
  const handles: ReturnType<typeof setTimeout>[] = [];
  for (const { delay, event } of script) {
    handles.push(setTimeout(() => onEvent(event), delay));
  }
  return () => handles.forEach(clearTimeout);
}

