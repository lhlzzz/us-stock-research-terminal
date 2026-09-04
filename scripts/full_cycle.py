#!/usr/bin/env python3
"""Full Cycle Orchestrator: research pipeline → backfill → replay → proposal.

Steps:
1. Pipeline - Generate research ranking candidates
2. Backfill - Update forward tracking with actual returns
3. Factor Backtest - Test all factors (existing + candidate)
4. Weight Optimization - Propose weights from IC (never apply in FROZEN)
5. Scoreboard - Update lifecycle scoreboard
6. Degradation Check - Meta-loop check
7. Pipeline Upgrade - Store RESEARCH_PROPOSAL only
"""

from __future__ import annotations

import json
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))

from historical_replay_baseline import (
    build_close_panel,
    fetch_universe,
    load_universe_source,
    project_root,
)
from market_regime import classify_market_regime, get_regime_thresholds
from candidate_factors import (
    ALL_FACTORS,
    CANDIDATE_FACTORS,
    EXISTING_FACTORS,
    compute_candidate_features,
)
from db.engine import SessionLocal, query_rows
from market_calendar import CALENDAR
from research.boundary import PRODUCTION_BOUNDARY, ProductionApplyBlocked, assert_production_apply_blocked
from research.sample_identity import DuplicateSampleError, sample_id
from research.weight_mutation import KEEP_PREVIOUS_WEIGHT, request_weight_change
from sqlalchemy import text


SCRIPTS_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPTS_DIR.parent
RESEARCH_DIR = PROJECT_ROOT / "research"
WEIGHTS_FILE = PROJECT_ROOT / "data" / "scoring_weights.json"
CYCLE_LOG = RESEARCH_DIR / "full-cycle-log.json"


def run_step(name: str, func, *args, **kwargs) -> dict:
    """Run a named step with timing and error handling."""
    print(f"\n{'='*60}")
    print(f"STEP: {name}")
    print(f"{'='*60}")
    start = time.time()
    try:
        result = func(*args, **kwargs)
        elapsed = time.time() - start
        print(f"  ✅ {name} completed in {elapsed:.1f}s")
        return {"status": "ok", "elapsed": round(elapsed, 1), "result": result}
    except Exception as e:
        elapsed = time.time() - start
        print(f"  ❌ {name} failed after {elapsed:.1f}s: {e}")
        return {"status": "error", "elapsed": round(elapsed, 1), "error": str(e)}


# ─── Step 1: Pipeline ───────────────────────────────────────────
def step_pipeline(output_date: str) -> dict:
    """Run the main ticket pipeline."""
    result = subprocess.run(
        [sys.executable, str(PROJECT_ROOT / "scripts" / "us_profit_ticket_pipeline.py"),
         "--output-date", output_date,
         "--save-db", "--skip-last30days"],
        capture_output=True, text=True, timeout=900,
        cwd=str(PROJECT_ROOT),
    )
    stdout = result.stdout[-2000:] if result.stdout else ""
    stderr = result.stderr[-1000:] if result.stderr else ""

    if result.returncode != 0:
        return {"status": "failed", "stdout": stdout, "stderr": stderr}

    # Parse last JSON line from stdout
    try:
        lines = [l.strip() for l in stdout.strip().split("\n") if l.strip()]
        for line in reversed(lines):
            if line.startswith("{"):
                payload = json.JSONDecoder().raw_decode(line)[0]
                return {
                    "status": "success",
                    "candidates": len(payload.get("top_candidates", [])),
                    "classification": payload.get("final_classification"),
                    "regime": payload.get("regime"),
                }
    except Exception:
        pass
    return {"status": "success", "raw_stdout_len": len(stdout)}


# ─── Step 2: Backfill ───────────────────────────────────────────
def step_backfill() -> dict:
    """Backfill forward tracking with actual returns."""
    result = subprocess.run(
        [sys.executable, str(PROJECT_ROOT / "scripts" / "backfill_forward_tracking.py"), "--db"],
        capture_output=True, text=True, timeout=300,
        cwd=str(PROJECT_ROOT),
    )
    # Count updated rows from stdout
    stdout = result.stdout or ""
    updated = 0
    for line in stdout.split("\n"):
        if "updated" in line.lower() or "filled" in line.lower():
            try:
                nums = [int(s) for s in line.split() if s.isdigit()]
                if nums:
                    updated = max(updated, max(nums))
            except Exception:
                pass
    return {"status": "ok" if result.returncode == 0 else "failed", "updated_rows": updated}


