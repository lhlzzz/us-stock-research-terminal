"""
xiaomei FastAPI service.
Standalone API server for xiaomei US stock research system.

Endpoints:
  /health                          - Health check
  /picks                           - List tickets/picks
  /picks/{date}/summary            - Daily pick summary
  /picks/{date}/detail             - Full pick detail
  /returns                         - Return records
  /signals                         - Raw signal values
  /signals/effectiveness           - Signal effectiveness analysis
  /stats/overview                  - High-level system stats
  /stats/performance               - Monthly performance breakdown
  /daily-candidates/{date}         - Daily candidate analysis
  /explain/{date}/{symbol}         - Explain a candidate
"""

from __future__ import annotations

import json
import logging
import os
from datetime import date, datetime
from typing import Optional

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from pathlib import Path
from decimal import Decimal

from db.engine import DATABASE_URL

logger = logging.getLogger(__name__)

app = FastAPI(
    title="xiaomei API",
    description="美股量化研究系统 API",
    version="1.0.0",
)

ROOT = Path(__file__).resolve().parent.parent

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def get_engine():
    from sqlalchemy import create_engine
    return create_engine(DATABASE_URL)


def _num(value, default: float = 0.0) -> float:
    """Convert database numerics to JSON-friendly floats."""
    if value is None:
        return default
    if isinstance(value, Decimal):
        return float(value)
    return float(value)


def _load_engine_state() -> dict:
    engine_state_path = ROOT / "research" / "engine-state.json"
    if not engine_state_path.exists():
        return {}
    try:
        return json.loads(engine_state_path.read_text(encoding="utf-8"))
    except Exception as exc:
        logger.warning("Failed to read engine state: %s", exc)
        return {}


# Models
class Pick(BaseModel):
    symbol: str
    output_date: str
    ticket_score: Optional[float] = None
    market_score: Optional[float] = None
    catalyst_score: Optional[float] = None
    classification: Optional[str] = None
    risk_verdict: Optional[str] = None
    entry_reason: Optional[str] = None


class Return(BaseModel):
    symbol: str
    output_date: str
    horizon_days: int
    forward_return: Optional[float] = None
    check_status: Optional[str] = None


class Signal(BaseModel):
    trade_date: str
    symbol: str
    signal_key: str
    signal_value: Optional[float] = None


class SystemStats(BaseModel):
    total_tickets: int
    total_completed: int
    overall_win_rate: Optional[float] = None
    overall_avg_return: Optional[float] = None
    date_range: Optional[dict] = None


# Endpoints
@app.get("/health")
async def health():
    """Health check."""
    try:
        engine = get_engine()
        from sqlalchemy import text
        with engine.connect() as conn:
            result = conn.execute(text("SELECT 1"))
            db_ok = result.scalar() == 1
    except Exception as e:
        db_ok = False

    return {
        "status": "ok" if db_ok else "degraded",
        "database": "connected" if db_ok else "disconnected",
        "timestamp": datetime.now().isoformat(),
    }


@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard():
    """Serve the dashboard HTML."""
    html_path = ROOT / "public" / "index.html"
    if html_path.exists():
        return HTMLResponse(content=html_path.read_text(encoding="utf-8"))
    return HTMLResponse(content="<h1>Dashboard not found</h1>", status_code=404)


