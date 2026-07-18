#!/usr/bin/env python3
"""East Money (东财) US stock data source for xiaomei.

East Money push2/push2his APIs for the xiaomei US market-data runtime.
US stock secid is not uniform; runtime probes both 105.{TICKER} and 106.{TICKER}.

Rate limiting: East Money APIs have per-IP rate limits.
Bulk kline fetch uses sequential requests with configurable delays.
"""

from __future__ import annotations

import json
import time
import urllib.request
from datetime import datetime, timedelta
from typing import Any

import numpy as np
import pandas as pd

HEADERS = {
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/120 Safari/537.36",
    "Referer": "https://quote.eastmoney.com/",
}

# Bypass proxy like xiaogu does
DIRECT_OPENER = urllib.request.build_opener(urllib.request.ProxyHandler({}))

KLINE_URL = "https://push2delay.eastmoney.com/api/qt/stock/kline/get"
STOCK_GET_URL = "https://push2delay.eastmoney.com/api/qt/stock/get"
TREND2_URL = "https://push2delay.eastmoney.com/api/qt/stock/trends2/get"

KLINE_FIELDS1 = "f1,f2,f3,f4,f5,f6"
KLINE_FIELDS2 = "f51,f52,f53,f54,f55,f56,f57,f58,f59,f60,f61"
STOCK_DETAIL_FIELDS = "f43,f44,f45,f46,f47,f48,f50,f51,f52,f57,f58,f60,f84,f85,f162,f167,f173,f191"

DATA_SOURCE = "eastmoney_us"
DATA_SOURCE_DISPLAY = "EastMoney US realtime/delayed quote + kline"
MARKET_TYPE = "US_STOCK"
DEFAULT_CURRENCY = "USD"
DEFAULT_KLINE_DELAY = 0.6
DEFAULT_DETAIL_DELAY = 0.4
DEFAULT_RETRIES = 3
DEFAULT_RETRY_BACKOFF = 2.0

EASTMONEY_QUOTE_BASE_URL = "https://quote.eastmoney.com"
EASTMONEY_US_QUOTE_CENTER_URL = f"{EASTMONEY_QUOTE_BASE_URL}/center/gridlist.html#us_stocks"
EASTMONEY_US_MARKET_TABS = {
    "required": [
        {
            "key": "us_quote_center",
            "label": "美股行情中心",
            "url": EASTMONEY_US_QUOTE_CENTER_URL,
            "role": "universe_scan",
        },
    ],
    "enhanced": [
        {
            "key": "us_quote_detail",
            "label": "个股详情页",
            "url_template": f"{EASTMONEY_QUOTE_BASE_URL}/us/{{symbol}}.html",
            "role": "quote_detail",
        },
        {
            "key": "us_quote_news",
            "label": "个股资讯页",
            "url_template": f"{EASTMONEY_QUOTE_BASE_URL}/us/{{symbol}}.html#news",
            "role": "news_detail",
        },
        {
            "key": "us_quote_company",
            "label": "个股公司页",
            "url_template": f"{EASTMONEY_QUOTE_BASE_URL}/us/{{symbol}}.html#company",
            "role": "company_detail",
        },
    ],
}
EASTMONEY_US_DATA_DIRECTORY_CATALOG = {
    "market_overview": ["us_quote_center"],
    "symbol_detail": ["us_quote_detail", "us_quote_news", "us_quote_company"],
}
EVIDENCE_DOMAINS = [
    "market_overview",
    "quote_detail",
    "company_detail",
    "news_detail",
]
CORE_ENHANCED_EVIDENCE_DOMAINS = [
    "quote_detail",
    "company_detail",
]
EXPERIMENTAL_EVIDENCE_DOMAINS = [
    "news_detail",
]
DOMAIN_URL_TOKENS = {
    "market_overview": ["gridlist", "us_stocks"],
    "quote_detail": ["/us/", ".html"],
    "company_detail": ["#company"],
    "news_detail": ["#news"],
}


