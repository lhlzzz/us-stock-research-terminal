"""Xiaomei Research OS.

Research knowledge and evidence only. Never a second production ranking
or paper-pick owner. Production ranking remains
``(ticket_score, market_score, volume_confirmation_ratio)``.
"""
from __future__ import annotations

from .boundary import PRODUCTION_BOUNDARY, assert_research_only
from .brains import (
    build_buffett_context,
    build_future_buyer_map,
    build_pricing_gap_context,
    build_serenity_context,
    build_supply_context,
    build_tradingagents_adapter,
    build_uzi_adapter,
)
from .contracts import capital_behavior, company_quality, independent_scores, industry_position, market_setup
from .decision import (
    build_company_research,
    contradiction_status,
    render_company_report,
    research_decision_matrix,
    why_not,
    write_company_report,
)
from .evidence import CLAIM_KINDS, EVIDENCE_LEVELS, Claim, claim
from .learning import (
    DATA_QUALITY_GATES,
    assemble_research_sample,
    history_census,
    independent_price_outcomes,
    research_data_ready,
    write_history_census,
)
from .memory import (
    filter_obsidian_as_of,
    ingest_obsidian_assets,
    portfolio_context,
    scan_obsidian_vault,
)
from .query import research_dashboard, research_query

__all__ = [
    "Claim",
    "DATA_QUALITY_GATES",
    "PRODUCTION_BOUNDARY",
    "assert_research_only",
    "assemble_research_sample",
    "build_buffett_context",
    "build_company_research",
    "build_future_buyer_map",
    "build_pricing_gap_context",
    "build_serenity_context",
    "build_supply_context",
    "build_tradingagents_adapter",
    "build_uzi_adapter",
    "claim",
    "capital_behavior",
    "company_quality",
    "contradiction_status",
    "filter_obsidian_as_of",
    "history_census",
    "independent_scores",
    "industry_position",
    "market_setup",
    "research_dashboard",
    "research_decision_matrix",
    "research_query",
    "why_not",
    "independent_price_outcomes",
    "ingest_obsidian_assets",
    "portfolio_context",
    "scan_obsidian_vault",
    "render_company_report",
    "research_data_ready",
    "write_company_report",
    "write_history_census",
]