@app.get("/api/positions")
async def get_positions(trade_date: Optional[str] = Query(None)):
    """Get current paper trading positions with database journal reasons.

    The current dashboard uses the latest OPEN trade_date in trade_journal so
    old unclosed review rows do not pollute today's paper simulation snapshot.
    """
    from sqlalchemy import text

    state = _load_engine_state()
    engine = get_engine()
    positions = []
    selected_date = trade_date

    with engine.connect() as conn:
        if not selected_date:
            selected_date = conn.execute(text("""
                SELECT MAX(trade_date)::text
                FROM trade_journal
                WHERE status = 'OPEN'
            """)).scalar()

        rows = []
        if selected_date:
            result = conn.execute(text("""
                SELECT trade_date::text, symbol, direction, entry_price, current_price,
                       quantity, cost_basis, stop_loss, take_profit, pnl_dollar, pnl_pct,
                       status, ticket_score, market_score, catalyst_score, classification,
                       risk_verdict, reason_market, reason_catalyst, reason_sentiment,
                       reason_risk, reason_summary, obsidian_path
                FROM trade_journal
                WHERE status = 'OPEN' AND trade_date = :trade_date
                ORDER BY ticket_score DESC NULLS LAST, symbol
            """), {"trade_date": selected_date})
            rows = [dict(row._mapping) for row in result.fetchall()]

    if rows:
        state_positions = state.get("positions", {}) or {}
        for row in rows:
            sym = row["symbol"]
            state_pos = state_positions.get(sym, {})
            positions.append({
                "trade_date": row["trade_date"],
                "symbol": sym,
                "direction": row.get("direction") or state_pos.get("side", "LONG"),
                "entry_price": round(_num(row.get("entry_price") or state_pos.get("avg_price")), 2),
                "current_price": round(_num(row.get("current_price") or state_pos.get("current_price")), 2),
                "shares": round(_num(row.get("quantity") or state_pos.get("quantity")), 4),
                "cost": round(_num(row.get("cost_basis") or state_pos.get("cost_basis")), 2),
                "pnl_pct": round(_num(row.get("pnl_pct") or state_pos.get("unrealized_pnl_pct")), 2),
                "pnl_dollar": round(_num(row.get("pnl_dollar") or state_pos.get("unrealized_pnl")), 2),
                "stop_loss": round(_num(row.get("stop_loss") or state_pos.get("stop_loss_price")), 2),
                "take_profit": round(_num(row.get("take_profit") or state_pos.get("take_profit_price")), 2),
                "ticket_score": _num(row.get("ticket_score")),
                "market_score": _num(row.get("market_score")),
                "catalyst_score": _num(row.get("catalyst_score")),
                "classification": row.get("classification") or "",
                "risk_verdict": row.get("risk_verdict") or "",
                "reason_market": row.get("reason_market") or "",
                "reason_catalyst": row.get("reason_catalyst") or "",
                "reason_sentiment": row.get("reason_sentiment") or "",
                "reason_risk": row.get("reason_risk") or "",
                "reason_summary": row.get("reason_summary") or "",
                "obsidian_path": row.get("obsidian_path") or "",
            })
    else:
        for sym, pos in (state.get("positions", {}) or {}).items():
            positions.append({
                "symbol": sym,
                "direction": pos.get("side", "LONG"),
                "entry_price": round(_num(pos.get("avg_price")), 2),
                "current_price": round(_num(pos.get("current_price")), 2),
                "shares": round(_num(pos.get("quantity")), 4),
                "cost": round(_num(pos.get("cost_basis")), 2),
                "pnl_pct": round(_num(pos.get("unrealized_pnl_pct")), 2),
                "pnl_dollar": round(_num(pos.get("unrealized_pnl")), 2),
                "stop_loss": round(_num(pos.get("stop_loss_price")), 2),
                "take_profit": round(_num(pos.get("take_profit_price")), 2),
                "reason_market": "",
                "reason_catalyst": "",
                "reason_sentiment": "",
                "reason_risk": "",
                "reason_summary": "",
                "obsidian_path": "",
            })

    db_position_symbols = {p["symbol"] for p in positions}
    state_position_symbols = set((state.get("positions", {}) or {}).keys())
    state_matches_db = bool(db_position_symbols) and db_position_symbols == state_position_symbols
    if state and state_matches_db:
        cash = _num(state.get("cash"))
        equity = _num(state.get("equity"))
        pnl = _num(state.get("total_pnl"))
        pnl_pct = _num(state.get("total_pnl_pct"))
    else:
        cost_basis = sum(p["cost"] for p in positions)
        open_pnl = sum(p["pnl_dollar"] for p in positions)
        cash = _num(state.get("cash")) if state else 0.0
        equity = cash + cost_basis + open_pnl
        pnl = open_pnl
        pnl_pct = (open_pnl / cost_basis * 100) if cost_basis else 0.0

    return {
        "positions": positions,
        "trade_date": selected_date,
        "source": "trade_journal",
        "cash": round(cash, 2),
        "equity": round(equity, 2),
        "initial_capital": _num(state.get("initial_capital"), 1000.0),
        "pnl": round(pnl, 2),
        "pnl_pct": round(pnl_pct, 2),
        "position_count": len(positions),
        "halted": state.get("halted", False),
        "win_rate": state.get("win_rate", 0),
        "updated_at": state.get("updated_at"),
    }


@app.get("/api/trade-journal")
async def get_trade_journal(status: str = None, limit: int = 50):
    """Get trade journal entries with reasons."""
    from sqlalchemy import text
    engine = get_engine()

    query = """
        SELECT trade_date::text, symbol, direction, entry_price, current_price,
               quantity, cost_basis, stop_loss, take_profit, pnl_dollar, pnl_pct,
               status, ticket_score, market_score, catalyst_score, classification,
               risk_verdict, reason_market, reason_catalyst, reason_sentiment,
               reason_risk, reason_summary, obsidian_path
        FROM trade_journal
        WHERE 1=1
    """
    params = {}
    if status:
        query += " AND status = :status"
        params["status"] = status
    query += " ORDER BY trade_date DESC, symbol LIMIT :limit"
    params["limit"] = limit

    with engine.connect() as conn:
        result = conn.execute(text(query), params)
        rows = [dict(row._mapping) for row in result.fetchall()]

    return rows


@app.get("/api/intraday/overview")
async def get_intraday_overview(limit: int = 100):
    """Return the paper-only intraday strategy lifecycle."""
    from sqlalchemy import text

    engine = get_engine()
    with engine.connect() as conn:
        runs = conn.execute(text("""
            SELECT id, session_date::text, strategy_version, status, candidate_count,
                   context_research_run_id, source_state, started_at::text, finished_at::text
            FROM intraday_strategy_runs
            ORDER BY started_at DESC LIMIT :limit
        """), {"limit": limit}).fetchall()
        decisions = conn.execute(text("""
            SELECT d.id, d.run_id, d.session_date::text, d.symbol, d.direction,
                   d.decision, d.decision_status, d.strategy_score, d.score_components,
                   d.quote_source, d.quote_age_seconds, d.reason, d.created_at::text
            FROM intraday_strategy_decisions d
            ORDER BY d.created_at DESC LIMIT :limit
        """), {"limit": limit}).fetchall()
        positions = conn.execute(text("""
            SELECT id, session_date::text, symbol, direction, status, entry_price,
                   current_price, quantity, stop_loss_price, take_profit_price,
                   exit_price, exit_reason, realized_pnl, entry_fees, exit_fees,
                   borrow_rate_daily, accrued_borrow_cost, squeeze_risk_score,
                   opened_at::text, closed_at::text, updated_at::text
            FROM intraday_paper_positions
            ORDER BY updated_at DESC LIMIT :limit
        """), {"limit": limit}).fetchall()
        fills = conn.execute(text("""
            SELECT f.id, o.symbol, o.side, o.status AS order_status, f.quantity,
                   f.price, f.commission, f.sec_fee, f.finra_fee, f.slippage,
                   f.filled_at::text, d.direction, d.reason
            FROM intraday_paper_fills f
            JOIN intraday_paper_orders o ON o.id = f.order_id
            JOIN intraday_strategy_decisions d ON d.id = f.decision_id
            ORDER BY f.filled_at DESC LIMIT :limit
        """), {"limit": limit}).fetchall()

    return {
        "paper_only": True,
        "short_model_status": "UNVALIDATED_PAPER_SHORT",
        "runs": [dict(row._mapping) for row in runs],
        "decisions": [dict(row._mapping) for row in decisions],
        "positions": [dict(row._mapping) for row in positions],
        "fills": [dict(row._mapping) for row in fills],
    }