# ─── Step 3: Factor Backtest ────────────────────────────────────
def step_factor_backtest(backtest_days: int = 200) -> dict:
    """Backtest all factors (existing + candidate) using DB data."""
    session = SessionLocal()
    try:
        # Load completed forward tracking
        tracking = session.execute(text("""
            SELECT t.output_date, t.symbol, t.horizon_days, t.forward_return,
                   t.as_of_close, t.due_close, t.ticket_id,
                   tk.market_score, tk.catalyst_score, tk.ticket_score
            FROM forward_tracking t
            LEFT JOIN tickets tk ON tk.id = t.ticket_id
            WHERE t.check_status = 'completed' AND t.forward_return IS NOT NULL
            ORDER BY t.output_date, t.symbol, t.ticket_id
        """)).fetchall()

        if not tracking:
            return {"status": "NO_DATA", "message": "No completed forward tracking data"}

        # Load factor snapshots
        factors = session.execute(text("""
            SELECT trade_date, symbol,
                   prior_5d_momentum, prior_20d_momentum, five_day_acceleration,
                   relative_strength, volume_weighted_momentum,
                   volume_confirmation, closing_strength_5d,
                   rsi_14, momentum_quality, breakout_score, reversal_quality
            FROM factor_snapshots
            ORDER BY trade_date, symbol
        """)).fetchall()

        # Build DataFrames
        track_df = pd.DataFrame(tracking, columns=[
            "output_date", "symbol", "horizon_days", "forward_return",
            "as_of_close", "due_close", "ticket_id",
            "market_score", "catalyst_score", "ticket_score",
        ])
        track_df["output_date"] = pd.to_datetime(track_df["output_date"])
        identities = []
        seen = set()
        for row in track_df.itertuples(index=False):
            if row.ticket_id in (None, ""):
                continue
            identity = sample_id(
                ticket_id=row.ticket_id,
                replay_horizon=row.horizon_days,
                replay_date=row.output_date.date().isoformat() if hasattr(row.output_date, "date") else str(row.output_date)[:10],
                symbol=row.symbol,
                output_date=row.output_date.date().isoformat() if hasattr(row.output_date, "date") else str(row.output_date)[:10],
            )
            if identity in seen:
                raise DuplicateSampleError(identity)
            seen.add(identity)
            identities.append(identity)
        track_df["sample_id"] = [
            sample_id(
                ticket_id=row.ticket_id,
                replay_horizon=row.horizon_days,
                replay_date=row.output_date.date().isoformat() if hasattr(row.output_date, "date") else str(row.output_date)[:10],
                symbol=row.symbol,
                output_date=row.output_date.date().isoformat() if hasattr(row.output_date, "date") else str(row.output_date)[:10],
            ) if row.ticket_id not in (None, "") else None
            for row in track_df.itertuples(index=False)
        ]

        factor_df = pd.DataFrame(factors, columns=[
            "trade_date", "symbol",
            "prior_5d_momentum", "prior_20d_momentum", "five_day_acceleration",
            "relative_strength", "volume_weighted_momentum",
            "volume_confirmation", "closing_strength_5d",
            "rsi_14", "momentum_quality", "breakout_score", "reversal_quality",
        ])
        factor_df["trade_date"] = pd.to_datetime(factor_df["trade_date"])

        # Merge
        merged = track_df.merge(
            factor_df,
            left_on=["output_date", "symbol"],
            right_on=["trade_date", "symbol"],
            how="inner",
        )

        if len(merged) < 10:
            return {"status": "INSUFFICIENT_DATA", "rows": len(merged)}

        # Compute IC for each factor per horizon
        from scipy import stats

        db_factors = [
            "prior_5d_momentum", "prior_20d_momentum", "five_day_acceleration",
            "relative_strength", "volume_weighted_momentum",
            "volume_confirmation", "closing_strength_5d",
            "rsi_14", "momentum_quality", "breakout_score", "reversal_quality",
            "market_score", "catalyst_score", "ticket_score",
        ]

        results = {"by_horizon": {}, "overall": {}, "sample_size": len(merged)}

        for horizon in [1, 3, 10]:
            h_df = merged[merged["horizon_days"] == horizon].copy()
            if len(h_df) < 5:
                continue

            horizon_results = {}
            for factor in db_factors:
                if factor not in h_df.columns:
                    continue
                valid = h_df[[factor, "forward_return"]].dropna()
                if len(valid) < 5:
                    continue
                try:
                    ic, p_value = stats.spearmanr(valid[factor], valid["forward_return"])
                    if np.isnan(ic) or np.isnan(p_value):
                        continue
                    # Long-short: top quartile vs bottom quartile
                    q25 = valid[factor].quantile(0.25)
                    q75 = valid[factor].quantile(0.75)
                    bottom = valid[valid[factor] <= q25]["forward_return"]
                    top = valid[valid[factor] >= q75]["forward_return"]
                    long_short = float(top.mean() - bottom.mean()) if len(bottom) >= 2 and len(top) >= 2 else 0.0

                    horizon_results[factor] = {
                        "ic": round(float(ic), 4),
                        "p_value": round(float(p_value), 4),
                        "abs_ic": round(abs(float(ic)), 4),
                        "long_short": round(long_short, 6),
                        "n": len(valid),
                        "significant": bool(p_value < 0.05),
                    }
                except Exception:
                    continue

            # Rank by abs IC
            ranked = sorted(horizon_results.items(), key=lambda x: x[1]["abs_ic"], reverse=True)
            results["by_horizon"][f"{horizon}d"] = {
                "factors": horizon_results,
                "ranking": [f[0] for f in ranked],
                "sample_size": len(h_df),
            }

        # Overall IC (across all horizons)
        overall_results = {}
        for factor in db_factors:
            if factor not in merged.columns:
                continue
            valid = merged[[factor, "forward_return"]].dropna()
            if len(valid) < 10:
                continue
            try:
                ic, p_value = stats.spearmanr(valid[factor], valid["forward_return"])
                if np.isnan(ic) or np.isnan(p_value):
                    continue
                overall_results[factor] = {
                    "ic": round(float(ic), 4),
                    "abs_ic": round(abs(float(ic)), 4),
                    "p_value": round(float(p_value), 4),
                    "n": len(valid),
                    "significant": bool(p_value < 0.05),
                }
            except Exception:
                continue

        ranked_overall = sorted(overall_results.items(), key=lambda x: x[1]["abs_ic"], reverse=True)
        results["overall"] = {
            "factors": overall_results,
            "ranking": [f[0] for f in ranked_overall],
        }

        return results

    finally:
        session.close()


