#!/usr/bin/env python3
"""Daily Loop: research ranking → backfill → replay → learning → production gate.

Steps:
1. Pipeline - Generate research ranking candidates
2. Backfill - Update forward tracking with actual returns
3. Factor Backtest - Test all factors
4. Weight Optimization - Proposal only while FROZEN
5. Scoreboard - Lifecycle scoreboard
6. Degradation Check - Meta-loop
7. Production gate - PASS or BLOCK
"""
import json
import subprocess
import sys
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPTS_DIR.parent
sys.path.insert(0, str(SCRIPTS_DIR))

from market_calendar import CALENDAR
from research.boundary import PRODUCTION_BOUNDARY, SCORE_SEMANTICS
from research.production_gate import evaluate_production_gate
from research.run_manifest import (
    assert_strategy_immutable,
    assert_weight_version_immutable,
    build_run_identity,
    load_weight_version,
    write_run_manifest,
)
from research.run_quality import (
    STEP_BLOCKED,
    STEP_FAILED,
    classify_step,
    run_quality_gate,
)


HARD_FAIL_STATUSES = {"failed", "error", "timeout", STEP_FAILED, STEP_BLOCKED}


def _canonical_session(output_date: str | None = None) -> str:
    if output_date:
        return str(output_date)[:10]
    return CALENDAR.previous_completed_session().isoformat()


def run_daily_loop(output_date: str = None, skip_pipeline: bool = False) -> dict:
    session_date = _canonical_session(output_date)
    start_weight = load_weight_version()
    start_strategy = PRODUCTION_BOUNDARY["strategy"]
    identity = build_run_identity(session_date=session_date, weight_version=start_weight)
    results = {
        "output_date": session_date,
        "canonical_us_session_date": session_date,
        "run_id": identity["run_id"],
        "weight_version": start_weight,
        "strategy": start_strategy,
        "strategy_status": PRODUCTION_BOUNDARY["strategy_status"],
        "score_semantics": dict(SCORE_SEMANTICS),
        "steps": {},
        "run_status": "RUNNING",
    }
    print("RUN START")
    print(f"canonical session={session_date}")
    print(f"strategy version={start_strategy} {PRODUCTION_BOUNDARY['strategy_status']}")
    print(f"weight version={start_weight}")

    ordered = []
    if not skip_pipeline:
        ordered.append(("pipeline", lambda: step_pipeline(session_date)))
    else:
        results["steps"]["pipeline"] = {"status": "ok", "reason": "skip_pipeline"}
    ordered.extend([
        ("backfill", step_backfill),
        ("factor_backtest", step_factor_backtest),
        ("weight_optimization", lambda: step_weight_optimization(results["steps"].get("factor_backtest", {}).get("result", {}))),
        ("scoreboard", step_scoreboard),
        ("degradation", step_degradation),
    ])

    stopped = False
    for name, func in ordered:
        payload = func()
        classified = classify_step(payload.get("status"), reason=payload.get("reason") or payload.get("error"))
        payload["step_status"] = classified
        results["steps"][name] = payload
        print(f"{name}: {classified}")
        if classified in {STEP_FAILED, STEP_BLOCKED} or str(payload.get("status") or "").lower() in HARD_FAIL_STATUSES:
            results["run_status"] = "FAILED"
            results["quality_gate"] = run_quality_gate(results["steps"])
            results["production_gate"] = evaluate_production_gate(
                session_date=session_date,
                weight_version=start_weight,
                start_weight_version=start_weight,
                finish_weight_version=load_weight_version(),
                snapshot_hash=identity["snapshot_id"],
                database_ok=False,
            )
            stopped = True
            break

    finish_weight = load_weight_version()
    try:
        assert_weight_version_immutable(start_weight, finish_weight)
        assert_strategy_immutable(start_strategy, PRODUCTION_BOUNDARY["strategy"])
        weight_ok = True
    except AssertionError:
        weight_ok = False
        results["run_status"] = "FAILED"

    if not stopped:
        quality = run_quality_gate(results["steps"])
        results["quality_gate"] = quality
        results["run_status"] = quality["status"]
    else:
        quality = results.get("quality_gate") or run_quality_gate(results["steps"])

    gate = evaluate_production_gate(
        session_date=session_date,
        weight_version=start_weight,
        start_weight_version=start_weight,
        finish_weight_version=finish_weight,
        snapshot_hash=identity["snapshot_id"],
        database_ok=weight_ok and results["run_status"] != "FAILED",
        weight_mutation_attempted=not weight_ok,
    )
    results["production_gate"] = gate
    results["identity"] = identity
    results["broker"] = "DISABLED"
    results["live_order"] = "DISABLED"
    results["weight_mutation"] = "BLOCKED"
    results["production_apply"] = "BLOCKED"
    manifest = write_run_manifest(
        identity,
        research_status=results["run_status"],
        production_gate=gate["production_gate"],
        extra={
            "steps": {name: payload.get("status") for name, payload in results["steps"].items()},
            "quality_gate": quality.get("status") if isinstance(quality, dict) else quality,
        },
    )
    results["manifest_path"] = str(manifest)
    print(f"production gate={gate['production_gate']}")
    print(f"RUN END {results['run_status']}")
    return results


