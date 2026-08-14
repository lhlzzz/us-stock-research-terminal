#!/usr/bin/env python3
"""Trade journal generator for xiaomei.

Reads tickets + engine state, generates detailed trade reasons,
persists to PostgreSQL and Obsidian markdown.

Usage:
    python3 scripts/trade_journal.py              # run once
    python3 scripts/trade_journal.py --update-all # update all open positions
"""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

from sqlalchemy import text

sys.path.insert(0, str(Path(__file__).resolve().parent))
from db.engine import SessionLocal

ROOT = Path(__file__).resolve().parents[1]
ENGINE_STATE = ROOT / "research" / "engine-state.json"
TRADES_FILE = ROOT / "research" / "dual-paper-trades.json"

# Obsidian vault path (WSL mount)
OBSIDIAN_VAULT = Path("/mnt/d/obisidian/Obsidian/Project")
OBSIDIAN_TRADES = OBSIDIAN_VAULT / "xiaomei-trades"

BJT = timezone(timedelta(hours=8))


def _now() -> datetime:
    return datetime.now(BJT)


def _read_json(path: Path, fallback=None):
    try:
        return json.loads(path.read_text())
    except (FileNotFoundError, OSError, json.JSONDecodeError):
        return fallback or {}


def _query(sql: str, params: dict = None) -> list[dict]:
    with SessionLocal() as session:
        result = session.execute(text(sql), params or {})
        cols = result.keys()
        return [dict(zip(cols, row)) for row in result.fetchall()]


# ── Reason Generation ────────────────────────────────────────────

# Pipeline writes to workspace dir, local research dir has old data
METRICS_DIR_ALT = Path("/workspace/workspaces/xiaomei/research/profit-ticket-pipeline")
METRICS_DIR = ROOT / "research" / "profit-ticket-pipeline"


def _load_pipeline_metrics(trade_date: str = "") -> dict:
    """Load pipeline metrics for a specific date (or latest), return symbol→candidate dict."""
    for d in [METRICS_DIR_ALT, METRICS_DIR]:
        if not d.exists():
            continue
        # Try exact date first
        if trade_date:
            exact = d / f"metrics-{trade_date}.json"
            if exact.exists():
                try:
                    data = json.loads(exact.read_text())
                    return {c["symbol"]: c for c in data.get("top_candidates", [])}
                except Exception:
                    pass
        # Fallback to latest
        files = sorted(d.glob("metrics-*.json"), reverse=True)
        if files:
            try:
                data = json.loads(files[0].read_text())
                return {c["symbol"]: c for c in data.get("top_candidates", [])}
            except Exception:
                pass
    return {}


