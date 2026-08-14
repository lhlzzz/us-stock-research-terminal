#!/usr/bin/env python3
"""[DEPRECATED] xiaomei US stock paper trading control room.

This Flask dashboard is DEPRECATED. Use xiaomei_api.py (FastAPI) instead.
The canonical frontend is public/index.html served via /dashboard endpoint
in xiaomei_api.py. This file is kept for reference only.

Original docstring:
  Reads tickets, positions, and lifecycle data from PostgreSQL and local JSON.
  Uses yfinance for live prices. No real trading.
"""
from __future__ import annotations

import json
import sys
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any

from flask import Flask, jsonify, render_template_string

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from db.engine import SessionLocal, query_rows
from sqlalchemy import text

TRADES_FILE = ROOT / "research" / "dual-paper-trades.json"
ENGINE_STATE = ROOT / "research" / "engine-state.json"
SCOREBOARD_JSON = ROOT / "research" / "lifecycle-scoreboard.json"

BJT = timezone(timedelta(hours=8))
ET = timezone(timedelta(hours=-4))  # EDT
app = Flask(__name__)


def _now() -> datetime:
    return datetime.now(BJT)


def _now_et() -> datetime:
    return datetime.now(ET)


def _read_json(path: Path, fallback: Any) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, OSError, json.JSONDecodeError):
        return fallback


def _query(sql: str, params: dict | None = None) -> list[dict]:
    with SessionLocal() as session:
        result = session.execute(text(sql), params or {})
        cols = result.keys()
        return [dict(zip(cols, row)) for row in result.fetchall()]


def _is_market_open() -> bool:
    et = _now_et()
    if et.weekday() >= 5:
        return False
    market_open = et.replace(hour=9, minute=30, second=0, microsecond=0)
    market_close = et.replace(hour=16, minute=0, second=0, microsecond=0)
    return market_open <= et <= market_close


def _latest_ticket_date() -> str:
    rows = _query("SELECT MAX(output_date) as d FROM tickets")
    return str(rows[0]["d"]) if rows and rows[0]["d"] else ""


def _trade_reasons() -> dict:
    """Get latest trade reasons from trade_journal or tickets."""
    # Try trade_journal first
    rows = _query("""
        SELECT symbol, reason_summary, reason_market, reason_catalyst,
               reason_sentiment, reason_risk
        FROM trade_journal
        WHERE status = 'OPEN'
        ORDER BY trade_date DESC
    """)
    if rows:
        return {r["symbol"]: r for r in rows}

    # Fallback to tickets
    latest = _latest_ticket_date()
    if not latest:
        return {}
    rows = _query("""
        SELECT symbol, entry_reason, classification, risk_verdict,
               ticket_score, market_score, catalyst_score
        FROM tickets WHERE output_date = :d
    """, {"d": latest})
    result = {}
    for r in rows:
        sym = r["symbol"]
        ms = float(r.get("market_score", 0) or 0)
        cs = float(r.get("catalyst_score", 0) or 0)
        result[sym] = {
            "symbol": sym,
            "reason_summary": f"综合评分 {r['ticket_score']:.3f} | 市场 {ms:.3f} 催化 {cs:.3f} | {r['classification']} | 风险 {r['risk_verdict']}",
            "reason_market": f"市场强度 {ms:.3f}" + (" 极强" if ms >= 1.0 else " 强" if ms >= 0.8 else " 中等" if ms >= 0.6 else " 弱"),
            "reason_catalyst": f"催化剂 {cs:.3f}" + (" 强催化" if cs >= 0.2 else " 中等" if cs >= 0.1 else " 偏弱"),
            "reason_sentiment": f"分类 {r['classification']}",
            "reason_risk": f"风险 {r['risk_verdict']} | {r.get('entry_reason', '')}",
        }
    return result


def _tickets_data() -> list[dict]:
    latest = _latest_ticket_date()
    if not latest:
        return []
    rows = _query("""
        SELECT symbol, ticket_score, market_score, catalyst_score,
               classification, risk_verdict, quality_verdict, entry_reason,
               output_date
        FROM tickets
        WHERE output_date = :d
        ORDER BY ticket_score DESC
    """, {"d": latest})
    for r in rows:
        r["output_date"] = str(r["output_date"])
        for k in ("ticket_score", "market_score", "catalyst_score"):
            r[k] = float(r[k] or 0)
    return rows


