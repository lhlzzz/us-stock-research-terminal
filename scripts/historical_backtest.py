#!/usr/bin/env python3
"""Historical backtest for xiaomei scoring: simulate daily stock selection over 300 trading days.

For each day t:
1. Use only data available on day t (no lookahead)
2. Compute scoring dimensions (closing_strength, volume_weighted_momentum, etc.)
3. Select top-K stocks
4. Check t+1, t+3, t+5 returns
5. Compute aggregate statistics
"""

from __future__ import annotations

import json
import sys
import time
from collections import defaultdict
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))

from historical_replay_baseline import (
    build_close_panel,
    fetch_universe,
    load_universe_source,
    project_root,
)
from market_regime import classify_market_regime, get_regime_thresholds


DEFAULT_BACKTEST_DAYS = 300
DEFAULT_TOP_K = 1
DEFAULT_UNIVERSE_SOURCE = "nasdaq100_sp500_union"
DEFAULT_UNIVERSE_KEY = "union"
RESEARCH_DIR = project_root() / "research"


def percentile_rank(series: pd.Series) -> pd.Series:
    return series.rank(pct=True, na_option="bottom")


def compute_daily_features(
    close_panel: pd.DataFrame,
    long_panel: pd.DataFrame,
    universe_symbols: list[str],
    as_of_date: pd.Timestamp,
) -> pd.DataFrame | None:
    """Compute scoring features as of a specific date using only data up to that date."""
    price_basis = close_panel.loc[:as_of_date]
    if len(price_basis) < 25:
        return None

    available = [s for s in universe_symbols if s in price_basis.columns]
    if len(available) < 10:
        return None

    volume_panel = (
        long_panel.assign(date=pd.to_datetime(long_panel["date"]))
        .pivot(index="date", columns="symbol", values="Volume")
        .reindex(price_basis.index)
        .sort_index()
        .astype(float)
    )

    prior_5d = price_basis / price_basis.shift(5) - 1.0
    prior_20d = price_basis / price_basis.shift(20) - 1.0
    five_day_acceleration = prior_5d - prior_20d
    dollar_volume = price_basis * volume_panel
    avg_dollar_volume_5d = dollar_volume.rolling(5, min_periods=5).mean()
    median_dollar_volume_20d = dollar_volume.rolling(20, min_periods=20).median()
    volume_confirmation = avg_dollar_volume_5d / median_dollar_volume_20d - 1.0
    equal_weight_20d_benchmark = float(prior_20d.iloc[-1][available].dropna().mean())
    relative_strength = prior_20d.iloc[-1] - equal_weight_20d_benchmark

    daily_high = long_panel.assign(date=pd.to_datetime(long_panel["date"])).pivot(
        index="date", columns="symbol", values="High"
    ).reindex(price_basis.index).sort_index().astype(float)
    daily_low = long_panel.assign(date=pd.to_datetime(long_panel["date"])).pivot(
        index="date", columns="symbol", values="Low"
    ).reindex(price_basis.index).sort_index().astype(float)
    daily_range = daily_high - daily_low
    closing_strength = (price_basis - daily_low) / daily_range.replace(0, np.nan)
    closing_strength_5d = closing_strength.rolling(5, min_periods=5).mean()
    prior_5d_volume = volume_panel.rolling(5, min_periods=5).mean()
    prior_20d_volume = volume_panel.rolling(20, min_periods=20).mean()
    volume_trend = prior_5d_volume / prior_20d_volume.replace(0, np.nan)
    volume_weighted_momentum = prior_20d * volume_trend

    latest_date = price_basis.index[-1]
    feature_frame = pd.DataFrame(
        {
            "symbol": available,
            "close": price_basis.iloc[-1][available].values,
            "prior_20d_momentum": prior_20d.iloc[-1][available].values,
            "five_day_acceleration": five_day_acceleration.iloc[-1][available].values,
            "relative_strength_vs_equal_weight": relative_strength.reindex(available).values,
            "volume_confirmation_ratio": volume_confirmation.iloc[-1][available].values,
            "closing_strength_5d": closing_strength_5d.iloc[-1][available].values,
            "volume_weighted_momentum": volume_weighted_momentum.iloc[-1][available].values,
            "median_dollar_volume_20d": median_dollar_volume_20d.iloc[-1][available].values,
        }
    ).set_index("symbol")

    feature_frame = feature_frame.dropna(subset=["close", "prior_20d_momentum"])
    if len(feature_frame) < 10:
        return None

    return feature_frame


