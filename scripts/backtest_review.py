"""
Backtest review: reads all completed forward tracking rows,
computes feedback signals, and outputs adjusted parameters
for the next pipeline run.
"""

import json
import os
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd

RESEARCH_BASE = Path(__file__).resolve().parent.parent / "research"
FORWARD_TRACKING_GLOBS = [
    "profit-ticket-pipeline/forward-tracking-*.csv",
    "profit-ticket-pipeline-opening/forward-tracking-*.csv",
]


def load_all_forward_tracking() -> pd.DataFrame:
    rows = []
    for pattern in FORWARD_TRACKING_GLOBS:
        for fpath in sorted(RESEARCH_BASE.glob(pattern)):
            try:
                df = pd.read_csv(fpath, on_bad_lines="warn")
                df["_source_file"] = fpath.name
                rows.append(df)
            except Exception:
                continue
    if not rows:
        return pd.DataFrame()
    combined = pd.concat(rows, ignore_index=True)
    return combined


def compute_feedback(df: pd.DataFrame) -> dict:
    completed = df[df["check_status"] == "completed"].copy()
    if completed.empty:
        return {"status": "NO_DATA", "message": "No completed forward tracking rows found"}

    completed["forward_return"] = pd.to_numeric(completed["forward_return"], errors="coerce")
    completed = completed.dropna(subset=["forward_return"])

    if completed.empty:
        return {"status": "NO_DATA", "message": "No valid forward_return values"}

    total = len(completed)
    wins = (completed["forward_return"] > 0).sum()
    losses = (completed["forward_return"] <= 0).sum()

    feedback = {
        "status": "OK",
        "as_of": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "total_completed": int(total),
        "wins": int(wins),
        "losses": int(losses),
        "win_rate": round(wins / total, 4) if total else 0,
        "avg_return": round(float(completed["forward_return"].mean()), 6),
        "median_return": round(float(completed["forward_return"].median()), 6),
        "avg_win": round(float(completed[completed["forward_return"] > 0]["forward_return"].mean()), 6) if wins else 0,
        "avg_loss": round(float(completed[completed["forward_return"] <= 0]["forward_return"].mean()), 6) if losses else 0,
        "profit_factor": 0.0,
        "by_horizon": {},
        "by_symbol": {},
        "symbol_penalties": {},
        "adjusted_momentum_exhaustion_threshold": None,
        "adjusted_scoring_weights": None,
        "adjusted_risk_params": None,
        "risk_insights": [],
    }

    if feedback["avg_loss"] != 0:
        feedback["profit_factor"] = round(
            abs(feedback["avg_win"] * wins / (feedback["avg_loss"] * losses)) if losses else float("inf"), 4
        )

    by_horizon = defaultdict(list)
    for _, row in completed.iterrows():
        h = str(row.get("horizon_days", row.get("review_window", "?")))
        by_horizon[h].append(float(row["forward_return"]))

    for h, returns in sorted(by_horizon.items()):
        arr = np.array(returns)
        feedback["by_horizon"][h] = {
            "count": int(len(arr)),
            "win_rate": round(float((arr > 0).mean()), 4),
            "avg_return": round(float(arr.mean()), 6),
            "median_return": round(float(np.median(arr)), 6),
            "max_win": round(float(arr.max()), 6),
            "max_loss": round(float(arr.min()), 6),
        }

    by_symbol = defaultdict(list)
    for _, row in completed.iterrows():
        by_symbol[str(row["symbol"])].append(float(row["forward_return"]))

    for sym, returns in sorted(by_symbol.items()):
        arr = np.array(returns)
        feedback["by_symbol"][sym] = {
            "count": int(len(arr)),
            "win_rate": round(float((arr > 0).mean()), 4),
            "avg_return": round(float(arr.mean()), 6),
        }

    for sym, data in feedback["by_symbol"].items():
        if data["count"] >= 2 and data["win_rate"] < 0.3:
            penalty = round(-0.05 * (1 - data["win_rate"]), 4)
            feedback["symbol_penalties"][sym] = {
                "penalty": penalty,
                "reason": f"win_rate={data['win_rate']:.0%} over {data['count']} trades",
            }

    d3 = feedback["by_horizon"].get("3d", {})
    d10 = feedback["by_horizon"].get("10d", {})

    if d3.get("count", 0) >= 3:
        d3_avg = d3["avg_return"]
        if d3_avg < -0.02:
            new_threshold = -0.10
            feedback["adjusted_momentum_exhaustion_threshold"] = new_threshold
            feedback["risk_insights"].append(
                f"3d avg return {d3_avg:+.2%} is negative; tightening exhaustion threshold from -0.15 to {new_threshold}"
            )
        elif d3_avg > 0.02:
            new_threshold = -0.18
            feedback["adjusted_momentum_exhaustion_threshold"] = new_threshold
            feedback["risk_insights"].append(
                f"3d avg return {d3_avg:+.2%} is positive; loosening exhaustion threshold to {new_threshold}"
            )

    if d10.get("count", 0) >= 3:
        d10_avg = d10["avg_return"]
        if d10_avg < -0.03:
            feedback["adjusted_scoring_weights"] = {
                "prior_20d_momentum": 0.30,
                "five_day_acceleration": 0.15,
                "volume_confirmation_ratio": 0.25,
                "relative_strength_vs_equal_weight": 0.30,
            }
            feedback["risk_insights"].append(
                f"10d avg return {d10_avg:+.2%} negative; shifting weight from acceleration to relative_strength"
            )

    if feedback["total_completed"] >= 5:
        actual_win_rate = feedback["win_rate"]
        actual_avg_win = feedback["avg_win"] if feedback["avg_win"] > 0 else 0.04
        actual_avg_loss = abs(feedback["avg_loss"]) if feedback["avg_loss"] < 0 else 0.02
        feedback["adjusted_risk_params"] = {
            "win_rate": round(actual_win_rate, 4),
            "avg_win_pct": round(actual_avg_win, 6),
            "avg_loss_pct": round(actual_avg_loss, 6),
        }
        feedback["risk_insights"].append(
            f"Risk manager params updated: win_rate={actual_win_rate:.0%}, avg_win={actual_avg_win:+.2%}, avg_loss={actual_avg_loss:+.2%}"
        )

    return feedback