@app.get("/api/trade-traces")
async def get_trade_traces(
    trade_date: str | None = None,
    symbol: str | None = None,
    record_type: str | None = None,
    limit: int = 200,
):
    """Return the single research lifecycle projection."""
    from sqlalchemy import text

    conditions = ["1 = 1"]
    params: dict[str, object] = {"limit": max(1, min(limit, 1000))}
    if trade_date:
        conditions.append("output_date = :trade_date")
        params["trade_date"] = trade_date
    if symbol:
        conditions.append("UPPER(symbol) = UPPER(:symbol)")
        params["symbol"] = symbol
    if record_type:
        conditions.append("record_type = :record_type")
        params["record_type"] = record_type

    query = f"""
        SELECT record_type, trace_id, record_id, ticket_id, tracking_id,
               output_date::text, symbol, horizon_days, lifecycle_stage,
               record_status, forward_return, pnl, selection_reason,
               outcome_classification, outcome_reason, paper_reason
        FROM research_trade_trace
        WHERE {' AND '.join(conditions)}
        ORDER BY output_date DESC, symbol, record_type, horizon_days NULLS FIRST, record_id
        LIMIT :limit
    """
    with get_engine().connect() as conn:
        result = conn.execute(text(query), params)
        return [dict(row._mapping) for row in result.fetchall()]


@app.get("/api/obsidian/status")
async def obsidian_status():
    """Report Obsidian/database linkage using real synced records."""
    from sqlalchemy import text

    project_root = Path(os.environ.get(
        "XIAOMEI_OBSIDIAN_PROJECT", "/mnt/d/obisidian/Obsidian/Project"
    ))
    shenlin_root = Path(os.environ.get(
        "XIAOMEI_OBSIDIAN_SHENLIN", "/mnt/d/obisidian/Obsidian/神临"
    ))

    engine = get_engine()
    with engine.connect() as conn:
        counts = conn.execute(text("""
            SELECT
                COUNT(*) AS assets,
                COALESCE(SUM((metadata->>'repo' = 'project')::int), 0) AS project_assets,
                COALESCE(SUM((metadata->>'repo' = 'shenlin')::int), 0) AS shenlin_assets,
                MAX(updated_at)::text AS latest_sync
            FROM knowledge_assets
        """)).fetchone()
        latest_assets = conn.execute(text("""
            SELECT title, source_path, source_type, updated_at::text
            FROM knowledge_assets
            ORDER BY updated_at DESC NULLS LAST, id DESC
            LIMIT 5
        """)).fetchall()
        linked_trades = conn.execute(text("""
            SELECT COUNT(*) AS linked
            FROM trade_journal
            WHERE obsidian_path IS NOT NULL AND obsidian_path <> ''
        """)).scalar()

    return {
        "project_path": str(project_root),
        "project_path_exists": project_root.exists(),
        "shenlin_path": str(shenlin_root),
        "shenlin_path_exists": shenlin_root.exists(),
        "knowledge_assets": int(counts.assets or 0),
        "project_assets": int(counts.project_assets or 0),
        "shenlin_assets": int(counts.shenlin_assets or 0),
        "latest_sync": counts.latest_sync,
        "linked_trade_notes": int(linked_trades or 0),
        "latest_assets": [dict(row._mapping) for row in latest_assets],
    }


@app.get("/picks", response_model=list[Pick])
async def list_picks(
    date_from: Optional[str] = Query(None, description="Start date (YYYY-MM-DD)"),
    date_to: Optional[str] = Query(None, description="End date (YYYY-MM-DD)"),
    symbol: Optional[str] = Query(None, description="Filter by symbol"),
    limit: int = Query(50, description="Max results"),
):
    """List tickets/picks."""
    from sqlalchemy import text

    engine = get_engine()
    query = """
        SELECT symbol, output_date::text, ticket_score, market_score, catalyst_score,
               classification, risk_verdict, entry_reason
        FROM tickets
        WHERE 1=1
    """
    params = {}

    if date_from:
        query += " AND output_date >= :date_from"
        params["date_from"] = date_from
    if date_to:
        query += " AND output_date <= :date_to"
        params["date_to"] = date_to
    if symbol:
        query += " AND symbol = :symbol"
        params["symbol"] = symbol

    query += " ORDER BY output_date DESC, ticket_score DESC LIMIT :limit"
    params["limit"] = limit

    with engine.connect() as conn:
        result = conn.execute(text(query), params)
        rows = [dict(row._mapping) for row in result.fetchall()]

    return rows


