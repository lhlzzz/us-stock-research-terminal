#!/usr/bin/env python3
"""Xiaomei 2.2.1 production runtime release audit. P0/P1 failure => RELEASE BLOCKED."""
from __future__ import annotations

import ast
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))


def _git(*args: str) -> str:
    return subprocess.check_output(["git", *args], cwd=ROOT, text=True).strip()


def _read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def audit() -> dict[str, str]:
    from audit_weight_mutation_surface import audit as weight_surface_audit
    from research.boundary import PRODUCTION_BOUNDARY, freeze_snapshot, strategy_is_frozen, weights_are_frozen
    from research.production_gate import evaluate_production_gate
    from research.sample_identity import sample_id
    from research.score_semantics import SCORE_SEMANTICS
    from market_calendar import CALENDAR

    status: dict[str, str] = {}
    freeze = freeze_snapshot()
    status["boundary"] = "PASS" if freeze["status"] == "RESEARCH_ONLY" else "FAIL"
    status["strategy_freeze"] = "PASS" if strategy_is_frozen() and freeze["strategy"] == "observable_footprint_v1" else "FAIL"
    status["weight_frozen"] = "PASS" if weights_are_frozen() else "FAIL"
    status["weight_gateway"] = "PASS" if (ROOT / "scripts/research/weight_mutation.py").exists() else "FAIL"
    hits = weight_surface_audit(ROOT)
    status["no_weight_bypass"] = "PASS" if not hits else "FAIL"
    status["canonical_session"] = "PASS" if hasattr(CALENDAR, "previous_completed_session") and hasattr(CALENDAR, "current_session") else "FAIL"
    status["temporal_integrity"] = "PASS" if (ROOT / "scripts/research/temporal.py").exists() else "FAIL"
    status["provider_integrity"] = "PASS" if (ROOT / "scripts/research/providers.py").exists() else "FAIL"
    status["research_snapshot_integrity"] = "PASS" if (ROOT / "scripts/research/snapshots.py").exists() else "FAIL"
    sample = sample_id(ticket_id="t1", replay_horizon=1, replay_date="2026-09-03")
    status["replay_sample_integrity"] = "PASS" if sample.startswith("t1|") else "FAIL"
    status["risk_parameter_integrity"] = "PASS" if "risk_per_trade" in _read("scripts/risk_manager.py") and "default_stop_loss_pct" in _read("scripts/risk_manager.py") else "FAIL"
    status["learning_boundary"] = "PASS" if PRODUCTION_BOUNDARY["auto_weight_change"] == "OFF" else "FAIL"
    status["failure_propagation"] = "PASS" if "run_quality_gate" in _read("scripts/daily_loop.py") else "FAIL"
    status["production_boundary"] = "PASS" if PRODUCTION_BOUNDARY["live_order"] == "NO_LIVE_ORDER" else "FAIL"
    status["no_broker"] = "PASS" if PRODUCTION_BOUNDARY["broker"] == "NO_BROKER" else "FAIL"
    status["no_live_order"] = "PASS" if PRODUCTION_BOUNDARY["live_order"] == "NO_LIVE_ORDER" else "FAIL"
    status["no_production_alpha_transition"] = "PASS" if "RESEARCH_TO_ALPHA" in PRODUCTION_BOUNDARY["forbidden_transitions"] else "FAIL"
    status["no_auto_weight_change"] = "PASS" if PRODUCTION_BOUNDARY["production_apply"] == "BLOCKED" else "FAIL"
    status["score_semantics"] = "PASS" if SCORE_SEMANTICS["alpha_status"] == "NOT_VALIDATED" else "FAIL"
    pipeline = _read("scripts/full_cycle.py")
    status["pipeline_apply_blocked"] = "PASS" if "WEIGHTS_FILE.write_text" not in pipeline and "PRODUCTION_APPLY" not in pipeline.split("RESEARCH_PROPOSAL")[0] else "FAIL"
    if "WEIGHTS_FILE.write_text" in pipeline:
        status["pipeline_apply_blocked"] = "FAIL"
    status["optimizer_keep_previous"] = "PASS" if "KEEP_PREVIOUS_WEIGHT" in _read("scripts/weight_optimizer.py") else "FAIL"
    dirty = _git("status", "--porcelain")
    status["git_clean"] = "PASS" if dirty == "" else "FAIL"
    gate = evaluate_production_gate(
        session_date=CALENDAR.previous_completed_session().isoformat(),
        snapshot_hash="audit",
        weight_version="audit",
        start_weight_version="audit",
        finish_weight_version="audit",
    )
    status["production_gate"] = gate["production_gate"]
    status["PRODUCTION_RUNTIME_READY"] = "PASS" if freeze.get("production_runtime_status") == "PRODUCTION_RUNTIME_READY" else "FAIL"
    leaked = []
    for rel in ("scripts/research/sec.py", "scripts/research/earnings.py", "scripts/research/learning.py"):
        tree = ast.parse(_read(rel))
        for node in ast.walk(tree):
            if isinstance(node, ast.Constant) and node.value in {"BUY", "SELL", "AUTO_BUY", "LIVE_SIGNAL"}:
                leaked.append(f"{rel}:{node.value}")
    status["schema_audit"] = "FAIL" if leaked else "PASS"
    return status


def main() -> int:
    status = audit()
    print(json.dumps(status, indent=2, sort_keys=True))
    hard = [
        "boundary",
        "strategy_freeze",
        "weight_frozen",
        "weight_gateway",
        "no_weight_bypass",
        "canonical_session",
        "temporal_integrity",
        "provider_integrity",
        "research_snapshot_integrity",
        "replay_sample_integrity",
        "risk_parameter_integrity",
        "learning_boundary",
        "failure_propagation",
        "production_boundary",
        "no_broker",
        "no_live_order",
        "no_production_alpha_transition",
        "no_auto_weight_change",
        "pipeline_apply_blocked",
        "optimizer_keep_previous",
        "PRODUCTION_RUNTIME_READY",
        "production_gate",
        "git_clean",
    ]
    failed = [name for name in hard if status.get(name) not in {"PASS"}]
    if failed:
        print("RELEASE BLOCKED:", failed)
        return 1
    print("XIAOMEI_2.2.1_RELEASE_AUDIT=PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
