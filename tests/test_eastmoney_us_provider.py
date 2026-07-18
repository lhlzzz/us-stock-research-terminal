from __future__ import annotations

import sys
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))

import eastmoney_us


def test_fetch_stock_detail_normalizes_eastmoney_payload(monkeypatch):
    def fake_get(url, params, retries=eastmoney_us.DEFAULT_RETRIES, timeout=15):
        assert params["secid"] == "105.NVDA"
        return {
            "data": {
                "f57": "NVDA",
                "f58": "NVIDIA Corp",
                "f43": "141.20",
                "f44": "142.00",
                "f45": "139.00",
                "f46": "140.00",
                "f47": "1000000",
                "f48": "141200000",
                "f51": "153.13",
                "f52": "86.62",
                "f60": "140.00",
                "f84": "24000000000",
                "f85": "23500000000",
                "f167": "55.5",
                "f173": "0.42",
                "f191": "0.0003",
            }
        }

    monkeypatch.setattr(eastmoney_us, "_eastmoney_get", fake_get)

    detail = eastmoney_us.fetch_stock_detail("nvda")
    quote = eastmoney_us.normalize_quote(detail)

    assert quote["symbol"] == "NVDA"
    assert quote["name"] == "NVIDIA Corp"
    assert quote["source"] == "eastmoney_us"
    assert quote["market_type"] == "US_STOCK"
    assert quote["latest_price"] == 141.20
    assert round(quote["pct_chg"], 6) == round(141.20 / 140.00 - 1.0, 6)
    assert "limit_up" not in quote
    assert "limit_down" not in quote
    assert "is_limit_up" not in quote


def test_fetch_stock_detail_falls_back_to_106_secid_when_105_is_empty(monkeypatch):
    seen = []

    def fake_get(url, params, retries=eastmoney_us.DEFAULT_RETRIES, timeout=15):
        seen.append(params["secid"])
        if params["secid"] == "105.IP":
            return {"data": None}
        if params["secid"] == "106.IP":
            return {
                "data": {
                    "f57": "IP",
                    "f58": "国际纸业",
                    "f43": "37.29",
                    "f44": "37.37",
                    "f45": "36.41",
                    "f46": "36.41",
                    "f47": "1238253",
                    "f48": "45848276",
                    "f51": "54.28",
                    "f52": "28.798",
                    "f60": "36.16",
                    "f84": "529516974",
                    "f85": "529516974",
                    "f167": "1.33",
                    "f173": "0.4",
                    "f191": "-37.93",
                }
            }
        raise AssertionError(params["secid"])

    monkeypatch.setattr(eastmoney_us, "_eastmoney_get", fake_get)

    detail = eastmoney_us.fetch_stock_detail("ip", retries=0)

    assert seen == ["105.IP", "106.IP"]
    assert detail["ticker"] == "IP"
    assert detail["name"] == "国际纸业"
    assert detail["latest_price"] == 37.29
    assert detail["secid"] == "106.IP"


def test_klines_to_dataframe_keeps_pipeline_ohlcv_contract():
    rows = [
        {
            "date": "2026-06-10",
            "open": 10.0,
            "high": 11.0,
            "low": 9.5,
            "close": 10.5,
            "volume": 1000.0,
        },
        {
            "date": "2026-06-11",
            "open": 10.5,
            "high": 12.0,
            "low": 10.0,
            "close": 11.5,
            "volume": 2000.0,
        },
    ]

    frame = eastmoney_us.klines_to_dataframe("aapl", rows)

    assert list(frame.columns) == [
        "Open",
        "High",
        "Low",
        "Close",
        "Adj Close",
        "Volume",
        "Dividends",
        "Stock Splits",
        "symbol",
    ]
    assert frame.iloc[-1]["Close"] == 11.5
    assert frame.iloc[-1]["Adj Close"] == 11.5
    assert frame.iloc[-1]["symbol"] == "AAPL"


def test_normalize_us_symbol_rewrites_dot_to_dash():
    assert eastmoney_us.normalize_us_symbol("brk.b") == "BRK-B"


def test_candidate_enhanced_urls_builds_us_quote_tabs():
    urls = eastmoney_us.candidate_enhanced_urls("aapl")

    assert urls == {
        "symbol": "AAPL",
        "quote_detail": "https://quote.eastmoney.com/us/AAPL.html",
        "news_detail": "https://quote.eastmoney.com/us/AAPL.html#news",
        "company_detail": "https://quote.eastmoney.com/us/AAPL.html#company",
    }


def test_information_coverage_audit_exposes_us_tab_configuration():
    audit = eastmoney_us.information_coverage_audit("nvda")

    assert audit["symbol"] == "NVDA"
    assert audit["required_tabs"] == ["us_quote_center"]
    assert "us_quote_detail" in audit["enhanced_tabs"]
    assert "quote_detail" in audit["evidence_domains"]
    assert audit["detail_urls"]["quote_detail"] == "https://quote.eastmoney.com/us/NVDA.html"
