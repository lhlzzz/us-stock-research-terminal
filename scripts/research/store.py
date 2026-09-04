"""SQLite-backed research evidence store. Raw rows are insert-only."""
from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any, Iterable, Mapping

from .evidence import utc_now

DEFAULT_DB = Path(__file__).resolve().parents[2] / "data" / "research-evidence" / "xiaomei22.sqlite"
SCHEMA = """
CREATE TABLE IF NOT EXISTS research_evidence (
    evidence_id TEXT PRIMARY KEY,
    symbol TEXT,
    as_of TEXT,
    published_at TEXT,
    effective_date TEXT,
    available_at TEXT,
    retrieved_at TEXT,
    source TEXT,
    source_type TEXT,
    source_url TEXT,
    document_id TEXT,
    claim_id TEXT,
    status TEXT,
    evidence_level TEXT,
    confidence REAL,
    raw_hash TEXT,
    content_hash TEXT,
    facts TEXT,
    metadata TEXT
);
CREATE UNIQUE INDEX IF NOT EXISTS uq_research_evidence_hash ON research_evidence(content_hash);
CREATE INDEX IF NOT EXISTS idx_research_evidence_symbol_as_of ON research_evidence(symbol, as_of);
CREATE INDEX IF NOT EXISTS idx_research_evidence_published ON research_evidence(symbol, published_at);
CREATE INDEX IF NOT EXISTS idx_research_evidence_effective ON research_evidence(symbol, effective_date);
CREATE INDEX IF NOT EXISTS idx_research_evidence_source_hash ON research_evidence(source, content_hash);

CREATE TABLE IF NOT EXISTS sec_documents (
    document_id TEXT PRIMARY KEY,
    source_url TEXT,
    retrieved_at TEXT,
    content_hash TEXT UNIQUE,
    published_at TEXT,
    effective_date TEXT,
    form TEXT,
    accession_number TEXT UNIQUE,
    cik TEXT,
    symbol TEXT,
    raw_payload TEXT
);
CREATE INDEX IF NOT EXISTS idx_sec_documents_symbol ON sec_documents(symbol, published_at);

CREATE TABLE IF NOT EXISTS sec_facts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    document_id TEXT,
    symbol TEXT,
    concept TEXT,
    unit TEXT,
    value TEXT,
    period TEXT,
    frame TEXT,
    form TEXT,
    filed TEXT,
    accn TEXT,
    fy TEXT,
    fp TEXT,
    selected INTEGER,
    supersedes TEXT
);
CREATE INDEX IF NOT EXISTS idx_sec_facts_symbol_period ON sec_facts(symbol, concept, period);
CREATE UNIQUE INDEX IF NOT EXISTS uq_sec_facts_identity ON sec_facts(symbol, concept, period, unit, accn, filed);

CREATE TABLE IF NOT EXISTS earnings_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    symbol TEXT,
    event_date TEXT,
    fiscal_period TEXT,
    announced_at TEXT,
    retrieved_at TEXT,
    source TEXT,
    source_url TEXT,
    status TEXT,
    UNIQUE(symbol, event_date, source)
);
CREATE INDEX IF NOT EXISTS idx_earnings_events_symbol_date ON earnings_events(symbol, event_date);

CREATE TABLE IF NOT EXISTS earnings_facts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    symbol TEXT,
    event_date TEXT,
    reported_eps REAL,
    consensus_eps REAL,
    eps_surprise REAL,
    reported_revenue REAL,
    consensus_revenue REAL,
    revenue_surprise REAL,
    source TEXT,
    UNIQUE(symbol, event_date, source)
);

CREATE TABLE IF NOT EXISTS estimate_revisions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    symbol TEXT,
    metric TEXT,
    estimate REAL,
    estimate_date TEXT,
    effective_date TEXT,
    source TEXT,
    analyst_count INTEGER,
    revision_direction TEXT,
    UNIQUE(symbol, metric, estimate_date, source)
);
CREATE INDEX IF NOT EXISTS idx_estimate_revisions_effective ON estimate_revisions(symbol, effective_date);

CREATE TABLE IF NOT EXISTS industry_nodes (
    node_id TEXT PRIMARY KEY,
    name TEXT,
    node_type TEXT,
    graph_snapshot_id TEXT,
    valid_from TEXT,
    valid_to TEXT,
    source TEXT,
    source_url TEXT
);

CREATE TABLE IF NOT EXISTS industry_edges (
    edge_id TEXT PRIMARY KEY,
    src TEXT,
    dst TEXT,
    relationship_type TEXT,
    directional INTEGER,
    source TEXT,
    source_url TEXT,
    effective_date TEXT,
    retrieved_at TEXT,
    confidence REAL,
    graph_snapshot_id TEXT,
    valid_from TEXT,
    valid_to TEXT
);
CREATE INDEX IF NOT EXISTS idx_industry_edges_valid ON industry_edges(valid_from, valid_to);

CREATE TABLE IF NOT EXISTS industry_snapshots (
    graph_snapshot_id TEXT PRIMARY KEY,
    as_of TEXT,
    content_hash TEXT,
    payload TEXT
);

CREATE TABLE IF NOT EXISTS universe_membership (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    symbol TEXT,
    universe_name TEXT,
    effective_from TEXT,
    effective_to TEXT,
    source TEXT,
    source_url TEXT,
    snapshot_date TEXT,
    version TEXT,
    UNIQUE(symbol, universe_name, effective_from, source)
);

CREATE TABLE IF NOT EXISTS research_snapshots (
    snapshot_id TEXT PRIMARY KEY,
    as_of TEXT,
    content_hash TEXT UNIQUE,
    research_version TEXT,
    code_commit TEXT,
    payload TEXT,
    generated_at TEXT
);

CREATE TABLE IF NOT EXISTS research_runs (
    run_id TEXT PRIMARY KEY,
    symbol TEXT,
    as_of TEXT,
    research_version TEXT,
    snapshot_hash TEXT,
    code_commit TEXT,
    started_at TEXT,
    completed_at TEXT,
    classification TEXT,
    evidence_count INTEGER,
    data_gaps TEXT,
    error_count INTEGER,
    duration_ms INTEGER,
    payload TEXT,
    UNIQUE(symbol, as_of, research_version, snapshot_hash)
);

CREATE TABLE IF NOT EXISTS failure_memory (
    failure_id TEXT PRIMARY KEY,
    symbol TEXT,
    as_of TEXT,
    research_layer TEXT,
    failure_type TEXT,
    expected TEXT,
    observed TEXT,
    diagnosis TEXT,
    root_cause TEXT,
    evidence_gap TEXT,
    outcome_horizon TEXT,
    severity TEXT,
    confidence REAL,
    source_episode TEXT,
    replay_id TEXT,
    created_at TEXT
);
CREATE INDEX IF NOT EXISTS idx_failure_memory_type ON failure_memory(failure_type);
CREATE INDEX IF NOT EXISTS idx_failure_memory_symbol ON failure_memory(symbol, as_of);

CREATE TABLE IF NOT EXISTS research_learning_patterns (
    pattern_id TEXT PRIMARY KEY,
    research_layer TEXT,
    pattern_type TEXT,
    condition TEXT,
    outcome TEXT,
    sample_count INTEGER,
    success_count INTEGER,
    failure_count INTEGER,
    confidence REAL,
    source_failures TEXT,
    source_samples TEXT,
    created_at TEXT,
    updated_at TEXT
);

CREATE TABLE IF NOT EXISTS research_evidence_links (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    claim_id TEXT,
    evidence_id TEXT,
    document_id TEXT,
    sample_id TEXT,
    run_id TEXT
);

CREATE TABLE IF NOT EXISTS provider_attempts (
    attempt_id TEXT PRIMARY KEY,
    provider TEXT,
    request TEXT,
    symbol TEXT,
    entity_id TEXT,
    as_of TEXT,
    attempt INTEGER,
    started_at TEXT,
    completed_at TEXT,
    status TEXT,
    http_status INTEGER,
    source TEXT,
    fallback TEXT,
    fallback_used INTEGER,
    error TEXT,
    error_class TEXT
);

CREATE TABLE IF NOT EXISTS research_outcomes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    symbol TEXT,
    as_of TEXT,
    horizon INTEGER,
    return_value REAL,
    complete INTEGER,
    ticket_id TEXT,
    sample_id TEXT,
    UNIQUE(symbol, as_of, horizon)
);
CREATE TABLE IF NOT EXISTS replay_samples (
    sample_id TEXT PRIMARY KEY,
    ticket_id TEXT NOT NULL,
    symbol TEXT,
    output_date TEXT,
    replay_date TEXT NOT NULL,
    replay_horizon TEXT NOT NULL
);
CREATE UNIQUE INDEX IF NOT EXISTS uq_replay_sample_identity
    ON replay_samples(ticket_id, replay_horizon, replay_date);
"""