# ─── Step 4: Weight Optimization ────────────────────────────────
# EMA smoothing factor: 0.3 = 30% new + 70% old (prevents oscillation)
WEIGHT_EMA_ALPHA = 0.3
# Maximum weight for any single factor (prevents concentration)
MAX_SINGLE_FACTOR_WEIGHT = 0.35
# Minimum sample size for IC to be considered stable
MIN_IC_SAMPLE_SIZE = 10


def step_weight_optimization(factor_backtest: dict) -> dict:
    """Compute optimal weights from IC analysis with stability constraints."""
    if factor_backtest.get("status") in ("NO_DATA", "INSUFFICIENT_DATA"):
        return {"status": "skipped", "reason": "no factor backtest data"}

    overall = factor_backtest.get("overall", {})
    factors = overall.get("factors", {})
    ranking = overall.get("ranking", [])

    if not factors:
        return {"status": "skipped", "reason": "no factor IC data"}

    # Map factor names to pipeline scoring weight keys
    factor_key_map = {
        "prior_20d_momentum": "prior_20d_momentum",
        "five_day_acceleration": "five_day_acceleration",
        "relative_strength": "relative_strength_vs_equal_weight",
        "volume_weighted_momentum": "volume_weighted_momentum",
        "closing_strength_5d": "closing_strength_5d",
        "volume_confirmation": "volume_confirmation_ratio",
        "reversal_quality": "reversal_quality",
        "rsi_14": "rsi_14",
        "momentum_quality": "momentum_quality",
        "breakout_score": "breakout_score",
        "market_score": "market_score",
        "catalyst_score": "catalyst_score",
    }

    # ── Filter: only factors with sufficient samples + significance ──
    stable_factors = {}
    for k, v in factors.items():
        if k not in factor_key_map:
            continue
        if v.get("n", 0) < MIN_IC_SAMPLE_SIZE:
            continue  # Too few observations — IC unreliable
        if not v.get("significant", False):
            continue  # Not statistically significant
        stable_factors[k] = v

    if not stable_factors:
        return {
            "status": KEEP_PREVIOUS_WEIGHT,
            "decision": KEEP_PREVIOUS_WEIGHT,
            "reason": "insufficient_evidence",
            "production_apply": False,
            "new_weights": {},
            "old_weights": {},
        }

    # Weight by abs IC, signed by IC direction
    abs_ic_sum = sum(v["abs_ic"] for v in stable_factors.values())
    if abs_ic_sum == 0:
        return {"status": "skipped", "reason": "all ICs are zero"}

    # First pass: raw weights from IC
    raw_weights = {}
    for factor_name, ic_data in stable_factors.items():
        pipeline_key = factor_key_map[factor_name]
        raw_weight = ic_data["abs_ic"] / abs_ic_sum
        sign = 1 if ic_data["ic"] >= 0 else -1
        raw_weights[pipeline_key] = raw_weight * sign

    # Apply minimum floor (5%) and maximum cap
    MIN_WEIGHT = 0.05
    new_weights = {}
    for pipeline_key, w in raw_weights.items():
        if abs(w) < MIN_WEIGHT and w != 0:
            w = MIN_WEIGHT if w > 0 else -MIN_WEIGHT
        # Cap single factor weight
        if abs(w) > MAX_SINGLE_FACTOR_WEIGHT:
            w = MAX_SINGLE_FACTOR_WEIGHT if w > 0 else -MAX_SINGLE_FACTOR_WEIGHT
        new_weights[pipeline_key] = round(w, 4)

    # Re-normalize to sum to 1.0
    total_abs = sum(abs(v) for v in new_weights.values())
    if total_abs > 0:
        for pipeline_key in new_weights:
            new_weights[pipeline_key] = round(new_weights[pipeline_key] / total_abs, 4)

    # Load current weights for EMA smoothing
    current_weights = {}
    if WEIGHTS_FILE.exists():
        try:
            current_data = json.loads(WEIGHTS_FILE.read_text())
            current_weights = current_data.get("weights", {})
        except Exception:
            pass

    # ── EMA Smoothing: blend new with old ──────────────────────────
    if current_weights:
        all_keys = set(list(new_weights.keys()) + list(current_weights.keys()))
        smoothed = {}
        for key in all_keys:
            old_w = current_weights.get(key, 0.0)
            new_w = new_weights.get(key, 0.0)
            smoothed[key] = round(
                WEIGHT_EMA_ALPHA * new_w + (1 - WEIGHT_EMA_ALPHA) * old_w, 4
            )
        # Re-cap after smoothing (EMA can push weights past the cap)
        for key in smoothed:
            if abs(smoothed[key]) > MAX_SINGLE_FACTOR_WEIGHT:
                smoothed[key] = MAX_SINGLE_FACTOR_WEIGHT if smoothed[key] > 0 else -MAX_SINGLE_FACTOR_WEIGHT
        # Re-normalize after smoothing + capping
        total_abs = sum(abs(v) for v in smoothed.values())
        if total_abs > 0:
            for key in smoothed:
                smoothed[key] = round(smoothed[key] / total_abs, 4)
        new_weights = smoothed

    mutation = request_weight_change(
        source="full_cycle",
        previous=current_weights,
        proposed=new_weights,
        persist=None,
        sample_count=int(factor_backtest.get("sample_size") or 0),
        trading_days=0,
        factor_coverage=None,
        confirmations=0,
        reason="full_cycle_optimization",
    )
    return {
        "status": KEEP_PREVIOUS_WEIGHT,
        "decision": mutation["decision"],
        "production_apply": False,
        "proposal_status": mutation["status"],
        "current_weight": mutation["current_weight"],
        "proposed_weight": mutation["proposed_weight"],
        "new_weights": mutation["proposed_weight"],
        "old_weights": current_weights,
        "ema_smoothed": bool(current_weights),
        "top_factors": ranking[:5],
        "stable_factors": list(stable_factors.keys()),
        "significant_count": sum(1 for v in factors.values() if v.get("significant")),
        "weight_mutation": mutation,
        "strategy_status": PRODUCTION_BOUNDARY["strategy_status"],
    }


