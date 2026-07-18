#!/usr/bin/env python3
"""Multi-source data provider for US stock klines and quotes.

Provider priority:
1. EastmoneyDirectProvider - 直接调用东财 push2his API (主源)
2. AkshareProvider - akshare fallback (当前实际主源)
3. YFinanceProvider - emergency fallback

Features:
- Bounded concurrency for batch operations
- Incremental kline fetching (only fetch missing/stale data)
- Retry queue with YFinance fallback
- Provider metrics tracking
- Trading calendar awareness
- EastmoneyDirect cooldown monitoring

Usage:
    provider = DataProvider()
    klines = provider.fetch_klines("NVDA", "2026-01-01", "2026-07-03")
    quote = provider.fetch_realtime_quote("NVDA")

    # Batch fetch with concurrency
    results = provider.fetch_klines_batch(symbols, "2025-01-01", "2026-07-03")
"""
import json
import os
import time
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field, asdict
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any

import pandas as pd
import numpy as np

# Configuration from environment
AKSHARE_KLINE_CONCURRENCY = int(os.environ.get("AKSHARE_KLINE_CONCURRENCY", "5"))
AKSHARE_KLINE_BATCH_SIZE = int(os.environ.get("AKSHARE_KLINE_BATCH_SIZE", "50"))
EASTMONEY_COOLDOWN_SECONDS = int(os.environ.get("EASTMONEY_COOLDOWN_SECONDS", "1800"))  # 30 min
MAX_RETRY_COUNT = 2

# Cache directory
CACHE_DIR = Path(__file__).resolve().parent.parent / "data" / "provider-cache"
METRICS_DIR = Path(__file__).resolve().parent.parent / "data" / "provider-metrics"

# EastMoney API endpoints
KLINE_URL = "https://push2his.eastmoney.com/api/qt/stock/kline/get"
STOCK_GET_URL = "https://push2delay.eastmoney.com/api/qt/stock/get"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/120 Safari/537.36",
    "Referer": "https://quote.eastmoney.com/",
}

DIRECT_OPENER = urllib.request.build_opener(urllib.request.ProxyHandler({}))

KLINE_FIELDS1 = "f1,f2,f3,f4,f5,f6"
KLINE_FIELDS2 = "f51,f52,f53,f54,f55,f56,f57,f58,f59,f60,f61"
STOCK_DETAIL_FIELDS = "f43,f44,f45,f46,f47,f48,f50,f51,f52,f57,f58,f60,f84,f85,f162,f167,f173,f191"

# US stock market holidays 2026 (NYSE observed)
US_MARKET_HOLIDAYS_2026 = {
    date(2026, 1, 1),   # New Year's Day
    date(2026, 1, 19),  # MLK Jr. Day
    date(2026, 2, 16),  # Presidents' Day
    date(2026, 4, 3),   # Good Friday
    date(2026, 5, 25),  # Memorial Day
    date(2026, 6, 19),  # Juneteenth
    date(2026, 7, 3),   # Independence Day observed
    date(2026, 9, 7),   # Labor Day
    date(2026, 11, 26), # Thanksgiving
    date(2026, 12, 25), # Christmas
}


def _fnum(v) -> float | None:
    if v is None or v == "-":
        return None
    try:
        return float(v)
    except (ValueError, TypeError):
        return None


def normalize_us_symbol(symbol: str) -> str:
    return symbol.replace(".", "-")


def secid_candidates(symbol: str) -> list[str]:
    normalized = normalize_us_symbol(symbol)
    return [f"105.{normalized}", f"106.{normalized}"]


def _eastmoney_get(url: str, params: dict, retries: int = 3, timeout: int = 10) -> dict | None:
    query = "&".join(f"{k}={v}" for k, v in params.items())
    full_url = f"{url}?{query}"
    for attempt in range(retries):
        try:
            req = urllib.request.Request(full_url, headers=HEADERS)
            resp = DIRECT_OPENER.open(req, timeout=timeout)
            return json.loads(resp.read())
        except Exception:
            if attempt < retries - 1:
                time.sleep(0.5 * (attempt + 1))
    return None


def is_trading_day(d: date) -> bool:
    """Check if a date is a US stock market trading day."""
    if d.weekday() >= 5:  # Saturday or Sunday
        return False
    return d not in US_MARKET_HOLIDAYS_2026


