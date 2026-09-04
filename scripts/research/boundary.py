"""Production boundary for Research OS. No second ranking or live order path."""
from __future__ import annotations

from typing import Any, Mapping


PRODUCTION_BOUNDARY = {
    "status": "RESEARCH_ONLY",
    "paper": "PAPER_ONLY",
    "broker": "NO_BROKER",
    "live_order": "NO_LIVE_ORDER",
    "ranking_owner": "observable_footprint_v1",
    "ranking": "KEEP_OBSERVABLE_FOOTPRINT_RANKING_UNCHANGED",
    "production_action": "NO_PRODUCTION_WEIGHT_CHANGE",
    "allowed_surfaces": ("research", "shadow", "replay", "diagnostics", "context", "learning"),
    "forbidden_outputs": ("BUY", "SELL", "ORDER", "PAPER_PICK"),
}

RANKING_KEY = ("ticket_score", "market_score", "volume_confirmation_ratio")


def assert_research_only(payload: Mapping[str, Any] | None = None) -> dict[str, Any]:
    """Return the frozen boundary. Research modules cannot emit picks."""
    if payload:
        if payload.get("produces_pick") is True:
            raise ValueError("research payload cannot produce a pick")
        if payload.get("allow_trade") is True or payload.get("auto_order") is True:
            raise ValueError("research payload cannot enable trading")
        action = str(payload.get("classification") or payload.get("action") or "")
        if action in PRODUCTION_BOUNDARY["forbidden_outputs"]:
            raise ValueError(f"research payload cannot emit production action {action}")
    return dict(PRODUCTION_BOUNDARY)


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