def connect(path: Path | None = None) -> sqlite3.Connection:
    """Single SQLite owner for research evidence / lineage / audit."""
    db_path = path or DEFAULT_DB
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    conn.executescript(SCHEMA)
    return conn


def persist_replay_sample(conn: sqlite3.Connection, item: Mapping[str, Any]) -> bool:
    from .sample_identity import sample_id

    identity = item.get("sample_id") or sample_id(
        ticket_id=item.get("ticket_id"),
        replay_horizon=item.get("replay_horizon") or item.get("horizon_days"),
        replay_date=item.get("replay_date") or item.get("as_of") or item.get("output_date"),
        symbol=item.get("symbol"),
        output_date=item.get("output_date"),
    )
    return insert_ignore(
        conn,
        """INSERT OR IGNORE INTO replay_samples(
            sample_id, ticket_id, symbol, output_date, replay_date, replay_horizon
        ) VALUES (?,?,?,?,?,?)""",
        (
            identity,
            str(item.get("ticket_id")),
            item.get("symbol"),
            None if item.get("output_date") is None else str(item.get("output_date"))[:10],
            str(item.get("replay_date") or item.get("as_of") or item.get("output_date"))[:10],
            str(item.get("replay_horizon") or item.get("horizon_days")),
        ),
    )


