"""Verify + book contracts: seller_sig and buyer_sig against registry pubkeys, block OPEN,
seller != buyer, guard checks; set open_access, add market_sig, store, ledger, contract.booked."""
from hizashi_shared.models import Contract


def book(contract: Contract) -> Contract:
    raise NotImplementedError("TODO(R1.6, Anurag)")