def normalize_us_symbol(symbol: str) -> str:
    """Normalize US tickers for East Money lookup without legacy market-data source-specific rewrites."""
    return str(symbol).strip().upper().replace(".", "-")


def secid_candidates(ticker: str) -> list[str]:
    normalized = normalize_us_symbol(ticker)
    return [f"105.{normalized}", f"106.{normalized}"]


def secid(ticker: str) -> str:
    return secid_candidates(ticker)[0]


def eastmoney_us_quote_url(symbol: str, tab: str | None = None) -> str:
    normalized = normalize_us_symbol(symbol)
    base_url = f"{EASTMONEY_QUOTE_BASE_URL}/us/{normalized}.html"
    if tab == "news":
        return f"{base_url}#news"
    if tab == "company":
        return f"{base_url}#company"
    return base_url


def candidate_enhanced_urls(symbol: str) -> dict[str, str]:
    normalized = normalize_us_symbol(symbol)
    return {
        "symbol": normalized,
        "quote_detail": eastmoney_us_quote_url(normalized),
        "news_detail": eastmoney_us_quote_url(normalized, tab="news"),
        "company_detail": eastmoney_us_quote_url(normalized, tab="company"),
    }


def information_coverage_audit(symbol: str) -> dict[str, Any]:
    urls = candidate_enhanced_urls(symbol)
    return {
        "symbol": urls["symbol"],
        "required_tabs": [item["key"] for item in EASTMONEY_US_MARKET_TABS["required"]],
        "enhanced_tabs": [item["key"] for item in EASTMONEY_US_MARKET_TABS["enhanced"]],
        "directory_catalog": EASTMONEY_US_DATA_DIRECTORY_CATALOG,
        "evidence_domains": EVIDENCE_DOMAINS,
        "core_enhanced_domains": CORE_ENHANCED_EVIDENCE_DOMAINS,
        "experimental_domains": EXPERIMENTAL_EVIDENCE_DOMAINS,
        "detail_urls": urls,
    }


def _fnum(s: str) -> float | None:
    try:
        v = float(s)
        return v if not (np.isnan(v) or np.isinf(v)) else None
    except (TypeError, ValueError):
        return None


def _eastmoney_get(
    url: str,
    params: dict[str, Any],
    retries: int = DEFAULT_RETRIES,
    timeout: int = 8,
) -> dict[str, Any] | None:
    qs = "&".join(f"{k}={v}" for k, v in params.items())
    full_url = f"{url}?{qs}"
    last_error = None
    for attempt in range(retries + 1):
        try:
            req = urllib.request.Request(full_url, headers=HEADERS)
            with DIRECT_OPENER.open(req, timeout=timeout) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except Exception as exc:
            last_error = exc
            if attempt < retries:
                time.sleep(min(DEFAULT_RETRY_BACKOFF * (attempt + 1), 3.0))
    return None


def fetch_klines(
    ticker: str,
    beg: str,
    end: str,
    fqt: int = 0,
    retries: int = DEFAULT_RETRIES,
) -> list[dict[str, Any]]:
    """Fetch daily klines from East Money. fqt: 0=不复权, 1=前复权, 2=后复权."""
    params = {
        "secid": secid(ticker),
        "fields1": KLINE_FIELDS1,
        "fields2": KLINE_FIELDS2,
        "klt": "101",
        "fqt": str(fqt),
        "beg": beg.replace("-", ""),
        "end": end.replace("-", ""),
    }
    payload = _eastmoney_get(KLINE_URL, params, retries=retries)
    if not payload or payload.get("data") is None:
        return []
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
    return rows


