"""Canonical score semantics. Ranking composites are not Alpha."""
from __future__ import annotations

from typing import Any, Mapping

from .boundary import PRODUCTION_BOUNDARY, SCORE_SEMANTICS, assert_research_only

FORBIDDEN_SEMANTIC_UPGRADES = (
    "institutional_order_flow",
    "institutional buying",
    "smart_money",
    "validated_alpha",
    "live_signal",
)


def score_semantics(payload: Mapping[str, Any] | None = None) -> dict[str, Any]:
    body = dict(SCORE_SEMANTICS)
    if payload:
        for key in ("market_score", "ticket_score", "catalyst_score", "risk_score", "capital_score", "research_score"):
            if key in payload and key in body:
                body[key] = {**body[key], "value": payload.get(key)}
    result = {
        **body,
        "production_boundary": PRODUCTION_BOUNDARY,
        "produces_pick": False,
        "not_a_buy_sell": True,
    }
    assert_research_only(result)
    return result


def assert_no_semantic_upgrade(text: str) -> None:
    lowered = str(text or "").lower()
    for token in FORBIDDEN_SEMANTIC_UPGRADES:
        if token in lowered:
            raise ValueError(f"semantic upgrade forbidden: {token}")