def next_trading_day(d: date) -> date:
    """Get the next trading day after d."""
    d = d + timedelta(days=1)
    while not is_trading_day(d):
        d += timedelta(days=1)
    return d


def prev_trading_day(d: date) -> date:
    """Get the previous trading day before d."""
    d = d - timedelta(days=1)
    while not is_trading_day(d):
        d -= timedelta(days=1)
    return d


def add_trading_days(d: date, n: int) -> date:
    """Add n trading days to date d."""
    if n >= 0:
        for _ in range(n):
            d = next_trading_day(d)
    else:
        for _ in range(-n):
            d = prev_trading_day(d)
    return d


def latest_us_trading_day(ref_date: date | None = None) -> date:
    """Get the latest US trading day on or before ref_date."""
    if ref_date is None:
        ref_date = date.today()
    while not is_trading_day(ref_date):
        ref_date -= timedelta(days=1)
    return ref_date


@dataclass
class ProviderMetrics:
    """Metrics for a single kline fetch operation."""
    symbol: str = ""
    provider_name: str = ""
    provider_status: str = ""  # available, cached, blocked, failed, fallback
    provider_latency_ms: int = 0
    cache_hit: bool = False
    stale_reason: str = ""
    retry_count: int = 0
    fallback_used: str = ""
    latest_kline_date: str = ""
    error_message: str = ""
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> dict:
        return asdict(self)


class EastmoneyDirectProvider:
    """主源：直接调用东财 push2his API.

    当前从该 IP 被 blocked，但保留代码结构。
    当 API 恢复可用时，自动作为 primary provider。
    """

    name = "eastmoney_direct"
    priority = 1

    def fetch_klines(self, symbol: str, beg: str, end: str, fqt: int = 1) -> list[dict] | None:
        """Fetch daily klines from EastMoney push2his API."""
        params = {
            "secid": secid_candidates(symbol)[0],
            "fields1": KLINE_FIELDS1,
            "fields2": KLINE_FIELDS2,
            "klt": "101",
            "fqt": str(fqt),
            "beg": beg.replace("-", ""),
            "end": end.replace("-", ""),
        }
        payload = _eastmoney_get(KLINE_URL, params, retries=2, timeout=8)
        if not payload or payload.get("data") is None:
            return None

        rows = []
        for raw in (payload["data"].get("klines") or []):
            parts = str(raw).split(",")
            if len(parts) < 11:
                continue
            try:
                datetime.strptime(parts[0], "%Y-%m-%d")
            except ValueError:
                continue
            values = [_fnum(parts[i]) for i in range(1, 11)]
            if any(v is None for v in values):
                continue
            rows.append({
                "date": parts[0],
                "open": values[0],
                "close": values[1],
                "high": values[2],
                "low": values[3],
                "volume": values[4],
                "amount": values[5],
                "amplitude_pct": values[6],
                "pct_chg": values[7],
                "chg": values[8],
                "turnover_rate": values[9],
            })
        return rows if rows else None

    def fetch_realtime_quote(self, symbol: str) -> dict | None:
        """Fetch realtime quote from EastMoney push2 API."""
        normalized = normalize_us_symbol(symbol)
        for secid in secid_candidates(normalized):
            params = {
                "ut": "fa5fd1943c7b386f172d6893dbfba10b",
                "fltt": "2",
                "invt": "2",
                "fields": STOCK_DETAIL_FIELDS,
                "secid": secid,
            }
            payload = _eastmoney_get(STOCK_GET_URL, params, retries=2, timeout=8)
            if not payload or payload.get("data") is None:
                continue
            d = payload["data"]
            latest = _fnum(d.get("f43"))
            prev = _fnum(d.get("f60"))
            if latest is None or prev is None:
                continue
            return {
                "symbol": normalized,
                "name": d.get("f58", ""),
                "latest_price": latest,
                "prev_close": prev,
                "open": _fnum(d.get("f46")),
                "high": _fnum(d.get("f44")),
                "low": _fnum(d.get("f45")),
                "volume": _fnum(d.get("f47")),
                "amount": _fnum(d.get("f48")),
                "pe_ttm": _fnum(d.get("f167")),
                "roe": _fnum(d.get("f173")),
                "week52_high": _fnum(d.get("f51")),
                "week52_low": _fnum(d.get("f52")),
                "as_of": datetime.now().isoformat(),
                "provider": self.name,
            }
        return None


