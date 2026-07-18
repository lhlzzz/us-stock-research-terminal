#!/usr/bin/env python3
from __future__ import annotations

import argparse
import io
import json
import sys
import time
import traceback
from collections import Counter
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import requests
from eastmoney_us import normalize_us_symbol, fetch_klines_period, klines_to_dataframe


DEFAULT_UNIVERSE = ["AAPL", "MSFT", "NVDA", "META", "AMZN", "TSLA"]
DEFAULT_PERIODS = ["1y", "6mo"]
DEFAULT_BATCH_SIZE = 50
DEFAULT_MIN_HISTORY_DAYS = 200
DEFAULT_MIN_PRICE = 5.0
DEFAULT_MIN_MEDIAN_DOLLAR_VOLUME = 5_000_000.0
PICK_METHODS = [
    "prior_5d_momentum",
    "prior_20d_momentum_only",
    "prior_20d_vol_adjusted_momentum",
    "simple_composite",
]
TOP1_METHODS = PICK_METHODS
FEATURE_ABLATION_METHODS = PICK_METHODS + ["equal_weight_reference"]
REFERENCE_METHOD = "equal_weight_reference"
ROLLING_WINDOW_LENGTHS = [60, 90, 120]
WIKIPEDIA_INDEX_SOURCES = {
    "nasdaq100": {
        "url": "https://en.wikipedia.org/wiki/Nasdaq-100",
        "symbol_columns": ("Ticker", "Symbol"),
    },
    "sp500": {
        "url": "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies",
        "symbol_columns": ("Symbol", "Ticker"),
    },
}
EASTMONEY_HISTORICAL_SOURCE_DISPLAY = "EastMoney US historical kline"
AKSHARE_HISTORICAL_SOURCE_DISPLAY = "EastMoney US historical kline (via akshare)"
COMBINED_MARKET_DATA_SOURCE_DISPLAY = f"{AKSHARE_HISTORICAL_SOURCE_DISPLAY} + EastMoney US realtime quote"


@dataclass
class SymbolFetchResult:
    symbol: str
    period: str
    rows: int
    adj_close_available: bool
    error: str | None
    frame: pd.DataFrame | None
    source: str = "unknown"


def repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


def project_root() -> Path:
    return repo_root() / "workspaces" / "xiaomei"


def output_date_string() -> str:
    return datetime.now().astimezone().date().isoformat()


def normalize_index(index: pd.Index) -> pd.DatetimeIndex:
    dt_index = pd.to_datetime(index)
    if getattr(dt_index, "tz", None) is not None:
        dt_index = dt_index.tz_convert(None)
    return pd.DatetimeIndex(dt_index).normalize()


def dedupe_preserve_order(symbols: list[str]) -> list[str]:
    return list(dict.fromkeys(symbols))


def chunked(items: list[str], chunk_size: int) -> list[list[str]]:
    return [items[index : index + chunk_size] for index in range(0, len(items), chunk_size)]


def load_wikipedia_constituents(source_name: str) -> dict[str, Any]:
    source = WIKIPEDIA_INDEX_SOURCES[source_name]
    response = requests.get(
        source["url"],
        headers={"User-Agent": "Mozilla/5.0"},
        timeout=30,
    )
    response.raise_for_status()
    tables = pd.read_html(io.StringIO(response.text))

    candidates: list[dict[str, Any]] = []
    for table_index, table in enumerate(tables):
        columns = [str(column) for column in table.columns]
        symbol_column = next((column for column in source["symbol_columns"] if column in columns), None)
        if symbol_column is None or len(table) < 50:
            continue

        raw_symbols = [
            normalize_us_symbol(value)
            for value in table[symbol_column].dropna().astype(str).tolist()
        ]
        symbols = [symbol for symbol in raw_symbols if symbol and symbol.lower() != "nan"]
        candidates.append(
            {
                "table_index": table_index,
                "row_count": int(len(table)),
                "symbol_column": symbol_column,
                "symbols": dedupe_preserve_order(symbols),
                "columns": columns,
            }
        )

    if not candidates:
        raise RuntimeError(f"unable to locate constituents table for {source_name}")

    chosen = max(candidates, key=lambda item: item["row_count"])
    return {
        "source_name": source_name,
        "source_url": source["url"],
        "table_index": chosen["table_index"],
        "row_count": chosen["row_count"],
        "symbol_column": chosen["symbol_column"],
        "symbols": chosen["symbols"],
        "candidate_tables": [
            {
                "table_index": item["table_index"],
                "row_count": item["row_count"],
                "symbol_column": item["symbol_column"],
            }
            for item in candidates
        ],
    }


def load_universe_source(source_name: str, explicit_universe: list[str] | None = None) -> dict[str, Any]:
    if source_name == "explicit":
        explicit_symbols = explicit_universe if explicit_universe is not None else DEFAULT_UNIVERSE
        return {
            "source_name": "explicit",
            "source_url": None,
            "universes": {
                "explicit": {
                    "symbols": dedupe_preserve_order([normalize_us_symbol(symbol) for symbol in explicit_symbols]),
                    "raw_count": len(explicit_symbols),
                }
            },
        }

    if source_name == "nasdaq100":
        constituents = load_wikipedia_constituents("nasdaq100")
        return {
            "source_name": "nasdaq100",
            "source_url": constituents["source_url"],
            "universes": {
                "nasdaq100": {
                    "symbols": constituents["symbols"],
                    "raw_count": constituents["row_count"],
                    "table_index": constituents["table_index"],
                    "symbol_column": constituents["symbol_column"],
                    "candidate_tables": constituents["candidate_tables"],
                }
            },
        }

    if source_name == "sp500":
        constituents = load_wikipedia_constituents("sp500")
        return {
            "source_name": "sp500",
            "source_url": constituents["source_url"],
            "universes": {
                "sp500": {
                    "symbols": constituents["symbols"],
                    "raw_count": constituents["row_count"],
                    "table_index": constituents["table_index"],
                    "symbol_column": constituents["symbol_column"],
                    "candidate_tables": constituents["candidate_tables"],
                }
            },
        }

    if source_name == "nasdaq100_sp500_union":
        nasdaq100 = load_wikipedia_constituents("nasdaq100")
        sp500 = load_wikipedia_constituents("sp500")
        combined = dedupe_preserve_order(nasdaq100["symbols"] + sp500["symbols"])
        return {
            "source_name": "nasdaq100_sp500_union",
            "source_url": {
                "nasdaq100": nasdaq100["source_url"],
                "sp500": sp500["source_url"],
            },
            "universes": {
                "nasdaq100": {
                    "symbols": nasdaq100["symbols"],
                    "raw_count": nasdaq100["row_count"],
                    "table_index": nasdaq100["table_index"],
                    "symbol_column": nasdaq100["symbol_column"],
                    "candidate_tables": nasdaq100["candidate_tables"],
                },
                "sp500": {
                    "symbols": sp500["symbols"],
                    "raw_count": sp500["row_count"],
                    "table_index": sp500["table_index"],
                    "symbol_column": sp500["symbol_column"],
                    "candidate_tables": sp500["candidate_tables"],
                },
                "union": {
                    "symbols": combined,
                    "raw_count": len(combined),
                    "overlap_count": len(set(nasdaq100["symbols"]) & set(sp500["symbols"])),
                },
            },
        }

    raise ValueError(f"unknown universe source: {source_name}")


def _fetch_akshare_us_kline(normalized: str, period: str) -> SymbolFetchResult | None:
    """Fetch US stock daily klines via DataProvider (multi-source with fallback)."""
    try:
        from data_provider import get_provider

        provider = get_provider()
        period_days = {"1y": 365, "6mo": 182, "3mo": 90, "2y": 730}.get(period, 365)
        beg = (pd.Timestamp.now() - pd.Timedelta(days=period_days)).strftime("%Y-%m-%d")
        end = pd.Timestamp.now().strftime("%Y-%m-%d")

        df, src = provider.fetch_klines_to_dataframe(normalized, beg, end)
        if df is None or df.empty:
            return None

        source_display = f"DataProvider ({src})"
        return frame_to_symbol_fetch_result(normalized, period, df, source=source_display)
    except Exception:  # noqa: BLE001
        return None


def history_frame(symbol: str, period: str) -> SymbolFetchResult:
    normalized = normalize_us_symbol(symbol)

    akshare_result = _fetch_akshare_us_kline(normalized, period)
    if akshare_result is not None and akshare_result.rows > 0:
        return akshare_result

    try:
        rows = fetch_klines_period(normalized, period, retries=2)
        if rows:
            df = klines_to_dataframe(normalized, rows)
            if df is not None and not df.empty:
                return frame_to_symbol_fetch_result(normalized, period, df, source=EASTMONEY_HISTORICAL_SOURCE_DISPLAY)
        error = "EastMoney kline returned empty data for US stock"
    except Exception as exc:  # noqa: BLE001
        error = f"EastMoney kline {exc.__class__.__name__}: {exc}"

    return SymbolFetchResult(
        symbol=normalized, period=period, rows=0, adj_close_available=False,
        error=error, frame=None, source="unavailable",
    )


def frame_to_symbol_fetch_result(
    symbol: str,
    period: str,
    df: pd.DataFrame | None,
    source: str = EASTMONEY_HISTORICAL_SOURCE_DISPLAY,
) -> SymbolFetchResult:
    if df is None or df.empty:
        return SymbolFetchResult(
            symbol=symbol,
            period=period,
            rows=0,
            adj_close_available=False,
            error="empty dataframe",
            frame=None,
            source=source,
        )

    df = df.copy()
    df.index = normalize_index(df.index)
    df.index.name = "date"

    required_columns = [
        "Open",
        "High",
        "Low",
        "Close",
        "Adj Close",
        "Volume",
        "Dividends",
        "Stock Splits",
    ]
    for column in required_columns:
        if column not in df.columns:
            df[column] = np.nan

    df = df[required_columns]
    df["symbol"] = symbol
    df["date"] = df.index.strftime("%Y-%m-%d")

    adj_close_available = bool(df["Adj Close"].notna().any())
    return SymbolFetchResult(
        symbol=symbol,
        period=period,
        rows=int(len(df)),
        adj_close_available=adj_close_available,
        error=None,
        frame=df,
        source=source,
    )