def generate_reasons(symbol: str, ticket: dict, engine_pos: dict, trade_date: str = "") -> dict:
    """Generate detailed, multi-dimensional trade reasons using full pipeline data."""
    market_score = float(ticket.get("market_score", 0) or 0)
    catalyst_score = float(ticket.get("catalyst_score", 0) or 0)
    classification = ticket.get("classification", "")
    risk_verdict = ticket.get("risk_verdict", "")
    entry_reason = ticket.get("entry_reason", "")

    # Load rich metrics from pipeline (match by trade date)
    metrics = _load_pipeline_metrics(trade_date)
    m = metrics.get(symbol, {})

    # ── Technical Analysis ──
    tech = m.get("research_panel", {}).get("agents", {}).get("technical_analyst", {})
    tech_signals = tech.get("signals", [])
    momentum_20d = tech.get("momentum_20d", 0)
    acceleration_5d = tech.get("acceleration_5d", 0)
    relative_strength = tech.get("relative_strength", 0)
    volume_conf = tech.get("volume_confirmation", 0)

    signal_cn = {
        "strong_momentum": "强动量",
        "moderate_momentum": "中等动量",
        "acceleration_bullish": "5日加速上涨",
        "deceleration_warning": "5日减速警告",
        "outperforming_market": "跑赢大盘",
        "volume_confirmed": "成交量确认",
        "volume_divergence": "量价背离",
    }
    tech_desc = [signal_cn.get(s, s) for s in tech_signals]

    # ── Market reason ──
    reason_market = f"市场维度: "
    if market_score >= 1.0:
        reason_market += f"极强动量信号 (评分 {market_score:.3f})。"
    elif market_score >= 0.8:
        reason_market += f"强动量信号 (评分 {market_score:.3f})。"
    elif market_score >= 0.6:
        reason_market += f"中等动量 (评分 {market_score:.3f})。"
    else:
        reason_market += f"弱动量 (评分 {market_score:.3f})。"

    if tech_desc:
        reason_market += f" 技术信号: {', '.join(tech_desc)}。"
    if momentum_20d:
        reason_market += f" 20日动量 {momentum_20d:.3f}，"
    if relative_strength:
        reason_market += f"相对强度 {relative_strength:.3f}{'(跑赢基准)' if relative_strength > 0 else '(跑输基准)'}，"
    if volume_conf:
        reason_market += f"量能确认度 {volume_conf:.2f}。"

    # ── Catalyst reason ──
    reason_catalyst = f"催化剂维度: "
    catalyst_summary = m.get("catalyst_summary", "")
    narrative = m.get("narrative_evidence", {})
    business = m.get("business_evidence", {})
    narrative_status = narrative.get("status", "missing")
    business_status = business.get("status", "missing")
    narrative_reason = narrative.get("top_evidence_reason", "")
    business_reason = business.get("top_evidence_reason", "")

    if catalyst_score >= 0.2:
        reason_catalyst += f"强催化剂信号 (评分 {catalyst_score:.3f})。"
    elif catalyst_score >= 0.1:
        reason_catalyst += f"中等催化剂 (评分 {catalyst_score:.3f})。"
    else:
        reason_catalyst += f"催化剂偏弱 (评分 {catalyst_score:.3f})。"

    if narrative_status != "missing":
        reason_catalyst += f" 叙事分析: {narrative_reason}。"
    if business_status != "missing":
        reason_catalyst += f" 业务证据: {business_reason}。"
    if catalyst_summary and "No relevant" not in catalyst_summary:
        reason_catalyst += f" {catalyst_summary}"

    # ── Bull/Bear case ──
    bull = m.get("research_panel", {}).get("agents", {}).get("bull_case", {})
    bear = m.get("research_panel", {}).get("agents", {}).get("bear_case", {})
    bull_points = bull.get("points", [])
    bear_points = bear.get("points", [])

    reason_sentiment = f"评审维度: "
    panel_verdict = m.get("research_panel", {}).get("panel_verdict", "MIXED")
    if panel_verdict == "MIXED":
        reason_sentiment += "65人评审团意见分歧，多空混合。"
    elif panel_verdict == "BULLISH":
        reason_sentiment += "评审团偏多。"
    elif panel_verdict == "BEARISH":
        reason_sentiment += "评审团偏空。"

    if bull_points:
        reason_sentiment += f" 看多理由({len(bull_points)}条): {'; '.join(bull_points)}。"
    if bear_points:
        reason_sentiment += f" 看空理由({len(bear_points)}条): {'; '.join(bear_points)}。"
    if not bull_points and not bear_points:
        reason_sentiment += " 评审团未给出明确多空论点。"

    # ── Quality + Risk ──
    quality = m.get("quality_check", {})
    quality_verdict = quality.get("overall_quality_score", 0)
    quality_dims = quality.get("passed_dimensions", 0)
    quality_total = quality.get("total_dimensions", 0)

    risk_checks = m.get("risk_checklist", {})
    red_count = risk_checks.get("red_count", 0)
    yellow_count = risk_checks.get("yellow_count", 0)
    green_count = risk_checks.get("green_count", 0)

    reason_risk = f"风险维度: "
    if risk_verdict == "CLEAN":
        reason_risk += "无明显风险信号。"
    elif risk_verdict == "WATCH":
        reason_risk += "存在需关注的风险因素。"
    elif risk_verdict == "ELEVATED":
        reason_risk += "风险等级偏高。"

    reason_risk += f" 质量评分 {quality_verdict:.2f} ({quality_dims}/{quality_total}维度通过)。"
    reason_risk += f" 风险检查: {green_count}绿 {yellow_count}黄 {red_count}红。"

    if red_count > 0:
        red_flags = [k for k, v in risk_checks.get("checks", {}).items() if v.get("flag") == "RED"]
        reason_risk += f" 红旗: {', '.join(red_flags)}。"
    if yellow_count > 0:
        yellow_flags = [k for k, v in risk_checks.get("checks", {}).items() if v.get("flag") == "YELLOW"]
        reason_risk += f" 黄旗: {', '.join(yellow_flags)}。"

    sl = engine_pos.get("stop_loss_price", 0) if engine_pos else 0
    tp = engine_pos.get("take_profit_price", 0) if engine_pos else 0
    if sl > 0:
        reason_risk += f" 止损 ${sl:.2f}。"
    if tp > 0:
        reason_risk += f" 止盈 ${tp:.2f}。"

    # ── Summary ──
    summary = f"{symbol} 入场逻辑:\n"
    summary += f"市场信号{'强劲' if market_score >= 0.8 else '一般'} (评分 {market_score:.3f})"
    if tech_signals:
        summary += f"，技术面: {', '.join(tech_desc)}"
    summary += f"。\n催化剂{'充足' if catalyst_score >= 0.1 else '偏弱'} (评分 {catalyst_score:.3f})"
    if catalyst_summary and "No relevant" not in catalyst_summary:
        summary += f"，{catalyst_summary}"
    summary += f"。\n评审团 {panel_verdict}"
    if bull_points:
        summary += f"，看多: {'; '.join(bull_points)}"
    if bear_points:
        summary += f"，看空: {'; '.join(bear_points)}"
    summary += f"。\n风险 {risk_verdict}，质量 {quality_verdict:.2f}/{quality_total}。"

    if market_score >= 0.8 and catalyst_score >= 0.1:
        summary += "\n结论: 市场+催化剂双重确认，高置信度入场。"
    elif market_score >= 0.8:
        summary += "\n结论: 纯动量驱动，需关注催化剂持续性。"
    elif catalyst_score >= 0.1:
        summary += "\n结论: 事件驱动型，依赖催化剂兑现。"
    else:
        summary += "\n结论: 基于综合评分入选，需持续跟踪验证。"

    return {
        "reason_market": reason_market,
        "reason_catalyst": reason_catalyst,
        "reason_sentiment": reason_sentiment,
        "reason_risk": reason_risk,
        "reason_summary": summary,
    }