@app.get("/picks/{trade_date}/summary")
async def pick_summary(trade_date: str):
    """Daily pick summary."""
    from sqlalchemy import text

    engine = get_engine()
    with engine.connect() as conn:
        # Get tickets
        result = conn.execute(text("""
            SELECT symbol, ticket_score, market_score, catalyst_score,
                   classification, risk_verdict, entry_reason
            FROM tickets
            WHERE output_date = :trade_date
            ORDER BY ticket_score DESC
        """), {"trade_date": trade_date})
        tickets = [dict(row._mapping) for row in result.fetchall()]

        # Get forward tracking summary
        result = conn.execute(text("""
            SELECT
                COUNT(*) as total_tracking,
                SUM(CASE WHEN check_status = 'completed' THEN 1 ELSE 0 END) as completed,
                SUM(CASE WHEN forward_return > 0 THEN 1 ELSE 0 END) as positive_returns,
                AVG(forward_return) as avg_return
            FROM forward_tracking ft
            JOIN tickets t ON ft.ticket_id = t.id
            WHERE t.output_date = :trade_date
        """), {"trade_date": trade_date})
        tracking = dict(result.fetchone()._mapping)

    return {
        "trade_date": trade_date,
        "tickets": tickets,
        "tracking": tracking,
        "ticket_count": len(tickets),
    }


@app.get("/picks/{trade_date}/detail")
async def pick_detail(trade_date: str):
    """Full pick detail with candidates and returns."""
    from sqlalchemy import text

    engine = get_engine()
    with engine.connect() as conn:
        # Get tickets with full details
        result = conn.execute(text("""
            SELECT t.symbol, t.ticket_score, t.market_score, t.catalyst_score,
                   t.classification, t.risk_verdict, t.quality_verdict, t.entry_reason,
                   ft.horizon_days, ft.forward_return, ft.check_status
            FROM tickets t
            LEFT JOIN forward_tracking ft ON t.id = ft.ticket_id
            WHERE t.output_date = :trade_date
            ORDER BY t.ticket_score DESC, ft.horizon_days
        """), {"trade_date": trade_date})
        rows = [dict(row._mapping) for row in result.fetchall()]

        # Get daily candidates
        result = conn.execute(text("""
            SELECT symbol, stock_name, final_score, market_score, catalyst_score,
                   decision, selection_reason
            FROM daily_candidates
            WHERE trade_date = :trade_date
            ORDER BY final_score DESC NULLS LAST
            LIMIT 20
        """), {"trade_date": trade_date})
        candidates = [dict(row._mapping) for row in result.fetchall()]

    return {
        "trade_date": trade_date,
        "tickets": rows,
        "candidates": candidates,
    }


@app.get("/returns", response_model=list[Return])
async def list_returns(
    date_from: Optional[str] = Query(None),
    date_to: Optional[str] = Query(None),
    symbol: Optional[str] = Query(None),
    horizon: Optional[int] = Query(None, description="Filter by horizon days"),
    limit: int = Query(100),
):
    """Return records."""
    from sqlalchemy import text

    engine = get_engine()
    query = """
        SELECT t.symbol, t.output_date::text, ft.horizon_days,
               ft.forward_return, ft.check_status
        FROM forward_tracking ft
        JOIN tickets t ON ft.ticket_id = t.id
        WHERE 1=1
    """
    params = {}

    if date_from:
        query += " AND t.output_date >= :date_from"
        params["date_from"] = date_from
    if date_to:
        query += " AND t.output_date <= :date_to"
        params["date_to"] = date_to
    if symbol:
        query += " AND t.symbol = :symbol"
        params["symbol"] = symbol
    if horizon:
        query += " AND ft.horizon_days = :horizon"
        params["horizon"] = horizon

    query += " ORDER BY t.output_date DESC, t.symbol, ft.horizon_days LIMIT :limit"
    params["limit"] = limit

    with engine.connect() as conn:
        result = conn.execute(text(query), params)
        rows = [dict(row._mapping) for row in result.fetchall()]

    return rows


@app.get("/signals", response_model=list[Signal])
async def list_signals(
    trade_date: Optional[str] = Query(None),
    symbol: Optional[str] = Query(None),
    signal_key: Optional[str] = Query(None),
    limit: int = Query(100),
):
    """Raw signal values."""
    from sqlalchemy import text

    engine = get_engine()
    query = """
        SELECT trade_date::text, symbol, signal_key, signal_value
        FROM signals
        WHERE 1=1
    """
    params = {}

    if trade_date:
        query += " AND trade_date = :trade_date"
        params["trade_date"] = trade_date
    if symbol:
        query += " AND symbol = :symbol"
        params["symbol"] = symbol
    if signal_key:
        query += " AND signal_key = :signal_key"
        params["signal_key"] = signal_key

    query += " ORDER BY trade_date DESC, symbol, signal_key LIMIT :limit"
    params["limit"] = limit

    with engine.connect() as conn:
        result = conn.execute(text(query), params)
        rows = [dict(row._mapping) for row in result.fetchall()]

    return rows


@app.get("/signals/effectiveness")
async def signal_effectiveness(
    date_from: Optional[str] = Query(None),
    date_to: Optional[str] = Query(None),
):
    """Signal effectiveness analysis."""
    from sqlalchemy import text

    engine = get_engine()
    query = """
        SELECT analysis_date::text, signal_key, present_count, win_rate,
               avg_return, weight_suggestion, ic_score, p_value
        FROM signal_effectiveness
        WHERE 1=1
    """
    params = {}

    if date_from:
        query += " AND analysis_date >= :date_from"
        params["date_from"] = date_from
    if date_to:
        query += " AND analysis_date <= :date_to"
        params["date_to"] = date_to

    query += " ORDER BY analysis_date DESC, signal_key"

    with engine.connect() as conn:
        result = conn.execute(text(query), params)
        rows = [dict(row._mapping) for row in result.fetchall()]

    return rows