# ─── Step 5: Scoreboard ─────────────────────────────────────────
def step_scoreboard() -> dict:
    """Update lifecycle scoreboard from DB."""
    result = subprocess.run(
        [sys.executable, str(PROJECT_ROOT / "scripts" / "lifecycle_scoreboard.py"), "--db"],
        capture_output=True, text=True, timeout=120,
        cwd=str(PROJECT_ROOT),
    )
    return {"status": "ok" if result.returncode == 0 else "failed"}


# ─── Step 6: Degradation Check ──────────────────────────────────
def step_degradation_check() -> dict:
    """Run meta-loop degradation detection."""
    result = subprocess.run(
        [sys.executable, str(PROJECT_ROOT / "scripts" / "meta_loop.py")],
        capture_output=True, text=True, timeout=60,
        cwd=str(PROJECT_ROOT),
    )
    if result.returncode == 0:
        try:
            return json.loads(result.stdout)
        except Exception:
            pass
    return {"status": "failed", "error": result.stderr[:200]}


# ─── Step 7: Pipeline Upgrade ───────────────────────────────────
def step_pipeline_upgrade(degradation: dict, weight_result: dict) -> dict:
    """Store a RESEARCH_PROPOSAL. Never PRODUCTION_APPLY while FROZEN."""
    try:
        assert_production_apply_blocked(source="pipeline_upgrade")
        production_apply = False
    except ProductionApplyBlocked:
        production_apply = False
    actions = []

    # Check degradation
    degradation_list = degradation.get("degradation", [])
    critical = [d for d in degradation_list if d.get("severity") == "CRITICAL"]
    high_severity = [d for d in degradation_list if d.get("severity") == "HIGH"]

    if critical:
        actions.append({
            "action": "STOP_PIPELINE",
            "reason": f"CRITICAL degradation: {len(critical)} critical issues",
            "details": [d.get("message", "") for d in critical],
        })

    if high_severity:
        actions.append({
            "action": "ALERT",
            "reason": f"Performance degradation: {len(high_severity)} high-severity issues",
            "details": [d.get("message", "") for d in high_severity],
        })

    # Add recommended actions from meta_loop
    for rec in degradation.get("recommended_actions", []):
        if rec.startswith("REDUCE_UNIVERSE") or rec.startswith("RAISE_SCORE_GATE"):
            actions.append({"action": "CONFIG_CHANGE", "reason": rec})

    # Check if weights changed significantly (after EMA, threshold is lower)
    old_w = weight_result.get("old_weights", {})
    new_w = weight_result.get("new_weights", {})
    if old_w and new_w:
        max_diff = 0
        for key in set(list(old_w.keys()) + list(new_w.keys())):
            diff = abs(new_w.get(key, 0) - old_w.get(key, 0))
            max_diff = max(max_diff, diff)
        if max_diff > 0.1:
            actions.append({
                "action": "RESEARCH_PROPOSAL",
                "reason": f"Weight proposal detected (max diff: {max_diff:.2%})",
                "old": old_w,
                "new": new_w,
                "production_apply": False,
            })

    # Note EMA smoothing status
    if weight_result.get("ema_smoothed"):
        actions.append({
            "action": "EMA_APPLIED",
            "reason": "Weights EMA-smoothed to prevent oscillation",
        })

    if not actions:
        actions.append({"action": "NO_CHANGE", "reason": "System performing within normal range"})

    return {
        "status": "RESEARCH_PROPOSAL",
        "actions": actions,
        "degradation_count": len(degradation_list),
        "has_critical": bool(critical),
        "production_apply": production_apply,
        "strategy_status": PRODUCTION_BOUNDARY["strategy_status"],
    }