def klines_to_dataframe(ticker: str, rows: list[dict[str, Any]]) -> pd.DataFrame:
    """Convert East Money kline rows to the pipeline-compatible OHLCV frame."""
    if not rows:
        return pd.DataFrame()
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
    df["symbol"] = normalize_us_symbol(ticker)
    df.index = pd.DatetimeIndex(df.index).normalize()
    return df[["Open", "High", "Low", "Close", "Adj Close", "Volume", "Dividends", "Stock Splits", "symbol"]]


def fetch_stock_detail(ticker: str, retries: int = DEFAULT_RETRIES) -> dict[str, Any] | None:
    """Fetch real-time stock detail from East Money."""
    normalized = normalize_us_symbol(ticker)
    for candidate_secid in secid_candidates(normalized):
        params = {
            "ut": "fa5fd1943c7b386f172d6893dbfba10b",
            "fltt": "2",
            "invt": "2",
            "fields": STOCK_DETAIL_FIELDS,
            "secid": candidate_secid,
        }
        payload = _eastmoney_get(STOCK_GET_URL, params, retries=retries)
        if not payload or payload.get("data") is None:
            continue
        d = payload["data"]
        return {
            "ticker": normalize_us_symbol(d.get("f57") or normalized),
            "name": d.get("f58", ""),
            "latest_price": _fnum(d.get("f43")),
            "high": _fnum(d.get("f44")),
            "low": _fnum(d.get("f45")),
            "open": _fnum(d.get("f46")),
            "volume": _fnum(d.get("f47")),
            "amount": _fnum(d.get("f48")),
            "prev_close": _fnum(d.get("f60")),
            "week52_high": _fnum(d.get("f51")),
            "week52_low": _fnum(d.get("f52")),
            "total_shares": _fnum(d.get("f84")),
            "float_shares": _fnum(d.get("f85")),
            "pe_ttm": _fnum(d.get("f167")),
            "roe": _fnum(d.get("f173")),
            "dividend_yield": _fnum(d.get("f191")),
            "secid": candidate_secid,
        }
    return None


def normalize_quote(detail: dict[str, Any] | None, requested_symbol: str | None = None) -> dict[str, Any] | None:
    """Normalize East Money detail data for xiaomei US-stock research tickets."""
    if not detail:
        return None
    symbol = normalize_us_symbol(detail.get("ticker") or requested_symbol or "")
    latest_price = _fnum(detail.get("latest_price"))
    prev_close = _fnum(detail.get("prev_close"))
    pct_chg = None
    if latest_price is not None and prev_close not in (None, 0):
        pct_chg = latest_price / float(prev_close) - 1.0
    return {
        "symbol": symbol,
        "name": str(detail.get("name") or "").strip(),
        "source": DATA_SOURCE,
        "source_display": DATA_SOURCE_DISPLAY,
        "source_status": "ok" if latest_price is not None else "price_unavailable",
        "market_type": MARKET_TYPE,
        "currency": DEFAULT_CURRENCY,
        "latest_price": latest_price,
        "open": _fnum(detail.get("open")),
        "high": _fnum(detail.get("high")),
        "low": _fnum(detail.get("low")),
        "prev_close": prev_close,
        "pct_chg": pct_chg,
        "volume": _fnum(detail.get("volume")),
        "amount": _fnum(detail.get("amount")),
        "turnover_rate": _fnum(detail.get("turnover_rate")),
        "week52_high": _fnum(detail.get("week52_high")),
        "week52_low": _fnum(detail.get("week52_low")),
        "total_shares": _fnum(detail.get("total_shares")),
        "float_shares": _fnum(detail.get("float_shares")),
        "pe_ttm": _fnum(detail.get("pe_ttm")),
        "roe": _fnum(detail.get("roe")),
        "dividend_yield": _fnum(detail.get("dividend_yield")),
        "as_of": datetime.now().astimezone().isoformat(),
    }


def fetch_realtime_quote(ticker: str, retries: int = DEFAULT_RETRIES) -> dict[str, Any] | None:
    """Fetch and normalize one East Money US quote."""
    normalized = normalize_us_symbol(ticker)
    return normalize_quote(fetch_stock_detail(normalized, retries=retries), requested_symbol=normalized)


