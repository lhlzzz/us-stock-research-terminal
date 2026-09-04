#!/usr/bin/env python3
"""Backfill candidate factors into factor_snapshots table.

Computes RSI, MACD, BB, ATR, Stochastic, Williams %R, OBV, MFI, VWAP
for all symbols that have forward_tracking records, using historical kline data.
"""

from __future__ import annotations

import sys
import time
from datetime import date, timedelta
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))

from db.engine import SessionLocal
from db.models import FactorSnapshot
from sqlalchemy import text
from candidate_factors import (
    compute_rsi, compute_macd, compute_bollinger_bands,
    compute_atr, compute_stochastic, compute_williams_r,
    compute_obv, compute_mfi, compute_vwap_ratio,
)
from data_provider import get_provider


def get_kline_data(session, symbol: str, start_date: str, end_date: str) -> pd.DataFrame | None:
    """Fetch kline data from daily_klines table."""
    rows = session.execute(text("""
        SELECT trade_date, open, high, low, close, volume
        FROM daily_klines
        WHERE symbol = :sym AND trade_date >= :start AND trade_date <= :end
        ORDER BY trade_date
    """), {"sym": symbol, "start": start_date, "end": end_date}).fetchall()

    if not rows or len(rows) < 20:
        return None

    df = pd.DataFrame(rows, columns=["date", "open", "high", "low", "close", "volume"])
    df["date"] = pd.to_datetime(df["date"])
    df = df.set_index("date").sort_index()
    for col in ["open", "high", "low", "close"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    df["volume"] = pd.to_numeric(df["volume"], errors="coerce").fillna(0).astype(int)
    return df


def compute_all_factors(df: pd.DataFrame) -> dict | None:
    """Compute all factors for a single symbol's kline data."""
    if df is None or len(df) < 20:
        return None

    close = df["close"]
    high = df["high"]
    low = df["low"]
    volume = df["volume"]

    # Existing factors
    prior_5d = close.iloc[-1] / close.iloc[-5] - 1 if len(close) >= 5 else 0
    prior_20d = close.iloc[-1] / close.iloc[-20] - 1 if len(close) >= 20 else 0
    five_day_accel = prior_5d - prior_20d

    # Volume confirmation
    dollar_vol = close * volume
    avg_5d = dollar_vol.rolling(5, min_periods=5).mean()
    med_20d = dollar_vol.rolling(20, min_periods=20).median()
    vol_conf = float(avg_5d.iloc[-1] / med_20d.iloc[-1] - 1) if med_20d.iloc[-1] > 0 else 0

    # Closing strength
    daily_range = high - low
    closing_str = (close - low) / daily_range.replace(0, np.nan)
    closing_str_5d = float(closing_str.rolling(5, min_periods=5).mean().iloc[-1]) if len(closing_str) >= 5 else 0

    # Volume weighted momentum
    vol_5d = volume.rolling(5, min_periods=5).mean()
    vol_20d = volume.rolling(20, min_periods=20).mean()
    vol_trend = float(vol_5d.iloc[-1] / vol_20d.iloc[-1]) if vol_20d.iloc[-1] > 0 else 1
    vwm = prior_20d * vol_trend

    # Candidate factors
    rsi = compute_rsi(close)
    _, _, macd_hist = compute_macd(close)
    _, bb_mid, _ = compute_bollinger_bands(close)
    atr = compute_atr(high, low, close)
    k, d = compute_stochastic(high, low, close)
    williams = compute_williams_r(high, low, close)
    obv = compute_obv(close, volume)
    mfi = compute_mfi(high, low, close, volume)
    vwap_ratio = compute_vwap_ratio(close, volume)

    # OBV trend
    obv_sma5 = obv.rolling(5, min_periods=5).mean()
    obv_sma20 = obv.rolling(20, min_periods=20).mean()
    obv_trend = float(obv_sma5.iloc[-1] / obv_sma20.iloc[-1] - 1) if obv_sma20.iloc[-1] != 0 else 0

    # ATR as % of price
    atr_pct = float(atr.iloc[-1] / close.iloc[-1]) if close.iloc[-1] > 0 else 0

    # Momentum quality: consistency of returns
    returns = close.pct_change().dropna()
    if len(returns) >= 10:
        recent = returns.iloc[-10:]
        momentum_quality = float(recent.mean() / recent.std()) if recent.std() > 0 else 0
    else:
        momentum_quality = 0

    # Breakout score: close relative to 20d range
    if len(close) >= 20:
        high_20d = high.iloc[-20:].max()
        low_20d = low.iloc[-20:].min()
        rng = high_20d - low_20d
        breakout_score = float((close.iloc[-1] - low_20d) / rng) if rng > 0 else 0.5
    else:
        breakout_score = 0.5

    # Reversal quality: recent direction change strength
    if len(returns) >= 10:
        recent_5 = returns.iloc[-5:].mean()
        prior_5 = returns.iloc[-10:-5].mean()
        reversal_quality = float(recent_5 - prior_5)
    else:
        reversal_quality = 0

    def safe(val):
        if val is None or (isinstance(val, float) and np.isnan(val)):
            return None
        return round(float(val), 6)

    return {
        "prior_5d_momentum": safe(prior_5d),
        "prior_20d_momentum": safe(prior_20d),
        "five_day_acceleration": safe(five_day_accel),
        "volume_confirmation": safe(vol_conf),
        "closing_strength_5d": safe(closing_str_5d),
        "volume_weighted_momentum": safe(vwm),
        "rsi_14": safe(float(rsi.iloc[-1]) if not rsi.empty else None),
        "momentum_quality": safe(momentum_quality),
        "breakout_score": safe(breakout_score),
        "reversal_quality": safe(reversal_quality),
        # Additional candidate factors stored as JSON
        "macd_histogram": safe(float(macd_hist.iloc[-1]) if not macd_hist.empty else None),
        "atr_pct": safe(atr_pct),
        "stochastic_k": safe(float(k.iloc[-1]) if not k.empty else None),
        "williams_r": safe(float(williams.iloc[-1]) if not williams.empty else None),
        "obv_trend": safe(obv_trend),
        "mfi_14": safe(float(mfi.iloc[-1]) if not mfi.empty else None),
        "vwap_ratio": safe(float(vwap_ratio.iloc[-1]) if not vwap_ratio.empty else None),
    }


def backfill_candidate_factors(
    lookback_days: int = 90,
    batch_size: int = 20,
) -> dict:
    """Backfill candidate factors for all symbols with forward_tracking records."""
    session = SessionLocal()
    stats = {"processed": 0, "updated": 0, "skipped": 0, "errors": 0}

    try:
        # Get unique symbols from forward_tracking
        symbols = session.execute(text("""
            SELECT DISTINCT symbol FROM forward_tracking
            ORDER BY symbol
        """)).fetchall()
        symbols = [s[0] for s in symbols]
        print(f"Found {len(symbols)} symbols with forward_tracking records")

        # Get unique dates from tickets
        dates = session.execute(text("""
            SELECT DISTINCT output_date FROM tickets
            ORDER BY output_date
        """)).fetchall()
        dates = [d[0] for d in dates]
        print(f"Found {len(dates)} unique ticket dates")

        end_date = date.today()
        start_date = end_date - timedelta(days=lookback_days + 60)

        kline_cache: dict[str, pd.DataFrame] = {}
        provider = get_provider()
        print(f"Fetching kline data via DataProvider for {len(symbols)} symbols...")
        for i, sym in enumerate(symbols):
            if i % 50 == 0:
                print(f"  Fetching {i}/{len(symbols)}...")
            try:
                rows, _src, _meta = provider.fetch_klines(sym, str(start_date), str(end_date))
                if not rows:
                    continue
                df = pd.DataFrame(rows)
                if "date" not in df.columns:
                    continue
                df["date"] = pd.to_datetime(df["date"])
                df = df.set_index("date").sort_index()
                if len(df) >= 20:
                    kline_cache[sym] = df
            except Exception:
                continue
        print(f"  Cached kline data for {len(kline_cache)} symbols")

        # Process each symbol + date combination
        for sym in symbols:
            for trade_date in dates:
                stats["processed"] += 1

                # Check if already exists with candidate factors
                existing = session.execute(text("""
                    SELECT id, rsi_14, momentum_quality FROM factor_snapshots
                    WHERE symbol = :sym AND trade_date = :d
                """), {"sym": sym, "d": trade_date}).fetchone()

                if existing and existing[1] is not None and existing[2] is not None:
                    stats["skipped"] += 1
                    continue

                # Get kline data
                if sym in kline_cache:
                    kdf = kline_cache[sym]
                    td = pd.Timestamp(trade_date)
                    available = kdf.index[kdf.index <= td]
                    if len(available) < 20:
                        stats["skipped"] += 1
                        continue
                    df = kdf.loc[:td].tail(120)  # Last 120 days of data
                else:
                    # Try DB
                    kline_end = trade_date
                    kline_start = trade_date - timedelta(days=lookback_days + 60)
                    df = get_kline_data(session, sym, str(kline_start), str(kline_end))

                if df is None or len(df) < 20:
                    stats["skipped"] += 1
                    continue

                # Compute factors
                try:
                    factors = compute_all_factors(df)
                    if factors is None:
                        stats["skipped"] += 1
                        continue
                except Exception:
                    stats["errors"] += 1
                    continue

                # Upsert into factor_snapshots
                try:
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
                            "rsi": factors["rsi_14"],
                            "mq": factors["momentum_quality"],
                            "bs": factors["breakout_score"],
                            "rq": factors["reversal_quality"],
                            "vc": factors["volume_confirmation"],
                            "cs": factors["closing_strength_5d"],
                            "vwm": factors["volume_weighted_momentum"],
                            "p5": factors["prior_5d_momentum"],
                            "p20": factors["prior_20d_momentum"],
                            "fa": factors["five_day_acceleration"],
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
                            "d": trade_date, "sym": sym,
                            "p5": factors["prior_5d_momentum"],
                            "p20": factors["prior_20d_momentum"],
                            "fa": factors["five_day_acceleration"],
                            "vwm": factors["volume_weighted_momentum"],
                            "rsi": factors["rsi_14"],
                            "mq": factors["momentum_quality"],
                            "bs": factors["breakout_score"],
                            "rq": factors["reversal_quality"],
                            "vc": factors["volume_confirmation"],
                            "cs": factors["closing_strength_5d"],
                        })
                    stats["updated"] += 1
                except Exception as e:
                    stats["errors"] += 1
                    session.rollback()
                    continue

            # Commit per symbol
            session.commit()

        return stats

    finally:
        session.close()


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Backfill candidate factors")
    parser.add_argument("--lookback", type=int, default=90, help="Lookback days for kline data")
    args = parser.parse_args()

    result = backfill_candidate_factors(
        lookback_days=args.lookback,
    )
    print(f"\nResult: {result}")
