#!/usr/bin/env python3
"""Auditable multi-source market-data provider for US-stock research.

Only this module owns market-data API transport. Its Scrapy bridge provides
bounded retries, timeout, per-domain concurrency, request de-duplication, and
response audit records. Provider fallbacks are explicit in returned metadata.

Historical priority:
1. Yahoo Finance chart API (bounded optional source)
2. EastMoney API
3. Akshare fallback

Usage:
    provider = DataProvider()
    klines = provider.fetch_klines("NVDA", "2026-01-01", "2026-07-03")
    quote = provider.fetch_realtime_quote("NVDA")

    # Batch fetch with concurrency
    results = provider.fetch_klines_batch(symbols, "2025-01-01", "2026-07-03")
"""
import json
import hashlib
import ipaddress
import os
import re
import threading
import time
from urllib.parse import urlencode, urlparse
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field, asdict
from datetime import date, datetime
from pathlib import Path
from typing import Any

import pandas as pd
import numpy as np

try:
    from scrapy import Request, Spider, signals
    from scrapy.crawler import CrawlerProcess
    from scrapy.exceptions import DontCloseSpider
    from twisted.internet import reactor

    SCRAPY_AVAILABLE = True
except ImportError:  # pragma: no cover - runtime dependency check
    SCRAPY_AVAILABLE = False

# Configuration from environment
AKSHARE_KLINE_CONCURRENCY = int(os.environ.get("AKSHARE_KLINE_CONCURRENCY", "5"))
AKSHARE_KLINE_BATCH_SIZE = int(os.environ.get("AKSHARE_KLINE_BATCH_SIZE", "50"))
EASTMONEY_COOLDOWN_SECONDS = int(os.environ.get("EASTMONEY_COOLDOWN_SECONDS", "1800"))  # 30 min
YAHOO_COOLDOWN_SECONDS = int(os.environ.get("YAHOO_COOLDOWN_SECONDS", "900"))
MAX_RETRY_COUNT = 2
SCRAPY_DOWNLOAD_TIMEOUT = int(os.environ.get("MARKET_DATA_DOWNLOAD_TIMEOUT", "12"))
SCRAPY_RETRY_TIMES = int(os.environ.get("MARKET_DATA_RETRY_TIMES", "1"))
SCRAPY_CONCURRENT_REQUESTS = int(os.environ.get("MARKET_DATA_CONCURRENT_REQUESTS", "8"))
SCRAPY_CONCURRENT_PER_DOMAIN = int(os.environ.get("MARKET_DATA_CONCURRENT_PER_DOMAIN", "2"))
BROWSER_CAPTURE_TIMEOUT = int(os.environ.get("MARKET_DATA_BROWSER_TIMEOUT", "20"))
BROWSER_KLINE_MAX_CAPTURES = int(os.environ.get("MARKET_DATA_BROWSER_KLINE_MAX_CAPTURES", "3"))

# Cache directory
CACHE_DIR = Path(__file__).resolve().parent.parent / "data" / "provider-cache"
METRICS_DIR = Path(__file__).resolve().parent.parent / "data" / "provider-metrics"

# EastMoney API endpoints
KLINE_URL = "https://push2his.eastmoney.com/api/qt/stock/kline/get"
STOCK_GET_URL = "https://push2delay.eastmoney.com/api/qt/stock/get"
YAHOO_CHART_URL = "https://query1.finance.yahoo.com/v8/finance/chart"
EASTMONEY_US_PAGE_URL = "https://quote.eastmoney.com/us/{symbol}.html"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/120 Safari/537.36",
    "Referer": "https://quote.eastmoney.com/",
}

KLINE_FIELDS1 = "f1,f2,f3,f4,f5,f6"
KLINE_FIELDS2 = "f51,f52,f53,f54,f55,f56,f57,f58,f59,f60,f61"
STOCK_DETAIL_FIELDS = "f43,f44,f45,f46,f47,f48,f50,f51,f52,f57,f58,f60,f84,f85,f162,f167,f173,f191"

from market_calendar import (
    CALENDAR,
    add_trading_days,
    is_trading_day,
    latest_us_trading_day,
    next_trading_day,
    prev_trading_day,
)

US_MARKET_HOLIDAYS_2026 = CALENDAR.holidays(2026)