def fetch_realtime_quotes(
    tickers: list[str],
    delay: float = DEFAULT_DETAIL_DELAY,
    retries: int = DEFAULT_RETRIES,
) -> dict[str, dict[str, Any] | None]:
    """Fetch normalized realtime quotes sequentially to respect provider limits."""
    results: dict[str, dict[str, Any] | None] = {}
    normalized_tickers = [normalize_us_symbol(ticker) for ticker in tickers]
    total = len(normalized_tickers)
    for i, ticker in enumerate(normalized_tickers):
        results[ticker] = fetch_realtime_quote(ticker, retries=retries)
        if i < total - 1 and delay > 0:
            time.sleep(delay)
    return results


def fetch_intraday_data(ticker: str, retries: int = DEFAULT_RETRIES) -> list[dict[str, Any]]:
    """Fetch intraday trend data from East Money trends2 endpoint."""
    normalized = normalize_us_symbol(ticker)
    for candidate_secid in secid_candidates(normalized):
        params = {
            "secid": candidate_secid,
            "fields1": "f1,f2,f3,f4,f5,f6,f7,f8,f9,f10,f11,f12,f13",
            "fields2": "f51,f52,f53,f54,f55,f56,f57,f58",
            "iscr": "0",
            "ndays": "1",
        }
        payload = _eastmoney_get(TREND2_URL, params, retries=retries)
        if not payload or payload.get("data") is None:
            continue
        trends = payload["data"].get("trends")
        if not trends:
            continue
        rows = []
        for raw in trends:
            parts = str(raw).split(",")
            if len(parts) < 5:
                continue
            row = {
                "time": parts[0],
                "price": _fnum(parts[1]),
                "avg_price": _fnum(parts[2]),
                "volume": _fnum(parts[3]),
                "amount": _fnum(parts[4]),
            }
            if row["price"] is not None:
                rows.append(row)
        if rows:
            return rows
    return []


def fetch_klines_period(
    ticker: str,
    period: str,
    retries: int = DEFAULT_RETRIES,
) -> list[dict[str, Any]]:
    """Fetch klines for a given period string like '1y' or '6mo'."""
    now = datetime.now()
    end_str = now.strftime("%Y-%m-%d")
    if period == "1y":
        beg = now - timedelta(days=365)
    elif period == "6mo":
        beg = now - timedelta(days=182)
    elif period == "3mo":
        beg = now - timedelta(days=90)
    elif period == "2y":
        beg = now - timedelta(days=730)
    else:
        beg = now - timedelta(days=365)
    return fetch_klines(ticker, beg.strftime("%Y-%m-%d"), end_str, fqt=0, retries=retries)


def fetch_universe_klines(
    universe: list[str],
    period: str = "1y",
    delay: float = DEFAULT_KLINE_DELAY,
    retries: int = DEFAULT_RETRIES,
) -> dict[str, list[dict[str, Any]]]:
    """Fetch klines sequentially with delay to respect rate limits."""
    results: dict[str, list[dict[str, Any]]] = {}
    total = len(universe)
    for i, ticker in enumerate(universe):
        rows = fetch_klines_period(ticker, period, retries=retries)
        results[ticker] = rows
        if i < total - 1 and delay > 0:
            time.sleep(delay)
    return results


def build_universe_dataframes(
    universe: list[str],
    period: str = "1y",
    delay: float = DEFAULT_KLINE_DELAY,
) -> dict[str, pd.DataFrame]:
    """Fetch and convert klines for universe to DataFrames."""
    raw = fetch_universe_klines(universe, period, delay=delay)
    frames: dict[str, pd.DataFrame] = {}
    for ticker, rows in raw.items():
        frames[ticker] = klines_to_dataframe(ticker, rows)
    return frames
