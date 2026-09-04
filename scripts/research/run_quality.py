"""Daily-loop step outcomes and fail-fast quality gate."""
from __future__ import annotations

from typing import Any, Mapping

STEP_SUCCESS = "STEP_SUCCESS"
STEP_DEGRADED = "STEP_DEGRADED"
STEP_DATA_GAP = "STEP_DATA_GAP"
STEP_BLOCKED = "STEP_BLOCKED"
STEP_FAILED = "STEP_FAILED"

HARD_FAIL_REASONS = (
    "provider_integrity_failure",
    "temporal_integrity_failure",
    "database_failure",
    "canonical_data_failure",
    "strategy_integrity_failure",
    "production_boundary_violation",
    "weight_mutation_attempt",
    "duplicate_sample_violation",
    "snapshot_hash_failure",
)

DEGRADED_REASONS = (
    "research_data_gap",
    "consensus_unavailable",
    "chokepoint_unavailable",
    "historical_universe_unavailable",
)


def classify_step(status: str | None, *, reason: str | None = None, hard: bool = False) -> str:
    label = str(status or "").upper()
    if hard or reason in HARD_FAIL_REASONS or label in {"FAILED", "ERROR", "BLOCKED", STEP_FAILED, STEP_BLOCKED}:
        if reason in HARD_FAIL_REASONS or hard or label in {"FAILED", "ERROR", STEP_FAILED}:
            return STEP_FAILED if label not in {STEP_BLOCKED} else STEP_BLOCKED
        return STEP_BLOCKED
    if reason in DEGRADED_REASONS or label in {"DATA_GAP", STEP_DATA_GAP, "DEGRADED", STEP_DEGRADED}:
        return STEP_DEGRADED if reason in DEGRADED_REASONS or label in {"DEGRADED", STEP_DEGRADED} else STEP_DATA_GAP
    if label in {"OK", "SUCCESS", "DONE", STEP_SUCCESS}:
        return STEP_SUCCESS
    if label in {"SKIPPED", "TIMEOUT"}:
        return STEP_DEGRADED
    return STEP_SUCCESS if not reason else STEP_DEGRADED


def run_quality_gate(steps: Mapping[str, Mapping[str, Any]]) -> dict[str, Any]:
    classified = {}
    hard = []
    degraded = []
    for name, payload in steps.items():
        reason = payload.get("reason") or payload.get("error")
        status = classify_step(payload.get("status"), reason=reason, hard=bool(payload.get("hard_fail")))
        classified[name] = status
        if status in {STEP_FAILED, STEP_BLOCKED}:
            hard.append(name)
        elif status in {STEP_DEGRADED, STEP_DATA_GAP}:
            degraded.append(name)
    if hard:
        run_status = "FAILED" if any(classified[name] == STEP_FAILED for name in hard) else "BLOCKED"
        return {
            "status": run_status,
            "steps": classified,
            "hard_fail": hard,
            "degraded": degraded,
            "publish_ranking": False,
            "production_output": False,
            "stop_run": True,
        }
    if degraded:
        return {
            "status": "DEGRADED",
            "steps": classified,
            "hard_fail": [],
            "degraded": degraded,
            "publish_ranking": False,
            "production_output": False,
            "stop_run": False,
        }
    return {
        "status": "SUCCESS",
        "steps": classified,
        "hard_fail": [],
        "degraded": [],
        "publish_ranking": False,
        "production_output": False,
        "stop_run": False,
    }
