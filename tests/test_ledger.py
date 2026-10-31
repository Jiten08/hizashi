"""Hash-chained ledger. entry_hash is fixed by the spec; append/verify come in R2.4."""
from hizashi_hub import db
from hizashi_hub.settlement import ledger
from hizashi_hub.settlement.ledger import GENESIS, entry_hash


def test_entry_hash_is_deterministic_and_chained():
    h1 = entry_hash(GENESIS, 1, "2026-10-31T10:00:00+05:30", "contract", "c1", '{"kwh":0.2}')
    assert h1 == entry_hash(GENESIS, 1, "2026-10-31T10:00:00+05:30", "contract", "c1", '{"kwh":0.2}')
    assert len(h1) == 64
    assert h1 != entry_hash(GENESIS, 1, "2026-10-31T10:00:00+05:30", "contract", "c1", '{"kwh":0.3}')
    assert entry_hash(h1, 2, "t", "k", "r", "p") != entry_hash(GENESIS, 2, "t", "k", "r", "p")


def test_verify_detects_tampering(tmp_path):
    """Append 3 entries, edit row 2's payload in sqlite -> verify == {"ok": False, "broken_at": 2}."""
    conn = db.connect(tmp_path / "t.db")
    db.init(conn)
    e1 = ledger.append(conn, "t1", "contract", "c1", {"seller": "h12", "buyer": "h14", "kwh": 0.2})
    e2 = ledger.append(conn, "t2", "settlement", "c1", {"seller": "h12", "buyer": "h14", "buyer_pays": 0.96})
    ledger.append(conn, "t3", "mandate", "h16", {"house": "h16"})
    assert e1["prev_hash"] == GENESIS and e2["prev_hash"] == e1["hash"]
    assert ledger.verify(conn) == {"ok": True, "entries": 3}
    assert [e["seq"] for e in ledger.entries(conn, "h14")] == [2, 1]
    assert [e["seq"] for e in ledger.entries(conn, "h16")] == [3]
    conn.execute("""UPDATE ledger SET payload = '{"buyer":"h14","buyer_pays":0.01,"seller":"h12"}' WHERE seq = 2""")
    assert ledger.verify(conn) == {"ok": False, "broken_at": 2}
    conn.close()
