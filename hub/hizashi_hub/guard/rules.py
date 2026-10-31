"""Guard rules (Phase 3): bad signature, impossible reading (solar at night, export >
inverter), wash trade (self or both ways in one block), price coordination (2+ sellers
identical asks for 4+ blocks in a row, KERC 5(a)(ii)), replay (seen nonce/seq)."""
from hizashi_shared.models import Contract, MeterReading, Offer


def check_contract(contract: Contract) -> list[str]:
    """Reasons to refuse booking; empty = ok."""
    raise NotImplementedError("TODO(N2, Jiten)")


def check_reading(reading: MeterReading) -> list[str]:
    raise NotImplementedError("TODO(N2, Jiten)")


def check_offer(offer: Offer) -> list[str]:
    raise NotImplementedError("TODO(N2, Jiten)")