class AkshareProvider:
    """Fallback：akshare（当前实际主源）。

    支持 bounded concurrency 和 incremental fetching。
    """

    name = "akshare"
    priority = 2

    def fetch_klines(self, symbol: str, beg: str, end: str, fqt: int = 1) -> list[dict] | None:
        """Fetch klines for a single symbol."""
        try:
            import akshare as ak
            ticker = normalize_us_symbol(symbol)
            df = ak.stock_us_daily(symbol=ticker, adjust="qfq" if fqt == 1 else "")
            if df is None or df.empty:
                return None

            df["date"] = pd.to_datetime(df["date"])
            df = df.set_index("date").sort_index()
            beg_dt = pd.Timestamp(beg)
            end_dt = pd.Timestamp(end)
            df = df.loc[beg_dt:end_dt]

            if df.empty:
                return None

            rows = []
            for dt, row in df.iterrows():
                rows.append({
                    "date": dt.strftime("%Y-%m-%d"),
                    "open": float(row.get("open", 0)),
                    "close": float(row.get("close", 0)),
                    "high": float(row.get("high", 0)),
                    "low": float(row.get("low", 0)),
                    "volume": float(row.get("volume", 0)),
                    "amount": 0.0,
                    "amplitude_pct": 0.0,
                    "pct_chg": 0.0,
                    "chg": 0.0,
                    "turnover_rate": 0.0,
                })
            return rows if rows else None
        except Exception:
            return None

    def fetch_realtime_quote(self, symbol: str) -> dict | None:
        try:
            import akshare as ak
            ticker = normalize_us_symbol(symbol)
            df = ak.stock_us_spot_em()
            if df is None or df.empty:
                return None
            row = df[df["代码"] == ticker]
            if row.empty:
                return None
            row = row.iloc[0]
            return {
                "symbol": ticker,
                "name": row.get("名称", ""),
                "latest_price": float(row.get("最新价", 0)),
                "prev_close": float(row.get("昨收", 0)),
                "open": float(row.get("今开", 0)),
                "high": float(row.get("最高", 0)),
                "low": float(row.get("最低", 0)),
                "volume": float(row.get("成交量", 0)),
                "amount": float(row.get("成交额", 0)),
                "as_of": datetime.now().isoformat(),
                "provider": self.name,
            }
        except Exception:
            return None