# ─── Main Orchestrator ──────────────────────────────────────────
def run_full_cycle(output_date: str = None, skip_pipeline: bool = False) -> dict:
    """Run the complete cycle."""
    if not output_date:
        output_date = CALENDAR.previous_completed_session().isoformat()

    cycle_start = time.time()
    results = {
        "output_date": output_date,
        "started_at": datetime.now().isoformat(),
        "steps": {},
    }

    # Step 1: Pipeline (出票)
    if not skip_pipeline:
        results["steps"]["pipeline"] = run_step("出票 Pipeline", step_pipeline, output_date)
    else:
        results["steps"]["pipeline"] = {"status": "skipped", "reason": "skip_pipeline=True"}

    # Step 2: Backfill (回填)
    results["steps"]["backfill"] = run_step("回填 Forward Tracking", step_backfill)

    # Step 3: Factor Backtest (因子回测)
    results["steps"]["factor_backtest"] = run_step("因子回测", step_factor_backtest)

    # Step 4: Weight Optimization (权重优化)
    fb_result = results["steps"]["factor_backtest"].get("result", {})
    results["steps"]["weight_optimization"] = run_step("权重优化", step_weight_optimization, fb_result)

    # Step 5: Scoreboard (记分板)
    results["steps"]["scoreboard"] = run_step("记分板更新", step_scoreboard)

    # Step 6: Degradation Check (退化检测)
    results["steps"]["degradation_check"] = run_step("退化检测", step_degradation_check)

    # Step 7: Pipeline Upgrade (链路升级)
    deg_result = results["steps"]["degradation_check"].get("result", {})
    weight_result = results["steps"]["weight_optimization"].get("result", {})
    results["steps"]["pipeline_upgrade"] = run_step(
        "链路升级决策", step_pipeline_upgrade, deg_result, weight_result
    )

    # Summary
    cycle_elapsed = time.time() - cycle_start
    results["completed_at"] = datetime.now().isoformat()
    results["total_elapsed"] = round(cycle_elapsed, 1)

    step_statuses = {k: v.get("status", "unknown") for k, v in results["steps"].items()}
    results["summary"] = {
        "total_steps": len(step_statuses),
        "ok_count": sum(1 for s in step_statuses.values() if s == "ok"),
        "error_count": sum(1 for s in step_statuses.values() if s == "error"),
        "skipped_count": sum(1 for s in step_statuses.values() if s == "skipped"),
        "step_statuses": step_statuses,
    }

    # Save cycle log
    RESEARCH_DIR.mkdir(parents=True, exist_ok=True)
    CYCLE_LOG.write_text(json.dumps(results, indent=2, ensure_ascii=False, default=str))

    return results


