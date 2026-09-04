from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_sqlite_connect_only_in_research_store():
    hits = []
    for path in (ROOT / "scripts").rglob("*.py"):
        rel = str(path.relative_to(ROOT)).replace("\\", "/")
        if "/__pycache__/" in rel:
            continue
        text = path.read_text(encoding="utf-8")
        if "sqlite3.connect(" in text:
            hits.append(rel)
    assert hits == ["scripts/research/store.py"]


def test_postgres_is_operational_owner():
    models = (ROOT / "scripts/db/models.py").read_text(encoding="utf-8")
    store = (ROOT / "scripts/research/store.py").read_text(encoding="utf-8")
    assert "class Ticket" in models or "tickets" in models.lower()
    assert "research evidence" in store.lower() or "xiaomei22.sqlite" in store