def score_and_select(
    feature_frame: pd.DataFrame,
    close_panel: pd.DataFrame,
    universe_symbols: list[str],
    top_k: int = 1,
) -> list[str]:
    """Score stocks and select top-K using the pipeline's scoring logic."""
    regime = classify_market_regime(close_panel, universe_symbols)
    regime_thresholds = get_regime_thresholds(regime.name)
    sw = regime_thresholds.scoring_weights

    percentile_features = {
        "prior_20d_momentum": percentile_rank(feature_frame["prior_20d_momentum"]),
        "five_day_acceleration": percentile_rank(feature_frame["five_day_acceleration"]),
        "volume_confirmation_ratio": percentile_rank(feature_frame["volume_confirmation_ratio"]),
        "relative_strength_vs_equal_weight": percentile_rank(feature_frame["relative_strength_vs_equal_weight"]),
        "closing_strength_5d": percentile_rank(feature_frame["closing_strength_5d"]),
        "volume_weighted_momentum": percentile_rank(feature_frame["volume_weighted_momentum"]),
    }

    raw_score = (
        sw.get("prior_20d_momentum", 0.10) * percentile_features["prior_20d_momentum"]
        + sw.get("five_day_acceleration", 0.15) * percentile_features["five_day_acceleration"]
        + sw.get("volume_confirmation_ratio", 0.30) * percentile_features["volume_confirmation_ratio"]
        + sw.get("relative_strength_vs_equal_weight", 0.15) * percentile_features["relative_strength_vs_equal_weight"]
        + sw.get("closing_strength_5d", 0.15) * percentile_features["closing_strength_5d"]
        + sw.get("volume_weighted_momentum", 0.15) * percentile_features["volume_weighted_momentum"]
    )

    risk_penalty = pd.Series(0.0, index=feature_frame.index)
    if regime.name in ("risk_on", "active"):
        risk_penalty = risk_penalty + np.where(
            (feature_frame["prior_20d_momentum"] > 0.15) & (feature_frame["closing_strength_5d"] < 0.45),
            0.08, 0.0,
        )
    risk_penalty = risk_penalty + np.where(
        feature_frame["five_day_acceleration"] < regime_thresholds.exhaustion_threshold * 1.5,
        0.06, 0.0,
    )
    risk_penalty = risk_penalty + np.where(
        feature_frame["volume_confirmation_ratio"] < 0.0, 0.04, 0.0,
    )
    risk_penalty = risk_penalty + np.where(
        feature_frame["closing_strength_5d"] < 0.35, 0.05, 0.0,
    )
    risk_penalty = risk_penalty + np.where(
        feature_frame["volume_weighted_momentum"] < 0, 0.03, 0.0,
    )

    final_score = raw_score - risk_penalty
    feature_frame = feature_frame.copy()
    feature_frame["final_score"] = final_score
    feature_frame = feature_frame.sort_values("final_score", ascending=False)

    return list(feature_frame.index[:top_k])


