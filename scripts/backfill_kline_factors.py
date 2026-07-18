#!/usr/bin/env python3
"""Quick backfill: fetch kline for tracking symbols and compute candidate factors."""

from __future__ import annotations

import sys
import time
from datetime import date, timedelta
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))

from db.engine import SessionLocal
from sqlalchemy import text
from candidate_factors import (
    compute_rsi, compute_macd, compute_bollinger_bands,
    compute_atr, compute_stochastic, compute_williams_r,
    compute_obv, compute_mfi, compute_vwap_ratio,
)


def safe(val):
    if val is None or (isinstance(val, float) and np.isnan(val)):
        return None
    return round(float(val), 6)


def fetch_and_backfill():
    session = SessionLocal()
    try:
        # Get symbols with forward_tracking
        symbols = [r[0] for r in session.execute(
            text("SELECT DISTINCT symbol FROM forward_tracking ORDER BY symbol")
        ).fetchall()]
        print(f"Processing {len(symbols)} symbols")

        # Get ticket dates
        dates = [r[0] for r in session.execute(
            text("SELECT DISTINCT output_date FROM tickets ORDER BY output_date")
        ).fetchall()]
        print(f"Ticket dates: {dates}")

        import akshare as ak

        stats = {"symbols": 0, "factor_rows": 0, "errors": 0}

        for sym in symbols:
            print(f"  {sym}...", end=" ", flush=True)
            try:
                # Fetch kline via akshare
                df = ak.stock_us_daily(symbol=sym, adjust="qfq")
                if df is None or df.empty:
                    print("no data")
                    continue

                df = df.rename(columns={
                    "date": "date", "open": "open", "high": "high",
                    "low": "low", "close": "close", "volume": "volume"
                })
                df["date"] = pd.to_datetime(df["date"])
                df = df.set_index("date").sort_index()

                for col in ["open", "high", "low", "close"]:
                    df[col] = pd.to_numeric(df[col], errors="coerce")
                df["volume"] = pd.to_numeric(df["volume"], errors="coerce").fillna(0).astype(int)

                # Save to daily_klines
                for idx, row in df.iterrows():
                    try:
                        session.execute(text("""
                            INSERT INTO daily_klines (symbol, trade_date, open, high, low, close, volume, source)
                            VALUES (:sym, :d, :o, :h, :l, :c, :v, 'akshare')
                            ON CONFLICT (symbol, trade_date) DO NOTHING
                        """), {
                            "sym": sym, "d": idx.date(),
                            "o": float(row["open"]), "h": float(row["high"]),
                            "l": float(row["low"]), "c": float(row["close"]),
                            "v": int(row["volume"]),
                        })
                    except Exception:
                        pass

                # Compute factors for each ticket date
                for td in dates:
                    td_ts = pd.Timestamp(td)
                    available = df.index[df.index <= td_ts]
                    if len(available) < 20:
                        continue

                    kdf = df.loc[:td_ts].tail(120)
                    if len(kdf) < 20:
                        continue

                    close = kdf["close"]
                    high = kdf["high"]
                    low = kdf["low"]
                    vol = kdf["volume"]

                    # Basic factors
                    p5 = float(close.iloc[-1] / close.iloc[-5] - 1) if len(close) >= 5 else 0
                    p20 = float(close.iloc[-1] / close.iloc[-20] - 1) if len(close) >= 20 else 0
                    fa = p5 - p20

                    # Volume confirmation
                    dollar_vol = close * vol
                    avg5 = dollar_vol.rolling(5, min_periods=5).mean()
                    med20 = dollar_vol.rolling(20, min_periods=20).median()
                    vc = float(avg5.iloc[-1] / med20.iloc[-1] - 1) if med20.iloc[-1] > 0 else 0

                    # Closing strength
                    rng = high - low
                    cs = (close - low) / rng.replace(0, np.nan)
                    cs5 = float(cs.rolling(5, min_periods=5).mean().iloc[-1]) if len(cs) >= 5 else 0

                    # VWM
                    v5 = vol.rolling(5, min_periods=5).mean()
                    v20 = vol.rolling(20, min_periods=20).mean()
                    vt = float(v5.iloc[-1] / v20.iloc[-1]) if v20.iloc[-1] > 0 else 1
                    vwm = p20 * vt

                    # RSI
                    rsi = compute_rsi(close)
                    rsi_val = safe(float(rsi.iloc[-1])) if not rsi.empty else None

                    # Momentum quality
                    returns = close.pct_change().dropna()
                    if len(returns) >= 10:
                        r10 = returns.iloc[-10:]
                        mq = safe(float(r10.mean() / r10.std())) if r10.std() > 0 else 0
                    else:
                        mq = 0

                    # Breakout score
                    if len(close) >= 20:
                        h20 = high.iloc[-20:].max()
                        l20 = low.iloc[-20:].min()
                        rng20 = h20 - l20
                        bs = safe(float((close.iloc[-1] - l20) / rng20)) if rng20 > 0 else 0.5
                    else:
                        bs = 0.5

                    # Reversal quality
                    if len(returns) >= 10:
                        r5 = returns.iloc[-5:].mean()
                        p5r = returns.iloc[-10:-5].mean()
                        rq = safe(float(r5 - p5r))
                    else:
                        rq = 0

                    # Upsert
                    existing = session.execute(text("""
                        SELECT id FROM factor_snapshots
                        WHERE symbol = :sym AND trade_date = :d
                    """), {"sym": sym, "d": td}).fetchone()

                    if existing:
                        session.execute(text("""
                            UPDATE factor_snapshots SET
                                rsi_14 = COALESCE(:rsi, rsi_14),
                                momentum_quality = COALESCE(:mq, momentum_quality),
                                breakout_score = COALESCE(:bs, breakout_score),
                                reversal_quality = COALESCE(:rq, reversal_quality),
                                volume_confirmation = COALESCE(:vc, volume_confirmation),
                                closing_strength_5d = COALESCE(:cs, closing_strength_5d),
                                volume_weighted_momentum = COALESCE(:vwm, volume_weighted_momentum),
                                prior_5d_momentum = COALESCE(:p5, prior_5d_momentum),
                                prior_20d_momentum = COALESCE(:p20, prior_20d_momentum),
                                five_day_acceleration = COALESCE(:fa, five_day_acceleration)
                            WHERE id = :id
                        """), {
                            "id": existing[0],
                            "rsi": rsi_val, "mq": mq, "bs": bs, "rq": rq,
                            "vc": safe(vc), "cs": safe(cs5), "vwm": safe(vwm),
                            "p5": safe(p5), "p20": safe(p20), "fa": safe(fa),
                        })
                    else:
                        session.execute(text("""
                            INSERT INTO factor_snapshots
                            (trade_date, symbol, prior_5d_momentum, prior_20d_momentum,
                             five_day_acceleration, volume_weighted_momentum,
                             rsi_14, momentum_quality, breakout_score, reversal_quality,
                             volume_confirmation, closing_strength_5d)
                            VALUES (:d, :sym, :p5, :p20, :fa, :vwm,
                                    :rsi, :mq, :bs, :rq, :vc, :cs)
                        """), {
                            "d": td, "sym": sym,
                            "p5": safe(p5), "p20": safe(p20), "fa": safe(fa),
                            "vwm": safe(vwm), "rsi": rsi_val, "mq": mq,
                            "bs": bs, "rq": rq, "vc": safe(vc), "cs": safe(cs5),
                        })
                    stats["factor_rows"] += 1

                session.commit()
                stats["symbols"] += 1
                print(f"ok ({len(dates)} dates)")
                time.sleep(0.2)  # Rate limit

            except Exception as e:
                stats["errors"] += 1
                session.rollback()
                print(f"error: {e}")
                continue

        return stats

    finally:
        session.close()


if __name__ == "__main__":
    result = fetch_and_backfill()
    print(f"\nResult: {result}")