def _positions_data() -> dict:
    """Read positions from engine state (preferred) or legacy trades JSON."""
    # Try engine state first (realtime_runner output)
    engine = _read_json(ENGINE_STATE, {})
    if engine and engine.get("positions"):
        reasons = _trade_reasons()
        positions = []
        for sym, pos in engine["positions"].items():
            r = reasons.get(sym, {})
            positions.append({
                "symbol": sym,
                "direction": pos.get("side", "LONG"),
                "entry_price": round(pos.get("avg_price", 0), 2),
                "current_price": round(pos.get("current_price", 0), 2),
                "shares": round(pos.get("quantity", 0), 4),
                "cost": round(pos.get("cost_basis", 0), 2),
                "pnl_pct": round(pos.get("unrealized_pnl_pct", 0), 2),
                "pnl_dollar": round(pos.get("unrealized_pnl", 0), 2),
                "stop_loss": round(pos.get("stop_loss_price", 0), 2),
                "take_profit": round(pos.get("take_profit_price", 0), 2),
                "status": "HOLD",
                "reason_summary": r.get("reason_summary", ""),
                "reason_market": r.get("reason_market", ""),
                "reason_catalyst": r.get("reason_catalyst", ""),
                "reason_sentiment": r.get("reason_sentiment", ""),
                "reason_risk": r.get("reason_risk", ""),
            })
        return {
            "positions": positions,
            "cash": engine.get("cash", 0),
            "equity": engine.get("equity", 0),
            "initial_capital": engine.get("initial_capital", 1000),
            "pnl": engine.get("total_pnl", 0),
            "pnl_pct": engine.get("total_pnl_pct", 0),
            "long_pnl": sum(p.get("unrealized_pnl", 0) for p in engine["positions"].values() if p.get("side") == "LONG"),
            "short_pnl": sum(p.get("unrealized_pnl", 0) for p in engine["positions"].values() if p.get("side") == "SHORT"),
            "position_count": engine.get("position_count", 0),
            "last_check": engine.get("updated_at", ""),
            "total_fills": engine.get("total_fills", 0),
            "total_fees": engine.get("total_fees", 0),
            "win_rate": engine.get("win_rate", 0),
            "max_drawdown": engine.get("max_drawdown", 0),
            "halted": engine.get("halted", False),
            "recent_fills": engine.get("recent_fills", []),
        }

    # Fallback to legacy JSON
    trades = _read_json(TRADES_FILE, {})
    if not trades:
        return {"positions": [], "cash": 0, "equity": 0, "pnl": 0, "pnl_pct": 0}

    monitor = {m["symbol"]: m for m in trades.get("monitor_results", [])}
    positions = []
    long_pnl = 0
    short_pnl = 0

    for pos in trades.get("positions", []):
        sym = pos["symbol"]
        entry = pos["entry_price"]
        direction = pos.get("direction", "LONG").upper()
        shares = pos.get("shares", 0)
        cost = pos.get("cost", 0)
        m = monitor.get(sym, {})
        current = m.get("current", 0)
        pnl_pct = m.get("pnl_pct", 0)
        pnl_dollar = m.get("pnl_dollar", 0)
        status = m.get("status", "HOLD")
        if direction == "SHORT":
            short_pnl += pnl_dollar
            sl = pos.get("stop_loss_price", entry * 1.05)
            tp = pos.get("take_profit_price", entry * 0.90)
        else:
            long_pnl += pnl_dollar
            sl = pos.get("stop_loss_price", entry * 0.95)
            tp = pos.get("take_profit_price", entry * 1.10)
        positions.append({
            "symbol": sym, "direction": direction,
            "entry_price": round(entry, 2), "current_price": round(current, 2),
            "shares": round(shares, 4), "cost": round(cost, 2),
            "pnl_pct": round(pnl_pct, 2), "pnl_dollar": round(pnl_dollar, 2),
            "stop_loss": round(sl, 2), "take_profit": round(tp, 2), "status": status,
        })

    initial = trades.get("initial_capital", 1000)
    cash = trades.get("cash", 0)
    equity = trades.get("current_equity", initial + trades.get("total_pnl", 0))
    return {
        "positions": positions, "cash": round(cash, 2), "equity": round(equity, 2),
        "initial_capital": initial,
        "pnl": round(equity - initial, 2),
        "pnl_pct": round((equity / initial - 1) * 100, 2) if initial else 0,
        "long_pnl": round(long_pnl, 2), "short_pnl": round(short_pnl, 2),
        "position_count": len(positions),
        "last_check": trades.get("last_check", trades.get("created_at", "")),
    }


def _scoreboard_data() -> dict:
    sb = _read_json(SCOREBOARD_JSON, {})
    if not sb:
        return {}
    overall = sb.get("overall", {})
    by_horizon = sb.get("by_horizon", [])
    top_symbols = sorted(
        sb.get("by_symbol", []),
        key=lambda x: float(x.get("avg_forward_return", 0)),
        reverse=True,
    )[:10]
    return {
        "win_rate": overall.get("win_rate", 0),
        "avg_return": round(float(overall.get("avg_forward_return", 0)), 2),
        "median_return": round(float(overall.get("median_forward_return", 0)), 2),
        "total_rows": overall.get("completed_rows", 0),
        "by_horizon": by_horizon,
        "top_symbols": top_symbols,
    }