def _fnum(v) -> float | None:
    if v is None:
        return None
    try:
        text = str(v).strip().replace(",", "")
        if text in {"", "-", "--"}:
            return None
        return float(text)
    except (ValueError, TypeError):
        return None


def normalize_us_symbol(symbol: str) -> str:
    return symbol.replace(".", "-")


def secid_candidates(symbol: str) -> list[str]:
    normalized = normalize_us_symbol(symbol)
    return [f"105.{normalized}", f"106.{normalized}"]


def _url_with_query(url: str, params: dict[str, Any]) -> str:
    return f"{url}?{urlencode(params)}"


def _is_loopback_url(url: str) -> bool:
    """Keep local health checks and fixtures out of environment HTTP proxies."""
    hostname = urlparse(url).hostname
    if hostname == "localhost":
        return True
    try:
        return bool(hostname and ipaddress.ip_address(hostname).is_loopback)
    except ValueError:
        return False


def _parse_eastmoney_browser_klines(payload: dict[str, Any], beg: str, end: str) -> list[dict]:
    """Normalize complete daily OHLCV rows extracted from an EastMoney page DOM."""
    rows_by_date: dict[str, dict[str, Any]] = {}
    beg_date = pd.Timestamp(beg).date()
    end_date = pd.Timestamp(end).date()
    for raw in payload.get("rows") or []:
        if not isinstance(raw, dict):
            continue
        try:
            row_date = pd.Timestamp(raw.get("date")).date()
        except (TypeError, ValueError):
            continue
        if not beg_date <= row_date <= end_date:
            continue
        values = {key: _fnum(raw.get(key)) for key in ("open", "close", "high", "low", "volume")}
        if any(value is None for value in values.values()):
            continue
        rows_by_date[row_date.isoformat()] = {
            "date": row_date.isoformat(),
            **values,
            "amount": _fnum(raw.get("amount")),
            "adj_close": _fnum(raw.get("adj_close")) or values["close"],
            "amplitude_pct": _fnum(raw.get("amplitude_pct")),
            "pct_chg": _fnum(raw.get("pct_chg")),
            "chg": _fnum(raw.get("chg")),
            "turnover_rate": _fnum(raw.get("turnover_rate")),
        }
    return [rows_by_date[key] for key in sorted(rows_by_date)]


class MarketDataHttpError(RuntimeError):
    """A completed non-success HTTP response from the Scrapy transport."""

    def __init__(self, status: int | None, url: str):
        self.status = status
        self.url = url
        super().__init__(f"MARKET_DATA_HTTP_{status or 'FAILED'}: {url}")


@dataclass
class _ScrapyRequestState:
    url: str
    event: threading.Event = field(default_factory=threading.Event)
    body: str | None = None
    error: Exception | None = None


def market_data_scrapy_settings() -> dict[str, Any]:
    """Return the sole network policy for public market-data API requests."""
    return {
        "BOT_NAME": "xiaomei_market_data",
        "DOWNLOAD_TIMEOUT": SCRAPY_DOWNLOAD_TIMEOUT,
        "RETRY_TIMES": SCRAPY_RETRY_TIMES,
        "RETRY_HTTP_CODES": [408, 429, 500, 502, 503, 504],
        "CONCURRENT_REQUESTS": SCRAPY_CONCURRENT_REQUESTS,
        "CONCURRENT_REQUESTS_PER_DOMAIN": SCRAPY_CONCURRENT_PER_DOMAIN,
        "TWISTED_REACTOR": os.environ.get(
            "MARKET_DATA_TWISTED_REACTOR",
            "twisted.internet.epollreactor.EPollReactor",
        ),
        "LOG_ENABLED": False,
        "TELNETCONSOLE_ENABLED": False,
    }