def _json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, default=str)


def insert_ignore(conn: sqlite3.Connection, sql: str, params: tuple[Any, ...]) -> bool:
    before = conn.total_changes
    conn.execute(sql, params)
    return conn.total_changes > before


def persist_evidence(conn: sqlite3.Connection, item: Mapping[str, Any]) -> bool:
    return insert_ignore(
        conn,
        """INSERT OR IGNORE INTO research_evidence(
            evidence_id, symbol, as_of, published_at, effective_date, available_at, retrieved_at,
            source, source_type, source_url, document_id, claim_id, status, evidence_level,
            confidence, raw_hash, content_hash, facts, metadata
        ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
        (
            item.get("evidence_id"),
            item.get("symbol"),
            item.get("as_of"),
            item.get("published_at"),
            item.get("effective_date"),
            item.get("available_at"),
            item.get("retrieved_at"),
            item.get("source"),
            item.get("source_type"),
            item.get("source_url"),
            item.get("document_id"),
            item.get("claim_id"),
            item.get("status"),
            item.get("evidence_level"),
            item.get("confidence"),
            item.get("raw_hash"),
            item.get("content_hash"),
            _json(item.get("facts") or {}),
            _json(item.get("metadata") or {}),
        ),
    )


def persist_sec_facts(conn: sqlite3.Connection, facts: Iterable[Mapping[str, Any]], *, document_id: str | None = None, symbol: str | None = None) -> int:
    inserted = 0
    for row in facts:
        if insert_ignore(
            conn,
            """INSERT OR IGNORE INTO sec_facts(
                document_id, symbol, concept, unit, value, period, frame, form, filed, accn, fy, fp, selected, supersedes
            ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (
                row.get("document_id") or document_id,
                row.get("symbol") or symbol,
                row.get("concept"),
                row.get("unit"),
                None if row.get("value") is None else str(row.get("value")),
                row.get("period"),
                row.get("frame"),
                row.get("form"),
                row.get("filed"),
                row.get("accn"),
                None if row.get("fy") is None else str(row.get("fy")),
                row.get("fp"),
                1 if row.get("selected") else 0,
                _json(row.get("supersedes") or []),
            ),
        ):
            inserted += 1
    return inserted


def persist_earnings_events(conn: sqlite3.Connection, events: Iterable[Mapping[str, Any]]) -> int:
    inserted = 0
    for row in events:
        if insert_ignore(
            conn,
            """INSERT OR IGNORE INTO earnings_events(
                symbol, event_date, fiscal_period, announced_at, retrieved_at, source, source_url, status
            ) VALUES (?,?,?,?,?,?,?,?)""",
            (
                row.get("symbol"),
                row.get("event_date"),
                row.get("fiscal_period"),
                row.get("announced_at"),
                row.get("retrieved_at"),
                row.get("source"),
                row.get("source_url"),
                row.get("status"),
            ),
        ):
            inserted += 1
        conn.execute(
            """INSERT OR IGNORE INTO earnings_facts(
                symbol, event_date, reported_eps, consensus_eps, eps_surprise, reported_revenue, consensus_revenue, revenue_surprise, source
            ) VALUES (?,?,?,?,?,?,?,?,?)""",
            (
                row.get("symbol"),
                row.get("event_date"),
                row.get("reported_eps"),
                row.get("consensus_eps"),
                row.get("eps_surprise"),
                row.get("reported_revenue"),
                row.get("consensus_revenue"),
                row.get("revenue_surprise"),
                row.get("source"),
            ),
        )
    return inserted


def persist_estimate_revisions(conn: sqlite3.Connection, rows: Iterable[Mapping[str, Any]]) -> int:
    inserted = 0
    for row in rows:
        if insert_ignore(
            conn,
            """INSERT OR IGNORE INTO estimate_revisions(
                symbol, metric, estimate, estimate_date, effective_date, source, analyst_count, revision_direction
            ) VALUES (?,?,?,?,?,?,?,?)""",
            (
                row.get("symbol"),
                row.get("metric"),
                row.get("estimate"),
                row.get("estimate_date"),
                row.get("effective_date"),
                row.get("source"),
                row.get("analyst_count"),
                row.get("revision_direction"),
            ),
        ):
            inserted += 1
    return inserted


def persist_sec_document(conn: sqlite3.Connection, doc: Mapping[str, Any]) -> bool:
    return insert_ignore(
        conn,
        """INSERT OR IGNORE INTO sec_documents(
            document_id, source_url, retrieved_at, content_hash, published_at, effective_date,
            form, accession_number, cik, symbol, raw_payload
        ) VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
        (
            doc.get("document_id"),
            doc.get("source_url"),
            doc.get("retrieved_at"),
            doc.get("content_hash"),
            doc.get("published_at"),
            doc.get("effective_date"),
            doc.get("form"),
            doc.get("accession_number"),
            doc.get("cik"),
            doc.get("symbol"),
            _json(doc.get("raw_payload") or {}),
        ),
    )


def persist_failure(conn: sqlite3.Connection, item: Mapping[str, Any]) -> bool:
    return insert_ignore(
        conn,
        """INSERT OR IGNORE INTO failure_memory(
            failure_id, symbol, as_of, research_layer, failure_type, expected, observed,
            diagnosis, root_cause, evidence_gap, outcome_horizon, severity, confidence,
            source_episode, replay_id, created_at
        ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
        (
            item.get("failure_id"),
            item.get("symbol"),
            item.get("as_of"),
            item.get("research_layer"),
            item.get("failure_type"),
            _json(item.get("expected")),
            _json(item.get("observed")),
            item.get("diagnosis"),
            item.get("root_cause"),
            item.get("evidence_gap"),
            item.get("outcome_horizon"),
            item.get("severity"),
            item.get("confidence"),
            item.get("source_episode"),
            item.get("replay_id"),
            item.get("created_at") or utc_now(),
        ),
    )


def persist_pattern(conn: sqlite3.Connection, item: Mapping[str, Any]) -> bool:
    return insert_ignore(
        conn,
        """INSERT OR IGNORE INTO research_learning_patterns(
            pattern_id, research_layer, pattern_type, condition, outcome, sample_count,
            success_count, failure_count, confidence, source_failures, source_samples,
            created_at, updated_at
        ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)""",
        (
            item.get("pattern_id"),
            item.get("research_layer"),
            item.get("pattern_type"),
            _json(item.get("condition") or {}),
            _json(item.get("outcome") or {}),
            item.get("sample_count") or 0,
            item.get("success_count") or 0,
            item.get("failure_count") or 0,
            item.get("confidence"),
            _json(item.get("source_failures") or []),
            _json(item.get("source_samples") or []),
            item.get("created_at") or utc_now(),
            item.get("updated_at") or utc_now(),
        ),
    )


def persist_snapshot(conn: sqlite3.Connection, snapshot: Mapping[str, Any]) -> bool:
    return insert_ignore(
        conn,
        """INSERT OR IGNORE INTO research_snapshots(
            snapshot_id, as_of, content_hash, research_version, code_commit, payload, generated_at
        ) VALUES (?,?,?,?,?,?,?)""",
        (
            snapshot.get("content_hash"),
            snapshot.get("as_of"),
            snapshot.get("content_hash"),
            snapshot.get("research_version"),
            snapshot.get("code_commit"),
            _json(snapshot),
            snapshot.get("generated_at") or utc_now(),
        ),
    )


def persist_run(conn: sqlite3.Connection, run: Mapping[str, Any]) -> dict[str, Any]:
    existing = conn.execute(
        """SELECT run_id, payload FROM research_runs
           WHERE symbol=? AND as_of=? AND research_version=? AND snapshot_hash=?""",
        (run.get("symbol"), run.get("as_of"), run.get("research_version"), run.get("snapshot_hash")),
    ).fetchone()
    if existing:
        payload = json.loads(existing["payload"])
        payload["reused"] = True
        payload["run_id"] = existing["run_id"]
        return payload
    conn.execute(
        """INSERT INTO research_runs(
            run_id, symbol, as_of, research_version, snapshot_hash, code_commit, started_at,
            completed_at, classification, evidence_count, data_gaps, error_count, duration_ms, payload
        ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
        (
            run.get("run_id"),
            run.get("symbol"),
            run.get("as_of"),
            run.get("research_version"),
            run.get("snapshot_hash"),
            run.get("code_commit"),
            run.get("started_at"),
            run.get("completed_at"),
            run.get("classification"),
            run.get("evidence_count") or 0,
            _json(run.get("data_gaps") or []),
            run.get("error_count") or 0,
            run.get("duration_ms"),
            _json(run),
        ),
    )
    copied = dict(run)
    copied["reused"] = False
    return copied


def persist_outcomes(conn: sqlite3.Connection, symbol: str, as_of: str, horizons: Mapping[Any, Mapping[str, Any]]) -> None:
    for horizon, payload in horizons.items():
        conn.execute(
            """INSERT OR IGNORE INTO research_outcomes(symbol, as_of, horizon, return_value, complete)
               VALUES (?,?,?,?,?)""",
            (
                str(symbol).upper(),
                as_of,
                int(horizon),
                payload.get("return"),
                1 if payload.get("complete") else 0,
            ),
        )


def persist_provider_attempts(conn: sqlite3.Connection, attempts: Iterable[Mapping[str, Any]]) -> None:
    for item in attempts:
        conn.execute(
            """INSERT OR IGNORE INTO provider_attempts(
                attempt_id, provider, request, symbol, entity_id, as_of, attempt, started_at,
                completed_at, status, http_status, source, fallback, fallback_used, error, error_class
            ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (
                item.get("attempt_id"),
                item.get("provider"),
                item.get("request"),
                item.get("symbol"),
                item.get("entity_id"),
                item.get("as_of"),
                item.get("attempt"),
                item.get("started_at"),
                item.get("completed_at"),
                item.get("status"),
                item.get("http_status"),
                item.get("source"),
                item.get("fallback"),
                1 if item.get("fallback_used") else 0,
                item.get("error"),
                item.get("error_class"),
            ),
        )


def persist_universe_membership(conn: sqlite3.Connection, rows: Iterable[Mapping[str, Any]]) -> int:
    inserted = 0
    for row in rows:
        if insert_ignore(
            conn,
            """INSERT OR IGNORE INTO universe_membership(
                symbol, universe_name, effective_from, effective_to, source, source_url, snapshot_date, version
            ) VALUES (?,?,?,?,?,?,?,?)""",
            (
                row.get("symbol"),
                row.get("universe_name"),
                row.get("effective_from"),
                row.get("effective_to"),
                row.get("source"),
                row.get("source_url"),
                row.get("snapshot_date"),
                row.get("version"),
            ),
        ):
            inserted += 1
    return inserted


def persist_industry_snapshot(conn: sqlite3.Connection, snapshot: Mapping[str, Any]) -> bool:
    return insert_ignore(
        conn,
        """INSERT OR IGNORE INTO industry_snapshots(graph_snapshot_id, as_of, content_hash, payload)
           VALUES (?,?,?,?)""",
        (
            snapshot.get("graph_snapshot_id") or snapshot.get("content_hash"),
            snapshot.get("as_of"),
            snapshot.get("content_hash"),
            _json(snapshot),
        ),
    )


def load_failures(conn: sqlite3.Connection, *, symbol: str | None = None) -> list[dict[str, Any]]:
    if symbol:
        rows = conn.execute("SELECT * FROM failure_memory WHERE symbol=?", (str(symbol).upper(),)).fetchall()
    else:
        rows = conn.execute("SELECT * FROM failure_memory").fetchall()
    return [dict(row) for row in rows]


def load_patterns(conn: sqlite3.Connection) -> list[dict[str, Any]]:
    return [dict(row) for row in conn.execute("SELECT * FROM research_learning_patterns").fetchall()]


def evidence_lineage(conn: sqlite3.Connection, *, symbol: str, as_of: str | None = None) -> list[dict[str, Any]]:
    if as_of:
        rows = conn.execute(
            "SELECT * FROM research_evidence WHERE symbol=? AND as_of=?",
            (str(symbol).upper(), as_of),
        ).fetchall()
    else:
        rows = conn.execute("SELECT * FROM research_evidence WHERE symbol=?", (str(symbol).upper(),)).fetchall()
    lineage = []
    for row in rows:
        payload = dict(row)
        payload["facts"] = json.loads(payload["facts"]) if payload.get("facts") else {}
        payload["metadata"] = json.loads(payload["metadata"]) if payload.get("metadata") else {}
        lineage.append({
            "claim": payload.get("claim_id"),
            "evidence": payload,
            "source": payload.get("source"),
            "document": payload.get("document_id"),
            "retrieved": payload.get("retrieved_at"),
            "as_of": payload.get("as_of"),
        })
    return lineage
