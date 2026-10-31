"""All /api routers. The Twilio webhook router is mounted separately at /webhooks."""
from fastapi import APIRouter

from . import approvals, console, guard, houses, ledger, market, push, schedules, state, wallet

router = APIRouter(prefix="/api")
for _module in (state, houses, wallet, approvals, market, ledger, guard, console, push, schedules):
    router.include_router(_module.router)
