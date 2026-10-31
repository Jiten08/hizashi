"""All /api routers. The Twilio webhook router is mounted separately at /webhooks."""
from fastapi import APIRouter

from . import approvals, console, guard, ledger, market, state, wallet

router = APIRouter(prefix="/api")
for _module in (state, wallet, approvals, market, ledger, guard, console):
    router.include_router(_module.router)
