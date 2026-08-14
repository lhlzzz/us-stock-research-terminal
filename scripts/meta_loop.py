#!/usr/bin/env python3
"""Meta Loop: 检查系统是否退化。

改进版检测维度:
1. 绝对阈值门控 — 胜率 <45% 告警, <40% 严重
2. 滚动窗口比较 — 7d vs 30d vs all-time 三档对比
3. 趋势检测 — 7d 是否持续劣于 30d（恶化趋势）
4. 收益转负检测 — 近期平均收益由正转负
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scripts.db.engine import query_rows

# ─── 绝对阈值 ──────────────────────────────────────────────────
ABSOLUTE_WIN_RATE_WARN = 45.0      # 胜率低于此值 → 告警
ABSOLUTE_WIN_RATE_CRITICAL = 40.0  # 胜率低于此值 → 严重
ABSOLUTE_AVG_RETURN_WARN = -0.5    # 平均收益低于此值(%) → 告警
ABSOLUTE_AVG_RETURN_CRITICAL = -1.5 # 平均收益低于此值(%) → 严重
MIN_SAMPLES_FOR_JUDGEMENT = 10     # 样本不足时不判定

# ─── 相对退化阈值 ──────────────────────────────────────────────
RELATIVE_WR_DROP_WARN = 8.0       # 7d vs 30d 胜率下降 >8% → 告警
RELATIVE_WR_DROP_CRITICAL = 15.0  # 7d vs 30d 胜率下降 >15% → 严重


def compute_metrics(days: int | None = None) -> dict:
    """计算指定时间窗口的指标。days=None 表示全历史。"""
    if days is not None:
        rows = query_rows("""
            SELECT
                COUNT(*) as total,
                COUNT(CASE WHEN forward_return > 0 THEN 1 END) as wins,
                AVG(forward_return) as avg_return,
                STDDEV(forward_return) as std_return
            FROM forward_tracking
            WHERE check_status = 'completed'
            AND forward_return IS NOT NULL
            AND completed_at >= NOW() - INTERVAL '%s days'
        """ % days)
    else:
        rows = query_rows("""
            SELECT
                COUNT(*) as total,
                COUNT(CASE WHEN forward_return > 0 THEN 1 END) as wins,
                AVG(forward_return) as avg_return,
                STDDEV(forward_return) as std_return
            FROM forward_tracking
            WHERE check_status = 'completed'
            AND forward_return IS NOT NULL
        """)

    r = rows[0] if rows else {}
    total = r.get("total") or 0
    wins = r.get("wins") or 0
    avg_ret = float(r.get("avg_return") or 0)
    std_ret = float(r.get("std_return") or 0)

    return {
        "win_rate": round(wins / total * 100, 2) if total else 0,
        "avg_return": round(avg_ret * 100, 4),
        "std_return": round(std_ret * 100, 4),
        "total": total,
        "wins": wins,
        "losses": total - wins,
    }


def compute_by_horizon(days: int | None = None) -> dict:
    """按持仓周期分别计算指标。"""
    time_filter = ""
    if days is not None:
        time_filter = f"AND completed_at >= NOW() - INTERVAL '{days} days'"

    rows = query_rows(f"""
        SELECT
            horizon_days,
            COUNT(*) as total,
            COUNT(CASE WHEN forward_return > 0 THEN 1 END) as wins,
            AVG(forward_return) as avg_return
        FROM forward_tracking
        WHERE check_status = 'completed'
        AND forward_return IS NOT NULL
        {time_filter}
        GROUP BY horizon_days
        ORDER BY horizon_days
    """)

    result = {}
    for r in rows:
        h = r["horizon_days"]
        total = r["total"] or 0
        wins = r["wins"] or 0
        result[f"{h}d"] = {
            "win_rate": round(wins / total * 100, 2) if total else 0,
            "avg_return": round(float(r["avg_return"] or 0) * 100, 4),
            "total": total,
        }
    return result


def detect_degradation(m7: dict, m30: dict, mall: dict) -> list:
    """多维度退化检测。"""
    issues = []

    # ── 1. 绝对阈值门控（不受历史数据影响）─────────────────────
    if m7["total"] >= MIN_SAMPLES_FOR_JUDGEMENT:
        if m7["win_rate"] < ABSOLUTE_WIN_RATE_CRITICAL:
            issues.append({
                "type": "absolute_win_rate_critical",
                "message": f"近7天胜率 {m7['win_rate']}% 低于严重阈值 {ABSOLUTE_WIN_RATE_CRITICAL}%",
                "severity": "CRITICAL",
            })
        elif m7["win_rate"] < ABSOLUTE_WIN_RATE_WARN:
            issues.append({
                "type": "absolute_win_rate_warn",
                "message": f"近7天胜率 {m7['win_rate']}% 低于告警阈值 {ABSOLUTE_WIN_RATE_WARN}%",
                "severity": "HIGH",
            })

        if m7["avg_return"] < ABSOLUTE_AVG_RETURN_CRITICAL:
            issues.append({
                "type": "absolute_return_critical",
                "message": f"近7天平均收益 {m7['avg_return']}% 低于严重阈值 {ABSOLUTE_AVG_RETURN_CRITICAL}%",
                "severity": "CRITICAL",
            })
        elif m7["avg_return"] < ABSOLUTE_AVG_RETURN_WARN:
            issues.append({
                "type": "absolute_return_warn",
                "message": f"近7天平均收益 {m7['avg_return']}% 低于告警阈值 {ABSOLUTE_AVG_RETURN_WARN}%",
                "severity": "HIGH",
            })

    # ── 2. 绝对阈值（30天窗口，样本更稳定）────────────────────
    if m30["total"] >= MIN_SAMPLES_FOR_JUDGEMENT:
        if m30["win_rate"] < ABSOLUTE_WIN_RATE_WARN:
            issues.append({
                "type": "absolute_win_rate_30d_warn",
                "message": f"近30天胜率 {m30['win_rate']}% 低于告警阈值 {ABSOLUTE_WIN_RATE_WARN}%",
                "severity": "HIGH",
            })
        if m30["avg_return"] < ABSOLUTE_AVG_RETURN_WARN:
            issues.append({
                "type": "absolute_return_30d_warn",
                "message": f"近30天平均收益 {m30['avg_return']}% 低于告警阈值 {ABSOLUTE_AVG_RETURN_WARN}%",
                "severity": "HIGH",
            })

    # ── 3. 相对退化（7d vs 30d 滚动窗口）────────────────────
    if m7["total"] >= 5 and m30["total"] >= MIN_SAMPLES_FOR_JUDGEMENT:
        wr_drop = m30["win_rate"] - m7["win_rate"]
        if wr_drop > RELATIVE_WR_DROP_CRITICAL:
            issues.append({
                "type": "relative_wr_critical",
                "message": f"7d胜率 {m7['win_rate']}% vs 30d胜率 {m30['win_rate']}%，下降 {wr_drop:.1f}%",
                "severity": "CRITICAL",
            })
        elif wr_drop > RELATIVE_WR_DROP_WARN:
            issues.append({
                "type": "relative_wr_warn",
                "message": f"7d胜率 {m7['win_rate']}% vs 30d胜率 {m30['win_rate']}%，下降 {wr_drop:.1f}%",
                "severity": "HIGH",
            })

    # ── 4. 收益恶化趋势（7d vs 30d）────────────────────────
    if m7["total"] >= 5 and m30["total"] >= MIN_SAMPLES_FOR_JUDGEMENT:
        if m30["avg_return"] >= 0 and m7["avg_return"] < 0:
            issues.append({
                "type": "return_turned_negative",
                "message": f"平均收益转负: 30d={m30['avg_return']}% → 7d={m7['avg_return']}%",
                "severity": "HIGH",
            })

    # ── 5. 全历史 vs 30d 退化（保留原有逻辑，但提高阈值）───
    if mall["total"] >= 50 and m30["total"] >= MIN_SAMPLES_FOR_JUDGEMENT:
        wr_drop_hist = mall["win_rate"] - m30["win_rate"]
        if wr_drop_hist > RELATIVE_WR_DROP_CRITICAL:
            issues.append({
                "type": "historical_wr_degradation",
                "message": f"30d胜率 {m30['win_rate']}% vs 全历史 {mall['win_rate']}%，下降 {wr_drop_hist:.1f}%",
                "severity": "HIGH",
            })

    # ── 6. 样本不足警告 ─────────────────────────────────────
    if m7["total"] < MIN_SAMPLES_FOR_JUDGEMENT and m30["total"] < MIN_SAMPLES_FOR_JUDGEMENT:
        issues.append({
            "type": "insufficient_data",
            "message": f"样本不足: 7d={m7['total']}条, 30d={m30['total']}条 (需>{MIN_SAMPLES_FOR_JUDGEMENT})",
            "severity": "MEDIUM",
        })

    return issues


def run_meta_loop() -> dict:
    """运行完整退化检测。"""
    m7 = compute_metrics(days=7)
    m30 = compute_metrics(days=30)
    mall = compute_metrics(days=None)

    h7 = compute_by_horizon(days=7)
    h30 = compute_by_horizon(days=30)

    degradation = detect_degradation(m7, m30, mall)

    # 按严重程度排序
    severity_order = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3}
    degradation.sort(key=lambda d: severity_order.get(d.get("severity", "LOW"), 9))

    has_critical = any(d.get("severity") == "CRITICAL" for d in degradation)
    has_high = any(d.get("severity") == "HIGH" for d in degradation)

    # 建议动作
    actions = []
    if has_critical:
        actions.append("STOP_PIPELINE: 严重退化，暂停出票直到问题修复")
    if has_high:
        actions.append("REDUCE_UNIVERSE: 收窄 Universe 到高流动性标的")
        actions.append("RAISE_SCORE_GATE: 提高出票门槛")
    if not degradation:
        actions.append("NO_ACTION: 系统运行正常")

    return {
        "window_7d": m7,
        "window_30d": m30,
        "window_all": mall,
        "by_horizon_7d": h7,
        "by_horizon_30d": h30,
        "degradation": degradation,
        "degradation_count": len(degradation),
        "has_critical": has_critical,
        "has_high": has_high,
        "recommended_actions": actions,
        "thresholds": {
            "win_rate_warn": ABSOLUTE_WIN_RATE_WARN,
            "win_rate_critical": ABSOLUTE_WIN_RATE_CRITICAL,
            "avg_return_warn": ABSOLUTE_AVG_RETURN_WARN,
            "avg_return_critical": ABSOLUTE_AVG_RETURN_CRITICAL,
            "relative_wr_drop_warn": RELATIVE_WR_DROP_WARN,
            "relative_wr_drop_critical": RELATIVE_WR_DROP_CRITICAL,
        },
    }


if __name__ == "__main__":
    import json
    result = run_meta_loop()
    print(json.dumps(result, indent=2, ensure_ascii=False))
