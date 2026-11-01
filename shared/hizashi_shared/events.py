"""Event type names published on the hub bus and sent over /ws."""

CLOCK_TICK = "clock.tick"
BLOCK_STATE = "block.state"
FORECAST_UPDATED = "forecast.updated"
PLAN_UPDATED = "plan.updated"
METER_READING = "meter.reading"
NEGO_OFFER = "nego.offer"
NEGO_RESULT = "nego.result"
WALLET_BLOCKED = "wallet.blocked"
APPROVAL_REQUESTED = "approval.requested"
APPROVAL_RESOLVED = "approval.resolved"
CONTRACT_BOOKED = "contract.booked"
MARKET_CLEARED = "market.cleared"
SETTLEMENT_DONE = "settlement.done"
SAVINGS_UPDATED = "savings.updated"
GUARD_FLAG = "guard.flag"
GRID_OUTAGE = "grid.outage"
CONSOLE_COMMAND = "console.command"
MANDATE_UPDATED = "mandate.updated"
SIM_EVENT = "sim.event"            # console cloud / ac / guests / away / outage started
HOUSE_UPDATED = "house.updated"    # onboarding changed a roof, buyback rate or metering
SCHEDULE_UPDATED = "schedule.updated"  # an owner planned (or dropped) time away or guests

ALL = (
    CLOCK_TICK, BLOCK_STATE, FORECAST_UPDATED, PLAN_UPDATED, METER_READING,
    NEGO_OFFER, NEGO_RESULT, WALLET_BLOCKED, APPROVAL_REQUESTED, APPROVAL_RESOLVED,
    CONTRACT_BOOKED, MARKET_CLEARED, SETTLEMENT_DONE, SAVINGS_UPDATED, GUARD_FLAG,
    GRID_OUTAGE, CONSOLE_COMMAND, MANDATE_UPDATED, SIM_EVENT, HOUSE_UPDATED, SCHEDULE_UPDATED,
)

# Events an agent socket receives (section 6.1); the scoped ones only for its own house.
AGENT_EVENTS = (CLOCK_TICK, BLOCK_STATE, MARKET_CLEARED, HOUSE_UPDATED, MANDATE_UPDATED,
                APPROVAL_RESOLVED, CONSOLE_COMMAND, METER_READING, SETTLEMENT_DONE, SCHEDULE_UPDATED,
                SIM_EVENT, GRID_OUTAGE)