class DataProvider:
    """Multi-source data provider with fallback chain.

    Provider priority:
    - Klines: EastmoneyDirect -> Akshare
    - Quote: EastmoneyDirect -> Akshare

    Features:
    - Bounded concurrency for batch operations
    - Incremental kline fetching
    - Retry queue with approved provider fallbacks
    - Provider metrics tracking
    - EastmoneyDirect cooldown monitoring
    """

    def __init__(self):
        self.eastmoney_direct = EastmoneyDirectProvider()
        self.akshare = AkshareProvider()

        self.kline_providers = [self.akshare, self.eastmoney_direct]
        self.quote_providers = [self.eastmoney_direct, self.akshare]

        self.cache_dir = CACHE_DIR
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.metrics_dir = METRICS_DIR
        self.metrics_dir.mkdir(parents=True, exist_ok=True)

        self._api_status = {
            "eastmoney_kline": "unknown",
            "eastmoney_quote": "unknown",
        }
        self._eastmoney_kline_cooldown_until: float = 0
        self._all_metrics: list[ProviderMetrics] = []

    # ─── Cache helpers ───────────────────────────────────────────────

    def _get_cache_path(self, symbol: str, data_type: str, date_str: str = "") -> Path:
        return self.cache_dir / f"{symbol}_{data_type}_{date_str}.json"

    def _load_cache(self, symbol: str, data_type: str, date_str: str = "", max_age_hours: int = 24) -> Any | None:
        cache_path = self._get_cache_path(symbol, data_type, date_str)
        if cache_path.exists():
            try:
                cached = json.loads(cache_path.read_text())
                cache_time = datetime.fromisoformat(cached.get("_cache_time", "2000-01-01"))
                if (datetime.now() - cache_time).total_seconds() < max_age_hours * 3600:
                    return cached.get("data")
            except Exception:
                pass
        return None

    def _save_cache(self, symbol: str, data_type: str, data: Any, date_str: str = ""):
        cache_path = self._get_cache_path(symbol, data_type, date_str)
        cache_path.write_text(json.dumps({
            "_cache_time": datetime.now().isoformat(),
            "data": data,
        }, ensure_ascii=False, default=str))

    def _get_kline_cache_ttl(self, is_historical: bool = True) -> int:
        """Cache TTL: historical=7 days, latest=1 hour."""
        if is_historical:
            return 7 * 24
        return 1

    def _load_cached_klines(self, symbol: str, beg: str, end: str) -> list[dict] | None:
        """Load klines from cache with appropriate TTL."""
        today = date.today().isoformat()
        is_historical = (end < today)
        ttl = self._get_kline_cache_ttl(is_historical)
        return self._load_cache(symbol, "klines", f"{beg}_{end}", max_age_hours=ttl)

    def _save_klines_cache(self, symbol: str, beg: str, end: str, rows: list[dict]):
        self._save_cache(symbol, "klines", rows, f"{beg}_{end}")

    # ─── EastmoneyDirect cooldown ────────────────────────────────────

    def _is_eastmoney_kline_available(self) -> bool:
        """Check if EastmoneyDirect kline API is available (not in cooldown)."""
        if self._api_status.get("eastmoney_kline") == "blocked":
            if time.time() < self._eastmoney_kline_cooldown_until:
                return False
        return True

    def _mark_eastmoney_kline_blocked(self):
        """Mark EastmoneyDirect kline as blocked with cooldown."""
        self._api_status["eastmoney_kline"] = "blocked"
        self._eastmoney_kline_cooldown_until = time.time() + EASTMONEY_COOLDOWN_SECONDS

    def _mark_eastmoney_kline_available(self):
        """Mark EastmoneyDirect kline as available."""
        self._api_status["eastmoney_kline"] = "available"
        self._eastmoney_kline_cooldown_until = 0

    # ─── API status check ────────────────────────────────────────────

    def check_api_status(self) -> dict[str, str]:
        """Check EastMoney API availability."""
        status = {}

        # Test kline API (respect cooldown)
        if self._is_eastmoney_kline_available():
            try:
                rows = self.eastmoney_direct.fetch_klines("NVDA", "2026-06-01", "2026-06-30")
                if rows:
                    status["eastmoney_kline"] = "available"
                    self._mark_eastmoney_kline_available()
                else:
                    status["eastmoney_kline"] = "blocked"
                    self._mark_eastmoney_kline_blocked()
            except Exception:
                status["eastmoney_kline"] = "blocked"
                self._mark_eastmoney_kline_blocked()
        else:
            status["eastmoney_kline"] = "blocked (cooldown)"

        # Test quote API
        try:
            quote = self.eastmoney_direct.fetch_realtime_quote("NVDA")
            status["eastmoney_quote"] = "available" if quote else "blocked"
        except Exception:
            status["eastmoney_quote"] = "blocked"

        self._api_status.update(status)
        return status

    # ─── Single symbol kline fetch ───────────────────────────────────

    def fetch_klines(self, symbol: str, beg: str, end: str, fqt: int = 1) -> tuple[list[dict], str, dict]:
        """Fetch klines with provider fallback.

        Returns (rows, provider_name, metadata).
        """
        metrics = ProviderMetrics(symbol=symbol)

        # Check cache first
        cached = self._load_cached_klines(symbol, beg, end)
        if cached:
            metrics.provider_name = "cache"
            metrics.provider_status = "cached"
            metrics.cache_hit = True
            metrics.latest_kline_date = cached[-1]["date"] if cached else ""
            self._record_metrics(metrics)
            return cached, "cache", metrics.to_dict()

        # Try providers in order
        providers_to_try = []
        if self._is_eastmoney_kline_available():
            providers_to_try.append(self.eastmoney_direct)
        providers_to_try.append(self.akshare)

        for provider in providers_to_try:
            for retry in range(MAX_RETRY_COUNT + 1):
                try:
                    start_time = time.time()
                    rows = provider.fetch_klines(symbol, beg, end, fqt)
                    latency_ms = int((time.time() - start_time) * 1000)

                    if rows:
                        self._save_klines_cache(symbol, beg, end, rows)
                        metrics.provider_name = provider.name
                        metrics.provider_status = "available"
                        metrics.provider_latency_ms = latency_ms
                        metrics.retry_count = retry
                        metrics.latest_kline_date = rows[-1]["date"] if rows else ""
                        self._record_metrics(metrics)
                        return rows, provider.name, metrics.to_dict()

                    # No data returned
                    if provider.name.startswith("eastmoney"):
                        self._mark_eastmoney_kline_blocked()
                    break  # Don't retry if provider returned empty

                except Exception as e:
                    if retry < MAX_RETRY_COUNT:
                        time.sleep(0.5 * (retry + 1))
                        continue
                    # All retries exhausted
                    metrics.error_message = f"{provider.name}: {type(e).__name__}: {e}"
                    if provider.name.startswith("eastmoney"):
                        self._mark_eastmoney_kline_blocked()
                    break

        metrics.provider_name = "none"
        metrics.provider_status = "unavailable"
        self._record_metrics(metrics)
        return [], "none", metrics.to_dict()

    def fetch_realtime_quote(self, symbol: str) -> tuple[dict | None, str, dict]:
        """Fetch realtime quote with provider fallback."""
        # Check cache (30s for realtime)
        cached = self._load_cache(symbol, "quote", "realtime", max_age_hours=0.008)
        if cached:
            return cached, "cache", {"provider_status": "cached"}

        for provider in self.quote_providers:
            try:
                start_time = time.time()
                quote = provider.fetch_realtime_quote(symbol)
                latency_ms = int((time.time() - start_time) * 1000)

                if quote and quote.get("latest_price", 0) > 0:
                    self._save_cache(symbol, "quote", quote, "realtime")
                    metadata = {
                        "provider_status": "available",
                        "provider_latency_ms": latency_ms,
                    }
                    return quote, provider.name, metadata
            except Exception:
                continue

        return None, "none", {"provider_status": "unavailable"}

    def fetch_batch_quotes(self, fs: str = "m:105+t:1,m:105+t:2,m:105+t:3", page_size: int = 100) -> dict[str, dict]:
        """Batch fetch US stock quotes via push2delay paginated API.

        Aligned with xiaogu runner_v2 approach: paginated calls get all quotes
        with price, pct_chg, volume, open/high/low/close — no per-symbol API calls needed.

        Returns dict mapping normalized symbol -> quote dict.
        """
        all_items = []
        page = 1
        while True:
            params = (
                f"pn={page}&pz={page_size}&po=1&np=1"
                f"&ut=bd1d9ddb04089700cf9c27f6f7426281"
                f"&fltt=2&invt=2&fid=f3&fs={fs}"
                f"&fields=f12,f13,f14,f2,f3,f4,f5,f6,f15,f16,f17,f18,f20,f21,f62,f115"
            )
            url = f"https://push2delay.eastmoney.com/api/qt/clist/get?{params}"
            try:
                req = urllib.request.Request(url, headers=HEADERS)
                resp = DIRECT_OPENER.open(req, timeout=15)
                data = json.loads(resp.read())
                diff = data.get("data", {}).get("diff", []) or []
                if not diff:
                    break
                all_items.extend(diff)
                if len(diff) < page_size:
                    break
                page += 1
                time.sleep(0.05)
            except Exception:
                break

        quotes = {}
        for item in all_items:
            code = str(item.get("f12", ""))
            if not code:
                continue
            symbol = normalize_us_symbol(code)
            price = _fnum(item.get("f2"))
            if price is None or price <= 0:
                continue
            quotes[symbol] = {
                "symbol": symbol,
                "name": str(item.get("f14", "")),
                "latest_price": price,
                "pct_chg": _fnum(item.get("f3")),
                "chg": _fnum(item.get("f4")),
                "volume": _fnum(item.get("f5")),
                "amount": _fnum(item.get("f6")),
                "high": _fnum(item.get("f15")),
                "low": _fnum(item.get("f16")),
                "open": _fnum(item.get("f17")),
                "prev_close": _fnum(item.get("f18")),
                "market_cap": _fnum(item.get("f20")),
                "float_market_cap": _fnum(item.get("f21")),
                "net_inflow": _fnum(item.get("f62")),
                "pe_ttm": _fnum(item.get("f115")),
                "source": "eastmoney_batch",
                "as_of": datetime.now().isoformat(),
            }
        return quotes

    def fetch_financials(self, symbol: str) -> dict | None:
        """Return no financials until an approved provider is integrated."""
        return None

    def fetch_klines_to_dataframe(self, symbol: str, beg: str, end: str, fqt: int = 1) -> tuple[pd.DataFrame, str]:
        """Fetch klines and return as DataFrame."""
        rows, provider, metadata = self.fetch_klines(symbol, beg, end, fqt)
        if not rows:
            return pd.DataFrame(), provider

        df = pd.DataFrame(rows)
        df["date"] = pd.to_datetime(df["date"])
        df = df.set_index("date").sort_index()
        df = df.rename(columns={
            "open": "Open",
            "high": "High",
            "low": "Low",
            "close": "Close",
            "volume": "Volume",
        })
        df["Adj Close"] = df["Close"]
        df["Dividends"] = 0.0
        df["Stock Splits"] = 0.0
        df["symbol"] = normalize_us_symbol(symbol)
        df.index = pd.DatetimeIndex(df.index).normalize()
        return df[["Open", "High", "Low", "Close", "Adj Close", "Volume", "Dividends", "Stock Splits", "symbol"]], provider

    # ─── Batch fetch with concurrency ────────────────────────────────

    def fetch_klines_batch(
        self,
        symbols: list[str],
        beg: str,
        end: str,
        fqt: int = 1,
        concurrency: int | None = None,
        batch_size: int | None = None,
    ) -> dict[str, tuple[list[dict], str, dict]]:
        """Fetch klines for multiple symbols with bounded concurrency.

        Features:
        - Processes in batches (default 50)
        - Bounded concurrency (default 5)
        - Incremental: skips cached historical data
        - Writes cache per-batch, not after all symbols complete
        - Single symbol failure doesn't block others
        - Retry queue for failed symbols

        Returns dict mapping symbol -> (rows, provider_name, metadata)
        """
        if concurrency is None:
            concurrency = AKSHARE_KLINE_CONCURRENCY
        if batch_size is None:
            batch_size = AKSHARE_KLINE_BATCH_SIZE

        results: dict[str, tuple[list[dict], str, dict]] = {}
        retry_queue: list[tuple[str, int]] = []  # (symbol, retry_count)

        # Phase 1: Check cache, build fetch list
        to_fetch: list[str] = []
        for symbol in symbols:
            cached = self._load_cached_klines(symbol, beg, end)
            if cached:
                results[symbol] = (cached, "cache", {
                    "provider_status": "cached",
                    "cache_hit": True,
                    "latest_kline_date": cached[-1]["date"] if cached else "",
                })
            else:
                to_fetch.append(symbol)

        if not to_fetch:
            return results

        # Phase 2: Fetch in batches with concurrency
        def fetch_one(symbol: str) -> tuple[str, list[dict], str, dict]:
            """Fetch one symbol through the approved provider chain."""
            rows, provider_name, metadata = self.fetch_klines(symbol, beg, end, fqt)
            return symbol, rows, provider_name, metadata

        # Process in batches
        for i in range(0, len(to_fetch), batch_size):
            batch = to_fetch[i:i + batch_size]

            with ThreadPoolExecutor(max_workers=concurrency) as executor:
                futures = {executor.submit(fetch_one, sym): sym for sym in batch}
                for future in as_completed(futures):
                    try:
                        symbol, rows, provider_name, meta = future.result()
                        if rows:
                            self._save_klines_cache(symbol, beg, end, rows)
                            results[symbol] = (rows, provider_name, meta)
                        else:
                            # Add to retry queue
                            retry_count = meta.get("retry_count", 0)
                            if retry_count < MAX_RETRY_COUNT:
                                retry_queue.append((symbol, retry_count + 1))
                            else:
                                results[symbol] = ([], provider_name, meta)
                        self._record_metrics(ProviderMetrics(**{
                            "symbol": symbol,
                            "provider_name": provider_name,
                            "provider_status": meta.get("provider_status", ""),
                            "provider_latency_ms": meta.get("provider_latency_ms", 0),
                            "cache_hit": meta.get("cache_hit", False),
                            "retry_count": meta.get("retry_count", 0),
                            "fallback_used": meta.get("fallback_used", ""),
                            "latest_kline_date": meta.get("latest_kline_date", ""),
                            "error_message": meta.get("error_message", ""),
                        }))
                    except Exception as e:
                        sym = futures[future]
                        results[sym] = ([], "error", {"error_message": str(e)})

        # Phase 3: Process retry queue
        if retry_queue:
            retry_symbols = [s for s, _ in retry_queue]
            with ThreadPoolExecutor(max_workers=min(concurrency, len(retry_symbols))) as executor:
                futures = {executor.submit(fetch_one, sym): sym for sym in retry_symbols}
                for future in as_completed(futures):
                    try:
                        symbol, rows, provider_name, meta = future.result()
                        if rows:
                            self._save_klines_cache(symbol, beg, end, rows)
                            results[symbol] = (rows, provider_name, meta)
                        else:
                            results[symbol] = ([], provider_name, meta)
                    except Exception as e:
                        sym = futures[future]
                        results[sym] = ([], "error", {"error_message": str(e)})

        return results

    # ─── Metrics ─────────────────────────────────────────────────────

    def _record_metrics(self, metrics: ProviderMetrics):
        """Record metrics for a kline fetch operation."""
        self._all_metrics.append(metrics)

    def flush_metrics(self):
        """Write accumulated metrics to file."""
        if not self._all_metrics:
            return
        metrics_file = self.metrics_dir / f"metrics_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        data = [m.to_dict() for m in self._all_metrics]
        metrics_file.write_text(json.dumps(data, ensure_ascii=False, indent=2))
        self._all_metrics.clear()

    def get_metrics_summary(self) -> dict:
        """Get summary of all recorded metrics."""
        if not self._all_metrics:
            return {}

        total = len(self._all_metrics)
        success = sum(1 for m in self._all_metrics if m.provider_status in ("available", "cached"))
        failed = sum(1 for m in self._all_metrics if m.provider_status == "failed")
        cache_hits = sum(1 for m in self._all_metrics if m.cache_hit)
        akshare_used = sum(1 for m in self._all_metrics if m.provider_name == "akshare")
        eastmoney_blocked = sum(1 for m in self._all_metrics if "blocked" in m.provider_status)

        latencies = [m.provider_latency_ms for m in self._all_metrics if m.provider_latency_ms > 0]
        avg_latency = int(sum(latencies) / len(latencies)) if latencies else 0
        p95_latency = int(sorted(latencies)[int(len(latencies) * 0.95)]) if latencies else 0

        return {
            "total_symbols": total,
            "kline_success_count": success,
            "kline_failed_count": failed,
            "cache_hit_rate": round(cache_hits / total * 100, 1) if total else 0,
            "akshare_used_count": akshare_used,
            "eastmoney_blocked_count": eastmoney_blocked,
            "avg_provider_latency_ms": avg_latency,
            "p95_provider_latency_ms": p95_latency,
        }


