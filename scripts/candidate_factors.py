#!/usr/bin/env python3
"""Candidate factors: additional technical indicators beyond the current pipeline.

Computes RSI, MACD, Bollinger Bands, ATR, MFI, OBV, Stochastic, Williams %R
for backtest comparison against existing factors.
"""

from __future__ import annotations

import numpy as np
import pandas as pd


def compute_rsi(close: pd.Series, period: int = 14) -> pd.Series:
    delta = close.diff()
    gain = delta.where(delta > 0, 0.0)
    loss = -delta.where(delta < 0, 0.0)
    avg_gain = gain.ewm(alpha=1 / period, min_periods=period).mean()
    avg_loss = loss.ewm(alpha=1 / period, min_periods=period).mean()
    rs = avg_gain / avg_loss.replace(0, np.nan)
    return 100 - (100 / (1 + rs))


def compute_macd(close: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9) -> tuple[pd.Series, pd.Series, pd.Series]:
    ema_fast = close.ewm(span=fast, min_periods=fast).mean()
    ema_slow = close.ewm(span=slow, min_periods=slow).mean()
    macd_line = ema_fast - ema_slow
    signal_line = macd_line.ewm(span=signal, min_periods=signal).mean()
    histogram = macd_line - signal_line
    return macd_line, signal_line, histogram


def compute_bollinger_bands(close: pd.Series, period: int = 20, std_dev: float = 2.0) -> tuple[pd.Series, pd.Series, pd.Series]:
    sma = close.rolling(period, min_periods=period).mean()
    std = close.rolling(period, min_periods=period).std()
    upper = sma + std_dev * std
    lower = sma - std_dev * std
    return upper, sma, lower


def compute_atr(high: pd.Series, low: pd.Series, close: pd.Series, period: int = 14) -> pd.Series:
    prev_close = close.shift(1)
    tr1 = high - low
    tr2 = (high - prev_close).abs()
    tr3 = (low - prev_close).abs()
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    return tr.ewm(alpha=1 / period, min_periods=period).mean()


def compute_stochastic(high: pd.Series, low: pd.Series, close: pd.Series, period: int = 14, smooth_k: int = 3) -> tuple[pd.Series, pd.Series]:
    lowest_low = low.rolling(period, min_periods=period).min()
    highest_high = high.rolling(period, min_periods=period).max()
    k = 100 * (close - lowest_low) / (highest_high - lowest_low).replace(0, np.nan)
    d = k.rolling(smooth_k, min_periods=smooth_k).mean()
    return k, d


def compute_williams_r(high: pd.Series, low: pd.Series, close: pd.Series, period: int = 14) -> pd.Series:
    highest_high = high.rolling(period, min_periods=period).max()
    lowest_low = low.rolling(period, min_periods=period).min()
    return -100 * (highest_high - close) / (highest_high - lowest_low).replace(0, np.nan)


def compute_obv(close: pd.Series, volume: pd.Series) -> pd.Series:
    direction = np.sign(close.diff())
    obv = (volume * direction).cumsum()
    return obv


def compute_mfi(high: pd.Series, low: pd.Series, close: pd.Series, volume: pd.Series, period: int = 14) -> pd.Series:
    typical_price = (high + low + close) / 3
    money_flow = typical_price * volume
    tp_diff = typical_price.diff()
    positive_flow = money_flow.where(tp_diff > 0, 0.0)
    negative_flow = money_flow.where(tp_diff < 0, 0.0)
    positive_sum = positive_flow.rolling(period, min_periods=period).sum()
    negative_sum = negative_flow.rolling(period, min_periods=period).sum()
    mfi = 100 - (100 / (1 + positive_sum / negative_sum.replace(0, np.nan)))
    return mfi


def compute_vwap_ratio(close: pd.Series, volume: pd.Series, period: int = 20) -> pd.Series:
    cum_vol = volume.rolling(period, min_periods=period).sum()
    cum_pv = (close * volume).rolling(period, min_periods=period).sum()
    vwap = cum_pv / cum_vol.replace(0, np.nan)
    return close / vwap - 1.0


