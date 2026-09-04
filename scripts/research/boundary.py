"""Production boundary for Research OS. No second ranking or live order path."""
from __future__ import annotations

from typing import Any, Mapping


class WeightMutationBlocked(AssertionError):
    """Hard block: production weights cannot be mutated while strategy is FROZEN."""


class ProductionApplyBlocked(AssertionError):
    """Hard block: production apply is forbidden in research-runtime mode."""


PRODUCTION_BOUNDARY = {
    "status": "RESEARCH_ONLY",
    "production_research_status": "PRODUCTION_RESEARCH_READY",
    "production_runtime_status": "PRODUCTION_RUNTIME_READY",
    "strategy": "observable_footprint_v1",
    "strategy_status": "FROZEN",
    "weights_status": "FROZEN",
    "research": "LIVE",
    "replay": "LIVE",
    "learning": "LIVE",
    "paper": "PAPER_ONLY",
    "broker": "NO_BROKER",
    "live_order": "NO_LIVE_ORDER",
    "ranking_owner": "observable_footprint_v1",
    "ranking": "KEEP_OBSERVABLE_FOOTPRINT_RANKING_UNCHANGED",
    "production_action": "NO_PRODUCTION_WEIGHT_CHANGE",
    "production_apply": "BLOCKED",
    "auto_weight_change": "OFF",
    "output_layers": (
        "RESEARCH",
        "RESEARCH_EVIDENCE",
        "RESEARCH_RANKING",
        "RESEARCH_RISK",
        "RESEARCH_LEARNING",
        "RESEARCH_PROPOSAL",
    ),
    "allowed_surfaces": ("research", "shadow", "replay", "diagnostics", "context", "learning"),
    "forbidden_outputs": (
        "BUY",
        "SELL",
        "ORDER",
        "PAPER_PICK",
        "PRODUCTION_ORDER",
        "LIVE_SIGNAL",
        "AUTO_BUY",
        "AUTO_SELL",
    ),
    "forbidden_transitions": (
        "RESEARCH_TO_ALPHA",
        "RESEARCH_TO_BUY_SELL",
        "LEARNING_TO_AUTO_WEIGHT_CHANGE",
        "BROKER_CONNECT",
        "LIVE_ORDER_ENABLE",
        "PRODUCTION_APPLY",
        "WEIGHT_BYPASS",
    ),
}

SCORE_SEMANTICS = {
    "market_score": {"semantic": "observable_market_footprint_proxy"},
    "ticket_score": {"semantic": "candidate_ranking_composite"},
    "catalyst_score": {"semantic": "catalyst_evidence_proxy"},
    "risk_score": {"semantic": "research_candidate_condition"},
    "capital_score": {"semantic": "capital_behavior_research_proxy"},
    "research_score": {"semantic": "research_composite_not_alpha"},
    "alpha_status": "NOT_VALIDATED",
    "not_institutional_order_flow": True,
    "not_validated_alpha": True,
}

RANKING_KEY = ("ticket_score", "market_score", "volume_confirmation_ratio")
LEARNING_WEIGHT_SOURCES = frozenset(
    {
        "learning",
        "failure",
        "failure_memory",
        "learning_pattern",
        "research_learning",
        "seed_demo",
    }
)


def freeze_snapshot() -> dict[str, Any]:
    """Xiaomei 2.2.1 production-runtime freeze. Ranking owner stays frozen."""
    return {
        "xiaomei": "2.2.1",
        "production_research_status": PRODUCTION_BOUNDARY["production_research_status"],
        "production_runtime_status": PRODUCTION_BOUNDARY["production_runtime_status"],
        "strategy": PRODUCTION_BOUNDARY["strategy"],
        "strategy_status": PRODUCTION_BOUNDARY["strategy_status"],
        "weights_status": PRODUCTION_BOUNDARY["weights_status"],
        "research": PRODUCTION_BOUNDARY["research"],
        "replay": PRODUCTION_BOUNDARY["replay"],
        "learning": PRODUCTION_BOUNDARY["learning"],
        "ranking_owner": PRODUCTION_BOUNDARY["ranking_owner"],
        "ranking_key": list(RANKING_KEY),
        "status": PRODUCTION_BOUNDARY["status"],
        "paper": PRODUCTION_BOUNDARY["paper"],
        "broker": PRODUCTION_BOUNDARY["broker"],
        "live_order": PRODUCTION_BOUNDARY["live_order"],
        "production_action": PRODUCTION_BOUNDARY["production_action"],
        "production_apply": PRODUCTION_BOUNDARY["production_apply"],
        "auto_weight_change": PRODUCTION_BOUNDARY["auto_weight_change"],
        "score_semantics": dict(SCORE_SEMANTICS),
        "output_layers": list(PRODUCTION_BOUNDARY["output_layers"]),
        "forbidden_transitions": list(PRODUCTION_BOUNDARY["forbidden_transitions"]),
    }


def strategy_is_frozen() -> bool:
    return PRODUCTION_BOUNDARY["strategy_status"] == "FROZEN"


def weights_are_frozen() -> bool:
    return PRODUCTION_BOUNDARY["weights_status"] == "FROZEN" or strategy_is_frozen()


