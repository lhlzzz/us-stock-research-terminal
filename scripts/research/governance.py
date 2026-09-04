"""Bounded self-evolution ledger. Frozen principles cannot be patched."""
from __future__ import annotations

from typing import Any, Mapping

from .boundary import PRODUCTION_BOUNDARY
from .contracts import ALLOWED_SELF_EVOLVE, FROZEN_SELF_EVOLVE

FORBIDDEN_KEYS = {
    "buffett_principles",
    "serenity_ontology",
    "fact_inference_semantics",
    "evidence_hierarchy",
    "no_lookahead_rules",
    "production_safety_boundary",
    "produces_pick",
    "ranking_key",
}


def evolve_change(
    *,
    key: str,
    before: Any,
    after: Any,
    evidence: Mapping[str, Any] | None = None,
    validation: Mapping[str, Any] | None = None,
    version: str | None = None,
) -> dict[str, Any]:
    frozen = key in FORBIDDEN_KEYS or key in FROZEN_SELF_EVOLVE
    allowed_family = any(token in key for token in ("weight", "threshold", "ranking_contribution", "calibration", "priorit"))
    if frozen or not allowed_family:
        return {
            "action": "REJECT",
            "key": key,
            "before": before,
            "after": before,
            "reason": "frozen" if frozen else "not_an_allowed_knob",
            "allowed": list(ALLOWED_SELF_EVOLVE),
            "forbidden": list(FROZEN_SELF_EVOLVE),
            "rollback": before,
            "production_boundary": PRODUCTION_BOUNDARY,
        }
    return {
        "action": "RECORD",
        "key": key,
        "version": version or "research_os_2.0",
        "before": before,
        "after": after,
        "evidence": dict(evidence or {}),
        "validation": dict(validation or {}),
        "rollback": before,
        "does_not_write_production_weights": True,
        "production_boundary": PRODUCTION_BOUNDARY,
    }