@app.get("/stats/overview", response_model=SystemStats)
async def stats_overview():
    """High-level system stats."""
    from sqlalchemy import text

    engine = get_engine()
    with engine.connect() as conn:
        result = conn.execute(text("""
            SELECT
                COUNT(DISTINCT output_date) as total_dates,
                COUNT(*) as total_tickets,
                MIN(output_date)::text as earliest_date,
                MAX(output_date)::text as latest_date
            FROM tickets
        """))
        ticket_stats = dict(result.fetchone()._mapping)

        result = conn.execute(text("""
            SELECT
                COUNT(*) as total_completed,
                SUM(CASE WHEN forward_return > 0 THEN 1 ELSE 0 END) as positive_returns,
                AVG(forward_return) as avg_return
            FROM forward_tracking
            WHERE check_status = 'completed'
        """))
        return_stats = dict(result.fetchone()._mapping)

    win_rate = None
    if return_stats["total_completed"] and return_stats["total_completed"] > 0:
        win_rate = return_stats["positive_returns"] / return_stats["total_completed"]

    return {
        "total_tickets": ticket_stats["total_tickets"],
        "total_completed": return_stats["total_completed"],
        "overall_win_rate": win_rate,
        "overall_avg_return": return_stats["avg_return"],
        "date_range": {
            "earliest": ticket_stats["earliest_date"],
            "latest": ticket_stats["latest_date"],
        },
    }


@app.get("/stats/performance")
async def stats_performance():
    """Monthly performance breakdown."""
    from sqlalchemy import text

    engine = get_engine()
    with engine.connect() as conn:
        result = conn.execute(text("""
            SELECT
                DATE_TRUNC('month', t.output_date)::text as month,
                COUNT(DISTINCT t.output_date) as trading_days,
                COUNT(*) as tickets,
                SUM(CASE WHEN ft.forward_return > 0 THEN 1 ELSE 0 END)::float /
                    NULLIF(COUNT(ft.id), 0) as win_rate,
                AVG(ft.forward_return) as avg_return
            FROM tickets t
            LEFT JOIN forward_tracking ft ON t.id = ft.ticket_id AND ft.check_status = 'completed'
            GROUP BY DATE_TRUNC('month', t.output_date)
            ORDER BY month DESC
        """))
        rows = [dict(row._mapping) for row in result.fetchall()]

    return rows


@app.get("/daily-candidates/{trade_date}")
async def daily_candidates(trade_date: str):
    """Daily candidate analysis."""
    from sqlalchemy import text

    engine = get_engine()
    with engine.connect() as conn:
        result = conn.execute(text("""
            SELECT symbol, stock_name, final_score, market_score, catalyst_score,
                   decision, is_official_pick, selection_reason, candidate_entry_reason
            FROM daily_candidates
            WHERE trade_date = :trade_date
            ORDER BY final_score DESC NULLS LAST
        """), {"trade_date": trade_date})
        rows = [dict(row._mapping) for row in result.fetchall()]

    return {
        "trade_date": trade_date,
        "candidates": rows,
        "count": len(rows),
    }


@app.get("/explain/{trade_date}/{symbol}")
async def explain_candidate(trade_date: str, symbol: str):
    """Explain a candidate using persisted fields."""
    from sqlalchemy import text

    engine = get_engine()
    with engine.connect() as conn:
        # Get ticket
        result = conn.execute(text("""
            SELECT symbol, ticket_score, market_score, catalyst_score,
                   classification, risk_verdict, quality_verdict, entry_reason
            FROM tickets
            WHERE output_date = :trade_date AND symbol = :symbol
        """), {"trade_date": trade_date, "symbol": symbol})
        ticket = result.fetchone()

        # Get daily candidate
        result = conn.execute(text("""
            SELECT symbol, stock_name, final_score, market_score, catalyst_score,
                   decision, selection_reason, candidate_entry_reason,
                   factor_snapshot, ranking_basis
            FROM daily_candidates
            WHERE trade_date = :trade_date AND symbol = :symbol
        """), {"trade_date": trade_date, "symbol": symbol})
        candidate = result.fetchone()

        # Get returns
        result = conn.execute(text("""
            SELECT ft.horizon_days, ft.forward_return, ft.check_status
            FROM forward_tracking ft
            JOIN tickets t ON ft.ticket_id = t.id
            WHERE t.output_date = :trade_date AND t.symbol = :symbol
            ORDER BY ft.horizon_days
        """), {"trade_date": trade_date, "symbol": symbol})
        returns = [dict(row._mapping) for row in result.fetchall()]

    if not ticket and not candidate:
        raise HTTPException(status_code=404, detail=f"No data for {symbol} on {trade_date}")

    return {
        "trade_date": trade_date,
        "symbol": symbol,
        "ticket": dict(ticket._mapping) if ticket else None,
        "candidate": dict(candidate._mapping) if candidate else None,
        "returns": returns,
    }


# ─── Consolidated endpoints (merged from scripts/api/main.py) ───

@app.get("/api/universe")
async def list_universe():
    """List all symbols in the universe."""
    from sqlalchemy import text
    engine = get_engine()
    with engine.connect() as conn:
        result = conn.execute(text("SELECT symbol, name, sector FROM universe ORDER BY symbol LIMIT 5000"))
        return [dict(zip(result.keys(), row)) for row in result.fetchall()]


@app.get("/api/klines/{symbol}")
async def get_klines(symbol: str, start: Optional[str] = Query(None), end: Optional[str] = Query(None)):
    """Get daily klines for a symbol."""
    from sqlalchemy import text
    engine = get_engine()
    conditions = ["symbol = :symbol"]
    params: dict = {"symbol": symbol.upper()}
    if start:
        conditions.append("trade_date >= :start")
        params["start"] = start
    if end:
        conditions.append("trade_date <= :end")
        params["end"] = end
    where = " AND ".join(conditions)
    with engine.connect() as conn:
        result = conn.execute(text(f"SELECT trade_date::text as date, open, high, low, close, volume FROM daily_klines WHERE {where} ORDER BY trade_date"), params)
        return [dict(zip(result.keys(), row)) for row in result.fetchall()]


