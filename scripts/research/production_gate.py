"""Production runtime gate. PASS or BLOCK only."""
from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Any, Mapping

from .boundary import PRODUCTION_BOUNDARY, RANKING_KEY, freeze_snapshot, strategy_is_frozen, weights_are_frozen
from .sample_identity import DuplicateSampleError, assert_unique_samples
from .score_semantics import SCORE_SEMANTICS

PROJECT_ROOT = Path(__file__).resolve().parents[2]
PASS = "PASS"
BLOCK = "BLOCK"

GATE_CHECKS = (
    "boundary",
    "strategy_frozen",
    "weights_frozen",
    "canonical_session",
    "data_integrity",
    "provider_integrity",
    "temporal_integrity",
    "survivorship_integrity",
    "replay_integrity",
    "sample_integrity",
    "risk_integrity",
    "snapshot_integrity",
    "database_integrity",
    "learning_boundary",
    "no_broker",
    "no_live_order",
    "no_production_alpha_transition",
    "no_auto_weight_change",
)


def _git_commit() -> str | None:
    try:
        return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=PROJECT_ROOT, text=True).strip()
    except (OSError, subprocess.CalledProcessError):
        return None


def _calendar_version() -> str:
    return "us_market_calendar_nyse"


def evaluate_production_gate(
    *,
    session_date: str | None = None,
    weight_version: str | None = None,
    start_weight_version: str | None = None,
    finish_weight_version: str | None = None,
    strategy: str | None = None,
    strategy_status: str | None = None,
    snapshot_hash: str | None = None,
    samples: list[Mapping[str, Any]] | None = None,
    provider_status: Mapping[str, Any] | None = None,
    database_ok: bool = True,
    temporal_ok: bool = True,
    survivorship_ok: bool = True,
    replay_ok: bool = True,
    risk_ok: bool = True,
    learning_mutates_weights: bool = False,
    broker_enabled: bool = False,
    live_order_enabled: bool = False,
    weight_mutation_attempted: bool = False,
    production_apply: bool = False,
) -> dict[str, Any]:
    freeze = freeze_snapshot()
    checks: dict[str, str] = {}
    checks["boundary"] = PASS if freeze["status"] == "RESEARCH_ONLY" else BLOCK
    checks["strategy_frozen"] = PASS if strategy_is_frozen() and (strategy in (None, freeze["strategy"])) and (strategy_status in (None, "FROZEN")) else BLOCK
    checks["weights_frozen"] = PASS if weights_are_frozen() else BLOCK
    if start_weight_version and finish_weight_version and start_weight_version != finish_weight_version:
        checks["weights_frozen"] = BLOCK
    if weight_mutation_attempted or production_apply:
        checks["weights_frozen"] = BLOCK
    checks["canonical_session"] = PASS if session_date else BLOCK
    checks["data_integrity"] = PASS if database_ok else BLOCK
    provider = dict(provider_status or {})
    if any(str(value).upper() in {"ERROR", "INFRA_FAILURE"} for value in provider.values()):
        checks["provider_integrity"] = BLOCK
    else:
        checks["provider_integrity"] = PASS
    checks["temporal_integrity"] = PASS if temporal_ok else BLOCK
    checks["survivorship_integrity"] = PASS if survivorship_ok else BLOCK
    checks["replay_integrity"] = PASS if replay_ok else BLOCK
    try:
        if samples:
            assert_unique_samples(samples)
        checks["sample_integrity"] = PASS
    except (DuplicateSampleError, ValueError):
        checks["sample_integrity"] = BLOCK
    checks["risk_integrity"] = PASS if risk_ok else BLOCK
    checks["snapshot_integrity"] = PASS if snapshot_hash else BLOCK
    checks["database_integrity"] = PASS if database_ok else BLOCK
    checks["learning_boundary"] = BLOCK if learning_mutates_weights else PASS
    checks["no_broker"] = BLOCK if broker_enabled or freeze["broker"] != "NO_BROKER" else PASS
    checks["no_live_order"] = BLOCK if live_order_enabled or freeze["live_order"] != "NO_LIVE_ORDER" else PASS
    checks["no_production_alpha_transition"] = PASS if "RESEARCH_TO_ALPHA" in freeze["forbidden_transitions"] else BLOCK
    checks["no_auto_weight_change"] = PASS if freeze["auto_weight_change"] == "OFF" else BLOCK

    blocked = [name for name, status in checks.items() if status != PASS]
    result = PASS if not blocked else BLOCK
    return {
        "production_gate": result,
        "status": result,
        "checks": checks,
        "blocked": blocked,
        "session_date": session_date,
        "strategy": freeze["strategy"],
        "strategy_status": freeze["strategy_status"],
        "weight_version": weight_version or start_weight_version,
        "calendar_version": _calendar_version(),
        "snapshot_hash": snapshot_hash,
        "git_commit": _git_commit(),
        "ranking_key": list(RANKING_KEY),
        "score_semantics": dict(SCORE_SEMANTICS),
        "production_boundary": PRODUCTION_BOUNDARY,
        "broker": "DISABLED",
        "live_order": "DISABLED",
        "weight_mutation": "BLOCKED",
        "production_apply": "BLOCKED",
    }
