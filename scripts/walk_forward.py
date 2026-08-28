#!/usr/bin/env python3
"""Walk-forward validation for xiaomei stock scoring.

Rolling window: train on past N days, predict next M days.
Each window: compute factor IC on training, generate weights, apply to test,
compare predicted rank vs actual return.
Output: win_rate, avg_return, IC stability.
"""
import argparse
import json
import sys
from datetime import date, timedelta
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats
from sqlalchemy import create_engine, text

from db.engine import DATABASE_URL

FACTORS = [
    "prior_5d_momentum", "prior_20d_momentum", "five_day_acceleration",
    "relative_strength", "volume_weighted_momentum", "rsi_14",
    "momentum_quality", "breakout_score", "reversal_quality",
    "volume_confirmation", "closing_strength_5d",
]
CAPITAL_FACTORS = [
    "upward_pressure", "downward_pressure", "volume_pressure",
    "demand_persistence", "supply_exhaustion", "absorption", "accumulation",
    "markup", "distribution", "crowding", "trap", "price_impact",
]

RESEARCH_DIR = Path(__file__).resolve().parent.parent / "research" / "walk-forward"


def load_data(engine, start_date, end_date):
    factor_df = pd.read_sql(
        text("SELECT trade_date, symbol, " + ", ".join(FACTORS) +
             " FROM factor_snapshots WHERE trade_date BETWEEN :start AND :end "
             "ORDER BY trade_date, symbol"),
        engine, params={"start": start_date, "end": end_date},
    )
    track_df = pd.read_sql(
        text("SELECT as_of_date, symbol, horizon_days, forward_return "
             "FROM forward_tracking WHERE check_status = 'completed' "
             "AND as_of_date BETWEEN :start AND :end"),
        engine, params={"start": start_date, "end": end_date},
    )
    return factor_df, track_df


def compute_train_ic(factor_df, track_df, train_dates, horizon):
    train_factors = factor_df[factor_df["trade_date"].isin(train_dates)]
    train_track = track_df[
        (track_df["horizon_days"] == horizon) &
        (track_df["as_of_date"].isin(train_dates))
    ]
    merged = train_factors.merge(
        train_track, left_on=["trade_date", "symbol"],
        right_on=["as_of_date", "symbol"], how="inner",
    )
    if len(merged) < 30:
        return None
    ic = {}
    for f in FACTORS:
        valid = merged[[f, "forward_return"]].dropna()
        if len(valid) < 10:
            ic[f] = 0.0
        else:
            ic[f], _ = stats.spearmanr(valid[f], valid["forward_return"])
    return ic


def ic_to_weights(ic_scores):
    abs_ic = {k: abs(v) for k, v in ic_scores.items()}
    total = sum(abs_ic.values())
    if total == 0:
        return {f: 0.0 for f in FACTORS}
    return {
        f: round(abs_ic.get(f, 0) / total * (1 if ic_scores.get(f, 0) >= 0 else -1), 6)
        for f in FACTORS
    }


def score_test(factor_df, weights, test_date):
    day_factors = factor_df[factor_df["trade_date"] == test_date].copy()
    if day_factors.empty:
        return None
    day_factors["composite"] = sum(
        day_factors[f].fillna(0) * w for f, w in weights.items()
    )
    return day_factors[["trade_date", "symbol", "composite"]].sort_values(
        "composite", ascending=False
    )


