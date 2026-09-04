from __future__ import annotations

from xiaomei_production_release_audit import audit


HARD = (
    "boundary",
    "strategy_freeze",
    "weight_frozen",
    "weight_gateway",
    "no_weight_bypass",
    "canonical_session",
    "temporal_integrity",
    "provider_integrity",
    "research_snapshot_integrity",
    "replay_sample_integrity",
    "risk_parameter_integrity",
    "learning_boundary",
    "failure_propagation",
    "production_boundary",
    "no_broker",
    "no_live_order",
    "no_production_alpha_transition",
    "no_auto_weight_change",
    "pipeline_apply_blocked",
    "optimizer_keep_previous",
    "PRODUCTION_RUNTIME_READY",
    "production_gate",
)


def test_release_audit_p0_p1_pass():
    status = audit()
    failed = [name for name in HARD if status.get(name) not in {"PASS"}]
    assert failed == []
    assert status["score_semantics"] == "PASS"
    assert status["schema_audit"] == "PASS"
