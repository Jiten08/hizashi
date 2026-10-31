"""Hash-chained ledger. entry_hash is fixed by the spec; append/verify come in R2.4."""
import pytest

from hizashi_hub.settlement.ledger import GENESIS, entry_hash


def test_entry_hash_is_deterministic_and_chained():
    h1 = entry_hash(GENESIS, 1, "2026-10-31T10:00:00+05:30", "contract", "c1", '{"kwh":0.2}')
    assert h1 == entry_hash(GENESIS, 1, "2026-10-31T10:00:00+05:30", "contract", "c1", '{"kwh":0.2}')
    assert len(h1) == 64
    assert h1 != entry_hash(GENESIS, 1, "2026-10-31T10:00:00+05:30", "contract", "c1", '{"kwh":0.3}')
    assert entry_hash(h1, 2, "t", "k", "r", "p") != entry_hash(GENESIS, 2, "t", "k", "r", "p")


@pytest.mark.skip(reason="TODO(R2.4): ledger.append + verify")
def test_verify_detects_tampering():
    """Append 3 entries, edit row 2's payload in sqlite -> verify == {"ok": False, "broken_at": 2}."""
