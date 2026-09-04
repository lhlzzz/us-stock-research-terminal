from __future__ import annotations

from research.industry import historical_universe_eligible, universe_as_of, universe_snapshot


def test_stock_removed_after_2024_stays_in_2024_replay():
    rows = [
        universe_snapshot(universe_name="CORE_UNIVERSE", symbol="OLD", effective_from="2023-01-01", effective_to="2024-12-31", source="fixture", source_url="https://example.test/2024"),
        universe_snapshot(universe_name="CORE_UNIVERSE", symbol="NEW", effective_from="2025-01-01", source="fixture", source_url="https://example.test/2026"),
        universe_snapshot(universe_name="CORE_UNIVERSE", symbol="KEPT", effective_from="2023-01-01", source="fixture", source_url="https://example.test/all"),
    ]
    assert "OLD" in universe_as_of(rows, as_of="2024-06-01")
    assert "NEW" not in universe_as_of(rows, as_of="2024-06-01")
    assert historical_universe_eligible("OLD", rows, as_of="2024-06-01") is True
    assert historical_universe_eligible("NEW", rows, as_of="2024-06-01") is False
    assert historical_universe_eligible("OLD", rows, as_of="2026-01-01") is False
    assert historical_universe_eligible("KEPT", rows, as_of="2026-01-01") is True
