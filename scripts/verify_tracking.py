#!/usr/bin/env python3
"""Tracking verification script — outputs structured tracking results.

Produces columns:
- entry_trading_date, tracking_due_trading_date, symbol, entry_price
- t+1_close_return, t+1_high_return, t+5_close_return, t+10_close_return, t+10_high_return
- max_high_return_in_window, hit_take_profit, hit_stop_loss, final_status

Uses US trading days for due_date calculation (not calendar days).
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import date, timedelta
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))

import pandas as pd
from data_provider import get_provider, is_trading_day, latest_us_trading_day

TAKE_PROFIT_PCT = 0.10  # +10%
STOP_LOSS_PCT = -0.05   # -5%


def fetch_kline_window(
    symbol: str, start: date, end: date
) -> list[dict[str, Any]]:
    """Fetch klines from DataProvider for the given window."""
    provider = get_provider()
    beg = start.strftime("%Y-%m-%d")
    ed = end.strftime("%Y-%m-%d")
    rows, _, _ = provider.fetch_klines(symbol, beg, ed)
    return rows or []


def compute_tracking_row(
    entry_date: date,
    entry_price: float,
    symbol: str,
    klines: list[dict[str, Any]],
    take_profit_pct: float = TAKE_PROFIT_PCT,
    stop_loss_pct: float = STOP_LOSS_PCT,
) -> dict[str, Any]:
    """Compute tracking metrics from kline data after entry."""
    # Build date-indexed klines
    by_date: dict[str, dict] = {}
    for row in klines:
        by_date[row["date"]] = row

    # Find entry index in the kline sequence
    sorted_dates = sorted(by_date.keys())
    entry_str = entry_date.strftime("%Y-%m-%d")
    try:
        entry_idx = sorted_dates.index(entry_str)
    except ValueError:
        # Entry date not in klines — find nearest
        for i, d in enumerate(sorted_dates):
            if d >= entry_str:
                entry_idx = i
                break
        else:
            entry_idx = len(sorted_dates) - 1

    # Collect returns at different horizons
    def get_close_return(horizon: int) -> float | None:
        target_idx = entry_idx + horizon
        if target_idx >= len(sorted_dates):
            return None
        target_date = sorted_dates[target_idx]
        target_close = float(by_date[target_date]["close"])
        return (target_close - entry_price) / entry_price

    def get_high_return(horizon: int) -> float | None:
        target_idx = entry_idx + horizon
        if target_idx >= len(sorted_dates):
            return None
        target_date = sorted_dates[target_idx]
        target_high = float(by_date[target_date].get("high", by_date[target_date]["close"]))
        return (target_high - entry_price) / entry_price

    def get_max_high_in_window(window: int) -> float | None:
        end_idx = min(entry_idx + window, len(sorted_dates))
        if entry_idx >= end_idx:
            return None
        max_high = 0.0
        for i in range(entry_idx + 1, end_idx):
            high = float(by_date[sorted_dates[i]].get("high", by_date[sorted_dates[i]]["close"]))
            if high > max_high:
                max_high = high
        if max_high == 0:
            return None
        return (max_high - entry_price) / entry_price

    t1_close = get_close_return(1)
    t1_high = get_high_return(1)
    t5_close = get_close_return(5)
    t10_close = get_close_return(10)
    t10_high = get_high_return(10)
    max_high = get_max_high_in_window(10)

    # Determine due_date (t+10 trading days from entry)
    due_date = None
    if entry_idx + 10 < len(sorted_dates):
        due_date = sorted_dates[entry_idx + 10]

    # Hit take-profit / stop-loss in window
    hit_tp = False
    hit_sl = False
    if max_high is not None and max_high >= take_profit_pct:
        hit_tp = True
    # Check low for stop-loss
    end_idx = min(entry_idx + 11, len(sorted_dates))
    for i in range(entry_idx + 1, end_idx):
        low = float(by_date[sorted_dates[i]].get("low", by_date[sorted_dates[i]]["close"]))
        ret = (low - entry_price) / entry_price
        if ret <= stop_loss_pct:
            hit_sl = True
            break

    # Final status
    if t10_close is None:
        final = "PENDING"
    elif t10_close >= take_profit_pct:
        final = "TP_HIT"
    elif hit_tp:
        final = "TP_HIT"
    elif hit_sl:
        final = "SL_HIT"
    elif t10_close > 0:
        final = "WIN"
    else:
        final = "LOSS"

    return {
        "entry_trading_date": entry_date.strftime("%Y-%m-%d"),
        "tracking_due_trading_date": due_date or "",
        "symbol": symbol,
        "entry_price": round(entry_price, 4),
        "t+1_close_return": round(t1_close, 6) if t1_close is not None else "",
        "t+1_high_return": round(t1_high, 6) if t1_high is not None else "",
        "t+5_close_return": round(t5_close, 6) if t5_close is not None else "",
        "t+10_close_return": round(t10_close, 6) if t10_close is not None else "",
        "t+10_high_return": round(t10_high, 6) if t10_high is not None else "",
        "max_high_return_in_window": round(max_high, 6) if max_high is not None else "",
        "hit_take_profit": hit_tp,
        "hit_stop_loss": hit_sl,
        "final_status": final,
    }


def verify_from_db(output_date: str | None = None) -> list[dict]:
    """Verify tracking from PostgreSQL forward_tracking table."""
    from scripts.db.engine import SessionLocal
    from sqlalchemy import text

    db = SessionLocal()
    try:
        where = "WHERE check_status = 'completed'"
        params: dict = {}
        if output_date:
            where += " AND output_date = :od"
            params["od"] = output_date

        rows = db.execute(text(
            f"SELECT ft.symbol, ft.as_of_date, ft.due_date, ft.as_of_close, "
            f"ft.due_close, ft.forward_return, ft.horizon_days, ft.track_key, "
            f"t.risk_stop_loss, t.risk_take_profit "
            f"FROM forward_tracking ft "
            f"LEFT JOIN tickets t ON ft.ticket_id = t.id "
            f"{where} ORDER BY ft.as_of_date, ft.symbol, ft.horizon_days"
        ), params).fetchall()

        results = []
        for row in rows:
            (symbol, as_of_date, due_date, as_of_close, due_close,
             forward_return, horizon_days, track_key,
             risk_stop_loss, risk_take_profit) = row

            entry_price = float(as_of_close) if as_of_close else 0
            close_ret = float(forward_return) if forward_return else None

            # Determine status from horizon and return
            tp = float(risk_take_profit) if risk_take_profit else TAKE_PROFIT_PCT
            sl = float(risk_stop_loss) if risk_stop_loss else STOP_LOSS_PCT

            final = "PENDING"
            if close_ret is not None:
                if close_ret >= tp:
                    final = "TP_HIT"
                elif close_ret <= sl:
                    final = "SL_HIT"
                elif close_ret > 0:
                    final = "WIN"
                else:
                    final = "LOSS"

            results.append({
                "entry_trading_date": str(as_of_date),
                "tracking_due_trading_date": str(due_date),
                "symbol": symbol,
                "entry_price": round(entry_price, 4),
                "horizon_days": horizon_days,
                "forward_return": round(close_ret, 6) if close_ret is not None else "",
                "final_status": final,
                "track_key": track_key,
            })

        return results
    finally:
        db.close()


def verify_from_csv(csv_path: str) -> list[dict]:
    """Verify tracking from a forward-tracking CSV file."""
    df = pd.read_csv(csv_path)
    results = []
    for _, row in df.iterrows():
        if row.get("check_status") != "completed":
            continue
        entry_price = float(row.get("as_of_adj_close") or row.get("as_of_close") or 0)
        fwd_ret = float(row["forward_return"]) if pd.notna(row.get("forward_return")) else None

        final = "PENDING"
        if fwd_ret is not None:
            if fwd_ret >= TAKE_PROFIT_PCT:
                final = "TP_HIT"
            elif fwd_ret <= STOP_LOSS_PCT:
                final = "SL_HIT"
            elif fwd_ret > 0:
                final = "WIN"
            else:
                final = "LOSS"

        results.append({
            "entry_trading_date": str(row.get("as_of_date", "")),
            "tracking_due_trading_date": str(row.get("due_date", "")),
            "symbol": row.get("symbol", ""),
            "entry_price": round(entry_price, 4),
            "horizon_days": int(row.get("horizon_days", 0)),
            "forward_return": round(fwd_ret, 6) if fwd_ret is not None else "",
            "final_status": final,
        })
    return results


def main():
    parser = argparse.ArgumentParser(description="Verify forward tracking results")
    parser.add_argument("--db", action="store_true", help="Read from PostgreSQL")
    parser.add_argument("--csv", help="Read from a CSV file")
    parser.add_argument("--output-date", help="Filter by output date (DB mode)")
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    parser.add_argument("--summary", action="store_true", help="Output summary only")
    args = parser.parse_args()

    if args.db:
        results = verify_from_db(args.output_date)
    elif args.csv:
        results = verify_from_csv(args.csv)
    else:
        print("Error: specify --db or --csv", file=sys.stderr)
        sys.exit(1)

    if args.summary:
        total = len(results)
        wins = sum(1 for r in results if r["final_status"] == "WIN")
        losses = sum(1 for r in results if r["final_status"] == "LOSS")
        tp = sum(1 for r in results if r["final_status"] == "TP_HIT")
        sl = sum(1 for r in results if r["final_status"] == "SL_HIT")
        pending = sum(1 for r in results if r["final_status"] == "PENDING")
        print(f"Total: {total} | WIN: {wins} | LOSS: {losses} | TP: {tp} | SL: {sl} | PENDING: {pending}")
        return

    if args.json:
        print(json.dumps(results, indent=2))
    else:
        # Tabular output
        if not results:
            print("No completed tracking rows found.")
            return
        headers = list(results[0].keys())
        print("\t".join(headers))
        for r in results:
            print("\t".join(str(r.get(h, "")) for h in headers))


if __name__ == "__main__":
    main()