def compute_candidate_features(
    close_panel: pd.DataFrame,
    long_panel: pd.DataFrame,
    symbols: list[str],
    as_of_date: pd.Timestamp,
) -> pd.DataFrame | None:
    """Compute candidate factor features for all symbols as of a given date."""
    price_basis = close_panel.loc[:as_of_date]
    if len(price_basis) < 30:
        return None

    available = [s for s in symbols if s in price_basis.columns]
    if len(available) < 10:
        return None

    high_panel = (
        long_panel.assign(date=pd.to_datetime(long_panel["date"]))
        .pivot(index="date", columns="symbol", values="High")
        .reindex(price_basis.index).sort_index().astype(float)
    )
    low_panel = (
        long_panel.assign(date=pd.to_datetime(long_panel["date"]))
        .pivot(index="date", columns="symbol", values="Low")
        .reindex(price_basis.index).sort_index().astype(float)
    )
    volume_panel = (
        long_panel.assign(date=pd.to_datetime(long_panel["date"]))
        .pivot(index="date", columns="symbol", values="Volume")
        .reindex(price_basis.index).sort_index().astype(float)
    )

    records = []
    for sym in available:
        close_s = price_basis[sym].dropna()
        high_s = high_panel[sym].dropna()
        low_s = low_panel[sym].dropna()
        vol_s = volume_panel[sym].dropna()

        if len(close_s) < 30:
            continue

        rsi = compute_rsi(close_s)
        _, _, macd_hist = compute_macd(close_s)
        upper, bb_mid, lower = compute_bollinger_bands(close_s)
        atr = compute_atr(high_s, low_s, close_s)
        k, d = compute_stochastic(high_s, low_s, close_s)
        williams = compute_williams_r(high_s, low_s, close_s)
        obv = compute_obv(close_s, vol_s)
        mfi = compute_mfi(high_s, low_s, close_s, vol_s)
        vwap_ratio = compute_vwap_ratio(close_s, vol_s)

        # BB position: (close - lower) / (upper - lower)
        bb_width = (upper - lower).replace(0, np.nan)
        bb_position = (close_s - lower) / bb_width

        # Normalized ATR (as % of price)
        atr_pct = atr / close_s

        # OBV trend: 5d vs 20d SMA of OBV
        obv_sma5 = obv.rolling(5, min_periods=5).mean()
        obv_sma20 = obv.rolling(20, min_periods=20).mean()
        obv_trend = (obv_sma5 / obv_sma20.replace(0, np.nan) - 1)

        records.append({
            "symbol": sym,
            "rsi_14": float(rsi.iloc[-1]) if not rsi.empty else np.nan,
            "macd_histogram": float(macd_hist.iloc[-1]) if not macd_hist.empty else np.nan,
            "bb_position": float(bb_position.iloc[-1]) if not bb_position.empty else np.nan,
            "atr_pct": float(atr_pct.iloc[-1]) if not atr_pct.empty else np.nan,
            "stochastic_k": float(k.iloc[-1]) if not k.empty else np.nan,
            "stochastic_d": float(d.iloc[-1]) if not d.empty else np.nan,
            "williams_r": float(williams.iloc[-1]) if not williams.empty else np.nan,
            "obv_trend": float(obv_trend.iloc[-1]) if not obv_trend.empty else np.nan,
            "mfi_14": float(mfi.iloc[-1]) if not mfi.empty else np.nan,
            "vwap_ratio": float(vwap_ratio.iloc[-1]) if not vwap_ratio.empty else np.nan,
        })

    if not records:
        return None

    df = pd.DataFrame(records).set_index("symbol")
    return df


CANDIDATE_FACTORS = [
    "rsi_14", "macd_histogram", "bb_position", "atr_pct",
    "stochastic_k", "stochastic_d", "williams_r",
    "obv_trend", "mfi_14", "vwap_ratio",
]

EXISTING_FACTORS = [
    "prior_5d_momentum", "prior_20d_momentum", "five_day_acceleration",
    "relative_strength_vs_equal_weight", "volume_confirmation_ratio",
    "closing_strength_5d", "volume_weighted_momentum",
]

ALL_FACTORS = EXISTING_FACTORS + CANDIDATE_FACTORS
