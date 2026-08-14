#!/usr/bin/env python3
"""Backfill forward tracking CSV files with today's close prices.

Uses DataProvider for kline data (multi-source with fallback).
"""

import argparse
import os
import subprocess
import sys
from datetime import datetime, date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import pandas as pd
from data_provider import get_provider, is_trading_day, latest_us_trading_day

_US_TRADING_DAY_CACHE: set[pd.Timestamp] | None = None


def normalize_us_symbol(symbol: str) -> str:
    """Convert US stock symbols to Yahoo Finance format."""
    return symbol.replace(".", "-")


def fetch_close_price_akshare(symbol: str, target_date: date) -> float | None:
    """Fetch closing price using akshare stock_us_daily."""
    try:
        import akshare as ak
        ticker = normalize_us_symbol(symbol)
        df = ak.stock_us_daily(symbol=ticker, adjust="qfq")
        if df is None or df.empty:
            return None

        df["date"] = pd.to_datetime(df["date"])
        df = df.set_index("date").sort_index()
        target_dt = pd.Timestamp(target_date)

        if target_dt in df.index:
            return float(df.loc[target_dt, "close"])

        closest_idx = df.index.get_indexer([target_dt], method="nearest")[0]
        if closest_idx >= 0 and closest_idx < len(df):
            return float(df["close"].iloc[closest_idx])
        return None
    except Exception as e:
        print(f"  akshare error for {symbol}: {e}")
        return None


def fetch_close_price_eastmoney_realtime(symbol: str) -> float | None:
    """Fallback: use EastMoney realtime quote for latest price."""
    try:
        from eastmoney_us import fetch_realtime_quotes
        quotes = fetch_realtime_quotes([symbol])
        if quotes and symbol in quotes:
            return float(quotes[symbol].get("latest_price"))
        return None
    except Exception:
        return None


def fetch_close_price(symbol: str, target_date: date) -> float | None:
    """Fetch closing price using DataProvider with fallback chain.

    For today's date, always prefer realtime quote.
    For historical dates, use klines from provider.
    """
    provider = get_provider()

    # If target_date is not a trading day, use the latest trading day before it
    if not is_trading_day(target_date):
        target_date = latest_us_trading_day(target_date)

    today = date.today()

    # For today, use realtime quote
    if target_date == today:
        quote, _, _ = provider.fetch_realtime_quote(symbol)
        if quote and quote.get("latest_price", 0) > 0:
            return float(quote["latest_price"])

    # For historical dates, use klines
    from datetime import timedelta
    beg = (target_date - timedelta(days=30)).strftime("%Y-%m-%d")
    end = target_date.strftime("%Y-%m-%d")
    rows, src, _ = provider.fetch_klines(symbol, beg, end)
    if rows:
        # Find exact date or closest
        for row in reversed(rows):
            if row["date"] <= target_date.strftime("%Y-%m-%d"):
                return float(row["close"])
        # If no earlier date, use first available
        return float(rows[0]["close"])

    # Fallback to realtime quote
    quote, _, _ = provider.fetch_realtime_quote(symbol)
    if quote and quote.get("latest_price", 0) > 0:
        return float(quote["latest_price"])

    return None