def run_backtest(
    close_panel: pd.DataFrame,
    long_panel: pd.DataFrame,
    universe_symbols: list[str],
    backtest_days: int = 300,
    top_k: int = 1,
) -> dict[str, Any]:
    """Run historical backtest over the last N trading days."""
    available_dates = close_panel.index
    if len(available_dates) < backtest_days + 25:
        backtest_days = len(available_dates) - 25

    start_idx = 25
    end_idx = start_idx + backtest_days
    test_dates = available_dates[start_idx:end_idx]

    results = []
    for i, as_of_date in enumerate(test_dates):
        if i % 50 == 0:
            print(f"  Backtest day {i+1}/{len(test_dates)}: {as_of_date.strftime('%Y-%m-%d')}")

        feature_frame = compute_daily_features(close_panel, long_panel, universe_symbols, as_of_date)
        if feature_frame is None:
            continue

        selected = score_and_select(feature_frame, close_panel, universe_symbols, top_k)
        if not selected:
            continue

        date_idx = close_panel.index.get_loc(as_of_date)
        for horizon, label in [(1, "1d"), (3, "3d"), (5, "5d")]:
            future_idx = date_idx + horizon
            if future_idx >= len(close_panel):
                continue
            future_date = close_panel.index[future_idx]

            for symbol in selected:
                if symbol not in close_panel.columns:
                    continue
                entry_price = close_panel.loc[as_of_date, symbol]
                exit_price = close_panel.loc[future_date, symbol]
                if pd.isna(entry_price) or pd.isna(exit_price) or entry_price <= 0:
                    continue
                forward_return = float(exit_price / entry_price - 1.0)
                results.append({
                    "date": as_of_date.strftime("%Y-%m-%d"),
                    "symbol": symbol,
                    "horizon": label,
                    "horizon_days": horizon,
                    "entry_price": float(entry_price),
                    "exit_price": float(exit_price),
                    "forward_return": forward_return,
                })

    return {"trades": results}


def compute_statistics(trades: list[dict]) -> dict[str, Any]:
    """Compute aggregate statistics from backtest trades."""
    if not trades:
        return {"status": "NO_DATA"}

    df = pd.DataFrame(trades)
    total = len(df)
    wins = (df["forward_return"] > 0).sum()
    losses = (df["forward_return"] <= 0).sum()

    stats = {
        "status": "OK",
        "total_trades": int(total),
        "wins": int(wins),
        "losses": int(losses),
        "win_rate": round(wins / total, 4) if total else 0,
        "avg_return": round(float(df["forward_return"].mean()), 6),
        "median_return": round(float(df["forward_return"].median()), 6),
        "avg_win": round(float(df[df["forward_return"] > 0]["forward_return"].mean()), 6) if wins else 0,
        "avg_loss": round(float(df[df["forward_return"] <= 0]["forward_return"].mean()), 6) if losses else 0,
        "profit_factor": 0.0,
        "max_win": round(float(df["forward_return"].max()), 6),
        "max_loss": round(float(df["forward_return"].min()), 6),
        "by_horizon": {},
        "by_symbol": {},
    }

    if stats["avg_loss"] != 0:
        stats["profit_factor"] = round(
            abs(stats["avg_win"] * wins / (stats["avg_loss"] * losses)) if losses else float("inf"), 4
        )

    for horizon in ["1d", "3d", "5d"]:
        h_df = df[df["horizon"] == horizon]
        if h_df.empty:
            continue
        h_wins = (h_df["forward_return"] > 0).sum()
        h_total = len(h_df)
        stats["by_horizon"][horizon] = {
            "count": int(h_total),
            "win_rate": round(h_wins / h_total, 4) if h_total else 0,
            "avg_return": round(float(h_df["forward_return"].mean()), 6),
            "median_return": round(float(h_df["forward_return"].median()), 6),
            "max_win": round(float(h_df["forward_return"].max()), 6),
            "max_loss": round(float(h_df["forward_return"].min()), 6),
        }

    for symbol in df["symbol"].unique():
        s_df = df[df["symbol"] == symbol]
        s_wins = (s_df["forward_return"] > 0).sum()
        s_total = len(s_df)
        stats["by_symbol"][symbol] = {
            "count": int(s_total),
            "win_rate": round(s_wins / s_total, 4) if s_total else 0,
            "avg_return": round(float(s_df["forward_return"].mean()), 6),
        }

    return stats


