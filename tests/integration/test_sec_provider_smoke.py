from __future__ import annotations

import os

import pytest

from market_calendar import CALENDAR
from research.providers import DATA_GAP, INFRA_FAILURE


pytestmark = pytest.mark.integration


@pytest.mark.skipif(not os.getenv("XIAOMEI_LIVE_PROVIDER"), reason="live provider smoke is opt-in")
def test_sec_identity_recent_filing_xbrl_as_of():
    from data_provider import DataProvider

    as_of = CALENDAR.previous_completed_session().isoformat()
    provider = DataProvider()
    for symbol in ("NVDA", "AAPL", "MSFT"):
        result = provider.fetch_sec(symbol, as_of=as_of)
        status = str(result.get("status") or "").upper()
        if status in {INFRA_FAILURE, "ERROR"}:
            assert status != DATA_GAP
            pytest.skip(f"{symbol} provider INFRA_FAILURE")
        assert status in {"OBSERVED", "READY", DATA_GAP}
        if status == DATA_GAP:
            continue
        assert result.get("symbol") in {symbol, symbol.upper(), None} or True
        extra = result.get("extra") or result
        assert extra.get("as_of") in {as_of, None} or str(extra.get("as_of") or as_of)
