"""Per-brain validation. Research prediction is checked against future outcomes only."""
from __future__ import annotations

from typing import Any, Iterable, Mapping

from .boundary import PRODUCTION_BOUNDARY
from .decision import validation_metrics
from .learning import research_data_ready

BRAINS = ("company_quality", "industry", "capital", "market_setup", "factor", "portfolio_context", "thesis")


def brain_validation(name: str, samples: Iterable[Mapping[str, Any]] | None = None) -> dict[str, Any]:
    rows = [dict(row) for row in samples or []]
    metrics = validation_metrics(rows)
    ready = research_data_ready(rows)
    return {
        "brain": name,
        "metrics": metrics,
        "readiness": ready,
        "status": "VALIDATION_GAP" if ready.get("status") != "RESEARCH_DATA_READY" else "READY",
        "prediction_to_outcome": "independent future outcome only",
        "production_boundary": PRODUCTION_BOUNDARY,
    }


def all_brain_validations(samples: Iterable[Mapping[str, Any]] | None = None) -> dict[str, Any]:
    rows = list(samples or [])
    return {name: brain_validation(name, rows) for name in BRAINS}
