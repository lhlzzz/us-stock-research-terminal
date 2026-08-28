from capital_backtest import write_report


def test_backtest_report_preserves_unvalidated_production_gate(tmp_path, monkeypatch):
    import capital_backtest

    monkeypatch.setattr(capital_backtest, "REPORT_JSON", tmp_path / "report.json")
    monkeypatch.setattr(capital_backtest, "REPORT_MD", tmp_path / "report.md")
    paths = write_report({
        "status": "UNVALIDATED_NO_FIXED_CHAIN",
        "production_action": "KEEP_OBSERVABLE_FOOTPRINT_RANKING_UNCHANGED",
        "gate": {"fixed_chain_rows": 0, "trading_days": 0},
        "variants": {},
    })
    assert paths["json"].exists()
    assert "KEEP_OBSERVABLE_FOOTPRINT_RANKING_UNCHANGED" in paths["markdown"].read_text()