def format_review_report(feedback: dict) -> str:
    lines = [
        "# Backtest Review Report",
        f"- Generated: {feedback.get('as_of', 'N/A')}",
        f"- Status: {feedback['status']}",
        "",
    ]

    if feedback["status"] == "NO_DATA":
        lines.append(f"- {feedback.get('message', 'No data')}")
        return "\n".join(lines)

    lines.extend([
        "## Overall Performance",
        f"- Total completed: {feedback['total_completed']}",
        f"- Win rate: {feedback['win_rate']:.0%} ({feedback['wins']}/{feedback['total_completed']})",
        f"- Avg return: {feedback['avg_return']:+.2%}",
        f"- Median return: {feedback['median_return']:+.2%}",
        f"- Avg win: {feedback['avg_win']:+.2%}",
        f"- Avg loss: {feedback['avg_loss']:+.2%}",
        f"- Profit factor: {feedback['profit_factor']:.2f}",
        "",
        "## By Horizon",
        "|horizon|count|win_rate|avg_return|max_win|max_loss|",
        "|---|---|---|---|---|---|",
    ])
    for h, data in sorted(feedback["by_horizon"].items()):
        lines.append(
            f"|{h}|{data['count']}|{data['win_rate']:.0%}|{data['avg_return']:+.2%}|{data['max_win']:+.2%}|{data['max_loss']:+.2%}|"
        )

    lines.extend(["", "## By Symbol", "|symbol|count|win_rate|avg_return|", "|---|---|---|---|"])
    for sym, data in sorted(feedback["by_symbol"].items(), key=lambda x: x[1]["avg_return"], reverse=True):
        lines.append(f"|{sym}|{data['count']}|{data['win_rate']:.0%}|{data['avg_return']:+.2%}|")

    if feedback.get("symbol_penalties"):
        lines.extend(["", "## Symbol Penalties"])
        for sym, p in feedback["symbol_penalties"].items():
            lines.append(f"- {sym}: {p['penalty']:+.2%} ({p['reason']})")

    lines.extend(["", "## Adjusted Parameters"])
    if feedback.get("adjusted_momentum_exhaustion_threshold") is not None:
        lines.append(f"- momentum_exhaustion_threshold: {feedback['adjusted_momentum_exhaustion_threshold']}")
    else:
        lines.append("- momentum_exhaustion_threshold: unchanged (-0.15)")

    if feedback.get("adjusted_scoring_weights"):
        w = feedback["adjusted_scoring_weights"]
        lines.append(f"- scoring_weights: momentum={w['prior_20d_momentum']}, accel={w['five_day_acceleration']}, volume={w['volume_confirmation_ratio']}, rs={w['relative_strength_vs_equal_weight']}")
    else:
        lines.append("- scoring_weights: unchanged")

    if feedback.get("adjusted_risk_params"):
        r = feedback["adjusted_risk_params"]
        lines.append(f"- risk_manager: win_rate={r['win_rate']:.0%}, avg_win={r['avg_win_pct']:+.2%}, avg_loss={r['avg_loss_pct']:+.2%}")

    if feedback.get("risk_insights"):
        lines.extend(["", "## Risk Insights"])
        for insight in feedback["risk_insights"]:
            lines.append(f"- {insight}")

    return "\n".join(lines)


def main():
    df = load_all_forward_tracking()
    if df.empty:
        print(json.dumps({"status": "NO_DATA", "message": "No forward tracking files found"}))
        return

    feedback = compute_feedback(df)

    report = format_review_report(feedback)
    report_path = RESEARCH_BASE / "backtest-review-report.md"
    report_path.write_text(report, encoding="utf-8")

    json_path = RESEARCH_BASE / "backtest-review-feedback.json"
    json_path.write_text(json.dumps(feedback, indent=2, ensure_ascii=False), encoding="utf-8")

    print(json.dumps(feedback, indent=2, ensure_ascii=False))
    print(f"\nReport: {report_path}")
    print(f"JSON: {json_path}")


if __name__ == "__main__":
    main()