@app.get("/api/scoreboard")
async def get_scoreboard():
    """Get latest lifecycle scoreboard."""
    from sqlalchemy import text
    engine = get_engine()
    with engine.connect() as conn:
        result = conn.execute(text("SELECT overall, by_horizon, by_stage, generated_at::text FROM lifecycle_scoreboard ORDER BY generated_at DESC LIMIT 1"))
        rows = [dict(zip(result.keys(), row)) for row in result.fetchall()]
        return rows[0] if rows else {"overall": {}, "by_horizon": {}}


@app.get("/api/capital/scoreboard")
async def get_capital_scoreboard():
    """Return research-only Capital Brain outcome diagnostics."""
    from sqlalchemy import text
    engine = get_engine()
    with engine.connect() as conn:
        summary = dict(conn.execute(text("""
            SELECT COUNT(*) AS sample_count,
                   AVG(CASE WHEN cpo.state_correct IS TRUE THEN 1.0
                            WHEN cpo.state_correct IS FALSE THEN 0.0 END) AS state_accuracy,
                   AVG(CASE WHEN cpo.intent_correct IS TRUE THEN 1.0
                            WHEN cpo.intent_correct IS FALSE THEN 0.0 END) AS intent_accuracy,
                   AVG(CASE WHEN cpo.path_correct IS TRUE THEN 1.0
                            WHEN cpo.path_correct IS FALSE THEN 0.0 END) AS path_accuracy,
                   AVG(ft.forward_return) AS avg_return,
                   AVG(CASE WHEN ft.forward_return > 0 THEN 1.0 ELSE 0.0 END) AS win_rate
            FROM forward_tracking ft
            LEFT JOIN capital_prediction_outcome cpo
              ON cpo.forward_tracking_id = ft.id
            WHERE ft.check_status = 'completed'
              AND ft.forward_return IS NOT NULL
              AND ft.capital_model_version = 'capital_behavior_v2'
              AND ft.capital_validation_status = 'VALIDATED_FOR_BENCHMARK'
        """)).mappings().one())
        horizons = [
            dict(row)
            for row in conn.execute(text("""
                SELECT horizon_days, COUNT(*) AS sample_count,
                       AVG(CASE WHEN t.expected_direction = 'LONG' AND ft.forward_return > 0 THEN 1.0
                                WHEN t.expected_direction = 'SHORT' AND ft.forward_return < 0 THEN 1.0
                                WHEN t.expected_direction IN ('LONG', 'SHORT') THEN 0.0 END) AS direction_accuracy
                FROM forward_tracking ft
                LEFT JOIN tickets t ON t.id = ft.ticket_id
                WHERE ft.check_status = 'completed'
                  AND ft.forward_return IS NOT NULL
                  AND ft.capital_model_version = 'capital_behavior_v2'
                  AND ft.capital_validation_status = 'VALIDATED_FOR_BENCHMARK'
                GROUP BY horizon_days
                ORDER BY horizon_days
            """)).mappings()
        ]
    return {
        "status": "RESEARCH_ONLY",
        "validation_status": "UNVALIDATED_NO_FIXED_CHAIN",
        **summary,
        "by_horizon": horizons,
        "mfe": "UNAVAILABLE_NOT_PERSISTED",
        "mae": "UNAVAILABLE_NOT_PERSISTED",
        "distribution_avoidance": "UNAVAILABLE_NO_PRODUCTION_GATE",
        "trap_avoidance": "UNAVAILABLE_NO_PRODUCTION_GATE",
    }


@app.get("/api/capital/history/{symbol}")
async def get_capital_history(symbol: str, limit: int = Query(60, ge=1, le=500)):
    """Return inferred daily Capital Brain state history for a symbol."""
    from sqlalchemy import text
    limit = int(limit) if isinstance(limit, (int, str)) else 60
    engine = get_engine()
    with engine.connect() as conn:
        rows = [
            dict(row)
            for row in conn.execute(text("""
                SELECT csh.as_of_date::text, csh.research_run_id, csh.model_version,
                       csh.capital_state,
                       csh.previous_capital_state, csh.state_transition, csh.state_duration,
                       csh.state_confidence, csh.state_reason, csh.state_momentum,
                       csh.transition_score, csh.transition_acceleration,
                       csh.evidence_persistence, csh.expected_duration,
                       csh.duration_percentile, csh.late_state_risk, csh.state_age_score,
                       csh.transition_probabilities, csh.transition_matrix,
                       ci.capital_intent, ci.intent_confidence, ci.intent_probability,
                       ci.intent_probabilities, ci.intent_alternatives,
                       ci.expected_direction, ci.previous_intent, ci.current_intent,
                       ci.intent_transition, ci.continuation_condition,
                       ci.invalidation_condition, cpp.path_type, cpp.t1_probability,
                       cpp.t3_probability, cpp.t5_probability, cpp.path_confidence,
                       cpp.path_distribution, cpp.path_sequence, cpp.path_invalidation,
                       cds.capital_strength, cds.capital_quality, cds.quality_label,
                       cds.absorption_score, cds.absorption_efficiency,
                       cds.absorption_persistence, cds.upside_control_efficiency,
                       cds.downside_control_efficiency, cds.control_asymmetry,
                       cds.control_regime, cds.control_collapse_score,
                       cds.distribution_probability, cds.distribution_stage,
                       cds.distribution_acceleration, cds.distribution_transition_risk,
                       cds.trap_probability, cds.evidence_json
                FROM capital_state_history csh
                LEFT JOIN capital_intent ci
                  ON ci.symbol = csh.symbol AND ci.research_run_id = csh.research_run_id
                LEFT JOIN capital_path_prediction cpp
                  ON cpp.symbol = csh.symbol AND cpp.research_run_id = csh.research_run_id
                LEFT JOIN capital_daily_snapshot cds
                  ON cds.symbol = csh.symbol AND cds.research_run_id = csh.research_run_id
                WHERE csh.symbol = :symbol
                ORDER BY csh.as_of_date DESC, csh.research_run_id DESC
                LIMIT :limit
            """), {"symbol": symbol.upper(), "limit": limit}).mappings()
        ]
    return {"symbol": symbol.upper(), "history": rows}