def step_pipeline(output_date: str) -> dict:
    result = subprocess.run(
        [sys.executable, str(SCRIPTS_DIR / "us_profit_ticket_pipeline.py"),
         "--output-date", output_date,
         "--save-db", "--skip-last30days"],
        capture_output=True, text=True, timeout=900,
        cwd=str(PROJECT_ROOT),
    )
    if result.returncode == 0:
        try:
            lines = [l.strip() for l in (result.stdout or "").strip().split("\n") if l.strip()]
            for line in reversed(lines):
                if line.startswith("{"):
                    payload = json.JSONDecoder().raw_decode(line)[0]
                    return {
                        "status": "success",
                        "candidates": payload.get("top_candidates", []),
                        "classification": payload.get("final_classification"),
                    }
        except Exception:
            pass
        return {"status": "success"}
    return {"status": "failed", "error": (result.stderr or "")[:200], "hard_fail": True}


def step_backfill(timeout: int = 120) -> dict:
    try:
        result = subprocess.run(
            [sys.executable, str(SCRIPTS_DIR / "backfill_forward_tracking.py"), "--db"],
            capture_output=True, text=True, timeout=timeout,
            cwd=str(PROJECT_ROOT),
        )
        return {"status": "ok" if result.returncode == 0 else "failed", "hard_fail": result.returncode != 0}
    except subprocess.TimeoutExpired:
        return {"status": "timeout", "message": f"Backfill exceeded {timeout}s limit", "hard_fail": True}


def step_factor_backtest() -> dict:
    try:
        from full_cycle import step_factor_backtest as _fb
        result = _fb()
        status = result.get("status") if isinstance(result, dict) else "ok"
        if status in ("NO_DATA", "INSUFFICIENT_DATA"):
            return {"status": "DATA_GAP", "result": result, "reason": "research_data_gap"}
        return {"status": "ok", "result": result}
    except Exception as e:
        return {"status": "error", "error": str(e), "hard_fail": True}


def step_weight_optimization(fb_result: dict) -> dict:
    try:
        from full_cycle import step_weight_optimization as _wo
        result = _wo(fb_result)
        if result.get("production_apply"):
            return {"status": "failed", "reason": "weight_mutation_attempt", "hard_fail": True, "result": result}
        return {"status": "ok", "result": result}
    except Exception as e:
        return {"status": "error", "error": str(e), "hard_fail": True, "result": {"decision": "KEEP_PREVIOUS_WEIGHT"}}


def step_scoreboard() -> dict:
    result = subprocess.run(
        [sys.executable, str(SCRIPTS_DIR / "lifecycle_scoreboard.py"), "--db"],
        capture_output=True, text=True, timeout=120,
        cwd=str(PROJECT_ROOT),
    )
    return {"status": "ok" if result.returncode == 0 else "failed", "hard_fail": result.returncode != 0}


def step_degradation() -> dict:
    result = subprocess.run(
        [sys.executable, str(SCRIPTS_DIR / "meta_loop.py")],
        capture_output=True, text=True, timeout=60,
        cwd=str(PROJECT_ROOT),
    )
    if result.returncode == 0:
        try:
            payload = json.loads(result.stdout)
            payload.setdefault("status", "ok")
            return payload
        except Exception:
            pass
    return {"status": "failed", "hard_fail": True}


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Daily loop orchestrator")
    parser.add_argument("--output-date", default=None)
    parser.add_argument("--skip-pipeline", action="store_true")
    args = parser.parse_args()

    result = run_daily_loop(
        output_date=args.output_date,
        skip_pipeline=args.skip_pipeline,
    )
    print(json.dumps(result, indent=2, ensure_ascii=False, default=str))