def backfill_csv_file(csv_path: Path, target_dates: list[date]) -> int:
    """Backfill pending rows in a CSV file for specified dates."""
    try:
        df = pd.read_csv(csv_path)
    except Exception as e:
        print(f"Error reading {csv_path}: {e}")
        return 0

    if 'check_status' not in df.columns or 'due_date' not in df.columns:
        return 0

    pending_mask = (df['check_status'] == 'pending') & (df['due_date'].isin([d.isoformat() for d in target_dates]))
    pending_rows = df[pending_mask]

    if pending_rows.empty:
        return 0

    updated_count = 0
    for idx, row in pending_rows.iterrows():
        symbol = row['symbol']
        due_date_str = row['due_date']
        due_date = date.fromisoformat(due_date_str)

        close_price = fetch_close_price(symbol, due_date)
        if close_price is None:
            print(f"  Skipping {symbol} for {due_date_str}: no price data")
            continue

        as_of_close = row.get('as_of_adj_close')
        if pd.isna(as_of_close) or as_of_close == '':
            as_of_close = row.get('as_of_close')
        if pd.isna(as_of_close) or as_of_close == '':
            print(f"  Skipping {symbol} for {due_date_str}: missing as_of_close")
            continue

        forward_return = (close_price - as_of_close) / as_of_close

        df.at[idx, 'due_close'] = close_price
        df.at[idx, 'due_adj_close'] = close_price
        df.at[idx, 'forward_return'] = forward_return
        df.at[idx, 'completed_at'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S CST')
        df.at[idx, 'check_status'] = 'completed'

        updated_count += 1
        print(f"  Updated {symbol} {due_date_str}: {close_price:.2f} (return: {forward_return:.4f})")

    if updated_count > 0:
        df.to_csv(csv_path, index=False)

    return updated_count


def rerun_lifecycle_scoreboard() -> None:
    script_path = Path(__file__).resolve().parent / 'lifecycle_scoreboard.py'
    try:
        result = subprocess.run(
            [sys.executable, str(script_path)],
            check=False,
            capture_output=True,
            text=True,
        )
        if result.returncode == 0:
            print("\nLifecycle scoreboard recomputed successfully.")
        else:
            print("\nLifecycle scoreboard recompute failed:")
            print(result.stderr or result.stdout)
    except Exception as exc:
        print(f"\nLifecycle scoreboard recompute exception: {exc}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Backfill pending forward tracking rows and recompute lifecycle scoreboard.")
    parser.add_argument("--anchor-date", default=None, help="Anchor date in YYYY-MM-DD; defaults to today.")
    parser.add_argument("--lookback-business-days", type=int, default=2, help="How many recent business days to backfill.")
    parser.add_argument("--db", action="store_true", help="Backfill from PostgreSQL database instead of CSV files.")
    return parser.parse_args()


def backfill_db(anchor_date: date, lookback_business_days: int) -> int:
    """Backfill forward tracking rows in PostgreSQL database."""
    from db.engine import SessionLocal
    from sqlalchemy import text

    db = SessionLocal()
    try:
        from db.crud import link_unlinked_forward_tracking

        linked = link_unlinked_forward_tracking(db)
        if linked:
            print(f"Linked {linked} legacy tracking rows to tickets")
        attributed = _backfill_completed_attribution(db)
        if attributed:
            print(f"Attributed {attributed} completed tracking rows")
        target_dates = infer_target_dates(anchor_date, lookback_business_days)
        print(f"DB backfill for dates: {target_dates}")

        pending = db.execute(text(
            "SELECT ft.id, ft.track_key, ft.symbol, ft.as_of_date, ft.horizon_days, "
            "ft.due_date, ft.as_of_close, "
            "t.narrative_title, t.risk_verdict, t.quality_verdict, t.panel_verdict, "
            "t.market_score, t.catalyst_score "
            "FROM forward_tracking ft "
            "LEFT JOIN tickets t ON ft.ticket_id = t.id "
            "WHERE ft.check_status = 'pending' AND ft.due_date <= :max_date"
        ), {"max_date": max(target_dates)}).fetchall()

        print(f"Found {len(pending)} pending rows")
        updated = 0
        for row in pending:
            (row_id, track_key, symbol, as_of_date, horizon_days, due_date, as_of_close,
             narrative_title, risk_verdict, quality_verdict, panel_verdict,
             market_score, catalyst_score) = row

            # Fetch as_of_close if missing
            if as_of_close is None:
                as_of_close = fetch_close_price(symbol, as_of_date)
                if as_of_close is None:
                    continue
                # Update as_of_close in DB
                db.execute(text(
                    "UPDATE forward_tracking SET as_of_close = :close WHERE id = :id"
                ), {"close": float(as_of_close), "id": row_id})

            price = fetch_close_price(symbol, due_date)
            if price is None:
                continue

            as_of = float(as_of_close)
            ret = (price - as_of) / as_of if as_of else 0

            # 生成盈亏理由
            outcome_classification = _return_classification(ret)
            outcome_reason = _generate_return_reason(
                symbol=symbol,
                horizon_days=horizon_days,
                forward_return=ret,
                as_of_close=as_of,
                due_close=price,
                narrative_title=narrative_title or "",
                risk_verdict=risk_verdict or "",
                quality_verdict=quality_verdict or "",
                panel_verdict=panel_verdict or "",
                market_score=float(market_score) if market_score else 0,
                catalyst_score=float(catalyst_score) if catalyst_score else 0,
            )
            outcome_reason = _analyze_loss_context(
                symbol=symbol,
                as_of_date=as_of_date,
                due_date=due_date,
                stock_return=ret,
                loss_reason=outcome_reason,
            )

            db.execute(text(
                "UPDATE forward_tracking SET due_close = :close, forward_return = :ret, "
                "check_status = 'completed', completed_at = NOW(), "
                "loss_reason = :reason, outcome_classification = :classification, "
                "outcome_reason = :reason WHERE id = :id"
            ), {
                "close": price,
                "ret": ret,
                "reason": outcome_reason,
                "classification": outcome_classification,
                "id": row_id,
            })
            updated += 1
            direction = "profit" if ret > 0 else "LOSS" if ret < 0 else "flat"
            print(f"  {symbol} {horizon_days}d: {as_of:.2f} -> {price:.2f} ({ret:+.4f}) [{direction}]")

        db.commit()
        print(f"\nDB rows updated: {updated}")
        return updated
    finally:
        db.close()


def _return_classification(forward_return: float) -> str:
    if forward_return >= 0.03:
        return "STRONG_WIN"
    if forward_return > 0:
        return "WIN"
    if forward_return <= -0.03:
        return "HEAVY_LOSS"
    if forward_return < 0:
        return "LOSS"
    return "FLAT"


def _backfill_completed_attribution(db) -> int:
    """Fill missing outcome explanations without fabricating missing tickets."""
    from sqlalchemy import text

    result = db.execute(text("""
        UPDATE forward_tracking ft
           SET outcome_classification = CASE
                   WHEN ft.forward_return >= 0.03 THEN 'STRONG_WIN'
                   WHEN ft.forward_return > 0 THEN 'WIN'
                   WHEN ft.forward_return <= -0.03 THEN 'HEAVY_LOSS'
                   WHEN ft.forward_return < 0 THEN 'LOSS'
                   ELSE 'FLAT'
               END,
               outcome_reason = COALESCE(
                   ft.outcome_reason,
                   ft.loss_reason,
                   CONCAT(
                       CASE
                           WHEN ft.forward_return >= 0.03 THEN 'STRONG_WIN'
                           WHEN ft.forward_return > 0 THEN 'WIN'
                           WHEN ft.forward_return <= -0.03 THEN 'HEAVY_LOSS'
                           WHEN ft.forward_return < 0 THEN 'LOSS'
                           ELSE 'FLAT'
                       END,
                       ' ',
                       ROUND((ft.forward_return * 100)::numeric, 2),
                       '% | thesis: ',
                       COALESCE(NULLIF(t.entry_reason, ''), 'unavailable')
                   )
               )
          FROM tickets t
         WHERE t.id = ft.ticket_id
           AND ft.check_status = 'completed'
           AND ft.forward_return IS NOT NULL
    """))
    db.commit()
    return int(result.rowcount or 0)


def _analyze_loss_context(
    symbol: str,
    as_of_date: date,
    due_date: date,
    stock_return: float,
    loss_reason: str,
) -> str:
    try:
        import akshare as ak
        ticker = normalize_us_symbol(symbol)
        df = ak.stock_us_daily(symbol=ticker, adjust="qfq")
        if df is None or df.empty:
            return loss_reason
        df["date"] = pd.to_datetime(df["date"]).dt.normalize()
        df = df.set_index("date").sort_index()

        due_ts = pd.Timestamp(due_date)
        idx = df.index.get_indexer([due_ts], method="nearest")[0]
        if idx < 0 or idx >= len(df):
            return loss_reason

        due_row = df.iloc[idx]
        gap_notes = []

        if idx > 0:
            prev_close = float(df.iloc[idx - 1]["close"])
            if prev_close > 0:
                gap_pct = (float(due_row["open"]) - prev_close) / prev_close
                if gap_pct < -0.02:
                    gap_notes.append(f"gap down {gap_pct*100:.1f}%")
                elif gap_pct > 0.03:
                    gap_notes.append(f"gap up {gap_pct*100:.1f}%")

        if idx > 0:
            avg_vol = float(df.iloc[max(0, idx-20):idx]["volume"].mean()) if idx >= 1 else 0
            cur_vol = float(due_row["volume"])
            if avg_vol > 0 and cur_vol / avg_vol > 2.0:
                gap_notes.append(f"vol spike {cur_vol/avg_vol:.1f}x")

        try:
            spy_df = ak.stock_us_daily(symbol="SPY", adjust="qfq")
            if spy_df is not None and not spy_df.empty:
                spy_df["date"] = pd.to_datetime(spy_df["date"]).dt.normalize()
                spy_df = spy_df.set_index("date").sort_index()
                as_of_ts = pd.Timestamp(as_of_date)
                spy_as_of = spy_df.index.get_indexer([as_of_ts], method="nearest")[0]
                spy_due = spy_df.index.get_indexer([due_ts], method="nearest")[0]
                if spy_as_of >= 0 and spy_due >= 0 and spy_as_of < len(spy_df) and spy_due < len(spy_df):
                    spy_open = float(spy_df.iloc[spy_as_of]["close"])
                    spy_close = float(spy_df.iloc[spy_due]["close"])
                    if spy_open > 0:
                        spy_ret = (spy_close - spy_open) / spy_open
                        if spy_ret < -0.01:
                            gap_notes.append(f"SPY down {spy_ret*100:.1f}%")
                        elif stock_return > 0 and spy_ret < 0:
                            gap_notes.append(f"outperformed SPY ({spy_ret*100:.1f}%)")
        except Exception:
            pass

        if gap_notes:
            loss_reason += " | context: " + ", ".join(gap_notes)
    except Exception:
        pass
    return loss_reason


def _generate_return_reason(
    symbol: str,
    horizon_days: int,
    forward_return: float,
    as_of_close: float,
    due_close: float,
    narrative_title: str,
    risk_verdict: str,
    quality_verdict: str,
    panel_verdict: str,
    market_score: float,
    catalyst_score: float,
) -> str:
    """Generate a human-readable reason for the forward return."""
    parts = []

    # 方向
    if forward_return > 0.03:
        parts.append(f"STRONG WIN +{forward_return*100:.1f}%")
    elif forward_return > 0:
        parts.append(f"WIN +{forward_return*100:.1f}%")
    elif forward_return > -0.03:
        parts.append(f"LOSS {forward_return*100:.1f}%")
    else:
        parts.append(f"HEAVY LOSS {forward_return*100:.1f}%")

    # 原始 thesis
    if narrative_title:
        parts.append(f"thesis: {narrative_title[:80]}")

    # 风险 vs 结果
    if risk_verdict == "CLEAN" and forward_return < 0:
        parts.append("risk=CLEAN but still lost — false signal")
    elif risk_verdict == "ELEVATED" and forward_return > 0:
        parts.append("risk=ELEVATED but still won — high-risk paid off")
    elif risk_verdict == "WATCH" and forward_return < 0:
        parts.append("risk=WATCH validated — caution was warranted")

    # panel vs 结果
    if panel_verdict == "BULLISH_CONSENSUS" and forward_return > 0:
        parts.append("panel BULLISH confirmed")
    elif panel_verdict == "BULLISH_CONSENSUS" and forward_return < 0:
        parts.append("panel BULLISH was wrong — re-examine consensus")
    elif panel_verdict == "BEARISH_CONSENSUS" and forward_return > 0:
        parts.append("panel BEARISH was wrong — contrarian won")

    # 催化剂 vs 结果
    if catalyst_score > 0.1 and forward_return > 0:
        parts.append("high catalyst score validated")
    elif catalyst_score > 0.1 and forward_return < 0:
        parts.append("high catalyst score failed — catalyst was noise")

    # 市场评分 vs 结果
    if market_score > 1.2 and forward_return > 0:
        parts.append("strong momentum continued")
    elif market_score > 1.2 and forward_return < 0:
        parts.append("strong momentum reversed")

    return " | ".join(parts)


def _load_us_trading_days() -> set[pd.Timestamp]:
    global _US_TRADING_DAY_CACHE
    if _US_TRADING_DAY_CACHE is not None:
        return _US_TRADING_DAY_CACHE
    try:
        import akshare as ak
        df = ak.stock_us_daily(symbol="SPY", adjust="qfq")
        if df is not None and not df.empty:
            df["date"] = pd.to_datetime(df["date"])
            _US_TRADING_DAY_CACHE = set(df["date"].dt.normalize())
            return _US_TRADING_DAY_CACHE
    except Exception:
        pass
    _US_TRADING_DAY_CACHE = set(pd.bdate_range(end=pd.Timestamp(date.today()), periods=90).normalize())
    return _US_TRADING_DAY_CACHE


def infer_target_dates(anchor_date: date, lookback_business_days: int) -> list[date]:
    trading_days = sorted(_load_us_trading_days())
    anchor_ts = pd.Timestamp(anchor_date).normalize()
    prior_days = [ts for ts in trading_days if ts <= anchor_ts]
    if not prior_days:
        return [anchor_date]
    selected = prior_days[-max(1, lookback_business_days):]
    result = [ts.date() for ts in selected]
    if anchor_date not in result:
        result.append(anchor_date)
    return result


def main():
    args = parse_args()
    anchor_date = date.fromisoformat(args.anchor_date) if args.anchor_date else date.today()
    target_dates = infer_target_dates(anchor_date, args.lookback_business_days)

    print(f"Backfilling forward tracking for dates: {target_dates}")

    if args.db:
        backfill_db(anchor_date, args.lookback_business_days)
    else:
        research_dir = Path('/root/hermes/company-ai-system/workspaces/xiaomei/research')
        csv_files = list(research_dir.glob('**/forward-tracking-*.csv'))

        total_updated = 0
        for csv_file in csv_files:
            print(f"\nProcessing {csv_file.name}...")
            updated = backfill_csv_file(csv_file, target_dates)
            total_updated += updated

        print(f"\nTotal rows updated: {total_updated}")

    rerun_lifecycle_scoreboard()

if __name__ == '__main__':
    main()