@app.get("/api/capital/transitions/{symbol}")
async def get_capital_transitions(symbol: str, limit: int = Query(60, ge=1, le=500)):
    """Return the inferred state and intent transition timeline."""
    limit = int(limit) if isinstance(limit, (int, str)) else 60
    history = await get_capital_history(symbol, limit=limit)
    return {
        "symbol": symbol.upper(),
        "transitions": [
            {
                "as_of_date": row.get("as_of_date"),
                "from_state": row.get("previous_capital_state"),
                "to_state": row.get("capital_state"),
                "state_transition": row.get("state_transition"),
                "state_confidence": row.get("state_confidence"),
                "transition_score": row.get("transition_score"),
                "transition_probabilities": row.get("transition_probabilities") or {},
                "intent_transition": row.get("intent_transition"),
                "intent_probability": row.get("intent_probability"),
            }
            for row in history["history"]
        ],
    }


@app.get("/api/capital/state/{symbol}")
async def get_capital_state(symbol: str):
    """Return the latest inferred capital state, or an explicit empty result."""
    history = await get_capital_history(symbol, limit=1)
    return {
        "symbol": symbol.upper(),
        "state": history["history"][0] if history["history"] else None,
        "semantic": "INFERRED",
    }


@app.get("/api/capital/path/{symbol}")
async def get_capital_path(symbol: str):
    """Return the latest predicted price path, or an explicit empty result."""
    from sqlalchemy import text
    engine = get_engine()
    with engine.connect() as conn:
        row = conn.execute(text("""
            SELECT cpp.as_of_date::text, cpp.research_run_id, cpp.model_version,
                   cpp.path_type,
                   cpp.t1_probability, cpp.t3_probability, cpp.t5_probability,
                   cpp.path_confidence, cpp.path_distribution, cpp.path_sequence,
                   cpp.path_invalidation, cpp.semantic
            FROM capital_path_prediction cpp
            WHERE cpp.symbol = :symbol
            ORDER BY cpp.as_of_date DESC, cpp.research_run_id DESC
            LIMIT 1
        """), {"symbol": symbol.upper()}).mappings().first()
    return {"symbol": symbol.upper(), "path": dict(row) if row else None}


@app.get("/api/capital/{symbol}")
async def get_capital(symbol: str):
    """Return the latest combined public-data Capital Brain assessment."""
    from sqlalchemy import text
    engine = get_engine()
    with engine.connect() as conn:
        row = conn.execute(text("""
            SELECT cds.symbol, cds.as_of_date::text, cds.research_run_id,
                   cds.model_version, cds.data_version, cds.validation_status,
                   cds.statistical_score, cds.capital_score, cds.combined_score,
                   cds.capital_strength, cds.capital_quality, cds.quality_label,
                   cds.dominant_direction, cds.dominant_pressure,
                   cds.absorption_score, cds.absorption_efficiency,
                   cds.absorption_persistence, cds.upside_control_efficiency,
                   cds.downside_control_efficiency, cds.control_asymmetry,
                   cds.control_regime, cds.control_collapse_score,
                   cds.distribution_risk, cds.distribution_probability,
                   cds.distribution_stage, cds.distribution_acceleration,
                   cds.distribution_transition_risk, cds.trap_risk,
                   cds.trap_probability, cds.transition_score,
                   cds.transition_acceleration, cds.state_age_score,
                   cds.late_state_risk, cds.intent_probability,
                   cds.intent_probabilities, cds.transition_probabilities,
                   cds.path_distribution, cds.evidence_json,
                   csh.capital_state, csh.previous_capital_state, csh.state_transition,
                   csh.state_duration, csh.state_confidence, csh.state_reason,
                   csh.state_momentum, csh.transition_acceleration AS state_transition_acceleration,
                   csh.evidence_persistence, csh.expected_duration,
                   csh.duration_percentile, csh.state_age_score AS state_age_score_history,
                   csh.transition_probabilities AS state_transition_probabilities,
                   csh.transition_matrix,
                   ci.capital_intent, ci.intent_confidence, ci.intent_probability,
                   ci.intent_probabilities, ci.intent_alternatives,
                   ci.previous_intent, ci.current_intent, ci.intent_transition,
                   ci.expected_direction,
                   ci.continuation_condition, ci.invalidation_condition,
                   cpp.path_type, cpp.t1_probability, cpp.t3_probability,
                   cpp.t5_probability, cpp.path_confidence,
                   cpp.path_distribution, cpp.path_sequence, cpp.path_invalidation
            FROM capital_daily_snapshot cds
            LEFT JOIN capital_state_history csh
              ON csh.symbol = cds.symbol AND csh.research_run_id = cds.research_run_id
            LEFT JOIN capital_intent ci
              ON ci.symbol = cds.symbol AND ci.research_run_id = cds.research_run_id
            LEFT JOIN capital_path_prediction cpp
              ON cpp.symbol = cds.symbol AND cpp.research_run_id = cds.research_run_id
            WHERE cds.symbol = :symbol
            ORDER BY cds.as_of_date DESC, cds.research_run_id DESC
            LIMIT 1
        """), {"symbol": symbol.upper()}).mappings().first()
    assessment = dict(row) if row else None
    return {
        "symbol": symbol.upper(),
        "assessment": assessment,
        "capital_state": assessment.get("capital_state") if assessment else None,
        "capital_intent": assessment.get("capital_intent") if assessment else None,
        "capital_strength": assessment.get("capital_strength") if assessment else None,
        "capital_quality": assessment.get("capital_quality") if assessment else None,
        "paths": {
            "t1": (assessment.get("path_distribution") or {}).get("t1", {}) if assessment else {},
            "t3": (assessment.get("path_distribution") or {}).get("t3", {}) if assessment else {},
            "t5": (assessment.get("path_distribution") or {}).get("t5", {}) if assessment else {},
        },
        "semantic_contract": {
            "evidence": "DERIVED",
            "state_and_intent": "INFERRED",
            "path": "PREDICTED",
        },
    }