# ── DB Persistence ──────────────────────────────────────────────

def save_to_db(trade_date: str, symbol: str, position: dict, ticket: dict, reasons: dict, obsidian_path: str = ""):
    with SessionLocal() as session:
        session.execute(text("""
            INSERT INTO trade_journal
                (trade_date, symbol, ticket_id, direction, entry_price, current_price, quantity, cost_basis,
                 stop_loss, take_profit, pnl_dollar, pnl_pct, status,
                 ticket_score, market_score, catalyst_score, classification, risk_verdict,
                 reason_market, reason_catalyst, reason_sentiment, reason_risk, reason_summary,
                 obsidian_path, updated_at)
            VALUES
                (:trade_date, :symbol, :ticket_id, :direction, :entry_price, :current_price, :quantity, :cost_basis,
                 :stop_loss, :take_profit, :pnl_dollar, :pnl_pct, :status,
                 :ticket_score, :market_score, :catalyst_score, :classification, :risk_verdict,
                 :reason_market, :reason_catalyst, :reason_sentiment, :reason_risk, :reason_summary,
                 :obsidian_path, NOW())
            ON CONFLICT (trade_date, symbol, status) DO UPDATE SET
                current_price = EXCLUDED.current_price,
                pnl_dollar = EXCLUDED.pnl_dollar,
                pnl_pct = EXCLUDED.pnl_pct,
                reason_market = EXCLUDED.reason_market,
                reason_catalyst = EXCLUDED.reason_catalyst,
                reason_sentiment = EXCLUDED.reason_sentiment,
                reason_risk = EXCLUDED.reason_risk,
                reason_summary = EXCLUDED.reason_summary,
                ticket_id = EXCLUDED.ticket_id,
                obsidian_path = EXCLUDED.obsidian_path,
                updated_at = NOW()
        """), {
            "trade_date": trade_date,
            "symbol": symbol,
            "ticket_id": ticket.get("id"),
            "direction": position.get("side", "LONG"),
            "entry_price": position.get("avg_price", 0),
            "current_price": position.get("current_price", 0),
            "quantity": position.get("quantity", 0),
            "cost_basis": position.get("cost_basis", 0),
            "stop_loss": position.get("stop_loss_price", 0),
            "take_profit": position.get("take_profit_price", 0),
            "pnl_dollar": position.get("unrealized_pnl", 0),
            "pnl_pct": position.get("unrealized_pnl_pct", 0),
            "status": "OPEN",
            "ticket_score": float(ticket.get("ticket_score", 0) or 0),
            "market_score": float(ticket.get("market_score", 0) or 0),
            "catalyst_score": float(ticket.get("catalyst_score", 0) or 0),
            "classification": ticket.get("classification", ""),
            "risk_verdict": ticket.get("risk_verdict", ""),
            "reason_market": reasons["reason_market"],
            "reason_catalyst": reasons["reason_catalyst"],
            "reason_sentiment": reasons["reason_sentiment"],
            "reason_risk": reasons["reason_risk"],
            "reason_summary": reasons["reason_summary"],
            "obsidian_path": obsidian_path,
        })
        session.commit()


