#!/usr/bin/env python3
"""Research-only Capital Brain A/B benchmark with fixed-chain gates."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import pandas as pd
from sqlalchemy import create_engine, text

from db.engine import DATABASE_URL


ROOT = Path(__file__).resolve().parent.parent
REPORT_JSON = ROOT / "research" / "capital-backtest.json"
REPORT_MD = ROOT / "research" / "capital-backtest.md"
MIN_COMPLETED_ROWS = 30
MIN_DATES = 10


def load_rows(engine) -> pd.DataFrame:
    """Load outcomes whose daily inputs and research run are versioned."""
    return pd.read_sql(text("""
        SELECT ft.id, ft.as_of_date, ft.symbol, ft.horizon_days, ft.forward_return,
               ft.capital_validation_status, ft.capital_score_at_entry,
               ft.distribution_score_at_entry, ft.trap_score_at_entry,
               ft.predicted_path, t.ticket_score, t.market_score, t.expected_direction,
               rr.config->>'strategy_version' AS strategy_version,
               rr.config->>'version_status' AS version_status
        FROM forward_tracking ft
        JOIN tickets t ON t.id = ft.ticket_id
        JOIN research_runs rr ON rr.run_id = t.research_run_id
        WHERE ft.check_status = 'completed'
          AND ft.forward_return IS NOT NULL
          AND ft.capital_model_version = 'capital_behavior_v1'
          AND rr.status = 'done'
          AND rr.finished_at IS NOT NULL
        ORDER BY ft.as_of_date, ft.symbol, ft.horizon_days
    """), engine)


def _metrics(rows: pd.DataFrame) -> dict[str, Any]:
    if rows.empty:
        return {"sample_count": 0, "win_rate": None, "avg_return": None, "median_return": None, "profit_factor": None}
    returns = rows["forward_return"].astype(float)
    gains = returns[returns > 0].sum()
    losses = returns[returns < 0].sum()
    return {
        "sample_count": int(len(rows)),
        "win_rate": round(float((returns > 0).mean()), 6),
        "avg_return": round(float(returns.mean()), 6),
        "median_return": round(float(returns.median()), 6),
        "profit_factor": round(float(gains / abs(losses)), 6) if losses < 0 else None,
        "t1_direction_accuracy": _direction_accuracy(rows[rows["horizon_days"] == 1]),
        "t3_direction_accuracy": _direction_accuracy(rows[rows["horizon_days"] == 3]),
        "t5_direction_accuracy": _direction_accuracy(rows[rows["horizon_days"] == 5]),
        "mfe": "UNAVAILABLE_NOT_PERSISTED",
        "mae": "UNAVAILABLE_NOT_PERSISTED",
    }


def _direction_accuracy(rows: pd.DataFrame) -> float | None:
    measurable = rows[rows["expected_direction"].isin(["LONG", "SHORT"])]
    if measurable.empty:
        return None
    matches = (
        ((measurable["expected_direction"] == "LONG") & (measurable["forward_return"] > 0))
        | ((measurable["expected_direction"] == "SHORT") & (measurable["forward_return"] < 0))
    )
    return round(float(matches.mean()), 6)


def _top_by_day(rows: pd.DataFrame, score: pd.Series, exclusion: pd.Series | None = None) -> pd.DataFrame:
    work = rows.copy()
    work["_score"] = score
    if exclusion is not None:
        work = work.loc[~exclusion].copy()
    work = work.dropna(subset=["_score"])
    if work.empty:
        return work
    return work.sort_values(["as_of_date", "_score"], ascending=[True, False]).groupby(
        "as_of_date", group_keys=False
    ).head(1)


def run_benchmark(engine=None) -> dict[str, Any]:
    """Run A-F in parallel only; this function never changes production weights."""
    engine = engine or create_engine(DATABASE_URL)
    raw = load_rows(engine)
    fixed = raw[
        (raw["strategy_version"] == "observable_footprint_v1")
        & (raw["version_status"] == "VERSIONED")
        & (raw["capital_validation_status"] == "VALIDATED_FOR_BENCHMARK")
    ].copy()
    gate = {
        "raw_completed_rows": int(len(raw)),
        "fixed_chain_rows": int(len(fixed)),
        "trading_days": int(fixed["as_of_date"].nunique()) if not fixed.empty else 0,
    }
    ready = gate["fixed_chain_rows"] >= MIN_COMPLETED_ROWS and gate["trading_days"] >= MIN_DATES
    if not ready:
        return {
            "status": "UNVALIDATED_NO_FIXED_CHAIN",
            "reason": "capital_parallel_model_has_no_independent_validated_completed_chain",
            "gate": gate,
            "production_action": "KEEP_OBSERVABLE_FOOTPRINT_RANKING_UNCHANGED",
            "variants": {},
        }

    statistical = fixed["ticket_score"].fillna(fixed["market_score"]).clip(0, 1)
    capital = fixed["capital_score_at_entry"].clip(0, 1)
    combined = 0.70 * statistical + 0.30 * capital
    high_distribution = fixed["distribution_score_at_entry"].fillna(0) >= 0.70
    high_trap = fixed["trap_score_at_entry"].fillna(0) >= 0.70
    path_reject = fixed["predicted_path"].isin(["DISTRIBUTION", "TRAP", "BREAKDOWN"])
    variants = {
        "A_current_xiaomei": _metrics(_top_by_day(fixed, statistical)),
        "B_capital_only": _metrics(_top_by_day(fixed, capital)),
        "C_current_plus_capital": _metrics(_top_by_day(fixed, combined)),
        "D_plus_distribution_gate": _metrics(_top_by_day(fixed, combined, high_distribution)),
        "E_plus_distribution_trap_path": _metrics(_top_by_day(fixed, combined, high_distribution | high_trap | path_reject)),
        "F_plus_intraday_capital": {
            "status": "UNVALIDATED_NO_COMPLETED_INTRADAY_OUTCOME_CHAIN",
            "reason": "intraday paper decisions have no versioned linked outcome benchmark",
        },
    }
    return {
        "status": "RESEARCH_ONLY_BENCHMARK",
        "validation_status": "UNVALIDATED_NOT_READY",
        "gate": gate,
        "production_action": "KEEP_OBSERVABLE_FOOTPRINT_RANKING_UNCHANGED",
        "variants": variants,
    }


def write_report(result: dict[str, Any]) -> dict[str, Path]:
    REPORT_JSON.parent.mkdir(parents=True, exist_ok=True)
    REPORT_JSON.write_text(json.dumps(result, indent=2, ensure_ascii=False, default=str) + "\n", encoding="utf-8")
    lines = [
        "# Capital Behavior A/B Benchmark",
        "",
        f"- Status: `{result['status']}`",
        f"- Production action: `{result['production_action']}`",
        f"- Fixed-chain rows: `{result['gate']['fixed_chain_rows']}`",
        f"- Trading days: `{result['gate']['trading_days']}`",
        "",
    ]
    for name, metrics in result.get("variants", {}).items():
        lines.extend([
            f"## {name}",
            "",
            f"- Sample count: `{metrics.get('sample_count')}`",
            f"- Win rate: `{metrics.get('win_rate')}`",
            f"- Average return: `{metrics.get('avg_return')}`",
            f"- Profit factor: `{metrics.get('profit_factor')}`",
            "",
        ])
    REPORT_MD.write_text("\n".join(lines), encoding="utf-8")
    return {"json": REPORT_JSON, "markdown": REPORT_MD}


def main() -> int:
    parser = argparse.ArgumentParser(description="Capital Brain research-only A/B benchmark")
    parser.parse_args()
    result = run_benchmark()
    paths = write_report(result)
    print(json.dumps({"result": result, "artifacts": {key: str(value) for key, value in paths.items()}}, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