def format_report(stats: dict, trades: list[dict]) -> str:
    """Format backtest results as markdown report."""
    lines = [
        "# Historical Backtest Report",
        f"- Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
        f"- Status: {stats['status']}",
        "",
    ]

    if stats["status"] == "NO_DATA":
        lines.append("- No trades generated")
        return "\n".join(lines)

    lines.extend([
        "## Overall Performance",
        f"- Total trades: {stats['total_trades']}",
        f"- Win rate: {stats['win_rate']:.1%} ({stats['wins']}/{stats['total_trades']})",
        f"- Avg return: {stats['avg_return']:+.2%}",
        f"- Median return: {stats['median_return']:+.2%}",
        f"- Avg win: {stats['avg_win']:+.2%}",
        f"- Avg loss: {stats['avg_loss']:+.2%}",
        f"- Profit factor: {stats['profit_factor']:.2f}",
        f"- Max win: {stats['max_win']:+.2%}",
        f"- Max loss: {stats['max_loss']:+.2%}",
        "",
        "## By Horizon",
        "|horizon|count|win_rate|avg_return|max_win|max_loss|",
        "|---|---|---|---|---|---|",
    ])
    for h, data in sorted(stats["by_horizon"].items()):
        lines.append(
            f"|{h}|{data['count']}|{data['win_rate']:.1%}|{data['avg_return']:+.2%}|{data['max_win']:+.2%}|{data['max_loss']:+.2%}|"
        )

    lines.extend(["", "## By Symbol (top 15 by avg_return)", "|symbol|count|win_rate|avg_return|", "|---|---|---|---|"])
    sorted_symbols = sorted(stats["by_symbol"].items(), key=lambda x: x[1]["avg_return"], reverse=True)
    for sym, data in sorted_symbols[:15]:
        lines.append(f"|{sym}|{data['count']}|{data['win_rate']:.1%}|{data['avg_return']:+.2%}|")

    return "\n".join(lines)


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Historical backtest for xiaomei scoring")
    parser.add_argument("--days", type=int, default=DEFAULT_BACKTEST_DAYS)
    parser.add_argument("--top-k", type=int, default=DEFAULT_TOP_K)
    parser.add_argument("--universe-source", default=DEFAULT_UNIVERSE_SOURCE)
    parser.add_argument("--sleep-seconds", type=float, default=0.3)
    args = parser.parse_args()

    print(f"Loading universe: {args.universe_source}")
    universe = load_universe_source(args.universe_source, explicit_universe=None)
    symbols = universe.get("universes", {}).get("union", {}).get("symbols", [])
    if not symbols:
        symbols = universe.get("universes", {}).get(args.universe_source, {}).get("symbols", [])
    print(f"Universe: {len(symbols)} symbols")

    print("Fetching historical data...")
    results, failures = fetch_universe(
        period="1y",
        universe=symbols,
        sleep_seconds=args.sleep_seconds,
        batch_size=50,
    )
    close_panel, adj_panel, long_panel = build_close_panel(results)
    included = [s for s in symbols if s in close_panel.columns]
    print(f"Included: {len(included)} symbols, {len(close_panel)} trading days")

    print(f"Running backtest: {args.days} days, top-{args.top_k}")
    backtest_result = run_backtest(close_panel, long_panel, included, args.days, args.top_k)
    trades = backtest_result["trades"]
    print(f"Generated {len(trades)} trades")

    stats = compute_statistics(trades)
    report = format_report(stats, trades)

    report_path = RESEARCH_DIR / "historical-backtest-report.md"
    report_path.write_text(report, encoding="utf-8")
    json_path = RESEARCH_DIR / "historical-backtest-feedback.json"
    json_path.write_text(json.dumps(stats, indent=2, ensure_ascii=False), encoding="utf-8")
    trades_path = RESEARCH_DIR / "historical-backtest-trades.json"
    trades_path.write_text(json.dumps(trades, indent=2, ensure_ascii=False), encoding="utf-8")

    print(f"\n{report}")
    print(f"\nReport: {report_path}")
    print(f"JSON: {json_path}")
    print(f"Trades: {trades_path}")


if __name__ == "__main__":
    main()
