from __future__ import annotations

from research.fundamentals import company_fundamentals, earnings_intelligence, sec_filing
from research.metric_semantics import decode_metric_value, normalize_metric
from research.providers import GapSECDataProvider, provider_record
from research_panel import build_quality_check


def test_provider_requires_symbol_as_of():
    gap = GapSECDataProvider()
    filing = sec_filing({}, provider=gap)
    assert filing["status"] in {"DATA_GAP", "ERROR"}
    assert filing.get("reason") == "symbol required" or "ticker" in filing.get("data_gaps", [])
    empty = company_fundamentals({}, provider=gap)
    assert empty["status"] == "ERROR"
    assert empty["reason"] == "symbol required"
    filled = company_fundamentals({}, provider=gap, symbol="NVDA", as_of="2024-06-01")
    assert filled["symbol"] == "NVDA"
    assert filled["as_of"] == "2024-06-01"
    earnings = earnings_intelligence({}, provider=gap, symbol="NVDA", as_of="2024-06-01")
    assert earnings["status"] == "DATA_GAP"


def test_provider_record_contract():
    record = provider_record(symbol="NVDA", as_of="2024-06-01", source="company_fundamentals", status="DATA_GAP", facts={})
    for key in ("symbol", "as_of", "published_at", "effective_date", "retrieved_at", "source", "source_type", "status", "facts"):
        assert key in record
    assert record["status"] == "DATA_GAP"


def test_ratio_versus_percent_encoding():
    quality = build_quality_check("NVDA", {"roe": 0.23, "pe_ttm": 18, "dividend_yield": 0.02})
    assert quality["metric_registry"] == "research.metric_semantics.REGISTRY"
    assert decode_metric_value(23, "percent_0_100") == 0.23
    assert decode_metric_value(0.23, "ratio_0_1") == 0.23
    assert normalize_metric("roe", 23) is None