def _forward_tracking_data() -> list[dict]:
    latest = _latest_ticket_date()
    if not latest:
        return []
    rows = _query("""
        SELECT symbol, horizon_days, due_date, check_status, forward_return
        FROM forward_tracking
        WHERE output_date = :d
        ORDER BY symbol, horizon_days
    """, {"d": latest})
    for r in rows:
        r["due_date"] = str(r["due_date"])
        if r["forward_return"] is not None:
            r["forward_return"] = round(float(r["forward_return"]), 2)
    return rows


def _recent_tickets() -> list[dict]:
    rows = _query("""
        SELECT output_date, symbol, ticket_score, classification
        FROM tickets
        WHERE output_date >= CURRENT_DATE - 7
        ORDER BY output_date DESC, ticket_score DESC
    """)
    for r in rows:
        r["output_date"] = str(r["output_date"])
        r["ticket_score"] = round(float(r["ticket_score"] or 0), 3)
    return rows


# ── API ──

@app.route("/api/overview")
def api_overview():
    tickets = _tickets_data()
    positions = _positions_data()
    scoreboard = _scoreboard_data()
    tracking = _forward_tracking_data()
    recent = _recent_tickets()
    market_open = _is_market_open()
    engine = _read_json(ENGINE_STATE, {})
    engine_mode = engine.get("mode", "paper")

    return jsonify({
        "server_time": _now().isoformat(),
        "server_time_et": _now_et().isoformat(),
        "market_open": market_open,
        "engine_mode": engine_mode,
        "tickets": tickets,
        "positions": positions,
        "scoreboard": scoreboard,
        "tracking": tracking,
        "recent_tickets": recent,
    })


@app.route("/api/positions")
def api_positions():
    return jsonify(_positions_data())


@app.route("/api/tickets")
def api_tickets():
    return jsonify(_tickets_data())


# ── HTML ──

