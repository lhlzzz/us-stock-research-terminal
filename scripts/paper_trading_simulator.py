#!/usr/bin/env python3
"""Paper Trading Simulator for xiaomei US stock tickets.

Simulates T+0 trading using historical ticket data from PostgreSQL.
- Buy at ticket date close price
- Sell at 1d/3d/5d/10d horizons (or stop-loss)
- Tracks cumulative P&L with configurable initial capital
- Reports win rate, avg return, max drawdown, Sharpe ratio

Usage:
    python3 scripts/paper_trading_simulator.py
    python3 scripts/paper_trading_simulator.py --capital 5000 --max-position-pct 0.15
    python3 scripts/paper_trading_simulator.py --horizon 3d --stop-loss 0.05
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))

from db.engine import SessionLocal, query_rows
from sqlalchemy import text


# ─── Configuration ──────────────────────────────────────────────
DEFAULT_CAPITAL = 1000.0
DEFAULT_MAX_POSITION_PCT = 0.20  # 20% per position
DEFAULT_HORIZON = "3d"
DEFAULT_STOP_LOSS = 0.08  # 8% stop-loss
DEFAULT_TAKE_PROFIT = 0.15  # 15% take-profit
HORIZON_DAYS = {"1d": 1, "3d": 3, "10d": 10}


def load_tickets_from_db(start_date: str | None = None) -> pd.DataFrame:
    """Load tickets from PostgreSQL."""
    query = """
        SELECT t.id AS ticket_id, t.output_date, t.symbol, t.ticket_score, t.market_score,
               t.catalyst_score, t.classification, t.entry_reason,
               ft.horizon_days, ft.forward_return, ft.check_status,
               ft.as_of_close as entry_price, ft.due_close as exit_price
        FROM tickets t
        LEFT JOIN forward_tracking ft ON ft.ticket_id = t.id
        WHERE t.classification IN ('CANDIDATE_FOR_PAPER_REVIEW', 'MARKET_WATCHLIST_NEEDS_EVIDENCE')
        AND (ft.check_status = 'completed' OR ft.check_status IS NULL)
        ORDER BY t.output_date, t.ticket_score DESC
    """
    if start_date:
        query = f"SELECT * FROM ({query}) sub WHERE output_date >= '{start_date}'"

    with SessionLocal() as session:
        result = session.execute(text(query))
        rows = result.fetchall()
        columns = result.keys()

    df = pd.DataFrame(rows, columns=columns)
    return df


def load_ticket_prices(
    symbol: str,
    entry_date: date,
    horizons: list[int],
    ticket_id: int | None = None,
) -> dict[str, float | None]:
    """Load actual prices for a ticket at various horizons."""
    query = """
        SELECT horizon_days, as_of_close, due_close, forward_return
        FROM forward_tracking
        WHERE check_status = 'completed'
          AND (:ticket_id IS NULL AND symbol = :symbol AND output_date = :entry_date
               OR :ticket_id IS NOT NULL AND ticket_id = :ticket_id)
        ORDER BY horizon_days
    """
    with SessionLocal() as session:
        result = session.execute(text(query), {
            "symbol": symbol,
            "entry_date": entry_date,
            "ticket_id": ticket_id,
        })
        rows = result.fetchall()

    prices = {}
    for row in rows:
        h = row[0]
        if h in horizons:
            prices[f"{h}d"] = {
                "entry": float(row[1]) if row[1] else None,
                "exit": float(row[2]) if row[2] else None,
                "return": float(row[3]) if row[3] else None,
            }
    return prices


class Portfolio:
    """Paper trading portfolio tracker."""

    def __init__(self, initial_capital: float, max_position_pct: float):
        self.initial_capital = initial_capital
        self.cash = initial_capital
        self.max_position_pct = max_position_pct
        self.positions: list[dict] = []
        self.closed_trades: list[dict] = []
        self.equity_curve: list[dict] = []
        self.day_count = 0

    def open_position(self, symbol: str, entry_date: date, entry_price: float,
                      ticket_score: float, horizon: int, stop_loss: float, take_profit: float,
                      direction: str = "long") -> bool:
        """Open a new position if we have enough cash. direction: 'long' or 'short'."""
        position_size = min(self.cash * self.max_position_pct, self.cash * 0.95)
        if position_size < 10:  # Minimum $10 position
            return False

        shares = position_size / entry_price
        cost = shares * entry_price

        self.cash -= cost
        self.positions.append({
            "symbol": symbol,
            "entry_date": entry_date,
            "entry_price": entry_price,
            "shares": shares,
            "cost": cost,
            "ticket_score": ticket_score,
            "horizon": horizon,
            "stop_loss": stop_loss,
            "take_profit": take_profit,
            "days_held": 0,
            "direction": direction,  # 'long' or 'short'
            "ticket_id": None,
        })
        return True

    def close_position(self, position: dict, exit_date: date, exit_price: float, reason: str) -> dict:
        """Close a position and record the trade."""
        direction = position.get("direction", "long")
        if direction == "short":
            # Short: profit when price goes down
            pnl = position["cost"] - (position["shares"] * exit_price)
            pnl_pct = pnl / position["cost"]
            proceeds = position["cost"] + pnl
        else:
            # Long: profit when price goes up
            proceeds = position["shares"] * exit_price
            pnl = proceeds - position["cost"]
            pnl_pct = pnl / position["cost"]

        self.cash += proceeds
        trade = {
            "symbol": position["symbol"],
            "entry_date": position["entry_date"],
            "exit_date": exit_date,
            "entry_price": position["entry_price"],
            "exit_price": exit_price,
            "shares": position["shares"],
            "cost": position["cost"],
            "proceeds": proceeds,
            "pnl": pnl,
            "pnl_pct": pnl_pct,
            "days_held": position["days_held"],
            "ticket_score": position["ticket_score"],
            "direction": position.get("direction", "long"),
            "reason": reason,
        }
        self.closed_trades.append(trade)
        self.positions.remove(position)
        return trade

    def record_equity(self, current_date: date, market_values: dict[str, float] | None = None):
        """Record current portfolio equity."""
        position_value = 0
        for p in self.positions:
            current = market_values.get(p["symbol"], p["entry_price"]) if market_values else p["entry_price"]
            if p.get("direction") == "short":
                # Short position: value = cost - (shares * current_price) + cost
                # Simplified: 2*cost - shares*current
                position_value += 2 * p["cost"] - p["shares"] * current
            else:
                position_value += p["shares"] * current
        total_equity = self.cash + position_value
        self.equity_curve.append({
            "date": current_date.isoformat(),
            "cash": round(self.cash, 2),
            "positions_value": round(position_value, 2),
            "total_equity": round(total_equity, 2),
            "num_positions": len(self.positions),
            "drawdown": round((total_equity / self.initial_capital - 1) * 100, 2),
        })

    def get_stats(self) -> dict[str, Any]:
        """Compute portfolio statistics."""
        if not self.closed_trades:
            return {"error": "No closed trades"}

        trades = pd.DataFrame(self.closed_trades)
        equity = pd.DataFrame(self.equity_curve)

        wins = trades[trades["pnl"] > 0]
        losses = trades[trades["pnl"] <= 0]

        # Drawdown
        if len(equity) > 0:
            equity["peak"] = equity["total_equity"].cummax()
            equity["drawdown_pct"] = (equity["total_equity"] - equity["peak"]) / equity["peak"] * 100
            max_drawdown = equity["drawdown_pct"].min()
        else:
            max_drawdown = 0

        # Sharpe ratio (annualized, assuming daily returns)
        if len(equity) > 1:
            equity["daily_return"] = equity["total_equity"].pct_change()
            sharpe = equity["daily_return"].mean() / equity["daily_return"].std() * np.sqrt(252) if equity["daily_return"].std() > 0 else 0
        else:
            sharpe = 0

        final_equity = equity["total_equity"].iloc[-1] if len(equity) > 0 else self.initial_capital
        total_return = (final_equity / self.initial_capital - 1) * 100

        return {
            "total_trades": len(trades),
            "wins": len(wins),
            "losses": len(losses),
            "win_rate": round(len(wins) / len(trades) * 100, 1),
            "avg_return_pct": round(trades["pnl_pct"].mean() * 100, 2),
            "avg_win_pct": round(wins["pnl_pct"].mean() * 100, 2) if len(wins) > 0 else 0,
            "avg_loss_pct": round(losses["pnl_pct"].mean() * 100, 2) if len(losses) > 0 else 0,
            "total_pnl": round(trades["pnl"].sum(), 2),
            "initial_capital": self.initial_capital,
            "final_equity": round(final_equity, 2),
            "total_return_pct": round(total_return, 2),
            "max_drawdown_pct": round(max_drawdown, 2),
            "sharpe_ratio": round(sharpe, 2),
            "avg_days_held": round(trades["days_held"].mean(), 1),
            "profit_factor": round(
                wins["pnl"].sum() / abs(losses["pnl"].sum()), 2
            ) if len(losses) > 0 and losses["pnl"].sum() != 0 else float("inf"),
            "best_trade": round(trades["pnl_pct"].max() * 100, 2),
            "worst_trade": round(trades["pnl_pct"].min() * 100, 2),
            "by_symbol": trades.groupby("symbol").agg(
                trades=("pnl", "count"),
                win_rate=("pnl", lambda x: round((x > 0).mean() * 100, 1)),
                avg_return=("pnl_pct", lambda x: round(x.mean() * 100, 2)),
                total_pnl=("pnl", lambda x: round(x.sum(), 2)),
            ).to_dict("index"),
        }


def run_simulation(
    capital: float = DEFAULT_CAPITAL,
    max_position_pct: float = DEFAULT_MAX_POSITION_PCT,
    horizon: str = DEFAULT_HORIZON,
    stop_loss: float = DEFAULT_STOP_LOSS,
    take_profit: float = DEFAULT_TAKE_PROFIT,
    start_date: str | None = None,
    max_concurrent: int = 5,
) -> dict:
    """Run paper trading simulation."""
    horizon_days = HORIZON_DAYS[horizon]

    print(f"Loading tickets from DB...")
    tickets_df = load_tickets_from_db(start_date)
    if tickets_df.empty:
        return {"error": "No tickets found"}

    # Get unique trading dates
    trading_dates = sorted(tickets_df["output_date"].unique())
    print(f"Found {len(trading_dates)} trading dates, {len(tickets_df)} ticket records")

    portfolio = Portfolio(capital, max_position_pct)

    for trade_date in trading_dates:
        day_tickets = tickets_df[
            (tickets_df["output_date"] == trade_date) &
            (tickets_df["horizon_days"] == horizon_days)
        ].copy()

        if day_tickets.empty:
            continue

        # Record equity at start of day
        portfolio.record_equity(trade_date)

        # Close positions that have reached their horizon
        for pos in list(portfolio.positions):
            pos["days_held"] += 1
            if pos["days_held"] >= pos["horizon"]:
                # Get actual return from forward_tracking
                prices = load_ticket_prices(pos["symbol"], pos["entry_date"], [pos["horizon"]], pos.get("ticket_id"))
                horizon_key = f"{pos['horizon']}d"
                if horizon_key in prices and prices[horizon_key]["return"] is not None:
                    actual_return = prices[horizon_key]["return"]
                    exit_price = pos["entry_price"] * (1 + actual_return)
                    reason = "horizon_reached"
                    if actual_return <= -pos["stop_loss"]:
                        reason = "stop_loss"
                    elif actual_return >= pos["take_profit"]:
                        reason = "take_profit"
                else:
                    # Fallback: assume flat
                    exit_price = pos["entry_price"]
                    reason = "no_data"

                portfolio.close_position(pos, trade_date, exit_price, reason)

        # Open new positions for top candidates
        top_tickets = day_tickets.head(max_concurrent - len(portfolio.positions))
        for _, ticket in top_tickets.iterrows():
            symbol = ticket["symbol"]
            entry_price = float(ticket.get("entry_price", 0) or 0)
            if entry_price <= 0:
                # Try to get from forward_tracking
                prices = load_ticket_prices(symbol, trade_date, [horizon_days])
                hkey = f"{horizon_days}d"
                if hkey in prices and prices[hkey]["entry"]:
                    entry_price = prices[hkey]["entry"]
                else:
                    continue

            portfolio.open_position(
                symbol=symbol,
                entry_date=trade_date,
                entry_price=entry_price,
                ticket_score=float(ticket.get("ticket_score", 0) or 0),
                horizon=horizon_days,
                stop_loss=stop_loss,
                take_profit=take_profit,
            )
            portfolio.positions[-1]["ticket_id"] = int(ticket["ticket_id"]) if pd.notna(ticket.get("ticket_id")) else None

    # Close any remaining positions
    for pos in list(portfolio.positions):
        prices = load_ticket_prices(pos["symbol"], pos["entry_date"], [pos["horizon"]], pos.get("ticket_id"))
        hkey = f"{pos['horizon']}d"
        if hkey in prices and prices[hkey]["return"] is not None:
            exit_price = pos["entry_price"] * (1 + prices[hkey]["return"])
        else:
            exit_price = pos["entry_price"]
        portfolio.close_position(pos, trading_dates[-1], exit_price, "simulation_end")

    portfolio.record_equity(trading_dates[-1])

    stats = portfolio.get_stats()
    stats["config"] = {
        "initial_capital": capital,
        "max_position_pct": max_position_pct,
        "horizon": horizon,
        "stop_loss": stop_loss,
        "take_profit": take_profit,
        "max_concurrent": max_concurrent,
        "start_date": start_date or "all",
    }
    stats["equity_curve"] = portfolio.equity_curve
    stats["trades"] = portfolio.closed_trades

    return stats


def generate_report(stats: dict) -> str:
    """Generate markdown report."""
    if "error" in stats:
        return f"# Paper Trading Simulation Error\n\n{stats['error']}"

    config = stats.get("config", {})
    lines = [
        "# Paper Trading Simulation Report",
        f"- Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
        f"- Initial Capital: ${config.get('initial_capital', 0):,.2f}",
        f"- Horizon: {config.get('horizon', 'N/A')}",
        f"- Max Position: {config.get('max_position_pct', 0)*100:.0f}%",
        f"- Stop Loss: {config.get('stop_loss', 0)*100:.0f}%",
        f"- Take Profit: {config.get('take_profit', 0)*100:.0f}%",
        "",
        "## Performance Summary",
        f"| Metric | Value |",
        f"|---|---|",
        f"| Total Trades | {stats.get('total_trades', 0)} |",
        f"| Win Rate | {stats.get('win_rate', 0):.1f}% |",
        f"| Avg Return | {stats.get('avg_return_pct', 0):+.2f}% |",
        f"| Total P&L | ${stats.get('total_pnl', 0):+,.2f} |",
        f"| Final Equity | ${stats.get('final_equity', 0):,.2f} |",
        f"| Total Return | {stats.get('total_return_pct', 0):+.2f}% |",
        f"| Max Drawdown | {stats.get('max_drawdown_pct', 0):.2f}% |",
        f"| Sharpe Ratio | {stats.get('sharpe_ratio', 0):.2f} |",
        f"| Profit Factor | {stats.get('profit_factor', 0):.2f} |",
        f"| Avg Days Held | {stats.get('avg_days_held', 0):.1f} |",
        f"| Best Trade | {stats.get('best_trade', 0):+.2f}% |",
        f"| Worst Trade | {stats.get('worst_trade', 0):+.2f}% |",
        "",
        "## By Symbol",
        "| Symbol | Trades | Win Rate | Avg Return | Total P&L |",
        "|---|---|---|---|---|",
    ]

    by_sym = stats.get("by_symbol", {})
    for sym, data in sorted(by_sym.items(), key=lambda x: x[1].get("total_pnl", 0), reverse=True):
        lines.append(
            f"| {sym} | {data.get('trades', 0)} | {data.get('win_rate', 0):.1f}% | "
            f"{data.get('avg_return', 0):+.2f}% | ${data.get('total_pnl', 0):+,.2f} |"
        )

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Paper trading simulator for xiaomei tickets")
    parser.add_argument("--capital", type=float, default=DEFAULT_CAPITAL, help="Initial capital")
    parser.add_argument("--max-position-pct", type=float, default=DEFAULT_MAX_POSITION_PCT, help="Max position % of capital")
    parser.add_argument("--horizon", default=DEFAULT_HORIZON, choices=HORIZON_DAYS.keys(), help="Trading horizon")
    parser.add_argument("--stop-loss", type=float, default=DEFAULT_STOP_LOSS, help="Stop-loss threshold")
    parser.add_argument("--take-profit", type=float, default=DEFAULT_TAKE_PROFIT, help="Take-profit threshold")
    parser.add_argument("--start-date", default=None, help="Start date (YYYY-MM-DD)")
    parser.add_argument("--max-concurrent", type=int, default=5, help="Max concurrent positions")
    args = parser.parse_args()

    print(f"=== Paper Trading Simulation ===")
    print(f"Capital: ${args.capital:,.2f}, Horizon: {args.horizon}, Max Position: {args.max_position_pct*100:.0f}%")
    print()

    stats = run_simulation(
        capital=args.capital,
        max_position_pct=args.max_position_pct,
        horizon=args.horizon,
        stop_loss=args.stop_loss,
        take_profit=args.take_profit,
        start_date=args.start_date,
        max_concurrent=args.max_concurrent,
    )

    report = generate_report(stats)
    print(report)

    # Save report
    research_dir = Path(__file__).resolve().parent.parent / "research"
    research_dir.mkdir(parents=True, exist_ok=True)
    report_path = research_dir / f"paper-trading-{args.horizon}-{date.today().isoformat()}.md"
    report_path.write_text(report)
    print(f"\nReport saved: {report_path}")

    # Save JSON
    json_path = research_dir / f"paper-trading-{args.horizon}-{date.today().isoformat()}.json"
    json_stats = {k: v for k, v in stats.items() if k not in ("equity_curve", "trades")}
    json_path.write_text(json.dumps(json_stats, indent=2, default=str))
    print(f"Stats saved: {json_path}")


if __name__ == "__main__":
    main()
