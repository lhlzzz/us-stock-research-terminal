from capital.evidence import build_capital_evidence
from capital_test_support import ohlcv


def test_evidence_has_structured_public_data_contract():
    result = build_capital_evidence(ohlcv())
    assert result["availability"] == "AVAILABLE"
    for field in result["evidence"].values():
        assert set(("value", "confidence", "availability", "source", "lookback", "semantic")) <= set(field)
        assert field["source"] == "PUBLIC_OHLCV"
        assert field["semantic"] == "DERIVED"


def test_evidence_rejects_insufficient_or_zero_volume_history():
    insufficient = build_capital_evidence(ohlcv(10))
    zero = ohlcv()
    zero["volume"] = 0
    zero_volume = build_capital_evidence(zero)
    assert insufficient["availability"] == "INSUFFICIENT_HISTORY"
    assert zero_volume["availability"] == "ZERO_OR_MISSING_VOLUME"
