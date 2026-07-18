#!/usr/bin/env python3
"""Meta Loop: 检查系统是否退化。"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scripts.db.engine import query_rows


def run_meta_loop() -> dict:
    recent = compute_recent_metrics(days=30)
    historical = compute_historical_metrics()
    degradation = detect_degradation(recent, historical)
    return {
        "recent_30d": recent,
        "historical": historical,
        "degradation": degradation,
        "action_needed": len(degradation) > 0,
    }


def compute_recent_metrics(days: int = 30) -> dict:
    rows = query_rows(f"""
        SELECT
            COUNT(*) as total,
            COUNT(CASE WHEN forward_return > 0 THEN 1 END) as wins,
            AVG(forward_return) as avg_return
        FROM forward_tracking
        WHERE check_status = 'completed'
        AND forward_return IS NOT NULL
        AND completed_at >= NOW() - INTERVAL '{days} days'
    """)
    r = rows[0]
    total = r["total"] or 0
    wins = r["wins"] or 0
    return {
        "win_rate": round(wins / total * 100, 2) if total else 0,
        "avg_return": round(float(r["avg_return"] or 0) * 100, 4),
        "total": total,
    }


def compute_historical_metrics() -> dict:
    rows = query_rows("""
        SELECT
            COUNT(*) as total,
            COUNT(CASE WHEN forward_return > 0 THEN 1 END) as wins,
            AVG(forward_return) as avg_return
        FROM forward_tracking
        WHERE check_status = 'completed' AND forward_return IS NOT NULL
    """)
    r = rows[0]
    total = r["total"] or 0
    wins = r["wins"] or 0
    return {
        "win_rate": round(wins / total * 100, 2) if total else 0,
        "avg_return": round(float(r["avg_return"] or 0) * 100, 4),
        "total": total,
    }


def detect_degradation(recent: dict, historical: dict) -> list:
    issues = []
    if historical["win_rate"] > 0:
        wr_drop = historical["win_rate"] - recent["win_rate"]
        if wr_drop > 10:
            issues.append({
                "type": "win_rate_degradation",
                "message": f"胜率下降 {wr_drop:.1f}%（历史 {historical['win_rate']}% → 近期 {recent['win_rate']}%）",
                "severity": "HIGH",
            })
    if recent["avg_return"] < -1 and historical["avg_return"] > 0:
        issues.append({
            "type": "return_degradation",
            "message": f"平均收益转负（近期 {recent['avg_return']}%）",
            "severity": "HIGH",
        })
    if recent["total"] < 10:
        issues.append({
            "type": "insufficient_data",
            "message": f"近期数据不足（仅 {recent['total']} 条）",
            "severity": "MEDIUM",
        })
    return issues


if __name__ == "__main__":
    import json
    result = run_meta_loop()
    print(json.dumps(result, indent=2, ensure_ascii=False))
