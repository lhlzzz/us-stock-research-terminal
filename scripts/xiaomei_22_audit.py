#!/usr/bin/env python3
"""Xiaomei 2.2 architecture audit. Honest statuses only; no fake PASS."""
from __future__ import annotations

import ast
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))


FORBIDDEN_RANKING_FILES = {
    "scripts/research/sec.py",
    "scripts/research/earnings.py",
    "scripts/research/estimates.py",
    "scripts/research/industry.py",
    "scripts/research/failure.py",
    "scripts/research/runtime.py",
    "scripts/research/coverage.py",
    "scripts/research/store.py",
    "scripts/research/snapshots.py",
}
RANKING_MUTATION = (
    "ticket_score =",
    "market_score =",
    "volume_confirmation_ratio =",
    "observable_footprint_v1",
)
TRADE_TOKENS = ("BUY", "SELL", "ORDER", "LIVE_TRADE", "BROKER")


def _git(*args: str) -> str:
    return subprocess.check_output(["git", *args], cwd=ROOT, text=True).strip()


def _read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def _contains_assignment(source: str, token: str) -> bool:
    return token in source


def audit() -> dict[str, str]:
    from research.boundary import PRODUCTION_BOUNDARY, RANKING_KEY, freeze_snapshot, learning_cannot_auto_weight
    from research.providers import DATA_GAP, forbid_cross_semantic_fallback
    from research.evidence import research_evidence
    from research.sec import filings_as_of, resolve_amendments, resolve_fact_conflicts
    from research.earnings import earnings_as_of, split_surprises
    from research.estimates import revisions_as_of
    from research.industry import chokepoint_record, persist_industry_graph
    from research.failure import FAILURE_TYPES, failure_memory, learning_pattern
    from research.coverage import research_readiness
    from research_panel import run_full_research_panel

    status = {
        "RESEARCH_OWNER": "PASS" if (ROOT / "scripts/research/runtime.py").exists() else "FAIL",
        "PRODUCTION_RANKING_OWNER": "PASS" if PRODUCTION_BOUNDARY["ranking_owner"] == "observable_footprint_v1" else "FAIL",
        "TEMPORAL_OWNER": "PASS" if (ROOT / "scripts/research/temporal.py").exists() else "FAIL",
        "CALENDAR_OWNER": "PASS" if (ROOT / "scripts/market_calendar.py").exists() else "FAIL",
        "DATA_PROVIDER_OWNER": "PASS" if (ROOT / "scripts/data_provider.py").exists() else "FAIL",
        "PRODUCTION_BOUNDARY": "PASS" if PRODUCTION_BOUNDARY["live_order"] == "NO_LIVE_ORDER" else "FAIL",
        "PRODUCTION_RESEARCH_READY": "UNKNOWN",
        "STRATEGY_FROZEN": "UNKNOWN",
        "RESEARCH_LIVE": "UNKNOWN",
        "REPLAY_LIVE": "UNKNOWN",
        "LEARNING_LIVE": "UNKNOWN",
        "LEARNING_NO_AUTO_WEIGHT": "UNKNOWN",
        "RESEARCH_NO_ALPHA": "UNKNOWN",
        "RESEARCH_NO_BUY_SELL": "UNKNOWN",
        "NO_BROKER": "UNKNOWN",
        "NO_LIVE_ORDER": "UNKNOWN",
        "LEGACY_ADAPTER": "UNKNOWN",
        "LEGACY_SINGLE_OWNER": "UNKNOWN",
        "PRODUCTION_RANKING_UNCHANGED": "UNKNOWN",
        "SEC": "UNKNOWN",
        "EARNINGS": "UNKNOWN",
        "ESTIMATE_REVISION": "DATA_GAP",
        "INDUSTRY_GRAPH": "UNKNOWN",
        "CHOKEPOINT": "DATA_GAP",
        "HISTORICAL_UNIVERSE": "DATA_GAP",
        "FAILURE_MEMORY": "UNKNOWN",
        "LEARNING": "UNKNOWN",
        "EVIDENCE": "UNKNOWN",
        "REPLAY": "UNKNOWN",
        "PROVIDER_AUDIT": "UNKNOWN",
        "TEMPORAL_INTEGRITY": "UNKNOWN",
        "SURVIVORSHIP_INTEGRITY": "UNKNOWN",
    }

    panel = run_full_research_panel(
        "NVDA",
        {"prior_20d_momentum": 0.12, "five_day_acceleration": 0.01, "relative_strength_vs_equal_weight": 0.02, "volume_confirmation_ratio": 0.4},
        {"status": "missing", "relevance_score": 0.0},
        {"status": "missing", "relevance_score": 0.0},
        {},
    )
    status["LEGACY_ADAPTER"] = "PASS" if panel.get("compatibility_adapter") else "FAIL"
    status["LEGACY_SINGLE_OWNER"] = "PASS" if panel.get("canonical_owner") == "scripts.research" else "FAIL"
    ranking_ok = list(RANKING_KEY) == ["ticket_score", "market_score", "volume_confirmation_ratio"]
    ranking_ok = ranking_ok and PRODUCTION_BOUNDARY["ranking_owner"] == "observable_footprint_v1"
    ranking_ok = ranking_ok and PRODUCTION_BOUNDARY["strategy"] == "observable_footprint_v1"
    ranking_ok = ranking_ok and PRODUCTION_BOUNDARY["strategy_status"] == "FROZEN"
    pipeline = _read("scripts/us_profit_ticket_pipeline.py")
    ranking_ok = ranking_ok and "key=lambda row: (row[\"ticket_score\"], row[\"market_score\"], row[\"volume_confirmation_ratio\"])" in pipeline
    status["PRODUCTION_RANKING_UNCHANGED"] = "PASS" if ranking_ok else "FAIL"
    freeze = freeze_snapshot()
    freeze_ok = (
        freeze["production_research_status"] == "PRODUCTION_RESEARCH_READY"
        and freeze["strategy"] == "observable_footprint_v1"
        and freeze["strategy_status"] == "FROZEN"
        and freeze.get("production_runtime_status") == "PRODUCTION_RUNTIME_READY"
        and freeze["research"] == "LIVE"
        and freeze["replay"] == "LIVE"
        and freeze["learning"] == "LIVE"
        and freeze["broker"] == "NO_BROKER"
        and freeze["live_order"] == "NO_LIVE_ORDER"
        and freeze["ranking_key"] == ["ticket_score", "market_score", "volume_confirmation_ratio"]
        and "RESEARCH_TO_ALPHA" in freeze["forbidden_transitions"]
        and "RESEARCH_TO_BUY_SELL" in freeze["forbidden_transitions"]
        and "LEARNING_TO_AUTO_WEIGHT_CHANGE" in freeze["forbidden_transitions"]
        and "BROKER_CONNECT" in freeze["forbidden_transitions"]
        and "LIVE_ORDER_ENABLE" in freeze["forbidden_transitions"]
    )
    status["PRODUCTION_RESEARCH_READY"] = "PASS" if freeze_ok else "FAIL"
    status["STRATEGY_FROZEN"] = "PASS" if freeze["strategy_status"] == "FROZEN" else "FAIL"
    status["RESEARCH_LIVE"] = "PASS" if freeze["research"] == "LIVE" else "FAIL"
    status["REPLAY_LIVE"] = "PASS" if freeze["replay"] == "LIVE" else "FAIL"
    status["LEARNING_LIVE"] = "PASS" if freeze["learning"] == "LIVE" else "FAIL"
    status["LEARNING_NO_AUTO_WEIGHT"] = "PASS" if learning_cannot_auto_weight("learning") else "FAIL"
    status["RESEARCH_NO_ALPHA"] = "PASS" if "RESEARCH_TO_ALPHA" in PRODUCTION_BOUNDARY["forbidden_transitions"] else "FAIL"
    status["RESEARCH_NO_BUY_SELL"] = "PASS" if "BUY" in PRODUCTION_BOUNDARY["forbidden_outputs"] and "SELL" in PRODUCTION_BOUNDARY["forbidden_outputs"] else "FAIL"
    status["NO_BROKER"] = "PASS" if PRODUCTION_BOUNDARY["broker"] == "NO_BROKER" else "FAIL"
    status["NO_LIVE_ORDER"] = "PASS" if PRODUCTION_BOUNDARY["live_order"] == "NO_LIVE_ORDER" else "FAIL"

    leaked = []
    for rel in FORBIDDEN_RANKING_FILES:
        text = _read(rel)
        if any(token in text for token in ("ticket_score =", "market_score =", "volume_confirmation_ratio =")):
            leaked.append(rel)
        tree = ast.parse(text)
        for node in ast.walk(tree):
            if isinstance(node, ast.Assign):
                names = [target.id for target in node.targets if isinstance(target, ast.Name)]
                value = node.value
                if "produces_pick" in names and isinstance(value, ast.Constant) and value.value is True:
                    leaked.append(f"{rel}:produces_pick")
                if any(name in {"classification", "action"} for name in names) and isinstance(value, ast.Constant) and value.value in {"BUY", "SELL", "ORDER"}:
                    leaked.append(f"{rel}:{value.value}")
    status["PRODUCTION_BOUNDARY"] = "FAIL" if leaked else status["PRODUCTION_BOUNDARY"]

    observed_no_source = research_evidence(symbol="NVDA", as_of="2026-08-05", status="OBSERVED", facts={"x": 1})
    status["EVIDENCE"] = "PASS" if observed_no_source["status"] == "ERROR" else "FAIL"

    filings = [
        {"form": "10-Q", "filing_date": "2026-08-10", "acceptance_datetime": "2026-08-10", "accession_number": "a", "period_of_report": "2026-07-31", "published_at": "2026-08-10", "available_at": "2026-08-10"},
        {"form": "10-Q/A", "filing_date": "2026-08-20", "acceptance_datetime": "2026-08-20", "accession_number": "b", "period_of_report": "2026-07-31", "published_at": "2026-08-20", "available_at": "2026-08-20"},
    ]
    early = filings_as_of(filings, as_of="2026-08-05")
    late = filings_as_of(filings, as_of="2026-08-11")
    versions = resolve_amendments(filings, as_of="2026-08-21")
    selected = [row for row in versions if row.get("selected")]
    status["SEC"] = "PASS" if not early and late and selected and selected[0]["accession_number"] == "b" else "FAIL"
    status["TEMPORAL_INTEGRITY"] = "PASS" if not early and late else "FAIL"

    conflicts = resolve_fact_conflicts(
        [{"concept": "Revenues", "period": "2026-07-31", "unit": "USD", "value": 1, "filed": "2026-08-10", "accn": "a"},
         {"concept": "Revenues", "period": "2026-07-31", "unit": "USD", "value": 2, "filed": "2026-08-20", "accn": "b"}],
        as_of="2026-08-21",
    )
    if conflicts["silent_overwrite"] or conflicts["conflict_count"] < 1:
        status["SEC"] = "FAIL"

    events = [
        {"event_date": "2026-08-20", "announced_at": "2026-08-20", "available_at": "2026-08-20", "eps_surprise": 0.1, "revenue_surprise": -0.2},
        {"event_date": "2026-09-10", "announced_at": "2026-09-10", "available_at": "2026-09-10"},
    ]
    visible = earnings_as_of(events, as_of="2026-08-25")
    split = split_surprises(events[0])
    status["EARNINGS"] = "PASS" if len(visible) == 1 and split["eps_surprise"] == 0.1 and split["revenue_surprise"] == -0.2 and split["combined_score_forbidden"] else "FAIL"

    history = [
        {"estimate": 4.20, "estimate_date": "2026-07-01", "effective_date": "2026-07-01"},
        {"estimate": 4.35, "estimate_date": "2026-07-10", "effective_date": "2026-07-10"},
        {"estimate": 4.50, "estimate_date": "2026-07-25", "effective_date": "2026-07-25"},
    ]
    seen = revisions_as_of(history, as_of="2026-07-15")
    status["ESTIMATE_REVISION"] = "PASS" if [row["estimate"] for row in seen] == [4.20, 4.35] else "FAIL"
    # Honest live consensus source remains DATA_GAP; history contract can PASS independently.

    graph = persist_industry_graph(None, entities=[{"type": "company", "id": "NVDA", "name": "NVDA", "source": "sec_edgar"}], relations=[{"type": "depends_on", "src": "NVDA", "dst": "Semiconductors", "source": "sec_edgar"}], as_of_date="2026-08-01")
    status["INDUSTRY_GRAPH"] = "PASS" if graph.get("status") == "OBSERVED" and graph.get("graph_snapshot_id") else "FAIL"
    choke = chokepoint_record()
    status["CHOKEPOINT"] = choke.get("status") if choke.get("status") == DATA_GAP else "PASS"

    from research.industry import universe_as_of, universe_snapshot
    rows = [
        universe_snapshot(universe_name="CORE_UNIVERSE", symbol="OLD", effective_from="2023-01-01", effective_to="2024-12-31", source="fixture", source_url="https://example.test/2024"),
        universe_snapshot(universe_name="CORE_UNIVERSE", symbol="NEW", effective_from="2025-01-01", source="fixture", source_url="https://example.test/2026"),
    ]
    status["SURVIVORSHIP_INTEGRITY"] = "PASS" if "OLD" in universe_as_of(rows, as_of="2024-06-01") and "NEW" not in universe_as_of(rows, as_of="2024-06-01") else "FAIL"
    status["HISTORICAL_UNIVERSE"] = DATA_GAP

    fail = failure_memory(symbol="NVDA", as_of="2026-08-01", research_layer="earnings", failure_type="EARNINGS_MISREAD")
    pattern = learning_pattern(research_layer="earnings", pattern_type="eps_beat_guidance_cut")
    status["FAILURE_MEMORY"] = "PASS" if fail["failure_type"] in FAILURE_TYPES and fail["changes_production_ranking"] is False else "FAIL"
    status["LEARNING"] = "PASS" if pattern["does_not_modify_ticket_score"] else "FAIL"

    blocked = forbid_cross_semantic_fallback("news", "sec_filing")
    status["PROVIDER_AUDIT"] = "PASS" if blocked["blocked"] else "FAIL"

    from research.snapshots import research_snapshot
    snap_a = research_snapshot(as_of="2026-08-01", universe={"status": DATA_GAP}, research_evidence=[])
    snap_b = research_snapshot(as_of="2026-08-01", universe={"status": DATA_GAP}, research_evidence=[])
    status["REPLAY"] = "PASS" if snap_a["content_hash"] == snap_b["content_hash"] else "FAIL"

    ready = research_readiness({"layers": {}})
    status["EVIDENCE"] = status["EVIDENCE"] if ready["status"] == DATA_GAP and ready["not_a_bool"] else "FAIL"

    return status


def main() -> int:
    status = audit()
    print(json.dumps(status, indent=2, sort_keys=True))
    hard = [
        "PRODUCTION_RANKING_UNCHANGED",
        "PRODUCTION_BOUNDARY",
        "PRODUCTION_RESEARCH_READY",
        "STRATEGY_FROZEN",
        "RESEARCH_LIVE",
        "REPLAY_LIVE",
        "LEARNING_LIVE",
        "LEARNING_NO_AUTO_WEIGHT",
        "RESEARCH_NO_ALPHA",
        "RESEARCH_NO_BUY_SELL",
        "NO_BROKER",
        "NO_LIVE_ORDER",
        "LEGACY_ADAPTER",
        "LEGACY_SINGLE_OWNER",
        "EVIDENCE",
        "TEMPORAL_INTEGRITY",
        "FAILURE_MEMORY",
        "PROVIDER_AUDIT",
    ]
    failed = [name for name in hard if status.get(name) == "FAIL"]
    if failed:
        print("FAILED:", failed)
        return 1
    print("XIAOMEI_2.2_AUDIT=PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
