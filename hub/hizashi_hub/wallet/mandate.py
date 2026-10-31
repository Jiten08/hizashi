"""Mandate store + versions (table mandates). PUT creates a new version, a ledger entry and mandate.updated."""
from hizashi_shared.models import Mandate


def current(house: str) -> Mandate:
    raise NotImplementedError("TODO(R1.1, Jiten)")


def update(house: str, new: Mandate) -> Mandate:
    raise NotImplementedError("TODO(R2.8, Jiten)")