def assert_weight_mutation_allowed(*, source: str | None = None) -> dict[str, Any]:
    """Hard-fail any production weight write while strategy/weights are frozen."""
    if strategy_is_frozen() or weights_are_frozen():
        raise WeightMutationBlocked(
            f"FROZEN strategy forbids production weight mutation (source={source})"
        )
    if PRODUCTION_BOUNDARY["production_action"] == "NO_PRODUCTION_WEIGHT_CHANGE":
        raise WeightMutationBlocked(
            f"NO_PRODUCTION_WEIGHT_CHANGE (source={source})"
        )
    if PRODUCTION_BOUNDARY["auto_weight_change"] == "OFF":
        raise WeightMutationBlocked(
            f"auto_weight_change is OFF (source={source})"
        )
    if learning_cannot_auto_weight(source):
        raise WeightMutationBlocked(
            f"LEARNING_TO_AUTO_WEIGHT_CHANGE (source={source})"
        )
    return {"allowed": True, "source": source}


def assert_production_apply_blocked(*, source: str | None = None) -> dict[str, Any]:
    """Production apply is never legal in RESEARCH_ONLY / FROZEN runtime."""
    if PRODUCTION_BOUNDARY["production_apply"] == "BLOCKED" or strategy_is_frozen():
        raise ProductionApplyBlocked(
            f"PRODUCTION_APPLY blocked (source={source})"
        )
    return {"allowed": True, "source": source}


def learning_cannot_auto_weight(source: str | None) -> bool:
    name = str(source or "").strip().lower()
    if name in LEARNING_WEIGHT_SOURCES:
        return True
    return name.startswith("learning") or "failure_memory" in name


def assert_research_only(payload: Mapping[str, Any] | None = None) -> dict[str, Any]:
    """Return the frozen boundary. Research modules cannot emit picks."""
    if payload:
        if payload.get("produces_pick") is True:
            raise ValueError("research payload cannot produce a pick")
        if payload.get("allow_trade") is True or payload.get("auto_order") is True:
            raise ValueError("research payload cannot enable trading")
        if payload.get("enters_alpha_score") is True:
            raise ValueError("research payload cannot enter alpha")
        if payload.get("changes_production_ranking") is True:
            raise ValueError("research payload cannot change production ranking")
        if payload.get("auto_weight_change") is True:
            raise ValueError("learning cannot auto-change production weights")
        if payload.get("production_apply") is True:
            raise ValueError("research payload cannot apply production changes")
        if payload.get("risk_pass_is_buy") is True or payload.get("risk_to_buy") is True:
            raise ValueError("risk_pass is a research candidate condition, not BUY")
        action = str(payload.get("classification") or payload.get("action") or "")
        if action in PRODUCTION_BOUNDARY["forbidden_outputs"]:
            raise ValueError(f"research payload cannot emit production action {action}")
        for key in ("BUY", "SELL", "ORDER", "BROKER", "LIVE_TRADE", "AUTO_BUY", "AUTO_SELL", "LIVE_SIGNAL", "PRODUCTION_ORDER"):
            if payload.get(key) not in (None, False, "", "NO", "NO_BROKER", "NO_LIVE_ORDER"):
                raise ValueError(f"research payload cannot enable {key}")
    return dict(PRODUCTION_BOUNDARY)


def validate(payload: Mapping[str, Any] | None = None) -> dict[str, Any]:
    """Canonical ResearchOutput gate. Flags are not sufficient by themselves."""
    return assert_research_only(payload)


def ranking_unchanged(before: Mapping[str, Any], after: Mapping[str, Any]) -> bool:
    return tuple(before.get(key) for key in RANKING_KEY) == tuple(after.get(key) for key in RANKING_KEY)


def skill_inventory() -> list[dict[str, Any]]:
    return [
        {
            "name": "us-stock-research",
            "path": "skills/us-stock-research/SKILL.md",
            "role": "canonical research skill",
            "produces_pick": False,
            "owner": "us_profit_ticket_pipeline",
        },
        {
            "name": "buffett",
            "path": "skills/buffett/SKILL.md",
            "role": "fundamental brain / company quality",
            "produces_pick": False,
            "provenance": "xiaogu/.agents/skills/uzi/deep-analysis/personas/buffett.yaml",
        },
        {
            "name": "serenity",
            "path": "skills/serenity/SKILL.md",
            "role": "industry brain / chokepoint",
            "produces_pick": False,
            "provenance": "xiaogu/.agents/skills/serenity-skill/",
        },
        {
            "name": "capital_behavior_v2",
            "path": "scripts/capital/",
            "role": "capital brain",
            "produces_pick": False,
            "owner": "capital.scoring.build_capital_assessment",
        },
        {
            "name": "observable_footprint_v1",
            "path": "scripts/us_profit_ticket_pipeline.py",
            "role": "production ranking owner",
            "produces_pick": True,
            "strategy_status": "FROZEN",
            "note": "only paper-review classification, never live order",
        },
        {
            "name": "quant",
            "path": "scripts/research/stability.py",
            "role": "statistical validation",
            "produces_pick": False,
        },
        {
            "name": "obsidian",
            "path": "scripts/research/memory.py",
            "role": "memory / thesis ledger",
            "produces_pick": False,
        },
        {
            "name": "postgresql",
            "path": "scripts/db/",
            "role": "structured facts",
            "produces_pick": False,
        },
    ]


SKILL_OWNERS = {
    "Buffett": "Company Research",
    "Serenity": "Industry Research",
    "Capital": "Market Capital Behavior",
    "Quant": "Statistical Validation",
    "Obsidian": "Memory",
    "PostgreSQL": "Structured Facts",
}
