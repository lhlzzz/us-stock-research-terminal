#!/usr/bin/env python3
"""Dynamic horizon allocation based on stock volatility.

Problem: 1d/3d returns are negative (-1.93%/-0.83%) while 10d returns are positive (+11.93%).
Root cause: Same stop-loss/take-profit for all stocks regardless of volatility.
Solution: Assign horizon based on volatility - high vol → short horizon, low vol → long horizon.

Volatility calculation: ATR(14) / price (normalized ATR).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np
import pandas as pd


@dataclass
class HorizonAllocation:
    """Dynamic horizon allocation for a stock."""
    symbol: str
    atr_14d: float
    volatility_pct: float
    assigned_horizon: int
    stop_loss_pct: float
    take_profit_pct: float
    risk_reward_ratio: float
    vol_category: str  # high/medium/low


# Volatility thresholds (percentile-based)
HIGH_VOL_THRESHOLD = 0.03    # >3% daily ATR = high volatility
LOW_VOL_THRESHOLD = 0.015    # <1.5% daily ATR = low volatility

# Horizon allocation rules - Updated 2026-07-14
# Based on win rate analysis: 1d=48%, 3d=58%, 5d=58%, 10d=71%
HORIZON_RULES = {
    "high": {
        "horizon": 3,           # High vol → 3d (avoid 1d's 48% win rate)
        "stop_loss_pct": 0.02,  # Standard stop (2%)
        "take_profit_pct": 0.05, # Moderate profit (5%)
        "rr_ratio": 2.5,
    },
    "medium": {
        "horizon": 5,           # Medium vol → 5d (58% win rate, +0.95% avg)
        "stop_loss_pct": 0.025, # Standard stop (2.5%)
        "take_profit_pct": 0.08, # Moderate profit (8%)
        "rr_ratio": 3.2,
    },
    "low": {
        "horizon": 10,          # Low vol → 10d (71% win rate, +6.93% avg)
        "stop_loss_pct": 0.03,  # Wider stop (3%)
        "take_profit_pct": 0.12, # Let profits run (12%)
        "rr_ratio": 4.0,
    },
}


def calculate_atr_14d(
    high: pd.Series,
    low: pd.Series,
    close: pd.Series,
    period: int = 14,
) -> float:
    """Calculate 14-period Average True Range."""
    if len(high) < period + 1:
        return np.nan

    # True Range = max(high-low, abs(high-prev_close), abs(low-prev_close))
    prev_close = close.shift(1)
    tr1 = high - low
    tr2 = (high - prev_close).abs()
    tr3 = (low - prev_close).abs()
    true_range = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)

    # ATR = EMA of True Range
    atr = true_range.ewm(span=period, min_periods=period).mean().iloc[-1]
    return float(atr) if not np.isnan(atr) else np.nan


def calculate_volatility_pct(
    close_panel: pd.DataFrame,
    symbol: str,
    lookback: int = 14,
) -> float:
    """Calculate normalized volatility (ATR / price)."""
    if symbol not in close_panel.columns:
        return np.nan

    close = close_panel[symbol].dropna()
    if len(close) < lookback + 1:
        return np.nan

    # Use close prices to estimate ATR (simplified)
    # In production, use actual high/low data
    daily_returns = close.pct_change().dropna()
    volatility = daily_returns.tail(lookback).std()

    # Normalize by price (approximate ATR/p)
    current_price = close.iloc[-1]
    if current_price <= 0:
        return np.nan

    return float(volatility)


def assign_dynamic_horizon(
    symbol: str,
    volatility_pct: float,
    custom_thresholds: dict[str, float] | None = None,
) -> HorizonAllocation:
    """Assign horizon based on volatility category.

    Args:
        symbol: Stock ticker
        volatility_pct: Normalized volatility (ATR/p or daily return std)
        custom_thresholds: Optional custom thresholds for high/low vol

    Returns:
        HorizonAllocation with assigned horizon and risk parameters
    """
    high_thresh = custom_thresholds.get("high", HIGH_VOL_THRESHOLD) if custom_thresholds else HIGH_VOL_THRESHOLD
    low_thresh = custom_thresholds.get("low", LOW_VOL_THRESHOLD) if custom_thresholds else LOW_VOL_THRESHOLD

    if np.isnan(volatility_pct) or volatility_pct <= 0:
        # Default to medium if no data
        vol_category = "medium"
    elif volatility_pct > high_thresh:
        vol_category = "high"
    elif volatility_pct < low_thresh:
        vol_category = "low"
    else:
        vol_category = "medium"

    rules = HORIZON_RULES[vol_category]

    return HorizonAllocation(
        symbol=symbol,
        atr_14d=volatility_pct * 100,  # Convert to percentage for display
        volatility_pct=volatility_pct,
        assigned_horizon=rules["horizon"],
        stop_loss_pct=rules["stop_loss_pct"],
        take_profit_pct=rules["take_profit_pct"],
        risk_reward_ratio=rules["rr_ratio"],
        vol_category=vol_category,
    )


def batch_assign_horizons(
    close_panel: pd.DataFrame,
    symbols: list[str],
    custom_thresholds: dict[str, float] | None = None,
) -> dict[str, HorizonAllocation]:
    """Assign horizons for multiple symbols."""
    allocations = {}

    for symbol in symbols:
        vol_pct = calculate_volatility_pct(close_panel, symbol)
        alloc = assign_dynamic_horizon(symbol, vol_pct, custom_thresholds)
        allocations[symbol] = alloc

    return allocations


def get_horizon_stats(allocations: dict[str, HorizonAllocation]) -> dict[str, Any]:
    """Get statistics about horizon allocation."""
    horizons = [a.assigned_horizon for a in allocations.values()]
    categories = [a.vol_category for a in allocations.values()]

    return {
        "total_symbols": len(allocations),
        "horizon_distribution": {
            "1d": sum(1 for h in horizons if h == 1),
            "3d": sum(1 for h in horizons if h == 3),
            "5d": sum(1 for h in horizons if h == 5),
            "10d": sum(1 for h in horizons if h == 10),
        },
        "volatility_distribution": {
            "high": sum(1 for c in categories if c == "high"),
            "medium": sum(1 for c in categories if c == "medium"),
            "low": sum(1 for c in categories if c == "low"),
        },
        "avg_volatility": np.mean([a.volatility_pct for a in allocations.values()]),
        "median_volatility": np.median([a.volatility_pct for a in allocations.values()]),
    }


def format_allocation_report(allocations: dict[str, HorizonAllocation]) -> str:
    """Format allocation report for display."""
    stats = get_horizon_stats(allocations)

    lines = [
        "## Dynamic Horizon Allocation Report",
        "",
        f"**Total Symbols:** {stats['total_symbols']}",
        "",
        "### Horizon Distribution",
        f"- 1d (High Vol): {stats['horizon_distribution']['1d']}",
        f"- 3d (Medium Vol): {stats['horizon_distribution']['3d']}",
        f"- 5d: {stats['horizon_distribution']['5d']}",
        f"- 10d (Low Vol): {stats['horizon_distribution']['10d']}",
        "",
        "### Volatility Distribution",
        f"- High (>3%): {stats['volatility_distribution']['high']}",
        f"- Medium (1.5-3%): {stats['volatility_distribution']['medium']}",
        f"- Low (<1.5%): {stats['volatility_distribution']['low']}",
        "",
        f"**Avg Volatility:** {stats['avg_volatility']:.4f}",
        f"**Median Volatility:** {stats['median_volatility']:.4f}",
        "",
        "### Top 10 Allocations",
        "| Symbol | Vol% | Category | Horizon | Stop Loss | Take Profit | R:R |",
        "|--------|------|----------|---------|-----------|-------------|-----|",
    ]

    # Sort by volatility descending
    sorted_allocs = sorted(allocations.values(), key=lambda a: a.volatility_pct, reverse=True)[:10]

    for alloc in sorted_allocs:
        lines.append(
            f"| {alloc.symbol} | {alloc.volatility_pct:.4f} | {alloc.vol_category} | "
            f"{alloc.assigned_horizon}d | {alloc.stop_loss_pct:.1%} | {alloc.take_profit_pct:.1%} | "
            f"{alloc.risk_reward_ratio:.1f} |"
        )

    return "\n".join(lines)


# Integration helper for pipeline
def get_dynamic_tracking_horizons(
    close_panel: pd.DataFrame,
    symbols: list[str],
) -> dict[str, list[int]]:
    """Get tracking horizons for each symbol based on volatility.

    Returns dict mapping symbol to list of horizons to track.
    Primary horizon is the assigned one, plus standard horizons for comparison.
    """
    allocations = batch_assign_horizons(close_panel, symbols)

    result = {}
    for symbol, alloc in allocations.items():
        # Primary horizon based on volatility
        primary = alloc.assigned_horizon

        # Always track all horizons for comparison, but primary gets extra weight
        all_horizons = [1, 3, 5, 10]
        if primary not in all_horizons:
            all_horizons.append(primary)
            all_horizons.sort()

        result[symbol] = {
            "primary_horizon": primary,
            "all_horizons": all_horizons,
            "stop_loss_pct": alloc.stop_loss_pct,
            "take_profit_pct": alloc.take_profit_pct,
            "vol_category": alloc.vol_category,
            "volatility_pct": alloc.volatility_pct,
        }

    return result


if __name__ == "__main__":
    # Test with synthetic data
    import pandas as pd

    # Create synthetic close panel
    dates = pd.date_range("2026-01-01", periods=100, freq="B")
    symbols = ["AAPL", "TSLA", "MSFT", "NVDA", "AMZN"]

    # TSLA high vol, AAPL/MSFT low vol, NVDA/AMZN medium
    np.random.seed(42)
    data = {}
    for sym in symbols:
        if sym == "TSLA":
            data[sym] = 100 * np.exp(np.random.randn(100) * 0.03)  # High vol
        elif sym in ["AAPL", "MSFT"]:
            data[sym] = 100 * np.exp(np.random.randn(100) * 0.01)  # Low vol
        else:
            data[sym] = 100 * np.exp(np.random.randn(100) * 0.02)  # Medium vol

    close_panel = pd.DataFrame(data, index=dates)

    # Test allocation
    allocations = batch_assign_horizons(close_panel, symbols)
    report = format_allocation_report(allocations)
    print(report)