def close_in_db(trade_date: str, symbol: str, exit_price: float, pnl: float, pnl_pct: float, reason: str):
    with SessionLocal() as session:
        session.execute(text("""
            UPDATE trade_journal SET
                status = 'CLOSED',
                current_price = :exit_price,
                pnl_dollar = :pnl,
                pnl_pct = :pnl_pct,
                reason_summary = reason_summary || ' [平仓: ' || :reason || ']',
                updated_at = NOW()
            WHERE symbol = :symbol AND status = 'OPEN'
        """), {
            "symbol": symbol,
            "exit_price": exit_price,
            "pnl": pnl,
            "pnl_pct": pnl_pct,
            "reason": reason,
        })
        session.commit()


# ── Obsidian Writer ──────────────────────────────────────────────

def write_obsidian(trade_date: str, symbol: str, position: dict, ticket: dict, reasons: dict) -> str:
    """Write a detailed Obsidian markdown note for a trade."""
    OBSIDIAN_TRADES.mkdir(parents=True, exist_ok=True)

    filename = f"{trade_date}-{symbol}.md"
    filepath = OBSIDIAN_TRADES / filename

    entry_price = position.get("avg_price", 0)
    current_price = position.get("current_price", 0)
    pnl_pct = position.get("unrealized_pnl_pct", 0)
    pnl_dollar = position.get("unrealized_pnl", 0)
    sl = position.get("stop_loss_price", 0)
    tp = position.get("take_profit_price", 0)
    qty = position.get("quantity", 0)
    cost = position.get("cost_basis", 0)
    direction = position.get("side", "LONG")

    emoji = "🟢" if pnl_pct >= 0 else "🔴"
    direction_cn = "做多" if direction == "LONG" else "做空"

    md = f"""# {emoji} {symbol} {direction_cn} — {trade_date}

## 交易概要

| 维度 | 数据 |
|------|------|
| 标的 | {symbol} |
| 方向 | {direction_cn} |
| 入场价 | ${entry_price:.2f} |
| 现价 | ${current_price:.2f} |
| 数量 | {qty:.4f} 股 |
| 成本 | ${cost:.2f} |
| 浮动盈亏 | ${pnl_dollar:+.2f} ({pnl_pct:+.2f}%) |
| 止损 | ${sl:.2f} |
| 止盈 | ${tp:.2f} |

## 入场逻辑

### 📊 市场信号

{reasons['reason_market']}

### 🔥 催化剂/事件驱动

{reasons['reason_catalyst']}

### 🗳️ 评审团研判

{reasons['reason_sentiment']}

### ⚠️ 风险评估

{reasons['reason_risk']}

## 综合判断

{reasons['reason_summary']}

## Pipeline 评分

| 指标 | 值 | 说明 |
|------|-----|------|
| 综合评分 | {float(ticket.get('ticket_score', 0) or 0):.3f} | Pipeline 输出 |
| 市场分 | {float(ticket.get('market_score', 0) or 0):.3f} | 相对强度+动量 |
| 催化分 | {float(ticket.get('catalyst_score', 0) or 0):.3f} | 叙事+业务证据 |
| 分类 | {ticket.get('classification', '')} | Pipeline 分类 |
| 风险 | {ticket.get('risk_verdict', '')} | 风险评级 |

## 原始 Pipeline 数据

```
{ticket.get('entry_reason', '')}
```

---
*xiaomei 自动生成 · {_now().strftime('%Y-%m-%d %H:%M')} BJT*
"""
    filepath.write_text(md)
    return str(filepath)