# Singleton instance
_provider = None


def get_provider() -> DataProvider:
    global _provider
    if _provider is None:
        _provider = DataProvider()
    return _provider


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Multi-source data provider")
    parser.add_argument("--symbol", default="NVDA")
    parser.add_argument("--action", choices=["klines", "quote", "status", "batch"], default="klines")
    parser.add_argument("--beg", default="2026-01-01")
    parser.add_argument("--end", default="2026-07-03")
    parser.add_argument("--symbols", nargs="+", help="Symbols for batch mode")
    args = parser.parse_args()

    provider = get_provider()

    if args.action == "status":
        status = provider.check_api_status()
        print(json.dumps(status, indent=2))
    elif args.action == "batch":
        symbols = args.symbols or ["NVDA", "TSLA", "AMD"]
        start = time.time()
        results = provider.fetch_klines_batch(symbols, args.beg, args.end)
        elapsed = time.time() - start

        summary = provider.get_metrics_summary()
        summary["total_runtime_seconds"] = round(elapsed, 2)
        print(json.dumps(summary, indent=2))
        provider.flush_metrics()
    elif args.action == "klines":
        df, src = provider.fetch_klines_to_dataframe(args.symbol, args.beg, args.end)
        print(f"Provider: {src}")
        print(f"Rows: {len(df)}")
        if not df.empty:
            print(df.tail(5))
    else:
        quote, src, meta = provider.fetch_realtime_quote(args.symbol)
        print(f"Provider: {src}")
        print(json.dumps(quote, indent=2, ensure_ascii=False))
