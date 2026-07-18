#!/usr/bin/env python3
"""Factor analysis: evaluate each scoring dimension's predictive power over 300-day backtest."""

from __future__ import annotations

import json
import sys
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


RESEARCH_DIR = project_root() / "research"


def percentile_rank(series: pd.Series) -> pd.Series:
    return series.rank(pct=True, na_option="bottom")


def compute_daily_features(
    close_panel: pd.DataFrame,
    long_panel: pd.DataFrame,
    universe_symbols: list[str],
    as_of_date: pd.Timestamp,
) -> pd.DataFrame | None:
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

    feature_frame = pd.DataFrame(
        {
            "symbol": available,
            "close": price_basis.iloc[-1][available].values,
            "prior_5d_momentum": prior_5d.iloc[-1][available].values,
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


def run_factor_analysis(
    close_panel: pd.DataFrame,
    long_panel: pd.DataFrame,
    universe_symbols: list[str],
    backtest_days: int = 300,
) -> dict[str, Any]:
    available_dates = close_panel.index
    if len(available_dates) < backtest_days + 25:
        backtest_days = len(available_dates) - 25

    start_idx = 25
    end_idx = start_idx + backtest_days
    test_dates = available_dates[start_idx:end_idx]

    factors = [
        "prior_5d_momentum", "prior_20d_momentum", "five_day_acceleration",
        "relative_strength_vs_equal_weight", "volume_confirmation_ratio",
        "closing_strength_5d", "volume_weighted_momentum",
    ]

    all_records = []
    for i, as_of_date in enumerate(test_dates):
        if i % 50 == 0:
            print(f"  Day {i+1}/{len(test_dates)}: {as_of_date.strftime('%Y-%m-%d')}")

        feature_frame = compute_daily_features(close_panel, long_panel, universe_symbols, as_of_date)
        if feature_frame is None:
            continue

        date_idx = close_panel.index.get_loc(as_of_date)
        for horizon, h_days in [("1d", 1), ("3d", 3), ("5d", 5)]:
            future_idx = date_idx + h_days
            if future_idx >= len(close_panel):
                continue
            future_date = close_panel.index[future_idx]

            for symbol in feature_frame.index:
                if symbol not in close_panel.columns:
                    continue
                entry_price = close_panel.loc[as_of_date, symbol]
                exit_price = close_panel.loc[future_date, symbol]
                if pd.isna(entry_price) or pd.isna(exit_price) or entry_price <= 0:
                    continue
                forward_return = float(exit_price / entry_price - 1.0)

                record = {
                    "date": as_of_date.strftime("%Y-%m-%d"),
                    "symbol": symbol,
                    "horizon": horizon,
                    "forward_return": forward_return,
                }
                for f in factors:
                    val = feature_frame.loc[symbol, f] if symbol in feature_frame.index else np.nan
                    record[f] = float(val) if not pd.isna(val) else np.nan
                all_records.append(record)

    return {"records": all_records, "factors": factors}


def analyze_factors(records: list[dict], factors: list[str]) -> dict[str, Any]:
    if not records:
        return {"status": "NO_DATA"}

    df = pd.DataFrame(records)
    results = {}

    for horizon in ["1d", "3d", "5d"]:
        h_df = df[df["horizon"] == horizon].copy()
        if h_df.empty:
            continue

        horizon_results = {"factors": {}, "sample_size": len(h_df)}

        for factor in factors:
            valid = h_df.dropna(subset=[factor, "forward_return"])
            if len(valid) < 30:
                continue

            factor_values = valid[factor].values
            returns = valid["forward_return"].values

            ic = float(np.corrcoef(factor_values, returns)[0, 1]) if len(valid) > 5 else 0.0

            q25 = np.percentile(factor_values, 25)
            q75 = np.percentile(factor_values, 75)
            bottom = valid[valid[factor] <= q25]["forward_return"]
            top = valid[valid[factor] >= q75]["forward_return"]
            long_short = float(top.mean() - bottom.mean()) if len(bottom) > 5 and len(top) > 5 else 0.0

            quintiles = pd.qcut(valid[factor], 5, labels=False, duplicates="drop") if len(valid) >= 50 else None
            quintile_returns = {}
            if quintiles is not None:
                for q in range(5):
                    q_data = valid[quintiles == q]["forward_return"]
                    if len(q_data) > 0:
                        quintile_returns[f"Q{q+1}"] = {
                            "count": int(len(q_data)),
                            "avg_return": round(float(q_data.mean()), 6),
                            "win_rate": round(float((q_data > 0).mean()), 4),
                        }

            top_winners = valid.nlargest(10, "forward_return")[factor].mean()
            top_losers = valid.nsmallest(10, "forward_return")[factor].mean()

            horizon_results["factors"][factor] = {
                "ic": round(ic, 4),
                "abs_ic": round(abs(ic), 4),
                "long_short_return": round(long_short, 6),
                "bottom_avg_return": round(float(bottom.mean()), 6) if len(bottom) > 5 else 0.0,
                "top_avg_return": round(float(top.mean()), 6) if len(top) > 5 else 0.0,
                "quintile_returns": quintile_returns,
                "winner_avg_factor": round(float(top_winners), 4),
                "loser_avg_factor": round(float(top_losers), 4),
                "factor_std": round(float(valid[factor].std()), 4),
                "valid_count": int(len(valid)),
            }

        sorted_factors = sorted(
            horizon_results["factors"].items(),
            key=lambda x: abs(x[1]["ic"]),
            reverse=True,
        )
        horizon_results["factor_ranking"] = [f[0] for f in sorted_factors]
        horizon_results["ic_summary"] = {f[0]: f[1]["ic"] for f in sorted_factors}

        results[horizon] = horizon_results

    return results


def format_factor_report(analysis: dict) -> str:
    lines = [
        "# Factor Analysis Report (300-day Backtest)",
        f"- Generated: {__import__('datetime').datetime.now().strftime('%Y-%m-%d %H:%M')}",
        "",
    ]

    if analysis.get("status") == "NO_DATA":
        lines.append("- No data")
        return "\n".join(lines)

    for horizon in ["1d", "3d", "5d"]:
        h_data = analysis.get(horizon, {})
        if not h_data:
            continue

        lines.extend([
            f"## {horizon} Horizon (n={h_data['sample_size']})",
            "",
            "### IC (Information Coefficient) Ranking",
            "|rank|factor|IC|abs(IC)|long_short|bottom_Q1|top_Q5|",
            "|---|---|---|---|---|---|---|",
        ])

        for rank, factor in enumerate(h_data.get("factor_ranking", []), 1):
            fd = h_data["factors"][factor]
            ic_str = f"{fd['ic']:+.4f}"
            ls_str = f"{fd['long_short_return']:+.2%}"
            lines.append(
                f"|{rank}|{factor}|{ic_str}|{fd['abs_ic']:.4f}|{ls_str}|{fd['bottom_avg_return']:+.2%}|{fd['top_avg_return']:+.2%}|"
            )

        lines.extend(["", "### Quintile Analysis (Top Factor)"])
        top_factor = h_data["factor_ranking"][0] if h_data.get("factor_ranking") else None
        if top_factor and h_data["factors"][top_factor].get("quintile_returns"):
            lines.append(f"- Factor: {top_factor}")
            lines.append("|quintile|count|avg_return|win_rate|")
            lines.append("|---|---|---|---|")
            for q, qd in sorted(h_data["factors"][top_factor]["quintile_returns"].items()):
                lines.append(f"|{q}|{qd['count']}|{qd['avg_return']:+.2%}|{qd['win_rate']:.1%}|")

        lines.extend(["", "### Winner vs Loser Factor Values"])
        lines.append("|factor|winner_avg|loser_avg|gap|")
        lines.append("|---|---|---|---|")
        for factor in h_data.get("factor_ranking", []):
            fd = h_data["factors"][factor]
            gap = fd["winner_avg_factor"] - fd["loser_avg_factor"]
            lines.append(
                f"|{factor}|{fd['winner_avg_factor']:.4f}|{fd['loser_avg_factor']:.4f}|{gap:+.4f}|"
            )

        lines.append("")

    lines.extend([
        "## Summary",
        "",
        "### Factor Effectiveness by Horizon",
        "|factor|1d_IC|3d_IC|5d_IC|avg_abs_IC|verdict|",
        "|---|---|---|---|---|---|",
    ])

    all_factors = set()
    for h in ["1d", "3d", "5d"]:
        all_factors.update(analysis.get(h, {}).get("ic_summary", {}))

    for factor in sorted(all_factors):
        ic_1d = analysis.get("1d", {}).get("ic_summary", {}).get(factor, 0)
        ic_3d = analysis.get("3d", {}).get("ic_summary", {}).get(factor, 0)
        ic_5d = analysis.get("5d", {}).get("ic_summary", {}).get(factor, 0)
        avg_abs = (abs(ic_1d) + abs(ic_3d) + abs(ic_5d)) / 3
        if avg_abs > 0.05:
            verdict = "EFFECTIVE"
        elif avg_abs > 0.02:
            verdict = "MARGINAL"
        else:
            verdict = "INEFFECTIVE"
        lines.append(f"|{factor}|{ic_1d:+.4f}|{ic_3d:+.4f}|{ic_5d:+.4f}|{avg_abs:.4f}|{verdict}|")

    return "\n".join(lines)


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Factor analysis for xiaomei scoring")
    parser.add_argument("--days", type=int, default=300)
    parser.add_argument("--universe-source", default="nasdaq100_sp500_union")
    parser.add_argument("--sleep-seconds", type=float, default=0.3)
    args = parser.parse_args()

    print("Loading universe...")
    universe = load_universe_source(args.universe_source, explicit_universe=None)
    symbols = universe.get("universes", {}).get("union", {}).get("symbols", [])
    print(f"Universe: {len(symbols)} symbols")

    print("Fetching historical data...")
    results, _ = fetch_universe(period="1y", universe=symbols, sleep_seconds=args.sleep_seconds, batch_size=50)
    close_panel, adj_panel, long_panel = build_close_panel(results)
    included = [s for s in symbols if s in close_panel.columns]
    print(f"Included: {len(included)} symbols, {len(close_panel)} trading days")

    print(f"Running factor analysis: {args.days} days...")
    analysis_data = run_factor_analysis(close_panel, long_panel, included, args.days)
    print(f"Generated {len(analysis_data['records'])} records")

    analysis = analyze_factors(analysis_data["records"], analysis_data["factors"])
    report = format_factor_report(analysis)

    report_path = RESEARCH_DIR / "factor-analysis-report.md"
    report_path.write_text(report, encoding="utf-8")
    json_path = RESEARCH_DIR / "factor-analysis.json"
    json_path.write_text(json.dumps(analysis, indent=2, ensure_ascii=False), encoding="utf-8")

    print(f"\n{report}")
    print(f"\nReport: {report_path}")
    print(f"JSON: {json_path}")


if __name__ == "__main__":
    main()
