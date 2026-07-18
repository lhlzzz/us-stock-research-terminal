"""Parquet writer for xiaomei factor warehouse."""
import os
from pathlib import Path
from datetime import date
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

FACTORS_ROOT = Path(__file__).resolve().parent.parent.parent / "data" / "factors"


def save_daily_factors(trade_date: date, df: pd.DataFrame):
    """Save daily factor snapshot to Parquet, partitioned by date."""
    y, m, d = trade_date.year, trade_date.month, trade_date.day
    path = FACTORS_ROOT / f"year={y}" / f"month={m:02d}" / f"day={d:02d}"
    path.mkdir(parents=True, exist_ok=True)
    filepath = path / f"factors_{trade_date}.parquet"
    df.to_parquet(filepath, index=False, engine="pyarrow")
    return filepath


def append_klines(symbol: str, df: pd.DataFrame):
    """Append kline data for a symbol, deduplicating on trade_date."""
    symbol_dir = FACTORS_ROOT / "daily_klines" / f"symbol={symbol}"
    symbol_dir.mkdir(parents=True, exist_ok=True)
    filepath = symbol_dir / f"klines_{symbol}.parquet"

    if filepath.exists():
        existing = pd.read_parquet(filepath)
        df = pd.concat([existing, df]).drop_duplicates(subset=["trade_date"], keep="last")
        df = df.sort_values("trade_date")

    df.to_parquet(filepath, index=False, engine="pyarrow")
    return filepath


def read_daily_factors(trade_date: date) -> pd.DataFrame | None:
    """Read daily factor snapshot."""
    y, m, d = trade_date.year, trade_date.month, trade_date.day
    filepath = FACTORS_ROOT / f"year={y}" / f"month={m:02d}" / f"day={d:02d}" / f"factors_{trade_date}.parquet"
    if not filepath.exists():
        return None
    return pd.read_parquet(filepath)


def read_klines(symbol: str) -> pd.DataFrame | None:
    """Read all klines for a symbol."""
    filepath = FACTORS_ROOT / "daily_klines" / f"symbol={symbol}" / f"klines_{symbol}.parquet"
    if not filepath.exists():
        return None
    return pd.read_parquet(filepath)


def read_factors_range(start_date: date, end_date: date) -> pd.DataFrame:
    """Read factor snapshots for a date range."""
    frames = []
    current = pd.Timestamp(start_date)
    end = pd.Timestamp(end_date)
    while current <= end:
        df = read_daily_factors(current.date())
        if df is not None:
            frames.append(df)
        current += pd.Timedelta(days=1)
    if not frames:
        return pd.DataFrame()
    return pd.concat(frames, ignore_index=True)


def list_available_dates() -> list[date]:
    """List all dates with factor data."""
    dates = []
    if not FACTORS_ROOT.exists():
        return dates
    for year_dir in sorted(FACTORS_ROOT.glob("year=*")):
        for month_dir in sorted(year_dir.glob("month=*")):
            for day_dir in sorted(month_dir.glob("day=*")):
                try:
                    y = int(year_dir.name.split("=")[1])
                    m = int(month_dir.name.split("=")[1])
                    d = int(day_dir.name.split("=")[1])
                    dates.append(date(y, m, d))
                except (ValueError, IndexError):
                    continue
    return dates