def download_history_batch(symbols: list[str], period: str) -> dict[str, tuple[pd.DataFrame, str]]:
    """Download history batch returning (frame, source) tuples."""
    frames: dict[str, tuple[pd.DataFrame, str]] = {}
    from concurrent.futures import ThreadPoolExecutor, as_completed
    max_workers = min(16, max(1, len(symbols)))
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {}
        for symbol in symbols:
            normalized = normalize_us_symbol(symbol)
            futures[executor.submit(history_frame, normalized, period)] = normalized
        for future in as_completed(futures):
            normalized = futures[future]
            try:
                result = future.result()
                if result.frame is not None and not result.frame.empty:
                    frames[normalized] = (result.frame.copy(), result.source)
            except Exception:
                pass
    return frames


def fetch_universe(
    period: str,
    universe: list[str],
    sleep_seconds: float = 0.5,
    batch_size: int = DEFAULT_BATCH_SIZE,
) -> tuple[dict[str, SymbolFetchResult], list[dict[str, str]]]:
    results: dict[str, SymbolFetchResult] = {}
    failures: list[dict[str, str]] = []

    for batch in chunked(universe, max(1, batch_size)):
        batch_frames = download_history_batch(batch, period)
        for symbol in batch:
            batch_result = batch_frames.get(symbol)
            if batch_result is None:
                result = history_frame(symbol, period)
            else:
                frame, source = batch_result
                result = frame_to_symbol_fetch_result(symbol, period, frame, source=source)

            results[symbol] = result
            if result.error:
                failures.append(
                    {
                        "period": period,
                        "symbol": symbol,
                        "error": result.error,
                    }
                )

        time.sleep(sleep_seconds)
    return results, failures


def evaluate_symbol_quality(
    result: SymbolFetchResult,
    min_history_days: int,
    min_price: float,
    min_median_dollar_volume: float,
) -> dict[str, Any]:
    frame = result.frame
    if frame is None or frame.empty:
        return {
            "include": False,
            "reasons": ["empty_frame"],
            "history_days": 0,
            "last_close": None,
            "median_dollar_volume": None,
        }

    frame = frame.sort_index()
    close = pd.to_numeric(frame["Close"], errors="coerce")
    volume = pd.to_numeric(frame["Volume"], errors="coerce")
    dollar_volume = close * volume
    last_close = None if close.dropna().empty else float(close.dropna().iloc[-1])
    median_dollar_volume = None if dollar_volume.dropna().empty else float(dollar_volume.dropna().median())

    reasons = []
    if result.rows < min_history_days:
        reasons.append(f"history_days<{min_history_days}")
    if not result.adj_close_available:
        reasons.append("adj_close_missing")
    if last_close is None or last_close < min_price:
        reasons.append(f"price_floor<{min_price}")
    if median_dollar_volume is None or median_dollar_volume < min_median_dollar_volume:
        reasons.append(f"median_dollar_volume<{min_median_dollar_volume}")

    return {
        "include": not reasons,
        "reasons": reasons,
        "history_days": int(result.rows),
        "last_close": last_close,
        "median_dollar_volume": median_dollar_volume,
        "adj_close_available": bool(result.adj_close_available),
    }


def build_close_panel(results: dict[str, SymbolFetchResult]) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    close_frames = []
    adj_frames = []
    long_frames = []

    for symbol, result in results.items():
        if result.frame is None:
            continue
        frame = result.frame.copy().reset_index(drop=True)
        frame["date"] = pd.to_datetime(frame["date"])
        frame = frame.sort_values("date")

        close_frames.append(frame.set_index("date")["Close"].rename(symbol))
        adj_frames.append(frame.set_index("date")["Adj Close"].rename(symbol))
        long_frames.append(frame.reset_index(drop=True))

    if not close_frames:
        return pd.DataFrame(), pd.DataFrame(), pd.DataFrame()

    close_panel = pd.concat(close_frames, axis=1).sort_index()
    adj_panel = pd.concat(adj_frames, axis=1).sort_index()
    long_panel = pd.concat(long_frames, ignore_index=True).sort_values(["date", "symbol"]).reset_index(drop=True)
    long_panel["date"] = pd.to_datetime(long_panel["date"]).dt.strftime("%Y-%m-%d")
    return close_panel, adj_panel, long_panel


def select_basket(row: pd.Series, selection_size: int, higher_is_better: bool = True) -> tuple[list[str], list[float]]:
    valid = row.dropna()
    if valid.empty:
        raise ValueError("no valid scores")

    ordered = valid.sort_values(ascending=not higher_is_better, kind="mergesort")
    if len(ordered) < selection_size:
        raise ValueError("not enough valid scores")

    selected = ordered.head(selection_size)
    return [str(symbol) for symbol in selected.index], [float(value) for value in selected.values]


def pick_best(row: pd.Series, higher_is_better: bool = True) -> str:
    selected_symbols, _ = select_basket(row, 1, higher_is_better=higher_is_better)
    return selected_symbols[0]


def rough_max_drawdown(returns: pd.Series) -> float:
    if returns.empty:
        return float("nan")
    equity = (1.0 + returns.fillna(0.0)).cumprod()
    peak = equity.cummax()
    drawdown = equity / peak - 1.0
    return float(drawdown.min())


def build_ranked_metrics_frame(method_metrics: dict[str, dict[str, Any]], method_order: list[str]) -> pd.DataFrame:
    frame = pd.DataFrame(
        {
            method: {
                "average_forward_return": method_metrics[method]["average_forward_return"],
                "median_forward_return": method_metrics[method]["median_forward_return"],
                "win_rate": method_metrics[method]["win_rate"],
                "trade_days": method_metrics[method]["trade_days"],
            }
            for method in method_order
        }
    ).T
    frame["_sort_key"] = pd.to_numeric(frame["average_forward_return"], errors="coerce")
    return frame.sort_values("_sort_key", ascending=False, kind="mergesort").drop(columns="_sort_key")


def subset_records_by_dates(records: pd.DataFrame, dates: list[str]) -> pd.DataFrame:
    if records.empty:
        return records.copy()
    return records[records["date"].isin(dates)].copy()


def metric_pack(
    method: str,
    records: pd.DataFrame,
    universe: list[str],
    reference_mode: bool = False,
    reference_symbol_records: pd.DataFrame | None = None,
) -> dict[str, Any]:
    selection_size = 1
    if not records.empty and "selection_size" in records.columns:
        selection_size = int(records["selection_size"].iloc[0])

    if records.empty:
        return {
            "method": method,
            "trade_days": 0,
            "first_trade_date": None,
            "last_trade_date": None,
            "average_forward_return": None,
            "median_forward_return": None,
            "win_rate": None,
            "max_drawdown_rough": None,
            "selected_counts": {},
            "per_symbol_average_forward_return": {},
            "selection_mode": "equal_weight_reference" if reference_mode else f"top{selection_size}",
        }

    if reference_mode:
        if reference_symbol_records is None:
            raise ValueError("reference_symbol_records is required for reference_mode")
        forward_returns = records["forward_return"].astype(float)
        selected_counts = (
            reference_symbol_records.groupby("symbol").size().reindex(universe, fill_value=0).astype(int).to_dict()
        )
        per_symbol = (
            reference_symbol_records.groupby("symbol")["symbol_forward_return"].mean().reindex(universe).to_dict()
        )
    else:
        forward_returns = records["forward_return"].astype(float)
        if "selected_symbols" in records.columns:
            exploded = records[["selected_symbols", "selected_symbol_forward_returns"]].explode(
                ["selected_symbols", "selected_symbol_forward_returns"]
            )
            selected_counts = (
                exploded["selected_symbols"].value_counts().reindex(universe, fill_value=0).astype(int).to_dict()
            )
            per_symbol = (
                exploded.groupby("selected_symbols")["selected_symbol_forward_returns"].mean().reindex(universe).to_dict()
            )
        else:
            selected_counts = (
                records["selected_symbol"].value_counts().reindex(universe, fill_value=0).astype(int).to_dict()
            )
            per_symbol = (
                records.groupby("selected_symbol")["forward_return"].mean().reindex(universe).to_dict()
            )

    return {
        "method": method,
        "trade_days": int(records["date"].nunique()) if reference_mode else int(len(records)),
        "first_trade_date": str(records["date"].iloc[0]),
        "last_trade_date": str(records["date"].iloc[-1]),
        "average_forward_return": float(forward_returns.mean()),
        "median_forward_return": float(forward_returns.median()),
        "win_rate": float((forward_returns > 0).mean()),
        "max_drawdown_rough": rough_max_drawdown(forward_returns),
        "selected_counts": selected_counts,
        "per_symbol_average_forward_return": {
            symbol: None if pd.isna(value) else float(value) for symbol, value in per_symbol.items()
        },
        "selection_mode": "equal_weight_reference" if reference_mode else f"top{selection_size}",
    }