# ── Main ────────────────────────────────────────────────────────

def _is_market_hours() -> bool:
    """Check if US market is currently open (9:30-16:00 ET, Mon-Fri)."""
    from datetime import timezone as _tz
    et = datetime.now(_tz(timedelta(hours=-4)))
    if et.weekday() >= 5:
        return False
    market_open = et.replace(hour=9, minute=30, second=0, microsecond=0)
    market_close = et.replace(hour=16, minute=0, second=0, microsecond=0)
    return market_open <= et <= market_close


def run_journal(force: bool = False):
    """Generate trade journal entries for all open positions."""
    if not force and not _is_market_hours():
        print("[JOURNAL] 美股已收盘，跳过。等开盘再跑。使用 --force 强制运行。")
        return

    # Load engine state
    engine = _read_json(ENGINE_STATE, {})
    if not engine or not engine.get("positions"):
        print("[JOURNAL] No positions in engine state")
        return

    # Get latest ticket date
    dates = _query("SELECT MAX(output_date) as d FROM tickets")
    if not dates or not dates[0]["d"]:
        print("[JOURNAL] No tickets in DB")
        return
    trade_date = str(dates[0]["d"])

    # Get tickets for reasoning
    tickets = _query("""
        SELECT id, symbol, ticket_score, market_score, catalyst_score,
               classification, risk_verdict, entry_reason
        FROM tickets WHERE output_date = :d
    """, {"d": trade_date})
    ticket_map = {t["symbol"]: t for t in tickets}

    print(f"[JOURNAL] Processing {len(engine['positions'])} positions for {trade_date}")

    for sym, pos in engine["positions"].items():
        ticket = ticket_map.get(sym, {})
        reasons = generate_reasons(sym, ticket, pos, trade_date)

        # Write Obsidian
        obs_path = write_obsidian(trade_date, sym, pos, ticket, reasons)

        # Save to DB
        save_to_db(trade_date, sym, pos, ticket, reasons, obs_path)

        pnl = pos.get("unrealized_pnl", 0)
        emoji = "+" if pnl >= 0 else ""
        print(f"  {sym}: ${pos.get('current_price',0):.2f} ({emoji}${pnl:.2f}) → {obs_path}")

    # Check for closed trades in engine
    for trade in engine.get("closed_trade_details", []):
        sym = trade.get("symbol", "")
        if sym and trade not in [t for t in engine.get("closed_trade_details", [])[-5:]]:
            continue
        close_in_db(
            trade_date, sym,
            trade.get("exit_price", 0),
            trade.get("pnl", 0),
            trade.get("pnl_pct", 0),
            trade.get("reason", ""),
        )

    print(f"[JOURNAL] Done. Obsidian notes at {OBSIDIAN_TRADES}")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Trade journal generator")
    parser.add_argument("--force", action="store_true", help="Run even when market is closed")
    parser.add_argument("--update-all", action="store_true", help="Update all open positions")
    args = parser.parse_args()
    run_journal(force=args.force)