@app.get("/api/factors")
async def get_factors(trade_date: str = None, symbol: str = None, limit: int = 100):
    """Get factor snapshots. Optionally filter by date and/or symbol."""
    from sqlalchemy import text
    engine = get_engine()
    conditions, params = [], {"limit": limit}
    if trade_date:
        conditions.append("trade_date = :td"); params["td"] = trade_date
    if symbol:
        conditions.append("symbol = :sym"); params["sym"] = symbol.upper()
    where = ("WHERE " + " AND ".join(conditions)) if conditions else ""
    with engine.connect() as conn:
        result = conn.execute(text(f"""
            SELECT trade_date::text, symbol,
                prior_5d_momentum, prior_20d_momentum, five_day_acceleration,
                relative_strength, volume_weighted_momentum, volume_confirmation,
                rsi_14, momentum_quality, breakout_score, reversal_quality,
                closing_strength_5d, market_score, announcement_catalyst, theme_strength, regime
            FROM factor_snapshots {where}
            ORDER BY trade_date DESC, symbol LIMIT :limit
        """), params)
        return [dict(zip(result.keys(), row)) for row in result.fetchall()]


@app.get("/api/market-regime")
async def get_market_regime(limit: int = 30):
    """Get market regime history."""
    from sqlalchemy import text
    engine = get_engine()
    with engine.connect() as conn:
        result = conn.execute(text("""
            SELECT trade_date::text, regime, breadth, momentum, volatility,
                   advance_ratio, universe_count
            FROM market_snapshots ORDER BY trade_date DESC LIMIT :limit
        """), {"limit": limit})
        return [dict(zip(result.keys(), row)) for row in result.fetchall()]


@app.get("/api/scoring-config")
async def get_scoring_config():
    """Get current scoring weight configuration."""
    import json as _json
    from pathlib import Path
    weights_file = Path(__file__).resolve().parent.parent / "data" / "scoring_weights.json"
    if weights_file.exists():
        try:
            return _json.loads(weights_file.read_text())
        except Exception:
            pass
    return {"weights": {}, "ic_scores": {}}


@app.get("/api/degradation")
async def get_degradation():
    """Run degradation detection and return results."""
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from meta_loop import run_meta_loop
    return run_meta_loop()


@app.get("/api/forward-tracking/stats")
async def get_forward_tracking_stats():
    """Get forward tracking stats by horizon with win rate and avg return."""
    from sqlalchemy import text
    engine = get_engine()
    with engine.connect() as conn:
        result = conn.execute(text("""
            SELECT
                horizon_days,
                COUNT(*) as total,
                COUNT(CASE WHEN forward_return > 0 THEN 1 END) as wins,
                ROUND(AVG(forward_return)::numeric, 6) as avg_return,
                ROUND(AVG(CASE WHEN forward_return > 0 THEN forward_return END)::numeric, 6) as avg_win,
                ROUND(AVG(CASE WHEN forward_return <= 0 THEN forward_return END)::numeric, 6) as avg_loss,
                MIN(forward_return) as worst,
                MAX(forward_return) as best
            FROM forward_tracking
            WHERE check_status = 'completed' AND forward_return IS NOT NULL
            GROUP BY horizon_days ORDER BY horizon_days
        """))
        rows = [dict(zip(result.keys(), row)) for row in result.fetchall()]
        for r in rows:
            total = r.get("total", 0)
            wins = r.get("wins", 0)
            r["win_rate"] = round(wins / total, 4) if total > 0 else 0
        return rows


@app.get("/api/symbols/{symbol}/detail")
async def get_symbol_detail(symbol: str):
    """Get comprehensive detail for a symbol: tickets, tracking, factors."""
    from sqlalchemy import text
    engine = get_engine()
    sym = symbol.upper()
    with engine.connect() as conn:
        result = conn.execute(text(
            "SELECT output_date::text, ticket_score, market_score, catalyst_score, classification, risk_verdict FROM tickets WHERE symbol=:s ORDER BY output_date DESC LIMIT 10"
        ), {"s": sym})
        cols = list(result.keys())
        tickets = [dict(zip(cols, row)) for row in result.fetchall()]

        result2 = conn.execute(text(
            "SELECT output_date::text, horizon_days, check_status, forward_return FROM forward_tracking WHERE symbol=:s ORDER BY output_date DESC LIMIT 20"
        ), {"s": sym})
        cols2 = list(result2.keys())
        tracking = [dict(zip(cols2, row)) for row in result2.fetchall()]

        return {"symbol": sym, "tickets": tickets, "tracking": tracking}


if __name__ == "__main__":
    raise SystemExit(
        "xiaomei no longer starts an independent HTTP server; "
        "use the shared Hermes Financial OS gateway at http://localhost:3000"
    )
