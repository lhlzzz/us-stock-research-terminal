#!/usr/bin/env python3
"""Quant Gate: 量化验证门，四级状态。"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scripts.db.engine import query_rows


def run_quant_gate(output_date: str = None) -> dict:
    if not output_date:
        from datetime import date
        output_date = date.today().isoformat()
    metrics = compute_metrics()
    status = evaluate_status(metrics)
    return {"output_date": output_date, "status": status, "metrics": metrics}


def compute_metrics() -> dict:
    rows = query_rows("""
        SELECT
            COUNT(*) as total,
            COUNT(CASE WHEN forward_return > 0 THEN 1 END) as wins,
            AVG(forward_return) as avg_return,
            MAX(forward_return) as max_return,
            MIN(forward_return) as min_return
        FROM forward_tracking
        WHERE check_status = 'completed' AND forward_return IS NOT NULL
    """)
    r = rows[0]
    total = r["total"] or 0
    wins = r["wins"] or 0
    avg_ret = float(r["avg_return"] or 0)
    max_ret = float(r["max_return"] or 0)
    min_ret = float(r["min_return"] or 0)
    win_rate = wins / total if total else 0
    profit_factor = abs(max_ret / min_ret) if min_ret and min_ret < 0 else 999
    signal_rows = query_rows("""
        SELECT
            COUNT(*) as total,
            COUNT(CASE WHEN forward_return > 0.03 THEN 1 END) as high_return
        FROM forward_tracking
        WHERE check_status = 'completed' AND forward_return IS NOT NULL
    """)
    sr = signal_rows[0]
    high_return_rate = (sr["high_return"] or 0) / (sr["total"] or 1)
    return {
        "win_rate": round(win_rate * 100, 2),
        "avg_return": round(avg_ret * 100, 4),
        "profit_factor": round(profit_factor, 2),
        "max_return": round(max_ret * 100, 4),
        "min_return": round(min_ret * 100, 4),
        "high_return_rate": round(high_return_rate * 100, 2),
        "total_records": total,
    }


def evaluate_status(metrics: dict) -> str:
    wr = metrics["win_rate"]
    ar = metrics["avg_return"]
    pf = metrics["profit_factor"]
    hr = metrics["high_return_rate"]
    if wr >= 55 and ar > 0 and pf > 1.5 and hr > 30:
        return "PASS"
    elif wr >= 50 and ar > -1 and pf > 1.0:
        return "SOFT_PASS"
    elif wr >= 45 and ar > -2:
        return "WATCH"
    else:
        return "FAIL"


if __name__ == "__main__":
    import json
    result = run_quant_gate()
    print(json.dumps(result, indent=2, ensure_ascii=False))
