#!/usr/bin/env python3
"""Daily Loop: 每日自动出票全流程编排。

Steps:
1. 出票 (Pipeline) - Generate trading signals
2. 回填 (Backfill) - Update forward tracking with actual returns
3. 因子回测 (Factor Backtest) - Test all factors
4. 权重优化 (Weight Optimization) - IC-driven weights
5. 记分板 (Scoreboard) - Lifecycle scoreboard
6. 退化检测 (Degradation Check) - Meta-loop
"""
import json
import subprocess
import sys
from datetime import date
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPTS_DIR.parent
sys.path.insert(0, str(SCRIPTS_DIR))


def run_daily_loop(output_date: str = None, skip_pipeline: bool = False) -> dict:
    if not output_date:
        output_date = date.today().isoformat()
    results = {"output_date": output_date, "steps": {}}

    # Step 1: Pipeline (出票)
    if not skip_pipeline:
        results["steps"]["pipeline"] = step_pipeline(output_date)
    else:
        results["steps"]["pipeline"] = {"status": "skipped"}

    # Step 2: Backfill (回填)
    results["steps"]["backfill"] = step_backfill()

    # Step 3: Factor Backtest (因子回测)
    results["steps"]["factor_backtest"] = step_factor_backtest()

    # Step 4: Weight Optimization (权重优化)
    fb = results["steps"]["factor_backtest"].get("result", {})
    results["steps"]["weight_optimization"] = step_weight_optimization(fb)

    # Step 5: Scoreboard (记分板)
    results["steps"]["scoreboard"] = step_scoreboard()

    # Step 6: Degradation Check (退化检测)
    results["steps"]["degradation"] = step_degradation()

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
    return {"status": "failed", "error": (result.stderr or "")[:200]}


def step_backfill(timeout: int = 120) -> dict:
    try:
        result = subprocess.run(
            [sys.executable, str(SCRIPTS_DIR / "backfill_forward_tracking.py"), "--db"],
            capture_output=True, text=True, timeout=timeout,
            cwd=str(PROJECT_ROOT),
        )
        return {"status": "ok" if result.returncode == 0 else "failed"}
    except subprocess.TimeoutExpired:
        return {"status": "timeout", "message": f"Backfill exceeded {timeout}s limit"}


def step_factor_backtest() -> dict:
    try:
        from full_cycle import step_factor_backtest as _fb
        result = _fb()
        return {"status": "ok", "result": result}
    except Exception as e:
        return {"status": "error", "error": str(e)}


def step_weight_optimization(fb_result: dict) -> dict:
    try:
        from full_cycle import step_weight_optimization as _wo
        result = _wo(fb_result)
        return {"status": "ok", "result": result}
    except Exception as e:
        return {"status": "error", "error": str(e)}


def step_scoreboard() -> dict:
    result = subprocess.run(
        [sys.executable, str(SCRIPTS_DIR / "lifecycle_scoreboard.py"), "--db"],
        capture_output=True, text=True, timeout=120,
        cwd=str(PROJECT_ROOT),
    )
    return {"status": "ok" if result.returncode == 0 else "failed"}


def step_degradation() -> dict:
    result = subprocess.run(
        [sys.executable, str(SCRIPTS_DIR / "meta_loop.py")],
        capture_output=True, text=True, timeout=60,
        cwd=str(PROJECT_ROOT),
    )
    if result.returncode == 0:
        try:
            return json.loads(result.stdout)
        except Exception:
            pass
    return {"status": "failed"}


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