def evaluate_window(test_factors_scored, track_df, horizon):
    test_track = track_df[
        (track_df["horizon_days"] == horizon) &
        (track_df["as_of_date"].isin(test_factors_scored["trade_date"].unique()))
    ]
    merged = test_factors_scored.merge(
        test_track, left_on=["trade_date", "symbol"],
        right_on=["as_of_date", "symbol"], how="inner",
    )
    if merged.empty:
        return None
    results = []
    for tdate, grp in merged.groupby("trade_date"):
        grp = grp.sort_values("composite", ascending=False)
        n = len(grp)
        if n < 3:
            continue
        actual_rank = grp["forward_return"].rank(ascending=False).astype(int)
        pred_rank = grp["composite"].rank(ascending=False).astype(int)
        spearman_corr, _ = stats.spearmanr(grp["composite"], grp["forward_return"])
        top_n = max(3, n // 3)
        top_pred = grp.nlargest(top_n, "composite")
        top_actual = grp.nlargest(top_n, "forward_return")
        overlap = len(set(top_pred["symbol"]) & set(top_actual["symbol"]))
        win = int(top_pred["forward_return"].mean() > 0)
        results.append({
            "date": str(tdate),
            "n_stocks": n,
            "ic": round(spearman_corr, 4),
            "top_n_overlap": overlap,
            "top_n_total": top_n,
            "top_pred_return": round(float(top_pred["forward_return"].mean()), 6),
            "avg_return": round(float(grp["forward_return"].mean()), 6),
            "win": win,
            "pred_rank_vs_actual": {
                str(row["symbol"]): {"pred": int(row["pred_rank"]), "actual": int(row["actual_rank"]), "ret": round(float(row["forward_return"]), 6)}
                for _, row in grp.iterrows()
            },
        })
    return results


def run_walk_forward(train_days=60, test_days=5, horizon=1):
    engine = create_engine(DATABASE_URL)
    all_dates = pd.read_sql(
        text("SELECT DISTINCT trade_date FROM factor_snapshots ORDER BY trade_date"),
        engine,
    )["trade_date"].tolist()
    if not all_dates:
        print("No factor_snapshots data")
        return
    min_date = all_dates[0]
    max_date = all_dates[-1]
    all_tracked_dates = pd.read_sql(
        text("SELECT DISTINCT as_of_date FROM forward_tracking "
             "WHERE check_status = 'completed' ORDER BY as_of_date"),
        engine,
    )["as_of_date"].tolist()
    factor_df, track_df = load_data(engine, min_date, max_date)
    factor_df["trade_date"] = pd.to_datetime(factor_df["trade_date"]).dt.date
    track_df["as_of_date"] = pd.to_datetime(track_df["as_of_date"]).dt.date

    windows = []
    train_start = 0
    while True:
        train_end = train_start + train_days
        test_end = train_end + test_days
        if train_end >= len(all_dates) or test_end > len(all_dates):
            break
        train_dates = all_dates[train_start:train_end]
        test_dates = all_dates[train_end:test_end]
        windows.append({"train": train_dates, "test": test_dates})
        train_start += test_days

    if not windows:
        print(f"Not enough data for train={train_days} test={test_days}")
        return

    all_window_results = []
    ic_history = []
    for i, w in enumerate(windows):
        ic = compute_train_ic(factor_df, track_df, w["train"], horizon)
        if ic is None:
            continue
        ic_history.append({"window": i, "ic": ic.copy()})
        weights = ic_to_weights(ic)
        all_scored = []
        for tdate in w["test"]:
            scored = score_test(factor_df, weights, tdate)
            if scored is not None:
                all_scored.append(scored)
        if not all_scored:
            continue
        test_scored = pd.concat(all_scored, ignore_index=True)
        eval_results = evaluate_window(test_scored, track_df, horizon)
        if not eval_results:
            continue
        avg_ic = np.mean([r["ic"] for r in eval_results])
        avg_overlap = np.mean([r["top_n_overlap"] / r["top_n_total"] for r in eval_results])
        avg_return = np.mean([r["avg_return"] for r in eval_results])
        win_rate = np.mean([r["win"] for r in eval_results])
        all_window_results.append({
            "window": i,
            "train_range": [str(w["train"][0]), str(w["train"][-1])],
            "test_range": [str(w["test"][0]), str(w["test"][-1])],
            "avg_ic": round(avg_ic, 4),
            "avg_overlap": round(avg_overlap, 4),
            "avg_return": round(avg_return, 6),
            "win_rate": round(win_rate, 4),
            "weights": weights,
            "details": eval_results,
        })

    if not all_window_results:
        print("No valid windows")
        return

    ic_stability = {}
    for f in FACTORS:
        ics = [w["ic"][f] for w in ic_history if f in w["ic"]]
        if ics:
            ic_stability[f] = {
                "mean": round(float(np.mean(ics)), 4),
                "std": round(float(np.std(ics)), 4),
                "min": round(float(np.min(ics)), 4),
                "max": round(float(np.max(ics)), 4),
                "positive_pct": round(float(np.mean([x > 0 for x in ics])), 4),
            }

    summary = {
        "config": {"train_days": train_days, "test_days": test_days, "horizon": horizon},
        "total_windows": len(all_window_results),
        "overall": {
            "avg_win_rate": round(float(np.mean([w["win_rate"] for w in all_window_results])), 4),
            "avg_return": round(float(np.mean([w["avg_return"] for w in all_window_results])), 6),
            "avg_ic": round(float(np.mean([w["avg_ic"] for w in all_window_results])), 4),
            "avg_overlap": round(float(np.mean([w["avg_overlap"] for w in all_window_results])), 4),
            "win_rate_std": round(float(np.std([w["win_rate"] for w in all_window_results])), 4),
            "return_std": round(float(np.std([w["avg_return"] for w in all_window_results])), 6),
        },
        "ic_stability": ic_stability,
        "windows": all_window_results,
    }

    RESEARCH_DIR.mkdir(parents=True, exist_ok=True)
    json_path = RESEARCH_DIR / f"walk-forward-{train_days}d-{test_days}d-h{horizon}.json"
    json_path.write_text(json.dumps(summary, indent=2, ensure_ascii=False))

    lines = [
        f"# Walk-Forward Validation (train={train_days}d, test={test_days}d, horizon={horizon}d)",
        f"- Windows: {len(all_window_results)}",
        f"- Avg Win Rate: {summary['overall']['avg_win_rate']:.1%}",
        f"- Avg Return: {summary['overall']['avg_return']:+.4%}",
        f"- Avg IC: {summary['overall']['avg_ic']:+.4f}",
        f"- Avg Top-N Overlap: {summary['overall']['avg_overlap']:.1%}",
        f"- Win Rate Std: {summary['overall']['win_rate_std']:.4f}",
        f"- Return Std: {summary['overall']['return_std']:.6f}",
        "",
        "## IC Stability by Factor",
        "|factor|mean_IC|std|min|max|positive_%|",
        "|---|---|---|---|---|---|",
    ]
    for f, s in sorted(ic_stability.items(), key=lambda x: abs(x[1]["mean"]), reverse=True):
        lines.append(f"|{f}|{s['mean']:+.4f}|{s['std']:.4f}|{s['min']:+.4f}|{s['max']:+.4f}|{s['positive_pct']:.0%}|")

    lines.extend(["", "## Per-Window Results", "|window|train|test|win_rate|avg_return|avg_ic|overlap|",
                   "|---|---|---|---|---|---|---|"])
    for w in all_window_results:
        lines.append(
            f"|{w['window']}|{w['train_range'][0]}~{w['train_range'][1]}|"
            f"{w['test_range'][0]}~{w['test_range'][1]}|"
            f"{w['win_rate']:.0%}|{w['avg_return']:+.4%}|{w['avg_ic']:+.4f}|{w['avg_overlap']:.0%}|"
        )

    md_path = RESEARCH_DIR / f"walk-forward-{train_days}d-{test_days}d-h{horizon}.md"
    md_path.write_text("\n".join(lines))
    print(json.dumps(summary["overall"], indent=2))
    print(f"\nJSON: {json_path}")
    print(f"Report: {md_path}")


def run_capital_walk_forward(train_days=60, test_days=5, horizon=1):
    """Run explicit TRAIN -> FIT -> TEST -> ADVANCE without production mutation."""
    engine = create_engine(DATABASE_URL)
    rows = pd.read_sql(text("""
        SELECT ce.as_of_date, ce.symbol, ce.evidence_type, ce.value,
               ft.forward_return, ft.capital_validation_status,
               rr.config->>'version_status' AS version_status
        FROM capital_evidence ce
        JOIN forward_tracking ft
          ON ft.symbol = ce.symbol AND ft.as_of_date = ce.as_of_date
        JOIN tickets t ON t.id = ft.ticket_id
        JOIN research_runs rr ON rr.run_id = t.research_run_id
        WHERE ft.check_status = 'completed'
          AND ft.forward_return IS NOT NULL
          AND ft.horizon_days = :horizon
          AND ce.model_version = 'capital_behavior_v1'
          AND rr.status = 'done'
          AND rr.finished_at IS NOT NULL
        ORDER BY ce.as_of_date, ce.symbol
    """), engine, params={"horizon": horizon})
    fixed = rows[
        (rows["capital_validation_status"] == "VALIDATED_FOR_BENCHMARK")
        & (rows["version_status"] == "VERSIONED")
    ].copy()
    output = RESEARCH_DIR / f"capital-walk-forward-{train_days}d-{test_days}d-h{horizon}.json"
    if fixed.empty:
        result = {
            "status": "UNVALIDATED_NO_FIXED_CHAIN",
            "reason": "no independent validated Capital Brain outcome chain",
            "production_action": "NO_PRODUCTION_WEIGHT_CHANGE",
            "workflow": ["TRAIN", "FIT", "TEST", "ADVANCE"],
            "raw_rows": int(len(rows)),
            "fixed_chain_rows": 0,
        }
        RESEARCH_DIR.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
        print(json.dumps(result, indent=2))
        return result

    panel = fixed.pivot_table(
        index=["as_of_date", "symbol", "forward_return"],
        columns="evidence_type",
        values="value",
        aggfunc="last",
    ).reset_index()
    panel["as_of_date"] = pd.to_datetime(panel["as_of_date"]).dt.date
    dates = sorted(panel["as_of_date"].unique())
    windows = []
    start = 0
    while start + train_days + test_days <= len(dates):
        train_dates = dates[start:start + train_days]
        test_dates = dates[start + train_days:start + train_days + test_days]
        train = panel[panel["as_of_date"].isin(train_dates)]
        test = panel[panel["as_of_date"].isin(test_dates)]
        if len(train) < 30 or test.empty:
            start += test_days
            continue
        # TRAIN: construct a strictly pre-test sample.
        ics = {}
        for feature in CAPITAL_FACTORS:
            cohort = train[[feature, "forward_return"]].dropna()
            if len(cohort) < 10:
                continue
            ic, _ = stats.spearmanr(cohort[feature], cohort["forward_return"])
            if np.isfinite(ic):
                ics[feature] = float(ic)
        if not ics:
            start += test_days
            continue
        # FIT: parameters are frozen before scoring every test date.
        normalizer = sum(abs(value) for value in ics.values())
        weights = {key: value / normalizer for key, value in ics.items()} if normalizer else {}
        # TEST: score only features known at each test date.
        scored = test.copy()
        scored["capital_composite"] = sum(
            scored[feature].fillna(0) * weight for feature, weight in weights.items()
        )
        top = scored.sort_values(["as_of_date", "capital_composite"], ascending=[True, False]).groupby(
            "as_of_date", group_keys=False
        ).head(1)
        windows.append({
            "train_range": [str(train_dates[0]), str(train_dates[-1])],
            "test_range": [str(test_dates[0]), str(test_dates[-1])],
            "train_rows": int(len(train)),
            "test_rows": int(len(test)),
            "weights": {key: round(value, 6) for key, value in weights.items()},
            "top_win_rate": round(float((top["forward_return"] > 0).mean()), 6),
            "top_avg_return": round(float(top["forward_return"].mean()), 6),
        })
        # ADVANCE: move forward only after the held-out period is scored.
        start += test_days

    result = {
        "status": "RESEARCH_ONLY" if windows else "UNVALIDATED_INSUFFICIENT_WINDOWS",
        "validation_status": "UNVALIDATED_NOT_READY",
        "production_action": "NO_PRODUCTION_WEIGHT_CHANGE",
        "workflow": ["TRAIN", "FIT", "TEST", "ADVANCE"],
        "config": {"train_days": train_days, "test_days": test_days, "horizon": horizon},
        "windows": windows,
        "overall": {
            "window_count": len(windows),
            "avg_top_win_rate": round(float(np.mean([item["top_win_rate"] for item in windows])), 6) if windows else None,
            "avg_top_return": round(float(np.mean([item["top_avg_return"] for item in windows])), 6) if windows else None,
        },
    }
    RESEARCH_DIR.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result["overall"], indent=2))
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Walk-forward validation")
    parser.add_argument("--train-days", type=int, default=60)
    parser.add_argument("--test-days", type=int, default=5)
    parser.add_argument("--horizon", type=int, default=1)
    parser.add_argument("--capital", action="store_true", help="Run research-only Capital Brain walk-forward.")
    args = parser.parse_args()
    if args.capital:
        run_capital_walk_forward(args.train_days, args.test_days, args.horizon)
    else:
        run_walk_forward(args.train_days, args.test_days, args.horizon)
