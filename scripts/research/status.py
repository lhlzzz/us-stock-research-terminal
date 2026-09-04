"""Xiaomei 2.0 completion status. Validated research only; never 'feature implemented'."""
from __future__ import annotations

from typing import Any, Mapping

from .boundary import PRODUCTION_BOUNDARY

FLOW = (
    "External Data",
    "Fact Store",
    "Evidence Layer",
    "Company Brain",
    "Industry Brain",
    "Capital Brain",
    "Market Brain",
    "Risk Brain",
    "Portfolio Context",
    "Historical Analogues",
    "Contradiction Engine",
    "Research Decision",
    "Paper Review",
    "Forward Outcome",
    "Calibration",
    "Learning",
    "Future Research",
)

FORBIDDEN = (
    "Skill → Direct Buy",
    "Obsidian holding → Score bonus",
    "Buffett → T+1 prediction",
    "Serenity → direct price prediction",
    "Social sentiment → Fundamental fact",
    "High IC → permanent weight",
    "Historical return → future guarantee",
    "Random split",
    "Future leakage",
    "Nearest-run fabrication",
)


def completion_status(coverage: Mapping[str, Any] | None = None) -> dict[str, Any]:
    coverage = dict(coverage or {})
    gaps = []
    if (coverage.get("valid_ticket_count") or 0) < 30:
        gaps.append("VALIDATION_GAP")
    if (coverage.get("company_data_coverage") or 0) < 1:
        gaps.append("DATA_GAP")
    if coverage.get("factor_stability") in (None, "INSUFFICIENT_DATA"):
        gaps.append("MODEL_GAP")
    unique = []
    for item in gaps:
        if item not in unique:
            unique.append(item)
    if not unique and coverage.get("brains_validated"):
        status = "COMPLETE_RESEARCH_OS"
    elif unique:
        status = unique[0] if len(unique) == 1 else "PARTIAL"
    else:
        status = "PARTIAL"
    return {
        "status": status,
        "gaps": unique,
        "flow": list(FLOW),
        "forbidden": list(FORBIDDEN),
        "feature_implemented_is_not_research_validated": True,
        "production_boundary": PRODUCTION_BOUNDARY,
    }
