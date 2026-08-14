"""
xiaomei neural vector store for case similarity search.
Aligned with xiaogu's xiaogu_case_vector_store.py architecture.

Uses sentence-transformers for neural embeddings with HNSW cosine index.
Falls back to structured embeddings if neural model unavailable.
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import threading
from datetime import date, datetime
from typing import Any

import numpy as np

logger = logging.getLogger(__name__)

# Configuration
EMBED_BACKEND = os.environ.get("XIAOMEI_EMBED_BACKEND", "auto")  # neural|structured|auto
EMBED_MODEL = os.environ.get("XIAOMEI_EMBED_MODEL", "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2")
STRUCTURED_DIM = int(os.environ.get("XIAOMEI_CASE_EMBED_DIM", "64"))

# Global model cache
_model_lock = threading.Lock()
_model = None
_model_dim = None


def _get_neural_model():
    """Lazy-load sentence-transformers model (thread-safe)."""
    global _model, _model_dim
    if _model is not None:
        return _model, _model_dim

    with _model_lock:
        if _model is not None:
            return _model, _model_dim

        try:
            from sentence_transformers import SentenceTransformer
            logger.info(f"Loading neural embedding model: {EMBED_MODEL}")
            _model = SentenceTransformer(EMBED_MODEL)
            _model_dim = _model.get_sentence_embedding_dimension()
            logger.info(f"Neural model loaded: dim={_model_dim}")
            return _model, _model_dim
        except Exception as e:
            logger.warning(f"Failed to load neural model: {e}")
            return None, None


def _numeric_as_text(value: float, name: str) -> str:
    """Convert numeric feature to text representation for neural model."""
    if value is None:
        return f"{name}: missing"
    if abs(value) < 0.001:
        return f"{name}: zero"
    direction = "positive" if value > 0 else "negative"
    magnitude = "strong" if abs(value) > 0.5 else "moderate" if abs(value) > 0.1 else "weak"
    return f"{name}: {magnitude} {direction} ({value:.4f})"


def case_text_from_ticket(ticket: dict) -> str:
    """Serialize ticket data into text for embedding."""
    parts = []

    # Basic info
    symbol = ticket.get("symbol", "unknown")
    parts.append(f"Stock: {symbol}")

    # Scores
    for score_key in ["ticket_score", "market_score", "catalyst_score"]:
        val = ticket.get(score_key)
        if val is not None:
            parts.append(_numeric_as_text(float(val), score_key))

    # Classification
    classification = ticket.get("classification", "")
    if classification:
        parts.append(f"Classification: {classification}")

    # Entry reason
    entry_reason = ticket.get("entry_reason", "")
    if entry_reason:
        parts.append(f"Reason: {entry_reason[:200]}")

    # Factor scores
    factor_keys = [
        "prior_20d_momentum", "five_day_acceleration", "relative_strength_vs_equal_weight",
        "volume_weighted_momentum", "closing_strength_5d", "volume_confirmation_ratio",
        "rsi_14", "momentum_quality", "breakout_score", "reversal_quality"
    ]
    for key in factor_keys:
        val = ticket.get(key)
        if val is not None:
            parts.append(_numeric_as_text(float(val), key))

    # Risk
    risk = ticket.get("risk_verdict", "")
    if risk:
        parts.append(f"Risk: {risk}")

    return " | ".join(parts)


def _structured_embedding(text: str, dim: int = STRUCTURED_DIM) -> np.ndarray:
    """Deterministic structured embedding (fallback)."""
    vec = np.zeros(dim, dtype=np.float32)

    # Hash-based token embedding
    tokens = text.lower().split()
    for token in tokens:
        h = int(hashlib.sha256(token.encode()).hexdigest(), 16)
        idx = h % dim
        vec[idx] += 1.0

    # Normalize
    norm = np.linalg.norm(vec)
    if norm > 0:
        vec = vec / norm

    return vec


def embed_text(text: str, backend: str = None) -> tuple[np.ndarray, str]:
    """Embed text using specified or auto-detected backend.

    Returns: (embedding_vector, backend_name)
    """
    backend = backend or EMBED_BACKEND

    if backend == "auto":
        # Try neural first
        model, dim = _get_neural_model()
        if model is not None:
            vec = model.encode(text, normalize_embeddings=True)
            return vec.astype(np.float32), "neural"
        else:
            return _structured_embedding(text), "structured"

    elif backend == "neural":
        model, dim = _get_neural_model()
        if model is None:
            raise RuntimeError("Neural model not available")
        vec = model.encode(text, normalize_embeddings=True)
        return vec.astype(np.float32), "neural"

    elif backend == "structured":
        return _structured_embedding(text), "structured"

    else:
        raise ValueError(f"Unknown backend: {backend}")


def get_embedding_dim(backend: str = None) -> int:
    """Get embedding dimension for the specified backend."""
    backend = backend or EMBED_BACKEND

    if backend == "neural" or backend == "auto":
        model, dim = _get_neural_model()
        if dim is not None:
            return dim

    return STRUCTURED_DIM


def ensure_case_embedding_table(engine, backend: str = None) -> int:
    """Create or align pick_case_embeddings table with current backend dimension.

    Returns: embedding dimension
    """
    from sqlalchemy import text

    dim = get_embedding_dim(backend)

    with engine.connect() as conn:
        # Check if table exists
        result = conn.execute(text(
            "SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'pick_case_embeddings')"
        ))
        exists = result.scalar()

        if not exists:
            # Create table
            conn.execute(text(f"""
                CREATE TABLE pick_case_embeddings (
                    id SERIAL PRIMARY KEY,
                    trade_date DATE NOT NULL,
                    symbol VARCHAR(10) NOT NULL,
                    decision VARCHAR(30) DEFAULT 'PAPER_PICK',
                    stock_name VARCHAR(50),
                    final_score NUMERIC(8,4),
                    case_text TEXT,
                    embedding VECTOR({dim}),
                    metadata JSONB,
                    t1_return NUMERIC(8,6),
                    created_at TIMESTAMP DEFAULT NOW(),
                    updated_at TIMESTAMP DEFAULT NOW(),
                    UNIQUE(trade_date, symbol, decision)
                )
            """))
            conn.execute(text(
                "CREATE INDEX idx_pick_case_embeddings_hnsw ON pick_case_embeddings "
                "USING hnsw (embedding vector_cosine_ops) WITH (m = 16, ef_construction = 64)"
            ))
            conn.commit()
            logger.info(f"Created pick_case_embeddings table with dim={dim}")
        else:
            # Check current dimension
            result = conn.execute(text(
                "SELECT atttypmod FROM pg_attribute "
                "WHERE attrelid = 'pick_case_embeddings'::regclass AND attname = 'embedding'"
            ))
            current_dim = result.scalar()
            if current_dim and current_dim - 4 != dim:
                logger.warning(f"Dimension mismatch: table={current_dim - 4}, backend={dim}. Consider migration.")

    return dim


def upsert_pick_case(
    engine,
    trade_date: date,
    symbol: str,
    decision: str,
    ticket_data: dict,
    t1_return: float = None,
    backend: str = None,
) -> dict:
    """Store/update a pick case embedding.

    Returns: {id, backend, dim}
    """
    from sqlalchemy import text

    case_text = case_text_from_ticket(ticket_data)
    embedding, actual_backend = embed_text(case_text, backend)
    dim = len(embedding)

    # Convert to pgvector format
    embedding_str = "[" + ",".join(str(x) for x in embedding.tolist()) + "]"

    metadata = {
        "backend": actual_backend,
        "dim": dim,
        "model": EMBED_MODEL if actual_backend == "neural" else "structured",
        "embedded_at": datetime.now().isoformat(),
    }

    with engine.connect() as conn:
        result = conn.execute(text("""
            INSERT INTO pick_case_embeddings
                (trade_date, symbol, decision, stock_name, final_score, case_text, embedding, metadata, t1_return)
            VALUES
                (:trade_date, :symbol, :decision, :stock_name, :final_score, :case_text, CAST(:embedding AS vector), :metadata, :t1_return)
            ON CONFLICT (trade_date, symbol, decision) DO UPDATE SET
                stock_name = EXCLUDED.stock_name,
                final_score = EXCLUDED.final_score,
                case_text = EXCLUDED.case_text,
                embedding = EXCLUDED.embedding,
                metadata = EXCLUDED.metadata,
                t1_return = EXCLUDED.t1_return,
                updated_at = NOW()
            RETURNING id
        """), {
            "trade_date": trade_date,
            "symbol": symbol,
            "decision": decision,
            "stock_name": ticket_data.get("stock_name", symbol),
            "final_score": ticket_data.get("ticket_score"),
            "case_text": case_text,
            "embedding": embedding_str,
            "metadata": json.dumps(metadata),
            "t1_return": t1_return,
        })
        row_id = result.scalar()
        conn.commit()

    return {"id": row_id, "backend": actual_backend, "dim": dim}


def search_similar_cases(
    engine,
    query_text: str,
    limit: int = 10,
    backend: str = None,
) -> list[dict]:
    """Search for similar historical cases using cosine similarity.

    Returns: list of {trade_date, symbol, decision, final_score, t1_return, similarity, case_text}
    """
    from sqlalchemy import text

    query_embedding, actual_backend = embed_text(query_text, backend)
    embedding_str = "[" + ",".join(str(x) for x in query_embedding.tolist()) + "]"

    with engine.connect() as conn:
        result = conn.execute(text("""
            SELECT
                trade_date, symbol, decision, stock_name, final_score, t1_return,
                case_text, metadata,
                1 - (embedding <=> CAST(:query AS vector)) as similarity
            FROM pick_case_embeddings
            WHERE embedding IS NOT NULL
            ORDER BY embedding <=> CAST(:query AS vector)
            LIMIT :limit
        """), {
            "query": embedding_str,
            "limit": limit,
        })

        rows = []
        for row in result:
            rows.append({
                "trade_date": row[0].isoformat() if row[0] else None,
                "symbol": row[1],
                "decision": row[2],
                "stock_name": row[3],
                "final_score": float(row[4]) if row[4] else None,
                "t1_return": float(row[5]) if row[5] else None,
                "case_text": row[6],
                "metadata": row[7],
                "similarity": float(row[8]) if row[8] else None,
            })

    return rows


def upsert_top10_cases_from_db(engine, trade_date: date, backend: str = None) -> int:
    """Persist top10 daily_candidates as TOP10 vectors for retrieval.

    Returns: number of cases upserted
    """
    from sqlalchemy import text

    with engine.connect() as conn:
        result = conn.execute(text("""
            SELECT symbol, stock_name, final_score, market_score, catalyst_score,
                   decision, candidate_entry_reason, selection_reason
            FROM daily_candidates
            WHERE trade_date = :trade_date
            ORDER BY final_score DESC NULLS LAST
            LIMIT 10
        """), {"trade_date": trade_date})

        rows = result.fetchall()

    count = 0
    for row in rows:
        ticket_data = {
            "symbol": row[0],
            "stock_name": row[1],
            "ticket_score": float(row[2]) if row[2] else None,
            "market_score": float(row[3]) if row[3] else None,
            "catalyst_score": float(row[4]) if row[4] else None,
            "classification": row[5],
            "entry_reason": str(row[6]) if row[6] else None,
            "risk_verdict": row[7],
        }
        upsert_pick_case(engine, trade_date, row[0], "TOP10", ticket_data, backend=backend)
        count += 1

    logger.info(f"Upserted {count} TOP10 cases for {trade_date}")
    return count


def rebuild_all_case_embeddings(engine, backend: str = None) -> int:
    """Re-embed all stored cases with current backend.

    Returns: number of cases re-embedded
    """
    from sqlalchemy import text

    with engine.connect() as conn:
        result = conn.execute(text("""
            SELECT id, trade_date, symbol, decision, case_text, t1_return
            FROM pick_case_embeddings
            WHERE case_text IS NOT NULL
            ORDER BY trade_date, symbol
        """))
        rows = result.fetchall()

    count = 0
    for row in rows:
        case_text = row[4]
        if not case_text:
            continue

        embedding, actual_backend = embed_text(case_text, backend)
        embedding_str = "[" + ",".join(str(x) for x in embedding.tolist()) + "]"

        with engine.connect() as conn:
            conn.execute(text("""
                UPDATE pick_case_embeddings
                SET embedding = CAST(:embedding AS vector),
                    metadata = jsonb_set(
                        COALESCE(metadata, '{}'),
                        '{backend}',
                        CAST(:backend AS jsonb)
                    ),
                    updated_at = NOW()
                WHERE id = :id
            """), {
                "id": row[0],
                "embedding": embedding_str,
                "backend": json.dumps(actual_backend),
            })
            conn.commit()
        count += 1

    logger.info(f"Re-embedded {count} cases with backend={backend or EMBED_BACKEND}")
    return count


def similar_cases_ranking_boost(
    similar_cases: list[dict],
    max_boost: float = 0.05,
) -> float:
    """Compute bounded soft boost from similar historical winners.

    Never forces picks - just a small nudge based on historical similarity.
    """
    if not similar_cases:
        return 0.0

    # Weight by similarity and historical return
    weighted_sum = 0.0
    weight_total = 0.0

    for case in similar_cases[:5]:  # Top 5 most similar
        similarity = case.get("similarity", 0)
        t1_return = case.get("t1_return")

        if similarity is None or t1_return is None:
            continue

        # Positive return contributes positive boost, negative contributes negative
        weight = max(0, similarity)
        weighted_sum += weight * t1_return
        weight_total += weight

    if weight_total == 0:
        return 0.0

    raw_boost = weighted_sum / weight_total

    # Bound the boost
    return max(-max_boost, min(max_boost, raw_boost))