def print_cycle_report(results: dict):
    """Print human-readable cycle report."""
    print(f"\n{'='*60}")
    print(f"FULL CYCLE REPORT - {results['output_date']}")
    print(f"{'='*60}")
    print(f"Total time: {results['total_elapsed']}s")
    print(f"Steps: {results['summary']['ok_count']} ok, "
          f"{results['summary']['error_count']} errors, "
          f"{results['summary']['skipped_count']} skipped")
    print()

    for step_name, step_data in results["steps"].items():
        status = step_data.get("status", "unknown")
        elapsed = step_data.get("elapsed", 0)
        icon = "✅" if status == "ok" else "❌" if status == "error" else "⏭️"
        print(f"  {icon} {step_name}: {status} ({elapsed}s)")

        # Print key results
        result = step_data.get("result", {})
        if step_name == "factor_backtest" and isinstance(result, dict):
            ranking = result.get("overall", {}).get("ranking", [])
            if ranking:
                print(f"     Top factors: {', '.join(ranking[:5])}")

        if step_name == "weight_optimization" and isinstance(result, dict):
            new_w = result.get("new_weights", {})
            if new_w:
                print(f"     New weights: {json.dumps(new_w, indent=0)}")

        if step_name == "pipeline_upgrade" and isinstance(result, dict):
            for action in result.get("actions", []):
                print(f"     → {action['action']}: {action['reason']}")

    print()


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Full cycle orchestrator")
    parser.add_argument("--output-date", default=None)
    parser.add_argument("--skip-pipeline", action="store_true", help="Skip ticket pipeline")
    args = parser.parse_args()

    results = run_full_cycle(
        output_date=args.output_date,
        skip_pipeline=args.skip_pipeline,
    )
    print_cycle_report(results)
    print(json.dumps(results, indent=2, ensure_ascii=False, default=str))
