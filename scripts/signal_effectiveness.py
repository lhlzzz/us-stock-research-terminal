#!/usr/bin/env python3
"""Signal effectiveness analysis for xiaomei.

Analyzes which scoring dimensions actually predict returns.
Inspired by xiaogu's xiaogu_signal_effectiveness_v0_1.py.
"""
import sys
from pathlib import Path
from datetime import date

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scripts.db.engine import query_rows


SIGNAL_FIELDS = [
    "market_score",
    "catalyst_score",
    "ticket_score",
    "prior_20d_momentum",
    "five_day_acceleration",
    "relative_strength_vs_equal_weight",
    "volume_weighted_momentum",
    "volume_confirmation_ratio",
    "closing_strength_5d",
]

RETURN_THRESHOLD = 0.03


def analyze_signal_effectiveness(min_samples: int = 3) -> dict:
    """Analyze per-signal effectiveness from tickets + forward_tracking."""
    rows = query_rows("""
        SELECT
            f.symbol, f.output_date, f.horizon_days, f.forward_return, f.check_status,
            t.market_score, t.catalyst_score, t.ticket_score,
            fs.prior_20d_momentum, fs.five_day_acceleration,
            fs.relative_strength, fs.volume_weighted_momentum,
            fs.volume_confirmation, fs.closing_strength_5d
        FROM forward_tracking f
        JOIN tickets t ON t.id = f.ticket_id
        LEFT JOIN factor_snapshots fs ON fs.symbol = f.symbol AND fs.trade_date = f.output_date
        WHERE f.check_status = 'completed' AND f.forward_return IS NOT NULL
    """)

    if not rows:
        return {"error": "no completed forward tracking data"}

    results = {"overall": {}, "by_signal": {}, "by_horizon": {}}

    total = len(rows)
    positive = sum(1 for r in rows if r["forward_return"] > 0)
    avg_return = sum(r["forward_return"] for r in rows) / total if total else 0
    results["overall"] = {
        "total": total,
        "positive": positive,
        "win_rate": round(positive / total * 100, 2) if total else 0,
        "avg_return": round(avg_return * 100, 4),
    }

    for horizon in [1, 3, 10]:
        h_rows = [r for r in rows if r["horizon_days"] == horizon]
        if not h_rows:
            continue
        h_total = len(h_rows)
        h_positive = sum(1 for r in h_rows if r["forward_return"] > 0)
        h_avg = sum(r["forward_return"] for r in h_rows) / h_total
        results["by_horizon"][f"{horizon}d"] = {
            "count": h_total,
            "win_rate": round(h_positive / h_total * 100, 2),
            "avg_return": round(h_avg * 100, 4),
        }

    for field in SIGNAL_FIELDS:
        present = [r for r in rows if r.get(field) is not None and r[field] != 0]
        if len(present) < min_samples:
            results["by_signal"][field] = {"status": "INSUFFICIENT_DATA", "count": len(present)}
            continue

        positive_signal = [r for r in present if r["forward_return"] > RETURN_THRESHOLD]
        negative_signal = [r for r in present if r["forward_return"] < -RETURN_THRESHOLD]

        avg_ret = sum(r["forward_return"] for r in present) / len(present)
        high_return_rate = len(positive_signal) / len(present) if present else 0

        if high_return_rate > 0.5:
            suggestion = "INCREASE"
        elif high_return_rate < 0.2:
            suggestion = "DECREASE"
        else:
            suggestion = "MAINTAIN"

        results["by_signal"][field] = {
            "count": len(present),
            "avg_return": round(avg_ret * 100, 4),
            "high_return_rate": round(high_return_rate * 100, 2),
            "suggestion": suggestion,
        }

    return results


def format_report(results: dict) -> str:
    """Format results as human-readable text."""
    lines = ["# Signal Effectiveness Report", ""]

    o = results.get("overall", {})
    lines.append(f"## Overall")
    lines.append(f"- Total records: {o.get('total', 0)}")
    lines.append(f"- Win rate: {o.get('win_rate', 0)}%")
    lines.append(f"- Avg return: {o.get('avg_return', 0)}%")
    lines.append("")

    lines.append("## By Horizon")
    for horizon, data in results.get("by_horizon", {}).items():
        lines.append(f"- {horizon}: {data['count']} records, {data['win_rate']}% win rate, avg {data['avg_return']}%")
    lines.append("")

    lines.append("## By Signal")
    lines.append(f"| Signal | Count | Avg Return | High Return Rate | Suggestion |")
    lines.append(f"|--------|-------|------------|------------------|------------|")
    for signal, data in results.get("by_signal", {}).items():
        if data.get("status") == "INSUFFICIENT_DATA":
            lines.append(f"| {signal} | {data['count']} | - | - | INSUFFICIENT_DATA |")
        else:
            lines.append(f"| {signal} | {data['count']} | {data['avg_return']}% | {data['high_return_rate']}% | {data['suggestion']} |")

    return "\n".join(lines)


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Signal effectiveness analysis")
    parser.add_argument("--min-samples", type=int, default=3)
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--db", action="store_true", help="Store results in database")
    args = parser.parse_args()

    results = analyze_signal_effectiveness(min_samples=args.min_samples)

    if args.db:
        store_results_db(results)

    if args.json:
        import json
        print(json.dumps(results, indent=2, ensure_ascii=False, default=float))
    else:
        print(format_report(results))


def store_results_db(results: dict):
    """Store signal effectiveness results in database."""
    from db.engine import SessionLocal
    from sqlalchemy import text

    # Map suggestions to numeric weights
    SUGGESTION_WEIGHTS = {
        "INCREASE": 1.1,
        "MAINTAIN": 1.0,
        "DECREASE": 0.9,
    }

    db = SessionLocal()
    try:
        analysis_date = date.today()

        # Store by_signal results
        stored = 0
        for signal_key, data in results.get("by_signal", {}).items():
            if data.get("status") == "INSUFFICIENT_DATA":
                continue

            suggestion = data.get("suggestion", "MAINTAIN")
            weight = SUGGESTION_WEIGHTS.get(suggestion, 1.0)

            db.execute(text("""
                INSERT INTO signal_effectiveness
                    (analysis_date, signal_key, present_count, win_rate, avg_return, weight_suggestion)
                VALUES
                    (:date, :key, :count, :win_rate, :avg_return, :suggestion)
                ON CONFLICT (analysis_date, signal_key) DO UPDATE SET
                    present_count = EXCLUDED.present_count,
                    win_rate = EXCLUDED.win_rate,
                    avg_return = EXCLUDED.avg_return,
                    weight_suggestion = EXCLUDED.weight_suggestion
            """), {
                "date": analysis_date,
                "key": signal_key,
                "count": data.get("count", 0),
                "win_rate": data.get("high_return_rate", 0) / 100,
                "avg_return": data.get("avg_return", 0) / 100,
                "suggestion": weight,
            })
            stored += 1

        db.commit()
        print(f"Stored {stored} signal effectiveness records to DB")
    except Exception as e:
        print(f"Error storing results: {e}")
        db.rollback()
    finally:
        db.close()


if __name__ == "__main__":
    main()