def serializable(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): serializable(item) for key, item in value.items()}
    if isinstance(value, list):
        return [serializable(item) for item in value]
    if isinstance(value, tuple):
        return [serializable(item) for item in value]
    if isinstance(value, (np.integer,)):
        return int(value)
    if isinstance(value, (np.floating,)):
        return float(value)
    if isinstance(value, (pd.Timestamp,)):
        return value.strftime("%Y-%m-%d")
    if isinstance(value, np.bool_):
        return bool(value)
    if pd.isna(value):
        return None
    return value


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(serializable(payload), indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def write_csv(path: Path, frame: pd.DataFrame) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(path, index=False)


def build_method_records(
    method: str,
    dates: pd.DatetimeIndex,
    close_panel: pd.DataFrame,
    next_close_panel: pd.DataFrame,
    signal_frame: pd.DataFrame,
    selection_size: int = 1,
    secondary_frame: pd.DataFrame | None = None,
    tertiary_frame: pd.DataFrame | None = None,
    descending: bool = True,
) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for date in dates:
        signal_row = signal_frame.loc[date]
        selected_symbols, selected_signal_values = select_basket(
            signal_row,
            selection_size=selection_size,
            higher_is_better=descending,
        )
        current_close = close_panel.loc[date, selected_symbols].astype(float)
        next_close = next_close_panel.loc[date, selected_symbols].astype(float)
        if current_close.isna().any() or next_close.isna().any():
            continue
        symbol_forward_returns = (next_close / current_close) - 1.0
        forward_return = float(symbol_forward_returns.mean())

        row: dict[str, Any] = {
            "date": date.strftime("%Y-%m-%d"),
            "method": method,
            "selection_size": int(selection_size),
            "selected_symbol": selected_symbols[0],
            "selected_symbols": selected_symbols,
            "signal_value": float(selected_signal_values[0]),
            "selected_signal_values": selected_signal_values,
            "selected_symbol_forward_returns": [float(value) for value in symbol_forward_returns.tolist()],
            "forward_return": forward_return,
            "current_close": float(current_close.mean()),
            "next_close": float(next_close.mean()),
        }

        if secondary_frame is not None:
            secondary_values = secondary_frame.loc[date, selected_symbols].astype(float)
            row["secondary_value"] = float(secondary_values.mean())
            row["secondary_values"] = [float(value) for value in secondary_values.tolist()]
        if tertiary_frame is not None:
            tertiary_values = tertiary_frame.loc[date, selected_symbols].astype(float)
            row["tertiary_value"] = float(tertiary_values.mean())
            row["tertiary_values"] = [float(value) for value in tertiary_values.tolist()]

        rows.append(row)

    return pd.DataFrame(
        rows,
        columns=[
            "date",
            "method",
            "selection_size",
            "selected_symbol",
            "selected_symbols",
            "signal_value",
            "selected_signal_values",
            "selected_symbol_forward_returns",
            "forward_return",
            "current_close",
            "next_close",
            "secondary_value",
            "secondary_values",
            "tertiary_value",
            "tertiary_values",
        ],
    )


def build_reference_records(
    method: str,
    dates: pd.DatetimeIndex,
    close_panel: pd.DataFrame,
    next_close_panel: pd.DataFrame,
) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for date in dates:
        current = close_panel.loc[date]
        nxt = next_close_panel.loc[date]
        symbol_returns = (nxt / current) - 1.0
        rows.append(
            {
                "date": date.strftime("%Y-%m-%d"),
                "method": method,
                "selected_symbol": "EQUAL_WEIGHT_REFERENCE",
                "symbol": "EQUAL_WEIGHT_REFERENCE",
                "forward_return": float(symbol_returns.mean()),
                "current_close": float(current.mean()),
                "next_close": float(nxt.mean()),
                "symbol_forward_return": None,
            }
        )

    frame = pd.DataFrame(
        rows,
        columns=[
            "date",
            "method",
            "selected_symbol",
            "symbol",
            "forward_return",
            "current_close",
            "next_close",
            "symbol_forward_return",
        ],
    )
    symbol_rows = []
    for date in dates:
        current = close_panel.loc[date]
        nxt = next_close_panel.loc[date]
        symbol_returns = (nxt / current) - 1.0
        for symbol in close_panel.columns:
            symbol_rows.append(
                {
                    "date": date.strftime("%Y-%m-%d"),
                    "method": method,
                    "selected_symbol": "EQUAL_WEIGHT_REFERENCE",
                    "symbol": symbol,
                    "symbol_forward_return": float(symbol_returns[symbol]),
                    "forward_return": float(symbol_returns.mean()),
                    "current_close": float(current[symbol]),
                    "next_close": float(nxt[symbol]),
                }
            )

    symbol_frame = pd.DataFrame(
        symbol_rows,
        columns=[
            "date",
            "method",
            "selected_symbol",
            "symbol",
            "symbol_forward_return",
            "forward_return",
            "current_close",
            "next_close",
        ],
    )
    symbol_frame["forward_return"] = symbol_frame["forward_return"].astype(float)
    return frame, symbol_frame


def evaluate_price_basis(
    basis_name: str,
    price_panel: pd.DataFrame,
    universe: list[str],
    selection_size: int = 1,
) -> dict[str, Any]:
    price_panel = price_panel.sort_index().astype(float)
    if price_panel.empty:
        raise RuntimeError(f"{basis_name} price panel empty after alignment")

    next_price_panel = price_panel.shift(-1)
    daily_returns = price_panel.pct_change(fill_method=None)
    mom_5d = price_panel / price_panel.shift(5) - 1.0
    mom_20d = price_panel / price_panel.shift(20) - 1.0
    vol_20d = daily_returns.rolling(20, min_periods=20).std().shift(1)
    score_20d = mom_20d / vol_20d

    rank_5d = mom_5d.rank(axis=1, ascending=False, method="min")
    rank_20d = score_20d.rank(axis=1, ascending=False, method="min")
    composite_rank_sum = rank_5d + rank_20d

    eval_dates = price_panel.index[:-1]

    def eligible_dates(signal_frame: pd.DataFrame) -> pd.DatetimeIndex:
        if len(eval_dates) == 0:
            return eval_dates
        valid_counts = signal_frame.loc[eval_dates].notna().sum(axis=1)
        return valid_counts[valid_counts >= selection_size].index

    method_records: dict[str, pd.DataFrame] = {}

    method_records["prior_5d_momentum"] = build_method_records(
        method="prior_5d_momentum",
        dates=eligible_dates(mom_5d),
        close_panel=price_panel,
        next_close_panel=next_price_panel,
        signal_frame=mom_5d,
        selection_size=selection_size,
    )

    method_records["prior_20d_momentum_only"] = build_method_records(
        method="prior_20d_momentum_only",
        dates=eligible_dates(mom_20d),
        close_panel=price_panel,
        next_close_panel=next_price_panel,
        signal_frame=mom_20d,
        selection_size=selection_size,
        secondary_frame=mom_20d,
    )

    method_records["prior_20d_vol_adjusted_momentum"] = build_method_records(
        method="prior_20d_vol_adjusted_momentum",
        dates=eligible_dates(score_20d),
        close_panel=price_panel,
        next_close_panel=next_price_panel,
        signal_frame=score_20d,
        selection_size=selection_size,
        secondary_frame=mom_20d,
        tertiary_frame=vol_20d,
    )

    method_records["simple_composite"] = build_method_records(
        method="simple_composite",
        dates=eligible_dates(composite_rank_sum),
        close_panel=price_panel,
        next_close_panel=next_price_panel,
        signal_frame=composite_rank_sum,
        selection_size=selection_size,
        secondary_frame=rank_5d,
        tertiary_frame=rank_20d,
        descending=False,
    )

    reference_records, reference_symbol_records = build_reference_records(
        method=REFERENCE_METHOD,
        dates=eval_dates,
        close_panel=price_panel,
        next_close_panel=next_price_panel,
    )

    metrics = {
        "price_basis": basis_name,
        "generated_at": datetime.now().astimezone().isoformat(),
        "status": "GROSS_RESEARCH_BASELINE_ONLY",
        "final_classification": "CANDIDATE_FOR_PAPER_REVIEW",
        "not_trading_advice": True,
        "no_fees": True,
        "no_slippage": True,
        "no_fx": True,
        "no_tax": True,
        "no_broker": True,
        "no_order": True,
        "no_ledger": True,
        "universe": universe,
        "selection_size": int(selection_size),
        "data_source": DATA_SOURCE_DISPLAY,
        "basis_method_family": TOP1_METHODS,
        "benchmark_method": REFERENCE_METHOD,
        "data_rows_per_symbol": {symbol: int(len(price_panel)) for symbol in universe},
        "start_date": price_panel.index[0].strftime("%Y-%m-%d"),
        "end_date": price_panel.index[-1].strftime("%Y-%m-%d"),
        "trade_date_start": {
            method: (None if frame.empty else str(frame["date"].iloc[0]))
            for method, frame in {**method_records, REFERENCE_METHOD: reference_records}.items()
        },
        "trade_date_end": {
            method: (None if frame.empty else str(frame["date"].iloc[-1]))
            for method, frame in {**method_records, REFERENCE_METHOD: reference_records}.items()
        },
        "trade_days_available": int(len(price_panel) - 1),
        "methods": {},
    }

    for method_name in TOP1_METHODS:
        metrics["methods"][method_name] = metric_pack(method_name, method_records[method_name], universe, reference_mode=False)

    metrics["methods"][REFERENCE_METHOD] = metric_pack(
        REFERENCE_METHOD,
        reference_records,
        universe,
        reference_mode=True,
        reference_symbol_records=reference_symbol_records,
    )

    pick_ranking = build_ranked_metrics_frame(metrics["methods"], TOP1_METHODS)
    metrics["ranked_pick_methods"] = list(pick_ranking.index)
    metrics["best_pick_method_by_average_forward_return"] = str(pick_ranking.index[0])
    metrics["best_method_by_average_forward_return"] = str(pick_ranking.index[0])
    metrics["benchmark_average_forward_return"] = float(metrics["methods"][REFERENCE_METHOD]["average_forward_return"])

    combined_picks = []
    for method_name in TOP1_METHODS:
        temp = method_records[method_name].copy()
        temp["method"] = method_name
        combined_picks.append(temp)
    combined_picks.append(reference_records.copy())

    picks = pd.concat(combined_picks, ignore_index=True, sort=False)
    picks = picks.sort_values(["method", "date"]).reset_index(drop=True)

    return {
        "basis": basis_name,
        "price_panel": price_panel.copy(),
        "next_price_panel": next_price_panel,
        "method_records": method_records,
        "reference_records": reference_records,
        "reference_symbol_records": reference_symbol_records,
        "metrics": metrics,
        "picks": picks,
    }


def build_rolling_window_record(
    window_length: int,
    window_dates: list[str],
    window_method_records: dict[str, pd.DataFrame],
    window_reference_records: pd.DataFrame,
    window_reference_symbol_records: pd.DataFrame,
    universe: list[str],
) -> dict[str, Any]:
    window_metrics = {
        method: metric_pack(method, window_method_records[method], universe, reference_mode=False)
        for method in TOP1_METHODS
    }
    window_metrics[REFERENCE_METHOD] = metric_pack(
        REFERENCE_METHOD,
        window_reference_records,
        universe,
        reference_mode=True,
        reference_symbol_records=window_reference_symbol_records,
    )

    ranking = build_ranked_metrics_frame(window_metrics, TOP1_METHODS)
    best_method = str(ranking.index[0])
    best_metrics = window_metrics[best_method]

    return {
        "window_length": int(window_length),
        "window_start": window_dates[0],
        "window_end": window_dates[-1],
        "trade_days": int(len(window_dates)),
        "best_pick_method_by_average_forward_return": best_method,
        "best_pick_average_forward_return": float(best_metrics["average_forward_return"]),
        "best_pick_median_forward_return": float(best_metrics["median_forward_return"]),
        "best_pick_win_rate": float(best_metrics["win_rate"]),
        "best_pick_max_drawdown_rough": float(best_metrics["max_drawdown_rough"]),
        "ranked_pick_methods": list(ranking.index),
        "method_average_forward_return": {
            method: float(window_metrics[method]["average_forward_return"]) for method in TOP1_METHODS
        },
        "method_win_rate": {method: float(window_metrics[method]["win_rate"]) for method in TOP1_METHODS},
        "method_max_drawdown_rough": {
            method: float(window_metrics[method]["max_drawdown_rough"]) for method in TOP1_METHODS
        },
        "method_trade_days": {method: int(window_metrics[method]["trade_days"]) for method in TOP1_METHODS},
        "benchmark_average_forward_return": float(window_metrics[REFERENCE_METHOD]["average_forward_return"]),
        "benchmark_win_rate": float(window_metrics[REFERENCE_METHOD]["win_rate"]),
    }


def build_rolling_window_validation(
    close_eval: dict[str, Any],
    universe: list[str],
    window_lengths: list[int],
) -> dict[str, Any]:
    method_records = close_eval["method_records"]
    reference_records = close_eval["reference_records"]
    reference_symbol_records = close_eval["reference_symbol_records"]
    full_best = close_eval["metrics"]["best_pick_method_by_average_forward_return"]

    common_dates = set(reference_records["date"].astype(str))
    for method_name in TOP1_METHODS:
        common_dates &= set(method_records[method_name]["date"].astype(str))
    common_dates_list = sorted(common_dates)

    by_window_length: dict[str, Any] = {}
    all_window_records: list[dict[str, Any]] = []

    for window_length in window_lengths:
        window_records: list[dict[str, Any]] = []
        if len(common_dates_list) >= window_length:
            for start in range(0, len(common_dates_list) - window_length + 1):
                window_dates = common_dates_list[start : start + window_length]
                window_method_records = {
                    method_name: subset_records_by_dates(method_records[method_name], window_dates)
                    for method_name in TOP1_METHODS
                }
                window_reference_records = subset_records_by_dates(reference_records, window_dates)
                window_reference_symbol_records = subset_records_by_dates(reference_symbol_records, window_dates)
                window_record = build_rolling_window_record(
                    window_length=window_length,
                    window_dates=window_dates,
                    window_method_records=window_method_records,
                    window_reference_records=window_reference_records,
                    window_reference_symbol_records=window_reference_symbol_records,
                    universe=universe,
                )
                window_records.append(window_record)

        all_window_records.extend(window_records)
        best_counts = Counter(record["best_pick_method_by_average_forward_return"] for record in window_records)
        total_windows = len(window_records)
        dominant_method = None
        dominant_count = 0
        if best_counts:
            dominant_method = max(best_counts, key=lambda method: (best_counts[method], -TOP1_METHODS.index(method)))
            dominant_count = int(best_counts[dominant_method])

        method_summaries: dict[str, Any] = {}
        for method_name in TOP1_METHODS:
            method_records_for_window = [record for record in window_records]
            ranks = [record["ranked_pick_methods"].index(method_name) + 1 for record in method_records_for_window]
            method_summaries[method_name] = {
                "best_count": int(best_counts.get(method_name, 0)),
                "best_share": None if total_windows == 0 else float(best_counts.get(method_name, 0) / total_windows),
                "average_rank": None if not ranks else float(np.mean(ranks)),
                "median_rank": None if not ranks else float(np.median(ranks)),
                "average_forward_return": None
                if not method_records_for_window
                else float(np.mean([record["method_average_forward_return"][method_name] for record in method_records_for_window])),
                "average_win_rate": None
                if not method_records_for_window
                else float(np.mean([record["method_win_rate"][method_name] for record in method_records_for_window])),
                "average_max_drawdown_rough": None
                if not method_records_for_window
                else float(np.mean([record["method_max_drawdown_rough"][method_name] for record in method_records_for_window])),
            }

        full_best_count = int(best_counts.get(full_best, 0))
        full_best_share = None if total_windows == 0 else float(full_best_count / total_windows)
        switch_count = sum(
            1
            for previous, current in zip(window_records, window_records[1:])
            if previous["best_pick_method_by_average_forward_return"] != current["best_pick_method_by_average_forward_return"]
        )
        switch_rate = None if total_windows <= 1 else float(switch_count / float(total_windows - 1))
        by_window_length[str(window_length)] = {
            "window_length": int(window_length),
            "window_count": int(total_windows),
            "common_trade_days": int(len(common_dates_list)),
            "common_trade_date_start": None if not common_dates_list else common_dates_list[0],
            "common_trade_date_end": None if not common_dates_list else common_dates_list[-1],
            "best_method_counts": {method: int(best_counts.get(method, 0)) for method in TOP1_METHODS},
            "best_method_shares": {
                method: None if total_windows == 0 else float(best_counts.get(method, 0) / total_windows)
                for method in TOP1_METHODS
            },
            "dominant_best_method": dominant_method,
            "dominant_best_method_count": int(dominant_count),
            "dominant_best_method_share": None if total_windows == 0 else float(dominant_count / total_windows),
            "full_sample_best_method": full_best,
            "full_sample_best_count": int(full_best_count),
            "full_sample_best_share": full_best_share,
            "full_sample_best_is_dominant": dominant_method == full_best if dominant_method else False,
            "best_method_switch_count": int(switch_count),
            "best_method_switch_rate": switch_rate,
            "method_summaries": method_summaries,
            "window_records": window_records,
        }

    overall_best_counts = Counter(record["best_pick_method_by_average_forward_return"] for record in all_window_records)
    overall_window_count = len(all_window_records)
    overall_dominant = None
    overall_dominant_count = 0
    if overall_best_counts:
        overall_dominant = max(overall_best_counts, key=lambda method: (overall_best_counts[method], -TOP1_METHODS.index(method)))
        overall_dominant_count = int(overall_best_counts[overall_dominant])

    full_best_overall_count = int(overall_best_counts.get(full_best, 0))
    full_best_overall_share = None if overall_window_count == 0 else float(full_best_overall_count / overall_window_count)
    per_length_full_best_shares = [
        by_window_length[str(window_length)]["full_sample_best_share"]
        for window_length in window_lengths
        if by_window_length[str(window_length)]["full_sample_best_share"] is not None
    ]
    per_length_dominant_matches = sum(
        1 for window_length in window_lengths if by_window_length[str(window_length)]["dominant_best_method"] == full_best
    )
    mean_full_best_share = None if not per_length_full_best_shares else float(np.mean(per_length_full_best_shares))
    stable = bool(
        per_length_full_best_shares
        and mean_full_best_share is not None
        and mean_full_best_share >= 0.5
        and per_length_dominant_matches >= max(1, int(np.ceil(len(window_lengths) * 2 / 3)))
    )
    final_classification = "CANDIDATE_FOR_PAPER_REVIEW" if stable else "REJECTED_FOR_INSTABILITY"

    overall_method_summaries: dict[str, Any] = {}
    for method_name in TOP1_METHODS:
        ranks = [record["ranked_pick_methods"].index(method_name) + 1 for record in all_window_records]
        overall_method_summaries[method_name] = {
            "best_count": int(overall_best_counts.get(method_name, 0)),
            "best_share": None if overall_window_count == 0 else float(overall_best_counts.get(method_name, 0) / overall_window_count),
            "average_rank": None if not ranks else float(np.mean(ranks)),
            "median_rank": None if not ranks else float(np.median(ranks)),
            "average_forward_return": None
            if not all_window_records
            else float(np.mean([record["method_average_forward_return"][method_name] for record in all_window_records])),
            "average_win_rate": None
            if not all_window_records
            else float(np.mean([record["method_win_rate"][method_name] for record in all_window_records])),
            "average_max_drawdown_rough": None
            if not all_window_records
            else float(np.mean([record["method_max_drawdown_rough"][method_name] for record in all_window_records])),
        }

    return {
        "window_lengths": [int(window_length) for window_length in window_lengths],
        "common_trade_days": int(len(common_dates_list)),
        "common_trade_date_start": None if not common_dates_list else common_dates_list[0],
        "common_trade_date_end": None if not common_dates_list else common_dates_list[-1],
        "full_sample_best_method": full_best,
        "overall_window_count": int(overall_window_count),
        "overall_best_counts": {method: int(overall_best_counts.get(method, 0)) for method in TOP1_METHODS},
        "overall_best_shares": {
            method: None if overall_window_count == 0 else float(overall_best_counts.get(method, 0) / overall_window_count)
            for method in TOP1_METHODS
        },
        "overall_dominant_best_method": overall_dominant,
        "overall_dominant_best_method_count": int(overall_dominant_count),
        "overall_dominant_best_method_share": None if overall_window_count == 0 else float(overall_dominant_count / overall_window_count),
        "full_sample_best_overall_count": int(full_best_overall_count),
        "full_sample_best_overall_share": full_best_overall_share,
        "mean_full_sample_best_share_across_lengths": mean_full_best_share,
        "length_summaries": by_window_length,
        "method_summaries": overall_method_summaries,
        "stable": stable,
        "stability_score": mean_full_best_share,
        "full_sample_best_dominant_length_count": int(per_length_dominant_matches),
        "candidate_review_recommended": stable,
        "final_classification": final_classification,
        "window_records": all_window_records,
    }


def summarize_basis_comparison(
    close_eval: dict[str, Any],
    adj_eval: dict[str, Any],
    universe: list[str],
) -> dict[str, Any]:
    def safe_float(value: Any) -> float | None:
        if value is None or pd.isna(value):
            return None
        return float(value)

    comparison = {
        "close_basis": close_eval["metrics"]["price_basis"],
        "adj_basis": adj_eval["metrics"]["price_basis"],
        "close_best_pick_method": close_eval["metrics"]["best_pick_method_by_average_forward_return"],
        "adj_best_pick_method": adj_eval["metrics"]["best_pick_method_by_average_forward_return"],
        "best_pick_method_match": close_eval["metrics"]["best_pick_method_by_average_forward_return"]
        == adj_eval["metrics"]["best_pick_method_by_average_forward_return"],
        "method_details": {},
    }

    for method_name in TOP1_METHODS:
        close_metrics = close_eval["metrics"]["methods"][method_name]
        adj_metrics = adj_eval["metrics"]["methods"][method_name]
        close_columns = ["date", "selected_symbol", "forward_return"]
        adj_columns = ["date", "selected_symbol", "forward_return"]
        if "selected_symbols" in close_eval["method_records"][method_name].columns:
            close_columns.append("selected_symbols")
            adj_columns.append("selected_symbols")
        close_frame = close_eval["method_records"][method_name][close_columns]
        adj_frame = adj_eval["method_records"][method_name][adj_columns]
        merged = close_frame.merge(adj_frame, on="date", suffixes=("_close", "_adj"))
        forward_corr = None
        if len(merged) > 1:
            corr = merged[["forward_return_close", "forward_return_adj"]].corr().iloc[0, 1]
            forward_corr = None if pd.isna(corr) else float(corr)

        basket_exact_match_rate = None
        basket_jaccard_mean = None
        top_symbol_agreement_rate = None
        if "selected_symbols_close" in merged.columns and "selected_symbols_adj" in merged.columns:
            close_baskets = merged["selected_symbols_close"].apply(
                lambda value: tuple(value) if isinstance(value, (list, tuple)) else (value,)
            )
            adj_baskets = merged["selected_symbols_adj"].apply(
                lambda value: tuple(value) if isinstance(value, (list, tuple)) else (value,)
            )
            basket_exact_match_rate = None if merged.empty else float((close_baskets == adj_baskets).mean())
            top_symbol_agreement_rate = None if merged.empty else float((merged["selected_symbol_close"] == merged["selected_symbol_adj"]).mean())
            basket_jaccard_values = []
            for close_basket, adj_basket in zip(close_baskets, adj_baskets):
                close_set = set(close_basket)
                adj_set = set(adj_basket)
                union = close_set | adj_set
                basket_jaccard_values.append(1.0 if not union else len(close_set & adj_set) / len(union))
            basket_jaccard_mean = None if not basket_jaccard_values else float(np.mean(basket_jaccard_values))

        comparison["method_details"][method_name] = {
            "trade_days_overlap": int(len(merged)),
            "selected_symbol_agreement_rate": None
            if merged.empty
            else float((merged["selected_symbol_close"] == merged["selected_symbol_adj"]).mean()),
            "selected_top_symbol_agreement_rate": top_symbol_agreement_rate,
            "selected_basket_exact_match_rate": basket_exact_match_rate,
            "selected_basket_jaccard_mean": basket_jaccard_mean,
            "average_forward_return_close": safe_float(close_metrics["average_forward_return"]),
            "average_forward_return_adj": safe_float(adj_metrics["average_forward_return"]),
            "average_forward_return_delta": None
            if close_metrics["average_forward_return"] is None or adj_metrics["average_forward_return"] is None
            else float(adj_metrics["average_forward_return"] - close_metrics["average_forward_return"]),
            "median_forward_return_close": safe_float(close_metrics["median_forward_return"]),
            "median_forward_return_adj": safe_float(adj_metrics["median_forward_return"]),
            "win_rate_close": safe_float(close_metrics["win_rate"]),
            "win_rate_adj": safe_float(adj_metrics["win_rate"]),
            "forward_return_correlation": forward_corr,
            "selected_counts_close": close_metrics["selected_counts"],
            "selected_counts_adj": adj_metrics["selected_counts"],
        }

    comparison["reference_method_details"] = {
        "trade_days_close": int(close_eval["metrics"]["methods"][REFERENCE_METHOD]["trade_days"]),
        "trade_days_adj": int(adj_eval["metrics"]["methods"][REFERENCE_METHOD]["trade_days"]),
        "average_forward_return_close": safe_float(close_eval["metrics"]["methods"][REFERENCE_METHOD]["average_forward_return"]),
        "average_forward_return_adj": safe_float(adj_eval["metrics"]["methods"][REFERENCE_METHOD]["average_forward_return"]),
        "average_forward_return_delta": None
        if close_eval["metrics"]["methods"][REFERENCE_METHOD]["average_forward_return"] is None
        or adj_eval["metrics"]["methods"][REFERENCE_METHOD]["average_forward_return"] is None
        else float(
            adj_eval["metrics"]["methods"][REFERENCE_METHOD]["average_forward_return"]
            - close_eval["metrics"]["methods"][REFERENCE_METHOD]["average_forward_return"]
        ),
    }

    return comparison


def build_sample_split_validation(
    close_eval: dict[str, Any],
    universe: list[str],
) -> dict[str, Any]:
    price_panel = close_eval["price_panel"]
    index = price_panel.index
    if len(index) < 4:
        return {
            "split_mode": "first_half_vs_second_half",
            "split_boundary": None,
            "stable_across_splits": False,
            "best_method_stability_score": None,
            "splits": {},
        }

    midpoint = len(index) // 2
    boundary = index[midpoint]
    split_masks = {
        "first_half": index <= boundary,
        "second_half": index > boundary,
    }

    splits: dict[str, Any] = {}
    full_best = close_eval["metrics"]["best_pick_method_by_average_forward_return"]

    for split_name, mask in split_masks.items():
        split_dates = index[mask].strftime("%Y-%m-%d")
        split_method_records = {
            method: frame[frame["date"].isin(split_dates)].copy()
            for method, frame in close_eval["method_records"].items()
        }
        split_reference_records = close_eval["reference_records"][
            close_eval["reference_records"]["date"].isin(split_dates)
        ].copy()
        split_reference_symbol_records = close_eval["reference_symbol_records"][
            close_eval["reference_symbol_records"]["date"].isin(split_dates)
        ].copy()

        split_metrics = {}
        for method_name in TOP1_METHODS:
            split_metrics[method_name] = metric_pack(method_name, split_method_records[method_name], universe, reference_mode=False)
        split_metrics[REFERENCE_METHOD] = metric_pack(
            REFERENCE_METHOD,
            split_reference_records,
            universe,
            reference_mode=True,
            reference_symbol_records=split_reference_symbol_records,
        )

        ranking = build_ranked_metrics_frame(split_metrics, TOP1_METHODS)
        best_method = str(ranking.index[0])
        splits[split_name] = {
            "date_start": split_dates[0] if len(split_dates) else None,
            "date_end": split_dates[-1] if len(split_dates) else None,
            "trade_days": int(len(split_dates)),
            "best_pick_method_by_average_forward_return": best_method,
            "ranked_pick_methods": list(ranking.index),
            "best_pick_matches_full_sample": best_method == full_best,
            "metrics": split_metrics,
        }

    best_methods = [splits["first_half"]["best_pick_method_by_average_forward_return"], splits["second_half"]["best_pick_method_by_average_forward_return"]]
    stable = len(set(best_methods + [full_best])) == 1
    stability_score = sum(method == full_best for method in best_methods) / float(len(best_methods))

    return {
        "split_mode": "first_half_vs_second_half",
        "split_boundary": boundary.strftime("%Y-%m-%d"),
        "full_sample_best_pick_method": full_best,
        "best_method_stability_score": stability_score,
        "stable_across_splits": stable,
        "best_method_matches_both_splits": stable,
        "splits": splits,
        "final_classification": "CANDIDATE_FOR_PAPER_REVIEW",
    }


def minimum_required_universe_size(universe_size: int) -> int:
    if universe_size <= 0:
        return 0
    return min(universe_size, max(20, int(np.ceil(universe_size * 0.7))))


def resolve_universe_key(universes: dict[str, Any], requested_key: str | None) -> str:
    if requested_key:
        if requested_key not in universes:
            raise ValueError(f"unknown universe key: {requested_key}")
        return requested_key
    if "union" in universes:
        return "union"
    return next(iter(universes))


def evaluate_selection_size_replay(
    close_panel: pd.DataFrame,
    adj_panel: pd.DataFrame,
    universe: list[str],
    selection_size: int,
) -> dict[str, Any]:
    close_eval = evaluate_price_basis("close", close_panel, universe, selection_size=selection_size)
    adj_eval = evaluate_price_basis("adj_close", adj_panel, universe, selection_size=selection_size)
    basis_comparison = summarize_basis_comparison(close_eval, adj_eval, universe)
    split_validation = build_sample_split_validation(close_eval, universe)
    rolling_validation = build_rolling_window_validation(close_eval, universe, ROLLING_WINDOW_LENGTHS)
    feature_ablation = {
        "methods": {
            method_name: close_eval["metrics"]["methods"][method_name] for method_name in FEATURE_ABLATION_METHODS
        },
        "ranked_methods_by_average_forward_return": list(
            build_ranked_metrics_frame(close_eval["metrics"]["methods"], FEATURE_ABLATION_METHODS).index
        ),
        "best_method_by_average_forward_return": close_eval["metrics"]["best_method_by_average_forward_return"],
        "benchmark_method": REFERENCE_METHOD,
    }

    final_classification = (
        "CANDIDATE_FOR_PAPER_REVIEW"
        if basis_comparison["best_pick_method_match"] and rolling_validation["stable"]
        else "REJECTED_FOR_INSTABILITY"
    )
    validation_state = (
        "stable"
        if final_classification == "CANDIDATE_FOR_PAPER_REVIEW"
        else ("mixed" if basis_comparison["best_pick_method_match"] else "unstable")
    )

    metrics = close_eval["metrics"]
    metrics.update(
        {
            "selection_size": int(selection_size),
            "selection_mode": f"top{selection_size}" if selection_size > 1 else "top1",
            "adj_close_basis_metrics": adj_eval["metrics"],
            "basis_comparison": basis_comparison,
            "sample_split_validation": split_validation,
            "rolling_window_validation": rolling_validation,
            "feature_ablation": feature_ablation,
            "validation_state": validation_state,
            "final_classification": final_classification,
            "candidate_review_recommended": final_classification == "CANDIDATE_FOR_PAPER_REVIEW",
        }
    )

    return {
        "metrics": metrics,
        "close_basis_metrics": close_eval["metrics"],
        "adj_basis_metrics": adj_eval["metrics"],
        "basis_comparison": basis_comparison,
        "sample_split_validation": split_validation,
        "rolling_window_validation": rolling_validation,
        "feature_ablation": feature_ablation,
        "validation_state": validation_state,
        "final_classification": final_classification,
        "candidate_review_recommended": final_classification == "CANDIDATE_FOR_PAPER_REVIEW",
        "close_eval": close_eval,
        "adj_eval": adj_eval,
    }


def run_replay(
    universe_source_name: str,
    explicit_universe: list[str] | None,
    universe_key: str | None,
    periods: list[str],
    output_date: str,
    run_name: str,
    sleep_seconds: float,
    selection_sizes: list[int],
    batch_size: int = DEFAULT_BATCH_SIZE,
    min_history_days: int = DEFAULT_MIN_HISTORY_DAYS,
    min_price: float = DEFAULT_MIN_PRICE,
    min_median_dollar_volume: float = DEFAULT_MIN_MEDIAN_DOLLAR_VOLUME,
) -> dict[str, Any]:
    source_config = load_universe_source(universe_source_name, explicit_universe=explicit_universe)
    universes = source_config["universes"]
    selected_universe_key = resolve_universe_key(universes, universe_key)
    selected_universe_info = universes[selected_universe_key]
    selected_universe = list(selected_universe_info["symbols"])

    attempts: list[dict[str, Any]] = []
    chosen_results: dict[str, SymbolFetchResult] | None = None
    chosen_period: str | None = None
    chosen_failures: list[dict[str, str]] = []
    chosen_quality: dict[str, Any] | None = None
    chosen_included_symbols: list[str] | None = None
    chosen_excluded_symbols: dict[str, Any] | None = None
    chosen_close_panel: pd.DataFrame | None = None
    chosen_adj_panel: pd.DataFrame | None = None
    chosen_long_panel: pd.DataFrame | None = None
    minimum_symbols = minimum_required_universe_size(len(selected_universe))

    for period in periods:
        results, failures = fetch_universe(
            period,
            selected_universe,
            sleep_seconds=sleep_seconds,
            batch_size=batch_size,
        )
        quality = {
            symbol: evaluate_symbol_quality(result, min_history_days, min_price, min_median_dollar_volume)
            for symbol, result in results.items()
        }
        included_symbols = [symbol for symbol in selected_universe if quality.get(symbol, {}).get("include")]
        excluded_symbols = {symbol: quality[symbol] for symbol in selected_universe if symbol not in included_symbols}
        filtered_results = {symbol: results[symbol] for symbol in included_symbols}
        close_panel, adj_panel, long_panel = build_close_panel(filtered_results)
        close_panel = close_panel.sort_index().astype(float)
        adj_panel = adj_panel.reindex(close_panel.index).sort_index().astype(float)
        if not long_panel.empty and "date" in long_panel.columns:
            long_panel = long_panel[long_panel["date"].isin(close_panel.index.strftime("%Y-%m-%d"))].copy()

        coverage_ratio = 0.0 if not selected_universe else float(len(included_symbols) / len(selected_universe))
        raw_rows = {symbol: result.rows for symbol, result in results.items()}
        adj_available = {symbol: result.adj_close_available for symbol, result in results.items()}
        attempts.append(
            {
                "period": period,
                "raw_rows_per_symbol": raw_rows,
                "adj_close_available": adj_available,
                "failures": failures,
                "quality_included_count": int(len(included_symbols)),
                "quality_excluded_count": int(len(excluded_symbols)),
                "quality_coverage_ratio": coverage_ratio,
                "panel_rows": int(len(close_panel)),
            }
        )

        if len(included_symbols) < minimum_symbols or close_panel.empty:
            chosen_failures = failures
            continue

        chosen_results = filtered_results
        chosen_period = period
        chosen_failures = failures
        chosen_quality = quality
        chosen_included_symbols = included_symbols
        chosen_excluded_symbols = excluded_symbols
        chosen_close_panel = close_panel
        chosen_adj_panel = adj_panel
        chosen_long_panel = long_panel
        break

    if (
        chosen_results is None
        or chosen_period is None
        or chosen_quality is None
        or chosen_included_symbols is None
        or chosen_excluded_symbols is None
        or chosen_close_panel is None
        or chosen_adj_panel is None
        or chosen_long_panel is None
    ):
        raise RuntimeError(
            "unable to fetch any usable Yahoo historical kline panel; attempts="
            + json.dumps(serializable(attempts), ensure_ascii=False)
        )

    selection_sizes = dedupe_preserve_order([int(size) for size in selection_sizes if int(size) > 0])
    if not selection_sizes:
        raise ValueError("selection_sizes must contain at least one positive integer")

    selection_size_evaluations: dict[str, dict[str, Any]] = {}
    selection_size_comparison: list[dict[str, Any]] = []
    combined_picks_frames: list[pd.DataFrame] = []

    for selection_size in selection_sizes:
        evaluation = evaluate_selection_size_replay(
            close_panel=chosen_close_panel,
            adj_panel=chosen_adj_panel,
            universe=chosen_included_symbols,
            selection_size=selection_size,
        )
        evaluation["metrics"].update(
            {
                "output_date": output_date,
                "period_attempted": periods,
                "period_used": chosen_period,
                "market_data_source": EASTMONEY_HISTORICAL_SOURCE_DISPLAY,
                "adjusted_close_semantics": "Adj Close comes from EastMoney historical kline with Close fallback when needed",
                "universe_source_name": source_config["source_name"],
                "universe_source_key": selected_universe_key,
                "source_universe_name": source_config["source_name"],
                "source_universe_key": selected_universe_key,
                "universe_source_details": source_config,
                "source_universe_total_symbols": int(len(selected_universe)),
                "source_universe_included_symbols": int(len(chosen_included_symbols)),
                "source_universe_excluded_symbols": int(len(chosen_excluded_symbols)),
                "source_universe_coverage_ratio": float(len(chosen_included_symbols) / len(selected_universe))
                if selected_universe
                else None,
                "source_universe_minimum_required_symbols": int(minimum_symbols),
                "source_universe_quality_filter": {
                    "min_history_days": int(min_history_days),
                    "min_price": float(min_price),
                    "min_median_dollar_volume": float(min_median_dollar_volume),
                },
                "data_rows_per_symbol": {symbol: int(result.rows) for symbol, result in chosen_results.items()},
                "adjusted_close_available": {
                    symbol: bool(result.adj_close_available) for symbol, result in chosen_results.items()
                },
                "common_panel_rows": int(len(chosen_close_panel)),
                "common_panel_columns": list(chosen_close_panel.columns),
                "attempts": attempts,
                "failures": chosen_failures,
                "limitations": [
                    "GROSS_RESEARCH_BASELINE_ONLY",
                    "NOT_TRADING_ADVICE",
                    "NO_FEES",
                    "NO_SLIPPAGE",
                    "NO_FX",
                    "NO_TAX",
                    "NO_BROKER",
                    "NO_ORDER",
                    "NO_LEDGER",
                    "close-to-close only",
                    EASTMONEY_HISTORICAL_SOURCE_DISPLAY,
                    "EastMoney historical kline owner; Adj Close preferred with Close fallback only when needed",
                    "current-listed universe snapshot",
                    "survivorship bias disclaimer applies",
                ],
                "candidate_review_recommended": evaluation["final_classification"] == "CANDIDATE_FOR_PAPER_REVIEW",
            }
        )
        evaluation["metrics"]["source_universe_symbols"] = list(chosen_included_symbols)
        evaluation["metrics"]["source_universe_dropped"] = {
            symbol: chosen_excluded_symbols[symbol] for symbol in chosen_excluded_symbols
        }
        selection_size_evaluations[str(selection_size)] = evaluation

        picks_frame = evaluation["close_eval"]["picks"].copy()
        picks_frame["selection_size"] = int(selection_size)
        picks_frame["source_universe_name"] = source_config["source_name"]
        picks_frame["source_universe_key"] = selected_universe_key
        combined_picks_frames.append(picks_frame)

        best_method = evaluation["metrics"]["best_method_by_average_forward_return"]
        rolling_validation = evaluation["rolling_window_validation"]
        selection_size_comparison.append(
            {
                "selection_size": int(selection_size),
                "best_method_by_average_forward_return": best_method,
                "best_method_average_forward_return": float(
                    evaluation["metrics"]["methods"][best_method]["average_forward_return"]
                ),
                "best_method_win_rate": float(evaluation["metrics"]["methods"][best_method]["win_rate"]),
                "benchmark_average_forward_return": float(
                    evaluation["metrics"]["methods"][REFERENCE_METHOD]["average_forward_return"]
                ),
                "validation_state": evaluation["validation_state"],
                "final_classification": evaluation["final_classification"],
                "rolling_stable": bool(rolling_validation["stable"]),
                "rolling_stability_score": rolling_validation["stability_score"],
                "best_method_by_average_forward_return_matches_basis": bool(
                    evaluation["basis_comparison"]["best_pick_method_match"]
                ),
                "selection_mode": f"top{selection_size}" if selection_size > 1 else "top1",
            }
        )

    primary_selection_size = selection_sizes[0]
    primary_evaluation = selection_size_evaluations[str(primary_selection_size)]
    metrics = primary_evaluation["metrics"]
    metrics.update(
        {
            "run_name": run_name,
            "selection_sizes_tested": [int(size) for size in selection_sizes],
            "selection_size_evaluations": {
                key: {
                    "best_method_by_average_forward_return": value["metrics"]["best_method_by_average_forward_return"],
                    "best_method_average_forward_return": float(
                        value["metrics"]["methods"][value["metrics"]["best_method_by_average_forward_return"]][
                            "average_forward_return"
                        ]
                    ),
                    "validation_state": value["validation_state"],
                    "final_classification": value["final_classification"],
                    "rolling_stable": bool(value["rolling_window_validation"]["stable"]),
                    "rolling_stability_score": value["rolling_window_validation"]["stability_score"],
                    "basis_match": bool(value["basis_comparison"]["best_pick_method_match"]),
                }
                for key, value in selection_size_evaluations.items()
            },
            "selection_size_comparison": selection_size_comparison,
        }
    )

    if selection_size_comparison:
        best_selection_size_row = max(
            selection_size_comparison,
            key=lambda row: (
                row["best_method_average_forward_return"],
                row["rolling_stable"],
                -row["selection_size"],
            ),
        )
    else:
        best_selection_size_row = {
            "selection_size": primary_selection_size,
            "best_method_by_average_forward_return": metrics["best_method_by_average_forward_return"],
            "best_method_average_forward_return": metrics["methods"][metrics["best_method_by_average_forward_return"]][
                "average_forward_return"
            ],
            "final_classification": metrics["final_classification"],
        }

    metrics.update(
        {
            "best_selection_size_by_average_forward_return": int(best_selection_size_row["selection_size"]),
            "best_selection_size_by_average_forward_return_method": best_selection_size_row[
                "best_method_by_average_forward_return"
            ],
            "best_selection_size_by_average_forward_return_value": float(
                best_selection_size_row["best_method_average_forward_return"]
            ),
            "best_selection_size_final_classification": best_selection_size_row.get("final_classification"),
            "selection_size_primary": int(primary_selection_size),
        }
    )

    long_panel = chosen_long_panel.copy()
    long_panel["source_period"] = chosen_period
    long_panel["output_date"] = output_date
    long_panel["source_universe_name"] = source_config["source_name"]
    long_panel["source_universe_key"] = selected_universe_key

    combined_picks = pd.concat(combined_picks_frames, ignore_index=True, sort=False)
    combined_picks = combined_picks.sort_values(["selection_size", "method", "date"]).reset_index(drop=True)

    outputs = {
        "metrics": metrics,
        "picks": combined_picks,
        "price_panel": long_panel,
        "reference_symbol_records": primary_evaluation["close_eval"]["reference_symbol_records"],
        "close_basis_metrics": primary_evaluation["close_basis_metrics"],
        "adj_basis_metrics": primary_evaluation["adj_basis_metrics"],
        "selection_size_evaluations": selection_size_evaluations,
        "source_config": source_config,
        "selected_universe_key": selected_universe_key,
    }
    return outputs


def build_summary_md(metrics: dict[str, Any], output_date: str) -> str:
    methods = metrics["methods"]
    best_method = metrics["best_method_by_average_forward_return"]
    basis_comparison = metrics.get("basis_comparison", {})
    split_validation = metrics.get("sample_split_validation", {})
    rolling_validation = metrics.get("rolling_window_validation", {})
    feature_ablation = metrics.get("feature_ablation", {})
    selection_size_comparison = metrics.get("selection_size_comparison", [])
    title = str(metrics.get("run_name", "historical-replay-baseline")).replace("-", " ").title()

    lines = [
        f"# {title}",
        "",
        "GROSS_RESEARCH_BASELINE_ONLY",
        "NOT_TRADING_ADVICE",
        "NO_FEES",
        "NO_SLIPPAGE",
        "NO_FX",
        "NO_TAX",
        "NO_BROKER",
        "NO_ORDER",
        "NO_LEDGER",
        "",
        f"- output_date: {output_date}",
        f"- data_source: {metrics['data_source']}",
        f"- universe: {', '.join(metrics['universe'])}",
        f"- universe_source_name: {metrics.get('source_universe_name')}",
        f"- universe_source_key: {metrics.get('source_universe_key')}",
        f"- source_universe_total_symbols: {metrics.get('source_universe_total_symbols')}",
        f"- source_universe_included_symbols: {metrics.get('source_universe_included_symbols')}",
        f"- source_universe_coverage_ratio: {metrics.get('source_universe_coverage_ratio')}",
        f"- period_used: {metrics['period_used']}",
        f"- start_date: {metrics['start_date']}",
        f"- end_date: {metrics['end_date']}",
        f"- common_panel_rows: {metrics['common_panel_rows']}",
        f"- selection_sizes_tested: {metrics.get('selection_sizes_tested')}",
        f"- best_selection_size_by_average_forward_return: {metrics.get('best_selection_size_by_average_forward_return')}",
        f"- best_selection_size_by_average_forward_return_method: {metrics.get('best_selection_size_by_average_forward_return_method')}",
        f"- best_selection_size_by_average_forward_return_value: {metrics.get('best_selection_size_by_average_forward_return_value')}",
        f"- best_method_by_average_forward_return: {best_method}",
        f"- selection_mode: {metrics.get('selection_mode')}",
        f"- validation_state: {metrics.get('validation_state')}",
        f"- final_classification: {metrics.get('final_classification')}",
        "",
        "## Method Results",
    ]

    for method_name in (
        "prior_5d_momentum",
        "prior_20d_momentum_only",
        "prior_20d_vol_adjusted_momentum",
        "simple_composite",
        "equal_weight_reference",
    ):
        item = methods[method_name]
        lines.extend(
            [
                f"### {method_name}",
                f"- trade_days: {item['trade_days']}",
                f"- average_forward_return: {item['average_forward_return']}",
                f"- median_forward_return: {item['median_forward_return']}",
                f"- win_rate: {item['win_rate']}",
                f"- max_drawdown_rough: {item['max_drawdown_rough']}",
                f"- selected_counts: {json.dumps(item['selected_counts'], ensure_ascii=False)}",
            ]
        )

    if selection_size_comparison:
        lines.extend(
            [
                "",
                "## Selection Size Comparison",
                "|selection_size|best_method|avg_forward_return|win_rate|rolling_stable|classification|basis_match|",
                "|---|---|---|---|---|---|---|",
            ]
        )
        for row in selection_size_comparison:
            lines.append(
                "|{selection_size}|{best_method}|{avg_return}|{win_rate}|{stable}|{classification}|{basis_match}|".format(
                    selection_size=row.get("selection_size"),
                    best_method=row.get("best_method_by_average_forward_return"),
                    avg_return=row.get("best_method_average_forward_return"),
                    win_rate=row.get("best_method_win_rate"),
                    stable=row.get("rolling_stable"),
                    classification=row.get("final_classification"),
                    basis_match=row.get("best_method_by_average_forward_return_matches_basis"),
                )
            )

    lines.extend(
        [
            "",
            "## Limitations",
        ]
    )
    for item in metrics["limitations"]:
        lines.append(f"- {item}")

    if basis_comparison:
        lines.extend(
            [
                "",
                "## Close vs Adj Close",
                f"- close_best_pick_method: {basis_comparison.get('close_best_pick_method')}",
                f"- adj_best_pick_method: {basis_comparison.get('adj_best_pick_method')}",
                f"- best_pick_method_match: {basis_comparison.get('best_pick_method_match')}",
            ]
        )
        for method_name in (
            "prior_5d_momentum",
            "prior_20d_momentum_only",
            "prior_20d_vol_adjusted_momentum",
            "simple_composite",
        ):
            detail = basis_comparison.get("method_details", {}).get(method_name, {})
            lines.extend(
                [
                    f"### {method_name}",
                    f"- selected_symbol_agreement_rate: {detail.get('selected_symbol_agreement_rate')}",
                    f"- average_forward_return_close: {detail.get('average_forward_return_close')}",
                    f"- average_forward_return_adj: {detail.get('average_forward_return_adj')}",
                    f"- average_forward_return_delta: {detail.get('average_forward_return_delta')}",
                    f"- forward_return_correlation: {detail.get('forward_return_correlation')}",
                ]
            )
        ref_detail = basis_comparison.get("reference_method_details", {})
        lines.extend(
            [
                "### equal_weight_reference",
                f"- average_forward_return_close: {ref_detail.get('average_forward_return_close')}",
                f"- average_forward_return_adj: {ref_detail.get('average_forward_return_adj')}",
                f"- average_forward_return_delta: {ref_detail.get('average_forward_return_delta')}",
            ]
        )

    if split_validation:
        lines.extend(
            [
                "",
                "## Sample Split Validation",
                f"- split_mode: {split_validation.get('split_mode')}",
                f"- split_boundary: {split_validation.get('split_boundary')}",
                f"- full_sample_best_pick_method: {split_validation.get('full_sample_best_pick_method')}",
                f"- best_method_stability_score: {split_validation.get('best_method_stability_score')}",
                f"- stable_across_splits: {split_validation.get('stable_across_splits')}",
            ]
        )
        for split_name in ("first_half", "second_half"):
            split = split_validation.get("splits", {}).get(split_name, {})
            lines.extend(
                [
                    f"### {split_name}",
                    f"- date_start: {split.get('date_start')}",
                    f"- date_end: {split.get('date_end')}",
                    f"- trade_days: {split.get('trade_days')}",
                    f"- best_pick_method_by_average_forward_return: {split.get('best_pick_method_by_average_forward_return')}",
                    f"- best_pick_matches_full_sample: {split.get('best_pick_matches_full_sample')}",
                ]
            )

    if feature_ablation:
        lines.extend(
            [
                "",
                "## Feature Ablation",
                f"- ranked_methods_by_average_forward_return: {feature_ablation.get('ranked_methods_by_average_forward_return')}",
                f"- benchmark_method: {feature_ablation.get('benchmark_method')}",
            ]
        )
        for method_name in FEATURE_ABLATION_METHODS:
            item = feature_ablation.get("methods", {}).get(method_name, methods.get(method_name, {}))
            lines.extend(
                [
                    f"### {method_name}",
                    f"- trade_days: {item.get('trade_days')}",
                    f"- average_forward_return: {item.get('average_forward_return')}",
                    f"- median_forward_return: {item.get('median_forward_return')}",
                    f"- win_rate: {item.get('win_rate')}",
                    f"- max_drawdown_rough: {item.get('max_drawdown_rough')}",
                ]
            )

    if rolling_validation:
        lines.extend(
            [
                "",
                "## Rolling Window Stability",
                f"- window_lengths: {rolling_validation.get('window_lengths')}",
                f"- common_trade_days: {rolling_validation.get('common_trade_days')}",
                f"- overall_window_count: {rolling_validation.get('overall_window_count')}",
                f"- overall_dominant_best_method: {rolling_validation.get('overall_dominant_best_method')}",
                f"- overall_best_counts: {json.dumps(rolling_validation.get('overall_best_counts', {}), ensure_ascii=False)}",
                f"- mean_full_sample_best_share_across_lengths: {rolling_validation.get('mean_full_sample_best_share_across_lengths')}",
                f"- full_sample_best_dominant_length_count: {rolling_validation.get('full_sample_best_dominant_length_count')}",
                f"- stable: {rolling_validation.get('stable')}",
                f"- stability_score: {rolling_validation.get('stability_score')}",
                f"- final_classification: {rolling_validation.get('final_classification')}",
            ]
        )
        for length in rolling_validation.get("window_lengths", []):
            length_summary = rolling_validation.get("length_summaries", {}).get(str(length), {})
            lines.extend(
                [
                    f"### window_{length}d",
                    f"- window_count: {length_summary.get('window_count')}",
                    f"- dominant_best_method: {length_summary.get('dominant_best_method')}",
                    f"- dominant_best_method_share: {length_summary.get('dominant_best_method_share')}",
                    f"- full_sample_best_count: {length_summary.get('full_sample_best_count')}",
                    f"- full_sample_best_share: {length_summary.get('full_sample_best_share')}",
                    f"- best_method_switch_count: {length_summary.get('best_method_switch_count')}",
                ]
            )
            for method_name in TOP1_METHODS:
                method_summary = length_summary.get("method_summaries", {}).get(method_name, {})
                lines.extend(
                    [
                        f"#### {method_name}",
                        f"- best_count: {method_summary.get('best_count')}",
                        f"- best_share: {method_summary.get('best_share')}",
                        f"- average_rank: {method_summary.get('average_rank')}",
                        f"- average_forward_return: {method_summary.get('average_forward_return')}",
                        f"- average_win_rate: {method_summary.get('average_win_rate')}",
                        f"- average_max_drawdown_rough: {method_summary.get('average_max_drawdown_rough')}",
                    ]
                )

    lines.extend(
        [
            "",
            "## Best Method",
            f"- method: {best_method}",
            "- why: highest average forward return in this gross-only replay",
            "- note: equal_weight_reference is a benchmark, not a top1 pick method",
            f"- final_classification: {metrics.get('final_classification')}",
            f"- rolling_window_final_classification: {rolling_validation.get('final_classification')}",
        ]
    )
    return "\n".join(lines) + "\n"


def save_outputs(outputs: dict[str, Any], output_date: str) -> dict[str, Path]:
    project = project_root()
    run_name = str(outputs["metrics"].get("run_name", "historical-replay-baseline"))
    research_dir = project / "research" / run_name
    data_dir = project / "data" / run_name

    summary_path = research_dir / f"summary-{output_date}.md"
    metrics_path = research_dir / f"metrics-{output_date}.json"
    picks_path = research_dir / f"picks-{output_date}.csv"
    price_path = data_dir / f"price-panel-{output_date}.csv"

    write_text(summary_path, build_summary_md(outputs["metrics"], output_date))
    write_json(metrics_path, outputs["metrics"])
    write_csv(picks_path, outputs["picks"])
    write_csv(price_path, outputs["price_panel"])

    return {
        "summary": summary_path,
        "metrics": metrics_path,
        "picks": picks_path,
        "price_panel": price_path,
    }


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Historical replay baseline for xiaomei US stocks.")
    parser.add_argument(
        "--universe",
        nargs="+",
        default=DEFAULT_UNIVERSE,
        help="Universe of symbols to replay.",
    )
    parser.add_argument(
        "--universe-source",
        choices=["explicit", "nasdaq100", "sp500", "nasdaq100_sp500_union"],
        default="explicit",
        help="Universe source snapshot to replay.",
    )
    parser.add_argument(
        "--universe-key",
        default=None,
        help="Universe key within the selected source snapshot (default: union if available, otherwise the only key).",
    )
    parser.add_argument(
        "--run-name",
        default="historical-replay-baseline",
        help="Output directory name under research/ and data/.",
    )
    parser.add_argument(
        "--period",
        default=None,
        help="Single EastMoney kline period to try instead of the default fallback sequence.",
    )
    parser.add_argument(
        "--output-date",
        default=output_date_string(),
        help="Date stamp for generated files (default: local today).",
    )
    parser.add_argument(
        "--sleep-seconds",
        type=float,
        default=0.5,
        help="Pause between serial EastMoney requests.",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=DEFAULT_BATCH_SIZE,
        help="Batch size for EastMoney sequential fetch groups.",
    )
    parser.add_argument(
        "--min-history-days",
        type=int,
        default=DEFAULT_MIN_HISTORY_DAYS,
        help="Minimum number of daily bars required per symbol.",
    )
    parser.add_argument(
        "--min-price",
        type=float,
        default=DEFAULT_MIN_PRICE,
        help="Minimum last close price for a symbol to stay in universe.",
    )
    parser.add_argument(
        "--min-median-dollar-volume",
        type=float,
        default=DEFAULT_MIN_MEDIAN_DOLLAR_VOLUME,
        help="Minimum median dollar volume for a symbol to stay in universe.",
    )
    parser.add_argument(
        "--selection-sizes",
        nargs="+",
        type=int,
        default=[1],
        help="Selection sizes to evaluate for each scoring method.",
    )
    return parser.parse_args(argv)


def main(argv: list[str]) -> int:
    args = parse_args(argv)
    periods = [args.period] if args.period else list(DEFAULT_PERIODS)
    selection_sizes = dedupe_preserve_order([int(size) for size in args.selection_sizes if int(size) > 0])
    if not selection_sizes:
        print("REPLAY_FAIL: selection-sizes must contain at least one positive integer", file=sys.stderr)
        return 1

    try:
        outputs = run_replay(
            args.universe_source,
            args.universe,
            args.universe_key,
            periods,
            args.output_date,
            args.run_name,
            args.sleep_seconds,
            selection_sizes,
            batch_size=args.batch_size,
            min_history_days=args.min_history_days,
            min_price=args.min_price,
            min_median_dollar_volume=args.min_median_dollar_volume,
        )
        paths = save_outputs(outputs, args.output_date)
    except Exception as exc:  # noqa: BLE001
        traceback.print_exc()
        print(f"REPLAY_FAIL: {exc}", file=sys.stderr)
        return 1

    metrics = outputs["metrics"]
    print(
        json.dumps(
            {
                "status": metrics["status"],
                "period_used": metrics["period_used"],
                "best_method": metrics["best_method_by_average_forward_return"],
                "paths": {key: str(value) for key, value in paths.items()},
                "common_panel_rows": metrics["common_panel_rows"],
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