class _MarketDataApiSpider(Spider if SCRAPY_AVAILABLE else object):
    name = "xiaomei_market_data_api"

    def __init__(self, bridge=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.bridge = bridge
        self._crawler = None

    @classmethod
    def from_crawler(cls, crawler, *args, **kwargs):
        spider = super().from_crawler(crawler, *args, **kwargs)
        spider._crawler = crawler
        crawler.signals.connect(spider._on_opened, signal=signals.spider_opened)
        crawler.signals.connect(spider._on_idle, signal=signals.spider_idle)
        return spider

    def start_requests(self):
        return ()

    def _on_opened(self):
        self.bridge._mark_ready(self._crawler, self)

    def _on_idle(self):
        raise DontCloseSpider

    def parse(self, response):
        self.bridge._complete_response(response)

    def on_error(self, failure):
        self.bridge._complete_error(failure)


class ScrapyApiBridge:
    """One long-lived Scrapy download owner for market-data API requests."""

    def __init__(self):
        self._lock = threading.Lock()
        self._ready = threading.Event()
        self._startup_error: Exception | None = None
        self._crawler = None
        self._spider = None
        self._process = None
        self._states: dict[str, _ScrapyRequestState] = {}
        self._cache: dict[str, str] = {}
        self._audit: list[dict[str, Any]] = []
        self._cache_hits = 0
        self._started = False

    def start(self) -> None:
        if not SCRAPY_AVAILABLE:
            raise RuntimeError("SCRAPY_MARKET_DATA_TRANSPORT_UNAVAILABLE")
        with self._lock:
            if not self._started:
                self._started = True
                thread = threading.Thread(
                    target=self._run_reactor,
                    name="xiaomei-market-data-reactor",
                    daemon=True,
                )
                thread.start()
        if not self._ready.wait(timeout=15):
            raise RuntimeError("SCRAPY_MARKET_DATA_START_TIMEOUT")
        if self._startup_error is not None:
            raise RuntimeError("SCRAPY_MARKET_DATA_START_FAILED") from self._startup_error

    def _run_reactor(self) -> None:
        try:
            self._process = CrawlerProcess(settings=market_data_scrapy_settings())
            self._process.crawl(_MarketDataApiSpider, bridge=self)
            self._process.start(stop_after_crawl=False, install_signal_handlers=False)
        except Exception as exc:  # pragma: no cover - startup environment failure
            self._startup_error = exc
            self._ready.set()

    def _mark_ready(self, crawler, spider) -> None:
        self._crawler = crawler
        self._spider = spider
        self._ready.set()

    def fetch_json(self, url: str) -> dict[str, Any]:
        try:
            payload = json.loads(self.fetch_text(url))
        except json.JSONDecodeError as exc:
            raise RuntimeError(f"MARKET_DATA_INVALID_JSON: {url}") from exc
        if not isinstance(payload, dict):
            raise RuntimeError(f"MARKET_DATA_JSON_OBJECT_REQUIRED: {url}")
        return payload

    def fetch_text(self, url: str) -> str:
        self.start()
        with self._lock:
            cached = self._cache.get(url)
            if cached is not None:
                self._cache_hits += 1
                return cached
            state = self._states.get(url)
            if state is None:
                state = _ScrapyRequestState(url=url)
                self._states[url] = state
                reactor.callFromThread(self._schedule, state)

        timeout = SCRAPY_DOWNLOAD_TIMEOUT * (SCRAPY_RETRY_TIMES + 1) + 15
        if not state.event.wait(timeout=timeout):
            with self._lock:
                self._states.pop(url, None)
            raise TimeoutError(f"SCRAPY_MARKET_DATA_REQUEST_TIMEOUT: {url}")
        if state.error is not None:
            raise state.error
        return state.body or ""

    def _schedule(self, state: _ScrapyRequestState) -> None:
        meta = {"bridge_url": state.url, "handle_httpstatus_all": True}
        if _is_loopback_url(state.url):
            meta["proxy"] = None
        request = Request(
            state.url,
            callback=self._spider.parse,
            errback=self._spider.on_error,
            headers=HEADERS,
            dont_filter=True,
            meta=meta,
        )
        self._crawler.engine.crawl(request)

    def _complete_response(self, response) -> None:
        url = response.meta["bridge_url"]
        body = response.text
        status = int(response.status)
        error = None if 200 <= status < 300 else MarketDataHttpError(status, url)
        self._complete(
            url,
            body=body,
            error=error,
            status=status,
            retry_count=int(response.request.meta.get("retry_times", 0)),
        )

    def _complete_error(self, failure) -> None:
        request = getattr(failure, "request", None)
        url = request.meta.get("bridge_url") if request is not None else "unknown"
        retry_count = int(request.meta.get("retry_times", 0)) if request is not None else 0
        self._complete(
            url,
            error=MarketDataHttpError(None, url),
            status=None,
            retry_count=retry_count,
        )

    def _complete(
        self,
        url: str,
        body: str | None = None,
        error: Exception | None = None,
        status: int | None = None,
        retry_count: int = 0,
    ) -> None:
        with self._lock:
            state = self._states.pop(url, None)
            if state is None:
                return
            if error is None and body is not None:
                self._cache[url] = body
            self._audit.append(
                {
                    "url": url,
                    "domain": re.sub(r"^https?://([^/]+).*$", r"\1", url),
                    "status": status,
                    "retry_count": retry_count,
                    "response_sha256": hashlib.sha256((body or "").encode("utf-8")).hexdigest(),
                    "response_bytes": len((body or "").encode("utf-8")),
                    "error": repr(error) if error is not None else "",
                    "transport": "scrapy_api_bridge",
                    "completed_at": datetime.now().isoformat(),
                }
            )
            state.body = body
            state.error = error
            state.event.set()

    def audit_snapshot(self) -> dict[str, Any]:
        with self._lock:
            records = list(self._audit)
            domains: dict[str, dict[str, int]] = {}
            for record in records:
                domain = record["domain"]
                summary = domains.setdefault(
                    domain,
                    {"request_count": 0, "success_count": 0, "error_count": 0, "retry_count": 0},
                )
                summary["request_count"] += 1
                summary["success_count"] += int(not record["error"])
                summary["error_count"] += int(bool(record["error"]))
                summary["retry_count"] += int(record["retry_count"])
            return {
                "transport": "scrapy_api_bridge",
                "request_count": len(records),
                "cache_hit_count": self._cache_hits,
                "domains": domains,
                "records": records,
            }





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
    source_attempts: list[dict[str, Any]] = field(default_factory=list)
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> dict:
        return asdict(self)


class EastmoneyDirectProvider:
    """EastMoney API provider using the module-owned Scrapy transport."""

    name = "eastmoney_direct"
    priority = 2

    def __init__(self, transport: ScrapyApiBridge):
        self.transport = transport

    def _fetch_json(self, url: str, params: dict[str, Any]) -> dict[str, Any]:
        return self.transport.fetch_json(_url_with_query(url, params))

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
        payload = self._fetch_json(KLINE_URL, params)
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
            payload = self._fetch_json(STOCK_GET_URL, params)
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


class EastmoneyBrowserKlineProvider:
    """Bounded public-page OHLCV fallback using CloakBrowser Playwright."""

    name = "eastmoney_browser_page"
    priority = 3
    schema_version = "eastmoney_browser_dom_ohlcv_v1"

    _EXTRACT_SCRIPT = r"""
JSON.stringify((() => {
  const text = (value) => String(value ?? '').replace(/,/g, '').trim();
  const headersFor = (table) => Array.from(table.querySelectorAll('tr')).find((row) =>
    Array.from(row.querySelectorAll('th,td')).some((cell) => /日期|date/i.test(cell.innerText))
  );
  const indexOf = (headers, names) => headers.findIndex((header) =>
    names.some((name) => header.includes(name))
  );
  const rows = [];
  for (const table of document.querySelectorAll('table')) {
    const headerRow = headersFor(table);
    if (!headerRow) continue;
    const headers = Array.from(headerRow.querySelectorAll('th,td')).map((cell) => text(cell.innerText).toLowerCase());
    const positions = {
      date: indexOf(headers, ['日期', 'date']),
      open: indexOf(headers, ['开盘', 'open']),
      close: indexOf(headers, ['收盘', 'close']),
      high: indexOf(headers, ['最高', 'high']),
      low: indexOf(headers, ['最低', 'low']),
      volume: indexOf(headers, ['成交量', 'volume']),
      amount: indexOf(headers, ['成交额', 'amount']),
    };
    if (Object.values(positions).slice(0, 6).some((position) => position < 0)) continue;
    for (const row of Array.from(table.querySelectorAll('tr'))) {
      if (row === headerRow) continue;
      const cells = Array.from(row.querySelectorAll('td')).map((cell) => text(cell.innerText));
      if (cells.length <= Math.max(...Object.values(positions).filter((position) => position >= 0))) continue;
      rows.push(Object.fromEntries(Object.entries(positions)
        .filter(([, position]) => position >= 0)
        .map(([field, position]) => [field, cells[position]])));
    }
  }
  return {
    schema_version: 'eastmoney_browser_dom_ohlcv_v1',
    url: location.href,
    title: document.title,
    rows,
  };
})())
"""

    def __init__(self):
        self._lock = threading.Lock()
        self._capture_count = 0
        self._local = threading.local()

    def _set_capture_metadata(self, **metadata: Any) -> None:
        self._local.capture_metadata = metadata

    def source_attempt_metadata(self) -> dict[str, Any]:
        return dict(getattr(self._local, "capture_metadata", {}))

    def _capture_page_payload(self, symbol: str) -> dict[str, Any]:
        url = EASTMONEY_US_PAGE_URL.format(symbol=normalize_us_symbol(symbol))
        browser = None
        try:
            from cloakbrowser import launch

            browser = launch(headless=True)
            page = browser.new_page()
            page.goto(url, wait_until="domcontentloaded", timeout=BROWSER_CAPTURE_TIMEOUT * 1000)
            page.wait_for_timeout(2500)
            text = page.evaluate(self._EXTRACT_SCRIPT)
        except Exception as exc:
            raise RuntimeError(f"EASTMONEY_BROWSER_CAPTURE_UNAVAILABLE: {exc}") from exc
        finally:
            if browser is not None:
                browser.close()

        if not isinstance(text, str):
            raise RuntimeError("EASTMONEY_BROWSER_INVALID_PAGE_PAYLOAD")
        try:
            payload = json.loads(text)
        except json.JSONDecodeError as exc:
            raise RuntimeError("EASTMONEY_BROWSER_INVALID_PAGE_PAYLOAD") from exc
        if not isinstance(payload, dict):
            raise RuntimeError("EASTMONEY_BROWSER_PAGE_OBJECT_REQUIRED")

        self._set_capture_metadata(
            browser_transport="cloakbrowser_playwright",
            endpoint_kind="public_page_dom",
            page_url=str(payload.get("url") or url),
            page_title=str(payload.get("title") or ""),
            schema_version=str(payload.get("schema_version") or self.schema_version),
            page_sha256=hashlib.sha256(text.encode("utf-8")).hexdigest(),
            captured_at=datetime.now().isoformat(),
        )
        return payload

    def fetch_klines(self, symbol: str, beg: str, end: str, fqt: int = 1) -> list[dict] | None:
        del fqt
        self._set_capture_metadata(
            browser_transport="cloakbrowser_playwright",
            endpoint_kind="public_page_dom",
            page_url=EASTMONEY_US_PAGE_URL.format(symbol=normalize_us_symbol(symbol)),
            schema_version=self.schema_version,
        )
        with self._lock:
            if self._capture_count >= BROWSER_KLINE_MAX_CAPTURES:
                raise RuntimeError("EASTMONEY_BROWSER_CAPTURE_LIMIT_REACHED")
            self._capture_count += 1
            payload = self._capture_page_payload(symbol)
        return _parse_eastmoney_browser_klines(payload, beg, end) or None


class YahooChartProvider:
    """Optional Yahoo Finance chart API source for daily historical OHLCV."""

    name = "yahoo_chart_api"
    priority = 1

    def __init__(self, transport: ScrapyApiBridge):
        self.transport = transport

    def fetch_klines(self, symbol: str, beg: str, end: str, fqt: int = 1) -> list[dict] | None:
        del fqt  # Yahoo chart response is already adjusted through adjclose.
        start = int(pd.Timestamp(beg, tz="UTC").timestamp())
        end_exclusive = int((pd.Timestamp(end, tz="UTC") + pd.Timedelta(days=1)).timestamp())
        url = _url_with_query(
            f"{YAHOO_CHART_URL}/{normalize_us_symbol(symbol)}",
            {
                "period1": start,
                "period2": end_exclusive,
                "interval": "1d",
                "events": "history",
                "includeAdjustedClose": "true",
            },
        )
        payload = self.transport.fetch_json(url)
        chart = payload.get("chart") or {}
        result = chart.get("result") or []
        if not result:
            return None
        panel = result[0]
        timestamps = panel.get("timestamp") or []
        quotes = (panel.get("indicators") or {}).get("quote") or []
        if not timestamps or not quotes:
            return None
        quote = quotes[0] or {}
        adjclose_rows = (panel.get("indicators") or {}).get("adjclose") or []
        adjcloses = (adjclose_rows[0] or {}).get("adjclose") if adjclose_rows else []

        rows: list[dict[str, Any]] = []
        for index, timestamp in enumerate(timestamps):
            values = {
                "open": _fnum((quote.get("open") or [None])[index] if index < len(quote.get("open") or []) else None),
                "close": _fnum((quote.get("close") or [None])[index] if index < len(quote.get("close") or []) else None),
                "high": _fnum((quote.get("high") or [None])[index] if index < len(quote.get("high") or []) else None),
                "low": _fnum((quote.get("low") or [None])[index] if index < len(quote.get("low") or []) else None),
                "volume": _fnum((quote.get("volume") or [None])[index] if index < len(quote.get("volume") or []) else None),
            }
            if any(value is None for value in values.values()):
                continue
            close = float(values["close"])
            adjclose = _fnum(adjcloses[index]) if index < len(adjcloses or []) else close
            row_date = datetime.utcfromtimestamp(int(timestamp)).strftime("%Y-%m-%d")
            rows.append(
                {
                    "date": row_date,
                    "open": values["open"],
                    "close": close,
                    "high": values["high"],
                    "low": values["low"],
                    "volume": values["volume"],
                    "amount": close * float(values["volume"]),
                    "adj_close": adjclose if adjclose is not None else close,
                    "amplitude_pct": None,
                    "pct_chg": None,
                    "chg": None,
                    "turnover_rate": None,
                }
            )
        return rows or None


class AkshareProvider:
    """Fallback：akshare（当前实际主源）。

    支持 bounded concurrency 和 incremental fetching。
    """

    name = "akshare"
    priority = 3

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
    - Klines: Yahoo chart API -> EastMoney API -> EastMoney browser page -> Akshare
    - Quote: EastmoneyDirect -> Akshare

    Features:
    - Bounded concurrency for batch operations
    - Incremental kline fetching
    - Retry queue with explicit provider fallbacks
    - Provider metrics tracking
    - EastmoneyDirect cooldown monitoring
    """

    def __init__(self):
        self.transport = ScrapyApiBridge()
        self.yahoo_chart = YahooChartProvider(self.transport)
        self.eastmoney_direct = EastmoneyDirectProvider(self.transport)
        self.eastmoney_browser = EastmoneyBrowserKlineProvider()
        self.akshare = AkshareProvider()

        self.kline_providers = [
            self.yahoo_chart,
            self.eastmoney_direct,
            self.eastmoney_browser,
            self.akshare,
        ]
        self.quote_providers = [self.eastmoney_direct, self.akshare]

        self.cache_dir = CACHE_DIR
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.metrics_dir = METRICS_DIR
        self.metrics_dir.mkdir(parents=True, exist_ok=True)

        self._api_status = {
            "yahoo_chart": "unknown",
            "eastmoney_kline": "unknown",
            "eastmoney_browser_kline": "unknown",
            "eastmoney_quote": "unknown",
        }
        self._eastmoney_kline_cooldown_until: float = 0
        self._eastmoney_browser_kline_cooldown_until: float = 0
        self._yahoo_chart_cooldown_until: float = 0
        self._last_batch_quote_status = "unknown"
        self._all_metrics: list[ProviderMetrics] = []

    # ─── Cache helpers ───────────────────────────────────────────────

    def _get_cache_path(self, symbol: str, data_type: str, date_str: str = "") -> Path:
        return self.cache_dir / f"{symbol}_{data_type}_{date_str}.json"

    def _session_stamp(self, date_str: str = "", data_type: str = "") -> str | None:
        if date_str and len(date_str) >= 10 and date_str[4] == "-" and date_str[7] == "-":
            return date_str[:10]
        if data_type == "quote":
            return datetime.now(CALENDAR.timezone).date().isoformat()
        return None

    def _load_cache(self, symbol: str, data_type: str, date_str: str = "", max_age_hours: int = 24) -> Any | None:
        cache_path = self._get_cache_path(symbol, data_type, date_str)
        if cache_path.exists():
            try:
                cached = json.loads(cache_path.read_text())
                cache_time = datetime.fromisoformat(cached.get("_cache_time", "2000-01-01"))
                data_as_of = cached.get("data_as_of")
                requested_as_of = self._session_stamp(date_str, data_type)
                if requested_as_of and data_as_of and str(data_as_of)[:10] != requested_as_of:
                    return None
                if requested_as_of and not data_as_of:
                    return None
                if (datetime.now() - cache_time).total_seconds() < max_age_hours * 3600:
                    return cached.get("data")
            except Exception:
                pass
        return None

    def _save_cache(self, symbol: str, data_type: str, data: Any, date_str: str = ""):
        cache_path = self._get_cache_path(symbol, data_type, date_str)
        session_date = self._session_stamp(date_str, data_type)
        cache_path.write_text(json.dumps({
            "_cache_time": datetime.now().isoformat(),
            "data_as_of": session_date,
            "source_timestamp": datetime.now().isoformat(),
            "session_date": session_date,
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

    def _is_eastmoney_browser_kline_available(self) -> bool:
        if self._api_status.get("eastmoney_browser_kline") == "unavailable":
            return time.time() >= self._eastmoney_browser_kline_cooldown_until
        return True

    def _mark_eastmoney_browser_kline_unavailable(self) -> None:
        self._api_status["eastmoney_browser_kline"] = "unavailable"
        self._eastmoney_browser_kline_cooldown_until = time.time() + EASTMONEY_COOLDOWN_SECONDS

    def _mark_eastmoney_browser_kline_available(self) -> None:
        self._api_status["eastmoney_browser_kline"] = "available"
        self._eastmoney_browser_kline_cooldown_until = 0

    def _is_yahoo_chart_available(self) -> bool:
        if self._api_status.get("yahoo_chart") == "rate_limited":
            return time.time() >= self._yahoo_chart_cooldown_until
        return True

    def _mark_yahoo_chart_rate_limited(self) -> None:
        self._api_status["yahoo_chart"] = "rate_limited"
        self._yahoo_chart_cooldown_until = time.time() + YAHOO_COOLDOWN_SECONDS

    def _mark_yahoo_chart_available(self) -> None:
        self._api_status["yahoo_chart"] = "available"
        self._yahoo_chart_cooldown_until = 0

    @staticmethod
    def _provider_error_status(provider_name: str, exc: Exception) -> str:
        if isinstance(exc, MarketDataHttpError) and exc.status == 429:
            return "rate_limited"
        if isinstance(exc, TimeoutError):
            return "timeout"
        if provider_name == "yahoo_chart_api":
            return "unavailable"
        if provider_name == "eastmoney_browser_page":
            return "unavailable"
        return "failed"

    def _provider_available(self, provider_name: str) -> bool:
        if provider_name == "yahoo_chart_api":
            return self._is_yahoo_chart_available()
        if provider_name == "eastmoney_direct":
            return self._is_eastmoney_kline_available()
        if provider_name == "eastmoney_browser_page":
            return self._is_eastmoney_browser_kline_available()
        return True

    # ─── API status check ────────────────────────────────────────────

    def check_api_status(self) -> dict[str, str]:
        """Return the latest explicit source states without hiding cooldowns."""
        status = {
            "yahoo_chart": (
                "rate_limited (cooldown)"
                if not self._is_yahoo_chart_available()
                else self._api_status["yahoo_chart"]
            )
        }

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
        providers_to_try = self.kline_providers

        for provider in providers_to_try:
            if not self._provider_available(provider.name):
                metrics.source_attempts.append(
                    {"provider": provider.name, "status": "cooldown", "rows": 0}
                )
                continue
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
                        metrics.source_attempts.append(
                            {
                                "provider": provider.name,
                                "status": "available",
                                "rows": len(rows),
                                "latency_ms": latency_ms,
                                **(
                                    provider.source_attempt_metadata()
                                    if hasattr(provider, "source_attempt_metadata")
                                    else {}
                                ),
                            }
                        )
                        if provider.name == "yahoo_chart_api":
                            self._mark_yahoo_chart_available()
                        if provider.name == "eastmoney_direct":
                            self._mark_eastmoney_kline_available()
                        if provider.name == "eastmoney_browser_page":
                            self._mark_eastmoney_browser_kline_available()
                        if len(metrics.source_attempts) > 1:
                            metrics.fallback_used = provider.name
                        self._record_metrics(metrics)
                        return rows, provider.name, metrics.to_dict()

                    metrics.source_attempts.append(
                        {
                            "provider": provider.name,
                            "status": "empty",
                            "rows": 0,
                            "latency_ms": latency_ms,
                            **(
                                provider.source_attempt_metadata()
                                if hasattr(provider, "source_attempt_metadata")
                                else {}
                            ),
                        }
                    )
                    if provider.name == "eastmoney_direct":
                        self._mark_eastmoney_kline_blocked()
                    if provider.name == "eastmoney_browser_page":
                        self._mark_eastmoney_browser_kline_unavailable()
                    break  # Don't retry if provider returned empty

                except Exception as e:
                    error_status = self._provider_error_status(provider.name, e)
                    metrics.source_attempts.append(
                        {
                            "provider": provider.name,
                            "status": error_status,
                            "retry": retry,
                            "error": f"{type(e).__name__}: {e}",
                            **(
                                provider.source_attempt_metadata()
                                if hasattr(provider, "source_attempt_metadata")
                                else {}
                            ),
                        }
                    )
                    if provider.name == "yahoo_chart_api" and error_status == "rate_limited":
                        self._mark_yahoo_chart_rate_limited()
                        break
                    if retry < MAX_RETRY_COUNT:
                        time.sleep(0.5 * (retry + 1))
                        continue
                    metrics.error_message = f"{provider.name}: {type(e).__name__}: {e}"
                    if provider.name == "eastmoney_direct":
                        self._mark_eastmoney_kline_blocked()
                    if provider.name == "eastmoney_browser_page":
                        self._mark_eastmoney_browser_kline_unavailable()
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
            cache_path = self._get_cache_path(symbol, "quote", "realtime")
            record: dict[str, Any] = {}
            try:
                record = json.loads(cache_path.read_text())
            except Exception:
                record = {}
            return cached, "cache", {
                "provider_status": "cached",
                "data_as_of": record.get("data_as_of"),
                "source_timestamp": record.get("source_timestamp"),
                "session_date": record.get("session_date"),
                "historical_research_must_not_use_current_cache": True,
            }

        attempts: list[dict[str, Any]] = []
        for provider in self.quote_providers:
            try:
                start_time = time.time()
                quote = provider.fetch_realtime_quote(symbol)
                latency_ms = int((time.time() - start_time) * 1000)

                if quote and quote.get("latest_price", 0) > 0:
                    self._save_cache(symbol, "quote", quote, "realtime")
                    stamp = CALENDAR.quote_session_stamp()
                    metadata = {
                        "provider_status": "available",
                        "provider_latency_ms": latency_ms,
                        "data_as_of": stamp["session_date"],
                        "source_timestamp": datetime.now().isoformat(),
                        "session_date": stamp["session_date"],
                        "source_attempts": attempts + [{
                            "provider": provider.name,
                            "status": "available",
                            "latency_ms": latency_ms,
                            "data_as_of": stamp["session_date"],
                            "timestamp": datetime.now().isoformat(),
                        }],
                        "chosen_provider": provider.name,
                        "fallback_chain": [item.get("provider") for item in attempts] + [provider.name],
                    }
                    if provider.name == "eastmoney_direct":
                        self._api_status["eastmoney_quote"] = "available"
                    return quote, provider.name, metadata
                attempts.append({"provider": provider.name, "status": "empty", "latency_ms": latency_ms})
            except Exception as exc:
                attempts.append(
                    {
                        "provider": provider.name,
                        "status": self._provider_error_status(provider.name, exc),
                        "error": f"{type(exc).__name__}: {exc}",
                    }
                )

        return None, "none", {"provider_status": "unavailable", "source_attempts": attempts}

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
                data = self.transport.fetch_json(url)
                diff = data.get("data", {}).get("diff", []) or []
                if not diff:
                    break
                all_items.extend(diff)
                if len(diff) < page_size:
                    break
                page += 1
                time.sleep(0.05)
            except Exception as exc:
                self._last_batch_quote_status = self._provider_error_status("eastmoney_direct", exc)
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

    def get_source_status(self) -> dict[str, Any]:
        """Expose source state and transport audit for runtime diagnostics."""
        return {
            "providers": dict(self._api_status),
            "batch_quote_status": self._last_batch_quote_status,
            "transport": self.transport.audit_snapshot(),
        }

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