HTML = r"""
<!doctype html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>🌙 Xiaomei · 美股 AI 投资终端</title>
<style>
:root {
  --bg: #FFF7FB; --bg-card: #FFFFFF;
  --primary: #FF8FB8; --primary-light: #FFD6E7; --primary-dark: #E8709E;
  --purple: #C8A7FF; --purple-light: #E8D5FF;
  --green: #A8E6CF; --green-dark: #7BC8A4;
  --red: #FFB3B3; --red-dark: #FF8A8A;
  --text: #4A3347; --muted: #8B7089; --muted-2: #BFA8BC;
  --border: #F5E6F0; --glow: rgba(255,143,184,0.3);
  --shadow: 0 2px 8px rgba(255,143,184,0.08);
  --shadow-hover: 0 4px 16px rgba(255,143,184,0.15);
}
* { box-sizing: border-box; }
html, body { margin: 0; min-height: 100%; background: var(--bg); color: var(--text); }
body { font: 14px/1.5 -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; }
button { font: inherit; cursor: pointer; }
::-webkit-scrollbar { width: 6px; }
::-webkit-scrollbar-thumb { background: var(--primary-light); border-radius: 3px; }

.shell { display: flex; min-height: 100vh; }

/* Sidebar */
.sidebar {
  width: 240px; min-height: 100vh; position: fixed; left: 0; top: 0; z-index: 50;
  background: linear-gradient(180deg, #FFF0F6 0%, #F5E6F0 100%);
  border-right: 1px solid var(--border); padding: 20px 12px;
  display: flex; flex-direction: column;
}
.sidebar-brand { display: flex; align-items: center; gap: 8px; padding: 4px 8px; margin-bottom: 20px; }
.sidebar-brand span.emoji { font-size: 20px; }
.sidebar-brand span.label { font-size: 13px; font-weight: 600; color: var(--muted-2); }
.sidebar-identity { display: flex; align-items: center; gap: 10px; padding: 0 8px; margin-bottom: 24px; }
.sidebar-avatar {
  width: 44px; height: 44px; border-radius: 50%; font-size: 22px;
  background: linear-gradient(135deg, var(--purple-light) 0%, var(--primary-light) 100%);
  display: flex; align-items: center; justify-content: center;
}
.sidebar-name { font-size: 17px; font-weight: 800; }
.sidebar-sub { font-size: 11px; color: var(--muted-2); }
.sidebar nav { flex: 1; display: flex; flex-direction: column; gap: 4px; }
.nav-item {
  display: flex; align-items: center; gap: 12px; padding: 10px 12px; border-radius: 12px;
  border: none; background: transparent; cursor: pointer; width: 100%; text-align: left;
  font-size: 14px; color: var(--muted); transition: all 0.15s;
}
.nav-item:hover { background: rgba(255,214,231,0.4); }
.nav-item.active { background: rgba(255,214,231,0.8); font-weight: 600; color: var(--primary-dark); }
.nav-item .icon { font-size: 18px; width: 24px; text-align: center; }
.sidebar-footer { margin-top: auto; padding: 8px; text-align: center; font-size: 11px; color: var(--muted-2); }

/* Main */
.main { flex: 1; margin-left: 240px; padding: 24px 32px; min-height: 100vh; }
.topbar { display: flex; justify-content: space-between; align-items: center; margin-bottom: 24px; }
.topbar h1 { font-size: 26px; font-weight: 800; margin: 0; }
.topbar p { font-size: 14px; color: var(--muted); margin-top: 4px; }
.top-actions { display: flex; align-items: center; gap: 8px; }
.status { display: inline-flex; align-items: center; gap: 6px; padding: 6px 14px; border-radius: 999px; font-size: 12px; font-weight: 600; background: #D4F5E9; color: #2D7A52; }
.status.closed { background: #FFE0E0; color: #C44; }
.dot { width: 7px; height: 7px; border-radius: 50%; background: currentColor; }
.icon-btn { width: 34px; height: 34px; display: grid; place-items: center; border: 1px solid var(--border); border-radius: 10px; background: var(--bg-card); color: var(--muted); cursor: pointer; transition: all 0.15s; }
.icon-btn:hover { border-color: var(--primary-light); color: var(--primary-dark); }

/* Stat grid */
.stat-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 16px; margin-bottom: 24px; }
.stat-card {
  background: var(--bg-card); border: 1px solid var(--border); border-radius: 16px; padding: 20px;
  box-shadow: var(--shadow); transition: all 0.25s;
}
.stat-card:hover { box-shadow: var(--shadow-hover); transform: translateY(-2px); }
.stat-card .label { font-size: 12px; color: var(--muted-2); font-weight: 500; }
.stat-card .value { font-size: 24px; font-weight: 800; margin-top: 6px; font-family: ui-monospace, monospace; }
.stat-card .change { font-size: 12px; margin-top: 6px; font-weight: 600; }

/* Section head */
.section-head { display: flex; justify-content: space-between; align-items: end; gap: 18px; margin: 28px 0 13px; }
.section-head h1, .section-head h2 { margin: 0; font-size: 20px; font-weight: 800; }
.section-head p { margin: 5px 0 0; color: var(--muted); font-size: 12px; }

/* Cards */
.card {
  background: var(--bg-card); border: 1px solid var(--border); border-radius: 16px;
  box-shadow: var(--shadow); transition: all 0.25s;
  animation: fade-in 0.4s ease-out;
}
.card:hover { box-shadow: var(--shadow-hover); }
.card-head { display: flex; justify-content: space-between; align-items: center; padding: 16px 20px; border-bottom: 1px solid var(--border); }
.card-head h2 { margin: 0; font-size: 15px; font-weight: 700; }
.card-head span { font-size: 12px; color: var(--muted-2); }
.card-body { padding: 16px 20px; }
@keyframes fade-in { from { opacity: 0; transform: translateY(8px); } to { opacity: 1; transform: translateY(0); } }

/* Book */
.book { background: var(--bg-card); border: 1px solid var(--border); border-radius: 16px; box-shadow: var(--shadow); overflow: hidden; }
.book-head { display: flex; justify-content: space-between; align-items: flex-start; gap: 16px; padding: 20px; border-bottom: 1px solid var(--border); }
.book-title h2 { margin: 0; font-size: 16px; font-weight: 700; }
.book-title p { margin: 5px 0 0 0; color: var(--muted); font-size: 12px; }
.book-equity { text-align: right; }
.book-equity strong { display: block; font: 700 28px ui-monospace, monospace; }
.book-equity span { font-size: 13px; font-family: ui-monospace, monospace; }
.metrics { display: grid; grid-template-columns: repeat(4, 1fr); border-bottom: 1px solid var(--border); }
.metric { padding: 14px 16px; min-width: 0; }
.metric .label { color: var(--muted-2); font-size: 11px; font-weight: 500; }
.metric .num { margin-top: 6px; font: 600 15px ui-monospace, monospace; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.metric .hint { margin-top: 3px; color: var(--muted); font-size: 11px; }

/* Table */
.workspace { display: grid; grid-template-columns: minmax(0, 1.5fr) minmax(300px, .75fr); gap: 20px; align-items: start; }
.table-wrap { overflow: auto; }
table { width: 100%; border-collapse: collapse; }
th { padding: 10px 14px; text-align: left; font-size: 11px; font-weight: 600; color: var(--muted-2); border-bottom: 1px solid var(--border); text-transform: uppercase; letter-spacing: 0.06em; }
td { padding: 12px 14px; border-bottom: 1px solid var(--border); font-size: 13px; white-space: nowrap; }
tr:hover td { background: rgba(255,214,231,0.15); }
.asset-symbol { font-weight: 700; color: var(--purple); font-family: ui-monospace, monospace; }
.side-pill { display: inline-flex; min-width: 50px; justify-content: center; padding: 4px 10px; border-radius: 999px; font-size: 11px; font-weight: 600; }
.side-long { background: #D4F5E9; color: #2D7A52; }
.side-short { background: #FFE0E0; color: #C44; }
.status-pill { display: inline-flex; min-width: 60px; justify-content: center; padding: 4px 10px; border-radius: 999px; font-size: 11px; font-weight: 600; }
.status-hold { background: var(--purple-light); color: #7C5CBF; }
.status-tp { background: #D4F5E9; color: #2D7A52; }
.status-sl { background: #FFE0E0; color: #C44; }
.class-pill { display: inline-flex; padding: 3px 10px; border-radius: 999px; font-size: 11px; font-weight: 600; }
.class-paper { background: #D4F5E9; color: #2D7A52; }
.class-watch { background: var(--purple-light); color: #7C5CBF; }
.empty { padding: 40px 16px; text-align: center; color: var(--muted-2); font-size: 13px; }
.pos-row { cursor: pointer; }
.reason-detail { padding: 14px 16px; background: var(--primary-light); border-radius: 0; }
.reason-grid { display: grid; grid-template-columns: repeat(2, 1fr); gap: 10px; }
.reason-grid div { padding: 8px 10px; background: var(--bg-card); border: 1px solid var(--border); border-radius: 10px; }
.reason-grid .kicker { display: block; margin-bottom: 4px; color: var(--primary); font-size: 10px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.1em; }
.reason-grid p { margin: 0; font-size: 12px; line-height: 1.5; }
.reason-summary { margin-top: 10px; padding: 10px 14px; background: var(--bg-card); border-left: 3px solid var(--primary); border-radius: 0 10px 10px 0; font-size: 12px; line-height: 1.6; }
.right-stack { display: grid; gap: 20px; }
.review-card { padding: 16px; }
.review-row { display: flex; justify-content: space-between; gap: 12px; padding: 9px 0; border-bottom: 1px solid var(--border); font-size: 12px; }
.review-row:last-child { border-bottom: 0; }
.review-row span { color: var(--muted); }
.review-row strong { font-family: ui-monospace, monospace; text-align: right; }

/* Horizon bars */
.horizon-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 8px; margin-top: 12px; }
.horizon-card { padding: 10px 12px; border: 1px solid var(--border); border-radius: 12px; background: var(--primary-light); }
.horizon-label { color: var(--muted-2); font-size: 10px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.08em; }
.horizon-wr { margin-top: 6px; font: 600 16px ui-monospace, monospace; }
.horizon-ret { margin-top: 3px; font-size: 12px; font-family: ui-monospace, monospace; }

/* Colors */
.positive { color: var(--green-dark) !important; }
.negative { color: var(--red-dark) !important; }
.amber { color: #B7791F !important; }

/* Footer */
.footer-note { display: flex; justify-content: space-between; gap: 12px; margin-top: 24px; padding-top: 14px; border-top: 1px solid var(--border); color: var(--muted-2); font-size: 11px; }
.footer-note strong { color: var(--primary); font-weight: 600; }

/* Responsive */
@media (max-width: 1050px) {
  .stat-grid { grid-template-columns: repeat(2, 1fr); }
  .workspace { grid-template-columns: 1fr; }
  .metrics { grid-template-columns: repeat(2, 1fr); }
}
@media (max-width: 760px) {
  .sidebar { display: none; }
  .main { margin-left: 0; padding: 16px; }
  .stat-grid { grid-template-columns: 1fr; }
  .metrics { grid-template-columns: 1fr; }
  .horizon-grid { grid-template-columns: repeat(2, 1fr); }
}
</style>
</head>
<body>
<div class="shell">
  <!-- Sidebar -->
  <aside class="sidebar">
    <div class="sidebar-brand"><span class="emoji">🌸</span><span class="label">Financial OS</span></div>
    <div class="sidebar-identity">
      <div class="sidebar-avatar">🐱</div>
      <div><div class="sidebar-name">Xiaomei</div><div class="sidebar-sub">美股 AI 投资助手</div></div>
    </div>
    <nav>
      <button class="nav-item active"><span class="icon">🏠</span>Dashboard</button>
      <button class="nav-item"><span class="icon">📈</span>Markets</button>
      <button class="nav-item"><span class="icon">🔍</span>Screener</button>
      <button class="nav-item"><span class="icon">📊</span>Research</button>
      <button class="nav-item"><span class="icon">💼</span>Portfolio</button>
      <button class="nav-item"><span class="icon">🧪</span>Backtest</button>
      <button class="nav-item"><span class="icon">⚙️</span>Settings</button>
    </nav>
    <div class="sidebar-footer">🌸 Financial OS v0.1</div>
  </aside>

  <!-- Main -->
  <main class="main">
    <header class="topbar">
      <div>
        <h1>🌙 Good evening, let's check your portfolio~</h1>
        <p>东财行情 + yfinance · Pipeline 出票 · 纸面账本</p>
      </div>
      <div class="top-actions">
        <div class="status" id="market-status"><i class="dot"></i><span id="market-label">检测中</span></div>
        <span style="color:var(--muted); font-size:12px; font-family:ui-monospace,monospace" id="server-time">--</span>
        <button class="icon-btn" id="refresh-btn" type="button" title="立即刷新">↻</button>
      </div>
    </header>

    <!-- Stat Grid -->
    <section class="stat-grid">
      <div class="stat-card">
        <div class="label">美股状态</div>
        <div class="value" id="market-state">--</div>
        <div class="change" id="market-time">--</div>
      </div>
      <div class="stat-card">
        <div class="label">今日出票</div>
        <div class="value" id="ticket-count">--</div>
        <div class="change">只标的</div>
      </div>
      <div class="stat-card">
        <div class="label">模拟本金</div>
        <div class="value">$1,000</div>
        <div class="change">USD</div>
      </div>
      <div class="stat-card">
        <div class="label">今日票池</div>
        <div id="ticket-strip" style="display:flex;gap:8px;flex-wrap:wrap;margin-top:8px"><span style="color:var(--muted);font-size:12px">加载中...</span></div>
      </div>
    </section>

    <!-- Portfolio book -->
    <div class="section-head">
      <div>
        <h1>💼 纸面交易组合</h1>
        <p>实时 yfinance 行情标记，含止盈止损判定。每 30 秒自动刷新。</p>
      </div>
      <p id="last-refresh" style="color:var(--muted);font-size:12px">等待数据...</p>
    </div>

    <article class="book" id="book-main"></article>

    <!-- Workspace -->
    <div class="section-head">
      <div><h2>📊 持仓明细</h2><p>当前模拟持仓，实时 P&L。</p></div>
    </div>
    <section class="workspace">
      <div class="card">
        <div class="card-head">
          <h2>当前持仓</h2>
          <span id="position-count">--</span>
        </div>
        <div class="table-wrap">
          <table>
            <thead><tr><th>标的</th><th>方向</th><th>入场</th><th>现价</th><th>变动</th><th>盈亏</th><th>止损</th><th>止盈</th><th>状态</th></tr></thead>
            <tbody id="positions"></tbody>
          </table>
        </div>
      </div>

      <aside class="right-stack">
        <div class="card">
          <div class="card-head"><h2>🎫 今日出票</h2><span id="ticket-date">--</span></div>
          <div class="table-wrap">
            <table>
              <thead><tr><th>标的</th><th>综合分</th><th>分类</th><th>风险</th></tr></thead>
              <tbody id="tickets-table"></tbody>
            </table>
          </div>
        </div>
        <div class="card">
          <div class="card-head"><h2>📈 生命周期胜率</h2><span>历史统计</span></div>
          <div id="scoreboard-card" class="review-card"></div>
        </div>
      </aside>
    </section>

    <!-- Forward tracking -->
    <div class="section-head">
      <div><h2>🔮 前瞻跟踪</h2><p>今日出票的 1d/3d/5d/10d 收益跟踪。</p></div>
    </div>
    <div class="card" style="margin-bottom:24px">
      <div class="table-wrap">
        <table>
          <thead><tr><th>标的</th><th>1d</th><th>3d</th><th>5d</th><th>10d</th></tr></thead>
          <tbody id="tracking-table"></tbody>
        </table>
      </div>
    </div>

    <footer class="footer-note">
      <span><strong>禁止实盘下单</strong> · 纸面模拟，不接入任何券商接口</span>
      <span>数据源：东财 + yfinance · 刷新间隔 30 秒</span>
    </footer>
  </main>
</div>
<script>
const $ = (id) => document.getElementById(id);
const money = (v) => `$${Number(v||0).toLocaleString('en-US',{minimumFractionDigits:2,maximumFractionDigits:2})}`;
const signed = (v,d=2) => `${Number(v||0)>=0?'+':''}${Number(v||0).toFixed(d)}`;
const cls = (v) => Number(v||0)>=0?'positive':'negative';
const esc = (v) => String(v??'').replace(/[&<>"']/g, c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));

function bookMarkup(d) {
  const c = d.pnl >= 0 ? 'positive' : 'negative';
  return `
    <div class="book-head">
      <div>
        <div class="book-title"><h2>模拟组合</h2></div>
        <p>Pipeline 出票 · 纸面交易 · 止盈止损自动化</p>
      </div>
      <div class="book-equity"><strong>${money(d.equity)}</strong><span class="${c}">${signed(d.pnl_pct)}%</span></div>
    </div>
    <div class="metrics">
      <div class="metric"><div class="label">总盈亏</div><div class="num ${c}">${signed(d.pnl)}</div><div class="hint">USD</div></div>
      <div class="metric"><div class="label">多头盈亏</div><div class="num ${cls(d.long_pnl)}">${signed(d.long_pnl)}</div><div class="hint">Long P&L</div></div>
      <div class="metric"><div class="label">空头盈亏</div><div class="num ${cls(d.short_pnl)}">${signed(d.short_pnl)}</div><div class="hint">Short P&L</div></div>
      <div class="metric"><div class="label">持仓数</div><div class="num">${d.position_count||0}</div><div class="hint">现金 ${money(d.cash)}</div></div>
    </div>`;
}

function renderPositions(d) {
  const rows = (d.positions||[]).map((p, i) => {
    const sc = p.status==='TAKE_PROFIT'?'status-tp':(p.status==='STOP_LOSS'?'status-sl':'status-hold');
    const sl = p.status==='TAKE_PROFIT'?'止盈':(p.status==='STOP_LOSS'?'止损':'持有');
    const reasonHtml = p.reason_summary ? `
      <tr class="reason-row" id="reason-${i}" style="display:none">
        <td colspan="9" style="padding:0">
          <div class="reason-detail">
            <div class="reason-grid">
              <div><span class="kicker">市场信号</span><p>${esc(p.reason_market||'--')}</p></div>
              <div><span class="kicker">催化剂</span><p>${esc(p.reason_catalyst||'--')}</p></div>
              <div><span class="kicker">情绪/分类</span><p>${esc(p.reason_sentiment||'--')}</p></div>
              <div><span class="kicker">风险评估</span><p>${esc(p.reason_risk||'--')}</p></div>
            </div>
            <div class="reason-summary">${esc(p.reason_summary)}</div>
          </div>
        </td>
      </tr>` : '';
    return `<tr class="pos-row" onclick="toggleReason(${i})" style="cursor:pointer">
      <td><span class="asset-symbol">${esc(p.symbol)}</span></td>
      <td><span class="side-pill ${p.direction==='LONG'?'side-long':'side-short'}">${p.direction==='LONG'?'做多':'做空'}</span></td>
      <td>${p.entry_price.toFixed(2)}</td>
      <td>${p.current_price.toFixed(2)}</td>
      <td class="${cls(p.pnl_pct)}">${signed(p.pnl_pct)}%</td>
      <td class="${cls(p.pnl_dollar)}">${signed(p.pnl_dollar)}</td>
      <td>${p.stop_loss.toFixed(2)}</td>
      <td>${p.take_profit.toFixed(2)}</td>
      <td><span class="status-pill ${sc}">${sl}</span><span class="kicker" style="margin-left:6px">▸</span></td>
    </tr>${reasonHtml}`;
  });
  $('positions').innerHTML = rows.length ? rows.join('') : '<tr><td colspan="9"><div class="empty">空仓等待信号</div></td></tr>';
  $('position-count').textContent = `${rows.length} 个持仓`;
}
function toggleReason(i) {
  const el = document.getElementById('reason-'+i);
  if (el) el.style.display = el.style.display==='none' ? '' : 'none';
}

function renderTickets(tickets) {
  const rows = (tickets||[]).map(t => {
    const cp = t.classification.includes('PAPER') ? 'class-paper' : 'class-watch';
    const cl = t.classification.includes('PAPER') ? '可交易' : '观察';
    return `<tr>
      <td><span class="asset-symbol">${esc(t.symbol)}</span></td>
      <td>${t.ticket_score.toFixed(3)}</td>
      <td><span class="class-pill ${cp}">${cl}</span></td>
      <td>${esc(t.risk_verdict||'--')}</td>
    </tr>`;
  });
  $('tickets-table').innerHTML = rows.length ? rows.join('') : '<tr><td colspan="4"><div class="empty">今日暂无出票</div></td></tr>';
  if (tickets && tickets.length) $('ticket-date').textContent = tickets[0].output_date;
}

function renderScoreboard(sb) {
  if (!sb || !sb.win_rate) { $('scoreboard-card').innerHTML = '<div class="empty">暂无数据</div>'; return; }
  let html = `<div class="review-row"><span>总胜率</span><strong class="${sb.win_rate>=50?'positive':'negative'}">${sb.win_rate.toFixed(1)}%</strong></div>
    <div class="review-row"><span>平均收益</span><strong class="${cls(sb.avg_return)}">${signed(sb.avg_return)}%</strong></div>
    <div class="review-row"><span>中位收益</span><strong class="${cls(sb.median_return)}">${signed(sb.median_return)}%</strong></div>
    <div class="review-row"><span>样本数</span><strong>${sb.total_rows}</strong></div>`;
  if (sb.top_symbols && sb.top_symbols.length) {
    html += '<div class="review-row"><span>最佳标的</span><strong>' + sb.top_symbols.slice(0,3).map(s=>`${s.symbol}(${signed(s.avg_return)}%)`).join(' · ') + '</strong></div>';
  }
  if (sb.by_horizon && sb.by_horizon.length) {
    html += '<div class="horizon-grid">';
    for (const h of sb.by_horizon) {
      html += `<div class="horizon-card"><div class="horizon-label">${h.horizon}</div><div class="horizon-wr ${h.win_rate>=50?'positive':'negative'}">${h.win_rate.toFixed(1)}%</div><div class="horizon-ret ${cls(h.avg_forward_return)}">${signed(h.avg_forward_return)}%</div></div>`;
    }
    html += '</div>';
  }
  $('scoreboard-card').innerHTML = html;
}

function renderTracking(tracking) {
  if (!tracking || !tracking.length) { $('tracking-table').innerHTML = '<tr><td colspan="5"><div class="empty">暂无跟踪</div></td></tr>'; return; }
  const grouped = {};
  for (const r of tracking) {
    if (!grouped[r.symbol]) grouped[r.symbol] = {};
    grouped[r.symbol][r.horizon_days] = r;
  }
  const rows = Object.entries(grouped).map(([sym, horizons]) => {
    const cells = [1,3,5,10].map(d => {
      const h = horizons[d];
      if (!h) return '<td>--</td>';
      if (h.forward_return != null) return `<td class="${cls(h.forward_return)}">${signed(h.forward_return)}%</td>`;
      return `<td class="amber">${h.check_status}</td>`;
    });
    return `<tr><td><span class="asset-symbol">${esc(sym)}</span></td>${cells.join('')}</tr>`;
  });
  $('tracking-table').innerHTML = rows.join('');
}

function renderMarket(data) {
  const open = data.market_open;
  $('market-status').className = 'status' + (open ? '' : ' closed');
  $('market-label').textContent = open ? '交易中' : '已收盘';
  $('market-state').textContent = open ? '美股开盘' : '美股收盘';
  const et = new Date(data.server_time_et);
  $('market-time').textContent = et.toLocaleTimeString('zh-CN', {hour12:false, timeZone:'America/New_York'}) + ' ET';
  $('server-time').textContent = new Date(data.server_time).toLocaleTimeString('zh-CN', {hour12:false});
  $('ticket-count').textContent = (data.tickets||[]).length;
  $('ticket-strip').innerHTML = (data.tickets||[]).map(t =>
    `<span style="color:#2D7A52;font:600 12px ui-monospace,monospace;background:#D4F5E9;padding:4px 10px;border-radius:999px">${esc(t.symbol)}</span>`
  ).join('') || '<span style="color:var(--muted);font-size:12px">暂无</span>';
}

async function refresh() {
  try {
    const res = await fetch('/api/overview', {cache:'no-store'});
    const d = await res.json();
    renderMarket(d);
    $('book-main').innerHTML = bookMarkup(d.positions);
    renderPositions(d.positions);
    renderTickets(d.tickets);
    renderScoreboard(d.scoreboard);
    renderTracking(d.tracking);
    $('last-refresh').textContent = `最近刷新 ${new Date().toLocaleTimeString('zh-CN',{hour12:false})}`;
  } catch(e) {
    $('last-refresh').textContent = '刷新失败，等待重试';
    console.error(e);
  }
}

$('refresh-btn').addEventListener('click', refresh);
refresh();
setInterval(refresh, 30000);
</script>
</body>
</html>
"""


@app.route("/")
def index():
    return render_template_string(HTML)
