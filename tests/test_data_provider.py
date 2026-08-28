from __future__ import annotations

import json
import sys
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import pytest

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))

from data_provider import (
    DataProvider,
    EastmoneyBrowserKlineProvider,
    MarketDataHttpError,
    ScrapyApiBridge,
    _parse_eastmoney_browser_klines,
)


class _FixtureHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/rate":
            self.send_response(429)
            self.end_headers()
            self.wfile.write(b'{"error":"rate_limited"}')
            return
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps({"ok": True}).encode())

    def log_message(self, *_args):
        return


def test_scrapy_transport_deduplicates_and_audits_http_status():
    server = ThreadingHTTPServer(("127.0.0.1", 0), _FixtureHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    base_url = f"http://127.0.0.1:{server.server_port}"
    bridge = ScrapyApiBridge()

    try:
        assert bridge.fetch_json(f"{base_url}/ok") == {"ok": True}
        assert bridge.fetch_json(f"{base_url}/ok") == {"ok": True}
        with pytest.raises(MarketDataHttpError) as error:
            bridge.fetch_json(f"{base_url}/rate")

        audit = bridge.audit_snapshot()
        assert error.value.status == 429
        assert audit["request_count"] == 2
        assert audit["cache_hit_count"] == 1
        assert audit["records"][-1]["status"] == 429
        assert audit["records"][-1]["retry_count"] == 1
    finally:
        server.shutdown()
        server.server_close()


def test_yahoo_rate_limit_is_explicit_before_fallback(monkeypatch):
    class RateLimitedYahoo:
        name = "yahoo_chart_api"

        @staticmethod
        def fetch_klines(*_args, **_kwargs):
            raise MarketDataHttpError(429, "https://query1.finance.yahoo.com/test")

    class Fallback:
        name = "akshare"

        @staticmethod
        def fetch_klines(*_args, **_kwargs):
            return [{
                "date": "2026-08-14",
                "open": 100.0,
                "close": 101.0,
                "high": 102.0,
                "low": 99.0,
                "volume": 1000.0,
            }]

    provider = DataProvider()
    monkeypatch.setattr(provider, "kline_providers", [RateLimitedYahoo(), Fallback()])
    monkeypatch.setattr(provider, "_load_cached_klines", lambda *_args: None)
    monkeypatch.setattr(provider, "_save_klines_cache", lambda *_args: None)

    rows, source, metadata = provider.fetch_klines("NVDA", "2026-08-01", "2026-08-14")

    assert source == "akshare"
    assert rows[0]["close"] == 101.0
    assert metadata["fallback_used"] == "akshare"
    assert metadata["source_attempts"][0]["provider"] == "yahoo_chart_api"
    assert metadata["source_attempts"][0]["status"] == "rate_limited"
    assert provider.get_source_status()["providers"]["yahoo_chart"] == "rate_limited"


def test_eastmoney_browser_page_parser_requires_complete_date_bounded_ohlcv():
    rows = _parse_eastmoney_browser_klines(
        {
            "rows": [
                {
                    "date": "2026-08-13",
                    "open": "100",
                    "close": "101",
                    "high": "102",
                    "low": "99",
                    "volume": "1,000",
                },
                {
                    "date": "2026-08-14",
                    "open": "101",
                    "close": "102",
                    "high": "103",
                    "low": "100",
                    "volume": "--",
                },
                {
                    "date": "2026-08-15",
                    "open": "102",
                    "close": "103",
                    "high": "104",
                    "low": "101",
                    "volume": "2,000",
                },
            ]
        },
        "2026-08-13",
        "2026-08-14",
    )

    assert rows == [{
        "date": "2026-08-13",
        "open": 100.0,
        "close": 101.0,
        "high": 102.0,
        "low": 99.0,
        "volume": 1000.0,
        "amount": None,
        "adj_close": 101.0,
        "amplitude_pct": None,
        "pct_chg": None,
        "chg": None,
        "turnover_rate": None,
    }]


def test_browser_kline_attempt_is_audited_after_eastmoney_api_failure(monkeypatch):
    class FailingProvider:
        name = "eastmoney_direct"

        @staticmethod
        def fetch_klines(*_args, **_kwargs):
            raise MarketDataHttpError(None, "https://push2his.eastmoney.com/test")

    browser = EastmoneyBrowserKlineProvider()
    monkeypatch.setattr(
        browser,
        "fetch_klines",
        lambda *_args, **_kwargs: [{
            "date": "2026-08-14",
            "open": 100.0,
            "close": 101.0,
            "high": 102.0,
            "low": 99.0,
            "volume": 1000.0,
        }],
    )
    monkeypatch.setattr(
        browser,
        "source_attempt_metadata",
        lambda: {
            "browser_transport": "cloakbrowser_playwright",
            "page_url": "https://quote.eastmoney.com/us/NVDA.html",
            "page_sha256": "fixture",
            "schema_version": "eastmoney_browser_dom_ohlcv_v1",
        },
    )

    provider = DataProvider()
    monkeypatch.setattr(provider, "kline_providers", [FailingProvider(), browser])
    monkeypatch.setattr(provider, "_load_cached_klines", lambda *_args: None)
    monkeypatch.setattr(provider, "_save_klines_cache", lambda *_args: None)

    rows, source, metadata = provider.fetch_klines("NVDA", "2026-08-14", "2026-08-14")

    assert source == "eastmoney_browser_page"
    assert rows[0]["close"] == 101.0
    attempts = metadata["source_attempts"]
    browser_index = next(
        index for index, attempt in enumerate(attempts)
        if attempt["provider"] == "eastmoney_browser_page"
    )
    assert browser_index > 0
    assert all(attempt["provider"] == "eastmoney_direct" for attempt in attempts[:browser_index])
    attempt = attempts[browser_index]
    assert attempt["provider"] == "eastmoney_browser_page"
    assert attempt["status"] == "available"
    assert attempt["rows"] == 1
    assert attempt["latency_ms"] >= 0
    assert attempt["browser_transport"] == "cloakbrowser_playwright"
    assert attempt["page_url"] == "https://quote.eastmoney.com/us/NVDA.html"
    assert attempt["page_sha256"] == "fixture"
    assert attempt["schema_version"] == "eastmoney_browser_dom_ohlcv_v1"
