"""Bridge between pipeline outputs and PostgreSQL database.

Called from pipeline's save_outputs to persist tickets, forward_tracking,
runtime_decisions, and research_runs to the database.
"""
from datetime import date, datetime
import json
import math
from pathlib import Path
import subprocess
from typing import Any
from sqlalchemy import text
from sqlalchemy.orm import Session


def _safe_float(val: Any, default: float = 0.0) -> float:
    """Safely convert value to float, returning default if None or invalid."""
    if val is None:
        return default
    try:
        return float(val)
    except (ValueError, TypeError):
        return default


def _safe_str(val: Any, default: str = "") -> str:
    """Safely convert value to string, returning default if None."""
    if val is None:
        return default
    return str(val)


def _safe_format_float(val: Any, fmt: str = ".3f", default: float = 0.0) -> str:
    """Safely format float value, returning formatted default if None."""
    return f"{_safe_float(val, default):{fmt}}"


def _json_default(value: Any) -> Any:
    if hasattr(value, "item"):
        return _json_default(value.item())
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    return str(value)


def _json_snapshot(value: Any) -> Any:
    def normalize(item: Any) -> Any:
        if hasattr(item, "item"):
            return normalize(item.item())
        if isinstance(item, float):
            return item if math.isfinite(item) else None
        if isinstance(item, (date, datetime)):
            return item.isoformat()
        if isinstance(item, dict):
            return {str(key): normalize(val) for key, val in item.items()}
        if isinstance(item, (list, tuple)):
            return [normalize(val) for val in item]
        return item

    return json.loads(json.dumps(normalize(value), default=_json_default, allow_nan=False))


def _current_git_commit() -> str | None:
    try:
        repo_root = Path(__file__).resolve().parents[2]
        return subprocess.check_output(
            ["git", "rev-parse", "HEAD"],
            cwd=repo_root,
            text=True,
            stderr=subprocess.DEVNULL,
        ).strip() or None
    except (OSError, subprocess.CalledProcessError):
        return None


def _scoring_config_snapshot(db: Session) -> dict[str, str]:
    rows = db.execute(
        text("SELECT config_key, config_value FROM scoring_config ORDER BY config_key")
    ).mappings()
    return {str(row["config_key"]): str(row["config_value"]) for row in rows}


def _candidate_source_layers(row: dict[str, Any]) -> dict[str, Any]:
    narrative = row.get("narrative_evidence") or {}
    business = row.get("business_evidence") or {}
    capital_score = row.get("capital_flow_proxy_score")
    return {
        "news": {
            "status": row.get("news_evidence_status", "UNAVAILABLE"),
            "score": row.get("news_quality_score"),
            "narrative_title": row.get("narrative_top_title"),
            "business_title": row.get("business_top_title"),
            "narrative_relevance": narrative.get("relevance_score"),
            "business_relevance": business.get("relevance_score"),
        },
        "capital_flow_proxy": {
            "status": row.get("capital_flow_status", "UNAVAILABLE"),
            "score": capital_score,
            "definition": "Observable price-volume footprint proxy; not verified institutional order flow.",
            "factor_coverage": row.get("footprint_factor_coverage"),
        },
        "social_sentiment": {
            "status": row.get("social_sentiment_status", "UNAVAILABLE"),
            "definition": "No validated social sentiment corpus was available for this run.",
        },
        "price_volume": {
            "status": "OBSERVED",
            "large_participant_footprint_score": row.get("large_participant_footprint_score"),
            "factor_contributions": row.get("footprint_factor_contributions") or {},
            "volume_confirmation_ratio": row.get("volume_confirmation_ratio"),
            "volume_weighted_momentum": row.get("volume_weighted_momentum"),
            "median_dollar_volume_20d": row.get("median_dollar_volume_20d"),
        },
        "market_participation": {
            "status": "OBSERVED",
            "score": row.get("market_participation_score"),
            "definition": "Cross-sectional breadth and advance ratio; not social sentiment.",
        },
    }


def _candidate_factor_snapshot(row: dict[str, Any]) -> dict[str, Any]:
    fields = (
        "prior_5d_momentum",
        "prior_20d_momentum",
        "five_day_acceleration",
        "relative_strength_vs_equal_weight",
        "volume_confirmation_ratio",
        "volume_weighted_momentum",
        "closing_strength_5d",
        "volume_trend_20d",
        "large_participant_footprint_score",
        "footprint_factor_coverage",
        "market_participation_score",
        "rsi_14",
        "momentum_quality",
        "breakout_score",
        "reversal_quality",
        "raw_market_score",
        "blended_score",
        "market_score",
        "catalyst_score",
        "ticket_score",
        "contrarian_penalty",
        "statistical_score",
        "capital_score",
        "combined_score",
        "capital_strength",
        "capital_quality",
        "quality_label",
        "distribution_score",
        "distribution_probability",
        "distribution_stage",
        "distribution_transition_risk",
        "trap_score",
        "trap_probability",
        "absorption_efficiency",
        "absorption_persistence",
        "upside_control_efficiency",
        "downside_control_efficiency",
        "control_asymmetry",
        "control_collapse_score",
        "state_duration",
        "state_age_score",
        "late_state_risk",
        "intent_probability",
        "transition_score",
        "price_control_score",
    )
    snapshot = {field: row.get(field) for field in fields if row.get(field) is not None}
    if row.get("footprint_factor_contributions") is not None:
        snapshot["footprint_factor_contributions"] = row["footprint_factor_contributions"]
    return snapshot


def _persist_capital_assessments(
    db: Session,
    *,
    output_date: str,
    research_run_id: int,
    candidate_rows: list[dict[str, Any]],
) -> None:
    """Persist public-data Capital Brain outputs in the existing run transaction."""
    for row in candidate_rows:
        evidence_bundle = row.get("capital_evidence") or {}
        evidence_items = evidence_bundle.get("evidence") or {}
        if not evidence_items:
            continue
        as_of_date = row.get("as_of_date") or output_date
        model_version = _safe_str(row.get("capital_model_version"), "capital_behavior_v2")
        data_version = _safe_str(row.get("capital_data_version"), "PUBLIC_OHLCV_V2")
        snapshot_params = {
            "symbol": row.get("symbol"),
            "as_of_date": as_of_date,
            "research_run_id": research_run_id,
            "model_version": model_version,
            "data_version": data_version,
            "validation_status": _safe_str(row.get("capital_validation_status"), "UNVALIDATED_NO_FIXED_CHAIN"),
            "statistical_score": row.get("statistical_score"),
            "capital_score": row.get("capital_score"),
            "combined_score": row.get("combined_score"),
            "capital_strength": row.get("capital_strength"),
            "capital_quality": row.get("capital_quality"),
            "quality_label": row.get("quality_label"),
            "dominant_direction": row.get("dominant_direction"),
            "dominant_pressure": row.get("dominant_pressure"),
            "absorption_score": row.get("absorption_score"),
            "absorption_efficiency": row.get("absorption_efficiency"),
            "absorption_persistence": row.get("absorption_persistence"),
            "upside_control_efficiency": row.get("upside_control_efficiency"),
            "downside_control_efficiency": row.get("downside_control_efficiency"),
            "control_asymmetry": row.get("control_asymmetry"),
            "control_regime": row.get("control_regime"),
            "control_collapse_score": row.get("control_collapse_score"),
            "distribution_risk": row.get("distribution_score"),
            "trap_risk": row.get("trap_score"),
            "distribution_probability": row.get("distribution_probability"),
            "distribution_stage": row.get("distribution_stage"),
            "distribution_acceleration": row.get("distribution_acceleration"),
            "distribution_transition_risk": row.get("distribution_transition_risk"),
            "trap_probability": row.get("trap_probability"),
            "transition_score": row.get("transition_score"),
            "transition_acceleration": row.get("transition_acceleration"),
            "state_age_score": row.get("state_age_score"),
            "late_state_risk": row.get("late_state_risk"),
            "intent_probability": row.get("intent_probability"),
            "intent_probabilities": json.dumps(_json_snapshot(row.get("intent_probabilities") or {})),
            "transition_probabilities": json.dumps(_json_snapshot(row.get("transition_probabilities") or {})),
            "path_distribution": json.dumps(_json_snapshot(row.get("paths") or {})),
            "evidence_json": json.dumps(_json_snapshot(evidence_bundle)),
        }
        db.execute(text("""
            INSERT INTO capital_daily_snapshot (
                symbol, as_of_date, research_run_id, model_version, data_version,
                validation_status, statistical_score, capital_score, combined_score,
                capital_strength, capital_quality, quality_label,
                dominant_direction, dominant_pressure, absorption_score,
                absorption_efficiency, absorption_persistence,
                upside_control_efficiency, downside_control_efficiency,
                control_asymmetry, control_regime, control_collapse_score,
                distribution_risk, trap_risk, distribution_probability,
                distribution_stage, distribution_acceleration,
                distribution_transition_risk, trap_probability, transition_score,
                transition_acceleration, state_age_score, late_state_risk,
                intent_probability, intent_probabilities, transition_probabilities,
                path_distribution, evidence_json
            ) VALUES (
                :symbol, :as_of_date, :research_run_id, :model_version, :data_version,
                :validation_status, :statistical_score, :capital_score, :combined_score,
                :capital_strength, :capital_quality, :quality_label,
                :dominant_direction, :dominant_pressure, :absorption_score,
                :absorption_efficiency, :absorption_persistence,
                :upside_control_efficiency, :downside_control_efficiency,
                :control_asymmetry, :control_regime, :control_collapse_score,
                :distribution_risk, :trap_risk, :distribution_probability,
                :distribution_stage, :distribution_acceleration,
                :distribution_transition_risk, :trap_probability, :transition_score,
                :transition_acceleration, :state_age_score, :late_state_risk,
                :intent_probability, CAST(:intent_probabilities AS jsonb),
                CAST(:transition_probabilities AS jsonb), CAST(:path_distribution AS jsonb),
                CAST(:evidence_json AS jsonb)
            )
            ON CONFLICT (symbol, as_of_date, research_run_id) DO UPDATE SET
                model_version = EXCLUDED.model_version,
                data_version = EXCLUDED.data_version,
                validation_status = EXCLUDED.validation_status,
                statistical_score = EXCLUDED.statistical_score,
                capital_score = EXCLUDED.capital_score,
                combined_score = EXCLUDED.combined_score,
                capital_strength = EXCLUDED.capital_strength,
                capital_quality = EXCLUDED.capital_quality,
                quality_label = EXCLUDED.quality_label,
                dominant_direction = EXCLUDED.dominant_direction,
                dominant_pressure = EXCLUDED.dominant_pressure,
                absorption_score = EXCLUDED.absorption_score,
                absorption_efficiency = EXCLUDED.absorption_efficiency,
                absorption_persistence = EXCLUDED.absorption_persistence,
                upside_control_efficiency = EXCLUDED.upside_control_efficiency,
                downside_control_efficiency = EXCLUDED.downside_control_efficiency,
                control_asymmetry = EXCLUDED.control_asymmetry,
                control_regime = EXCLUDED.control_regime,
                control_collapse_score = EXCLUDED.control_collapse_score,
                distribution_risk = EXCLUDED.distribution_risk,
                trap_risk = EXCLUDED.trap_risk,
                distribution_probability = EXCLUDED.distribution_probability,
                distribution_stage = EXCLUDED.distribution_stage,
                distribution_acceleration = EXCLUDED.distribution_acceleration,
                distribution_transition_risk = EXCLUDED.distribution_transition_risk,
                trap_probability = EXCLUDED.trap_probability,
                transition_score = EXCLUDED.transition_score,
                transition_acceleration = EXCLUDED.transition_acceleration,
                state_age_score = EXCLUDED.state_age_score,
                late_state_risk = EXCLUDED.late_state_risk,
                intent_probability = EXCLUDED.intent_probability,
                intent_probabilities = EXCLUDED.intent_probabilities,
                transition_probabilities = EXCLUDED.transition_probabilities,
                path_distribution = EXCLUDED.path_distribution,
                evidence_json = EXCLUDED.evidence_json
        """), snapshot_params)
        for evidence_type, item in evidence_items.items():
            db.execute(text("""
                INSERT INTO capital_evidence (
                    symbol, as_of_date, research_run_id, model_version, data_version,
                    evidence_type, value, confidence, availability, source, lookback, semantic
                ) VALUES (
                    :symbol, :as_of_date, :research_run_id, :model_version, :data_version,
                    :evidence_type, :value, :confidence, :availability, :source, :lookback, :semantic
                )
                ON CONFLICT (symbol, as_of_date, research_run_id, evidence_type) DO UPDATE SET
                    value = EXCLUDED.value,
                    confidence = EXCLUDED.confidence,
                    availability = EXCLUDED.availability,
                    source = EXCLUDED.source,
                    lookback = EXCLUDED.lookback,
                    semantic = EXCLUDED.semantic
            """), {
                **snapshot_params,
                "evidence_type": evidence_type,
                "value": item.get("value"),
                "confidence": item.get("confidence"),
                "availability": item.get("availability", "UNAVAILABLE"),
                "source": item.get("source"),
                "lookback": item.get("lookback"),
                "semantic": item.get("semantic", "DERIVED"),
            })
        db.execute(text("""
            INSERT INTO capital_state_history (
                symbol, as_of_date, research_run_id, model_version, data_version,
                capital_state, previous_capital_state, state_transition, state_duration,
                state_confidence, state_reason, state_momentum, transition_score,
                transition_acceleration, evidence_persistence, expected_duration,
                duration_percentile, late_state_risk, state_age_score,
                transition_probabilities, transition_matrix, semantic
            ) VALUES (
                :symbol, :as_of_date, :research_run_id, :model_version, :data_version,
                :capital_state, :previous_capital_state, :state_transition, :state_duration,
                :state_confidence, :state_reason, :state_momentum, :transition_score,
                :transition_acceleration, :evidence_persistence, :expected_duration,
                :duration_percentile, :late_state_risk, :state_age_score,
                CAST(:transition_probabilities AS jsonb), CAST(:transition_matrix AS jsonb), 'INFERRED'
            )
            ON CONFLICT (symbol, as_of_date, research_run_id) DO UPDATE SET
                capital_state = EXCLUDED.capital_state,
                previous_capital_state = EXCLUDED.previous_capital_state,
                state_transition = EXCLUDED.state_transition,
                state_duration = EXCLUDED.state_duration,
                state_confidence = EXCLUDED.state_confidence,
                state_reason = EXCLUDED.state_reason,
                state_momentum = EXCLUDED.state_momentum,
                transition_score = EXCLUDED.transition_score,
                transition_acceleration = EXCLUDED.transition_acceleration,
                evidence_persistence = EXCLUDED.evidence_persistence,
                expected_duration = EXCLUDED.expected_duration,
                duration_percentile = EXCLUDED.duration_percentile,
                late_state_risk = EXCLUDED.late_state_risk,
                state_age_score = EXCLUDED.state_age_score,
                transition_probabilities = EXCLUDED.transition_probabilities,
                transition_matrix = EXCLUDED.transition_matrix
        """), {
            **snapshot_params,
            "capital_state": row.get("capital_state", "UNKNOWN"),
            "previous_capital_state": row.get("previous_capital_state", "UNKNOWN"),
            "state_transition": row.get("state_transition", "UNKNOWN"),
            "state_duration": int(row.get("state_duration") or 0),
            "state_confidence": row.get("capital_state_confidence", row.get("state_confidence")),
            "state_reason": row.get("capital_state_reason", row.get("state_reason")),
            "state_momentum": row.get("state_momentum"),
            "transition_score": row.get("transition_score"),
            "transition_acceleration": row.get("transition_acceleration"),
            "evidence_persistence": row.get("evidence_persistence"),
            "expected_duration": row.get("expected_duration"),
            "duration_percentile": row.get("duration_percentile"),
            "late_state_risk": row.get("late_state_risk"),
            "state_age_score": row.get("state_age_score"),
            "transition_probabilities": json.dumps(_json_snapshot(row.get("transition_probabilities") or {})),
            "transition_matrix": json.dumps(_json_snapshot(row.get("transition_matrix") or {})),
        })
        db.execute(text("""
            INSERT INTO capital_intent (
                symbol, as_of_date, research_run_id, model_version, data_version,
                capital_intent, intent_confidence, expected_direction,
                continuation_condition, invalidation_condition, intent_probability,
                intent_probabilities, intent_alternatives, previous_intent,
                current_intent, intent_transition, semantic
            ) VALUES (
                :symbol, :as_of_date, :research_run_id, :model_version, :data_version,
                :capital_intent, :intent_confidence, :expected_direction,
                :continuation_condition, :invalidation_condition, :intent_probability,
                CAST(:intent_probabilities AS jsonb), CAST(:intent_alternatives AS jsonb),
                :previous_intent, :current_intent, :intent_transition, 'INFERRED'
            )
            ON CONFLICT (symbol, as_of_date, research_run_id) DO UPDATE SET
                capital_intent = EXCLUDED.capital_intent,
                intent_confidence = EXCLUDED.intent_confidence,
                intent_probability = EXCLUDED.intent_probability,
                intent_probabilities = EXCLUDED.intent_probabilities,
                intent_alternatives = EXCLUDED.intent_alternatives,
                expected_direction = EXCLUDED.expected_direction,
                continuation_condition = EXCLUDED.continuation_condition,
                invalidation_condition = EXCLUDED.invalidation_condition,
                previous_intent = EXCLUDED.previous_intent,
                current_intent = EXCLUDED.current_intent,
                intent_transition = EXCLUDED.intent_transition
        """), {
            **snapshot_params,
            "capital_intent": row.get("capital_intent", "UNKNOWN"),
            "intent_confidence": row.get("capital_intent_confidence", row.get("intent_confidence")),
            "intent_probability": row.get("intent_probability"),
            "intent_probabilities": json.dumps(_json_snapshot(row.get("intent_probabilities") or {})),
            "intent_alternatives": json.dumps(_json_snapshot(row.get("intent_alternatives") or [])),
            "expected_direction": row.get("expected_direction", "UNKNOWN"),
            "continuation_condition": row.get("continuation_condition"),
            "invalidation_condition": row.get("invalidation_condition"),
            "previous_intent": row.get("previous_intent"),
            "current_intent": row.get("current_intent"),
            "intent_transition": row.get("intent_transition"),
        })
        db.execute(text("""
            INSERT INTO capital_path_prediction (
                symbol, as_of_date, research_run_id, model_version, data_version,
                path_type, t1_probability, t3_probability, t5_probability,
                path_confidence, path_distribution, path_sequence, path_invalidation, semantic
            ) VALUES (
                :symbol, :as_of_date, :research_run_id, :model_version, :data_version,
                :path_type, :t1_probability, :t3_probability, :t5_probability,
                :path_confidence, CAST(:path_distribution AS jsonb),
                CAST(:path_sequence AS jsonb), CAST(:path_invalidation AS jsonb), 'PREDICTED'
            )
            ON CONFLICT (symbol, as_of_date, research_run_id) DO UPDATE SET
                path_type = EXCLUDED.path_type,
                t1_probability = EXCLUDED.t1_probability,
                t3_probability = EXCLUDED.t3_probability,
                t5_probability = EXCLUDED.t5_probability,
                path_confidence = EXCLUDED.path_confidence,
                path_distribution = EXCLUDED.path_distribution,
                path_sequence = EXCLUDED.path_sequence,
                path_invalidation = EXCLUDED.path_invalidation
        """), {
            **snapshot_params,
            "path_type": row.get("path_type", "UNKNOWN"),
            "t1_probability": row.get("t1_probability"),
            "t3_probability": row.get("t3_probability"),
            "t5_probability": row.get("t5_probability"),
            "path_confidence": row.get("path_confidence"),
            "path_distribution": json.dumps(_json_snapshot(row.get("paths") or {})),
            "path_sequence": json.dumps(_json_snapshot(row.get("path_sequence") or [])),
            "path_invalidation": json.dumps(_json_snapshot(row.get("path_invalidation") or [])),
        })


def _persist_daily_candidates(
    db: Session,
    output_date: str,
    research_run_id: int,
    candidate_rows: list[dict[str, Any]],
) -> int:
    count = 0
    for row in candidate_rows:
        source_layers = _candidate_source_layers(row)
        narrative = row.get("narrative_evidence") or {}
        business = row.get("business_evidence") or {}
        candidate_entry_reason = {
            "classification": row.get("classification"),
            "evidence_gate_status": row.get("evidence_gate_status"),
            "evidence_gap_reason": row.get("evidence_gap_reason"),
            "risk_summary": row.get("risk_summary"),
            "footprint_factor_coverage": row.get("footprint_factor_coverage"),
        }
        auxiliary_evidence = {
            "narrative": narrative,
            "business": business,
            "risk_checklist": row.get("risk_checklist") or {},
            "research_panel": row.get("research_panel") or {},
        }
        db.execute(
            text(
                """
                INSERT INTO daily_candidates (
                    trade_date, symbol, stock_name, rank, final_score, is_official_pick,
                    decision, open, high, low, close, volume, amount, pct_chg,
                    sentiment_catalyst, theme_catalyst, news_catalyst, positive_catalyst,
                    selection_reason, candidate_entry_reason, ticket_reason,
                    not_selected_reason, fund_flow_momentum, sector_catalyst_score,
                    market_score, catalyst_score, ticket_score, market_regime,
                    source_layers, factor_snapshot, auxiliary_evidence_snapshot,
                    ranking_basis, reconstruction_provenance, raw_json, research_run_id,
                    updated_at
                ) VALUES (
                    :trade_date, :symbol, :stock_name, :rank, :final_score, :is_official_pick,
                    :decision, :open, :high, :low, :close, :volume, :amount, :pct_chg,
                    NULL, :theme_catalyst, :news_catalyst, :positive_catalyst,
                    :selection_reason, CAST(:candidate_entry_reason AS jsonb), CAST(:ticket_reason AS jsonb),
                    CAST(:not_selected_reason AS jsonb), :fund_flow_momentum, :sector_catalyst_score,
                    :market_score, :catalyst_score, :ticket_score, :market_regime,
                    CAST(:source_layers AS jsonb), CAST(:factor_snapshot AS jsonb), CAST(:auxiliary_evidence_snapshot AS jsonb),
                    CAST(:ranking_basis AS jsonb), CAST(:reconstruction_provenance AS jsonb), CAST(:raw_json AS jsonb), :research_run_id,
                    NOW()
                )
                ON CONFLICT (trade_date, symbol) DO UPDATE SET
                    stock_name = EXCLUDED.stock_name,
                    rank = EXCLUDED.rank,
                    final_score = EXCLUDED.final_score,
                    is_official_pick = EXCLUDED.is_official_pick,
                    decision = EXCLUDED.decision,
                    open = EXCLUDED.open,
                    high = EXCLUDED.high,
                    low = EXCLUDED.low,
                    close = EXCLUDED.close,
                    volume = EXCLUDED.volume,
                    amount = EXCLUDED.amount,
                    pct_chg = EXCLUDED.pct_chg,
                    theme_catalyst = EXCLUDED.theme_catalyst,
                    news_catalyst = EXCLUDED.news_catalyst,
                    positive_catalyst = EXCLUDED.positive_catalyst,
                    selection_reason = EXCLUDED.selection_reason,
                    candidate_entry_reason = EXCLUDED.candidate_entry_reason,
                    ticket_reason = EXCLUDED.ticket_reason,
                    not_selected_reason = EXCLUDED.not_selected_reason,
                    fund_flow_momentum = EXCLUDED.fund_flow_momentum,
                    sector_catalyst_score = EXCLUDED.sector_catalyst_score,
                    market_score = EXCLUDED.market_score,
                    catalyst_score = EXCLUDED.catalyst_score,
                    ticket_score = EXCLUDED.ticket_score,
                    market_regime = EXCLUDED.market_regime,
                    source_layers = EXCLUDED.source_layers,
                    factor_snapshot = EXCLUDED.factor_snapshot,
                    auxiliary_evidence_snapshot = EXCLUDED.auxiliary_evidence_snapshot,
                    ranking_basis = EXCLUDED.ranking_basis,
                    reconstruction_provenance = EXCLUDED.reconstruction_provenance,
                    raw_json = EXCLUDED.raw_json,
                    research_run_id = EXCLUDED.research_run_id,
                    updated_at = NOW()
                """
            ),
            {
                "trade_date": output_date,
                "symbol": row.get("symbol"),
                "stock_name": row.get("company_name"),
                "rank": row.get("ticket_rank"),
                "final_score": row.get("ticket_score"),
                "is_official_pick": row.get("classification") == "CANDIDATE_FOR_PAPER_REVIEW",
                "decision": row.get("classification") or "CANDIDATE",
                "open": row.get("open"),
                "high": row.get("high"),
                "low": row.get("low"),
                "close": row.get("close"),
                "volume": row.get("volume"),
                "amount": row.get("amount"),
                "pct_chg": row.get("intraday_pct_chg"),
                "theme_catalyst": row.get("sector_propagation_bonus"),
                "news_catalyst": row.get("news_quality_score"),
                "positive_catalyst": row.get("catalyst_score"),
                "selection_reason": row.get("evidence_note") or row.get("risk_summary"),
                "candidate_entry_reason": json.dumps(_json_snapshot(candidate_entry_reason)),
                "ticket_reason": json.dumps(_json_snapshot(source_layers)),
                "not_selected_reason": json.dumps(
                    _json_snapshot(
                        {"status": "SELECTED"}
                        if row.get("classification") == "CANDIDATE_FOR_PAPER_REVIEW"
                        else {"status": "NOT_OFFICIAL_PICK", "classification": row.get("classification")}
                    )
                ),
                "fund_flow_momentum": None,
                "sector_catalyst_score": row.get("sector_propagation_bonus"),
                "market_score": row.get("market_score"),
                "catalyst_score": row.get("catalyst_score"),
                "ticket_score": row.get("ticket_score"),
                "market_regime": row.get("market_regime"),
                "source_layers": json.dumps(_json_snapshot(source_layers)),
                "factor_snapshot": json.dumps(_json_snapshot(_candidate_factor_snapshot(row))),
                "auxiliary_evidence_snapshot": json.dumps(_json_snapshot(auxiliary_evidence)),
                "ranking_basis": json.dumps(
                    _json_snapshot(
                        {
                            "ranking_metric": "ticket_score",
                            "score": row.get("ticket_score"),
                            "strategy_version": "observable_footprint_v1",
                            "formula": "0.75 * market_score + 0.25 * catalyst_score",
                            "factor_coverage": row.get("footprint_factor_coverage"),
                            "expected_return_status": "UNAVAILABLE_HISTORICAL_MODEL",
                            "profit_guarantee": False,
                        }
                    )
                ),
                "reconstruction_provenance": json.dumps(
                    _json_snapshot(
                        {
                            "source": "us_profit_ticket_pipeline",
                            "version_status": "VERSIONED",
                        }
                    )
                ),
                "raw_json": json.dumps(_json_snapshot(row)),
                "research_run_id": research_run_id,
            },
        )
        count += 1
    return count


def normalize_ticket(row: dict) -> dict:
    """Normalize ticket fields to ensure no None values cause format errors."""
    normalized = dict(row)

    # Numeric fields with safe defaults
    numeric_fields = {
        "market_score": 0.0,
        "catalyst_score": 0.0,
        "ticket_score": 0.0,
        "raw_market_score": 0.0,
        "blended_score": 0.0,
        "risk_penalty": 0.0,
        "confirmation_score": 0.0,
        "prior_5d_momentum": 0.0,
        "prior_20d_momentum": 0.0,
        "five_day_acceleration": 0.0,
        "relative_strength_vs_equal_weight": 0.0,
        "volume_weighted_momentum": 0.0,
        "rsi_14": 50.0,
        "momentum_quality": 0.0,
        "breakout_score": 0.0,
        "reversal_quality": 0.0,
        "volume_confirmation_ratio": 0.0,
        "closing_strength_5d": 0.0,
        "median_dollar_volume_20d": 0.0,
    }
    for field, default in numeric_fields.items():
        normalized[field] = _safe_float(normalized.get(field), default)

    # Text fields with safe defaults
    text_fields = {
        "symbol": "",
        "classification": "NEED_MORE_EVIDENCE",
        "evidence_gate_status": "",
        "risk_verdict": "",
        "quality_verdict": "",
        "lifecycle_stage": "",
        "narrative_title": "",
        "business_title": "",
        "risk_summary": "",
        "quality_summary": "",
        "panel_verdict": "",
        "market_regime": "",
        "entry_reason": "",
    }
    for field, default in text_fields.items():
        normalized[field] = _safe_str(normalized.get(field), default)

    # Ensure symbol is not empty
    if not normalized["symbol"]:
        normalized["symbol"] = "UNKNOWN"

    return normalized


def save_pipeline_to_db(
    db: Session,
    output_date: str,
    metrics: dict[str, Any],
    top_candidates: list[dict],
    forward_tracking_rows: list[dict],
    candidate_rows: list[dict] | None = None,
) -> dict[str, int]:
    """Save pipeline outputs to PostgreSQL.

    Returns counts of inserted records.
    """
    from scripts.db.crud import (
        create_ticket, upsert_forward_tracking,
        create_runtime_decision, create_research_run, finish_research_run,
        upsert_market_snapshot, upsert_factor_snapshot,
    )

    counts = {"tickets": 0, "candidates": 0, "forward_tracking": 0, "runtime_decisions": 0}
    ticket_ids: dict[tuple[str, str], int] = {}

    # Save research run
    run_config = {
        "version_status": "VERSIONED",
        "git_commit": _current_git_commit(),
        "data_as_of": metrics.get("as_of_date"),
        "generated_at": metrics.get("generated_at"),
        "source_mode": metrics.get("source_mode"),
        "strategy_version": metrics.get("strategy_version", "observable_footprint_v1"),
        "scoring_config": _scoring_config_snapshot(db),
        "capital_model": {
            "model_version": "capital_behavior_v2",
            "data_version": "PUBLIC_OHLCV_V2",
            "validation_status": "UNVALIDATED_NO_FIXED_CHAIN",
            "mode": "parallel_only",
        },
    }
    run = create_research_run(
        db,
        run_name=metrics.get("run_name", "pipeline"),
        output_date=output_date,
        status="running",
        candidate_count=metrics.get("paper_review_count", 0) + metrics.get("market_watchlist_count", 0),
        pass_count=metrics.get("paper_review_count", 0),
        git_commit=run_config["git_commit"],
        config=_json_snapshot(run_config),
    )

    def fail_run(error: Exception):
        db.rollback()
        finish_research_run(
            db,
            run.run_id,
            status="failed",
            error_message=str(error)[:500],
        )
        raise RuntimeError(f"pipeline persistence failed for run {run.run_id}") from error

    try:
        counts["candidates"] = _persist_daily_candidates(
            db,
            output_date,
            run.run_id,
            candidate_rows or top_candidates,
        )
        _persist_capital_assessments(
            db,
            output_date=output_date,
            research_run_id=run.run_id,
            candidate_rows=candidate_rows or top_candidates,
        )
    except Exception as exc:
        fail_run(exc)

    # Save tickets
    for row in top_candidates:
        try:
            # Normalize ticket to handle None values
            row = normalize_ticket(row)

            # 构建出票理由
            narrative_title = row.get("narrative_top_title") or row.get("narrative_title", "")
            business_title = row.get("business_top_title") or row.get("business_title", "")
            risk_summary = row.get("risk_summary", "")

            # 从嵌套结构提取
            quality_check = row.get("quality_check", {})
            quality_verdict_str = quality_check.get("quality_verdict", "") if isinstance(quality_check, dict) else ""
            quality_score_val = quality_check.get("overall_quality_score") if isinstance(quality_check, dict) else None
            quality_summary = quality_verdict_str
            if quality_score_val is not None:
                quality_summary += f" (score={_safe_float(quality_score_val):.2f})"

            risk_checklist = row.get("risk_checklist", {})
            risk_verdict_detail = risk_checklist.get("risk_verdict", "") if isinstance(risk_checklist, dict) else ""
            red_count = risk_checklist.get("red_count", 0) if isinstance(risk_checklist, dict) else 0
            yellow_count = risk_checklist.get("yellow_count", 0) if isinstance(risk_checklist, dict) else 0
            if risk_verdict_detail:
                risk_summary = f"{risk_verdict_detail} (red={red_count}, yellow={yellow_count})"

            research_panel = row.get("research_panel", {})
            panel_verdict = research_panel.get("panel_verdict", "") if isinstance(research_panel, dict) else ""
            panel_summary = research_panel.get("summary", "") if isinstance(research_panel, dict) else ""

            market_regime = metrics.get("regime", "")
            if hasattr(market_regime, "name"):
                market_regime = market_regime.name

            # 构建 entry_reason (使用 safe format)
            entry_parts = []
            if narrative_title:
                entry_parts.append(f"catalyst: {narrative_title}")
            if business_title:
                entry_parts.append(f"business: {business_title}")
            ms = _safe_float(row.get("market_score"))
            cs = _safe_float(row.get("catalyst_score"))
            entry_parts.append(f"scores: market={ms:.3f} catalyst={cs:.3f}")
            if panel_verdict:
                entry_parts.append(f"panel: {panel_verdict}")
            if risk_verdict_detail:
                entry_parts.append(f"risk: {risk_verdict_detail}")
            entry_reason = " | ".join(entry_parts)

            ticket = create_ticket(
                db,
                output_date=output_date,
                symbol=row["symbol"],
                as_of_date=row.get("as_of_date", output_date),
                ticket_rank=row.get("ticket_rank"),
                market_score=row.get("market_score"),
                catalyst_score=row.get("catalyst_score"),
                ticket_score=row.get("ticket_score"),
                classification=row.get("classification"),
                evidence_gate_status=row.get("evidence_gate_status"),
                risk_verdict=risk_verdict_detail or row.get("risk_verdict"),
                quality_verdict=quality_verdict_str or row.get("quality_verdict"),
                lifecycle_stage=row.get("lifecycle_stage"),
                run_name=metrics.get("run_name"),
                research_run_id=run.run_id,
                narrative_title=narrative_title,
                business_title=business_title,
                risk_summary=risk_summary,
                quality_summary=quality_summary,
                panel_verdict=panel_verdict,
                market_regime=market_regime,
                entry_reason=entry_reason,
                institutional_flow_score=None,
                social_sentiment_score=None,
                raw_market_score=row.get("raw_market_score"),
                blended_score=row.get("blended_score"),
                breakout_score=row.get("breakout_score"),
                risk_penalty=row.get("risk_penalty"),
                confirmation_score=row.get("confirmation_score"),
                capital_score=row.get("capital_score"),
                capital_strength=row.get("capital_strength"),
                capital_quality=row.get("capital_quality"),
                quality_label=row.get("quality_label"),
                capital_state=row.get("capital_state"),
                capital_state_confidence=row.get("capital_state_confidence"),
                capital_intent=row.get("capital_intent"),
                capital_intent_confidence=row.get("capital_intent_confidence"),
                accumulation_score=row.get("accumulation_score"),
                absorption_score=row.get("absorption_score"),
                supply_exhaustion_score=row.get("supply_exhaustion_score"),
                demand_persistence_score=row.get("demand_persistence_score"),
                markup_score=row.get("markup_score"),
                distribution_score=row.get("distribution_score"),
                price_control_score=row.get("price_control_score"),
                crowding_score=row.get("crowding_score"),
                trap_score=row.get("trap_score"),
                absorption_efficiency=row.get("absorption_efficiency"),
                absorption_persistence=row.get("absorption_persistence"),
                upside_control_efficiency=row.get("upside_control_efficiency"),
                downside_control_efficiency=row.get("downside_control_efficiency"),
                control_asymmetry=row.get("control_asymmetry"),
                distribution_probability=row.get("distribution_probability"),
                distribution_stage=row.get("distribution_stage"),
                distribution_acceleration=row.get("distribution_acceleration"),
                distribution_transition_risk=row.get("distribution_transition_risk"),
                trap_probability=row.get("trap_probability"),
                transition_score=row.get("transition_score"),
                late_state_risk=row.get("late_state_risk"),
                state_age_score=row.get("state_age_score"),
                intent_probability=row.get("intent_probability"),
                intent_probabilities=row.get("intent_probabilities"),
                transition_probabilities=row.get("transition_probabilities"),
                path_distribution=row.get("paths"),
                expected_direction=row.get("expected_direction"),
                path_type=row.get("path_type"),
                t1_probability=row.get("t1_probability"),
                t3_probability=row.get("t3_probability"),
                t5_probability=row.get("t5_probability"),
                capital_thesis=row.get("capital_thesis"),
                invalidation_condition=row.get("invalidation_condition"),
                commit=False,
            )
            as_of_date = row.get("as_of_date", output_date)
            ticket_ids[(row["symbol"], str(as_of_date))] = ticket.id
            ticket_ids.setdefault((row["symbol"], str(output_date)), ticket.id)
            counts["tickets"] += 1
        except Exception as e:
            fail_run(e)

    # Save forward tracking rows
    for ft in forward_tracking_rows:
        try:
            track_key = ft.get("track_key") or f"{output_date}:{ft['symbol']}:{ft.get('horizon_days', '')}d"
            as_of_date = ft.get("as_of_date", output_date)
            ticket_id = ft.get("ticket_id")
            if ticket_id is None:
                ticket_id = ticket_ids.get((ft["symbol"], str(as_of_date)))
            if ticket_id is None:
                ticket_id = ticket_ids.get((ft["symbol"], str(output_date)))
            upsert_forward_tracking(
                db,
                track_key=track_key,
                output_date=output_date,
                symbol=ft["symbol"],
                as_of_date=ft.get("as_of_date", output_date),
                horizon_days=ft.get("horizon_days"),
                due_date=ft.get("due_date"),
                as_of_close=ft.get("as_of_close"),
                check_status="pending",
                ticket_id=ticket_id,
                capital_model_version=ft.get("capital_model_version"),
                capital_validation_status=ft.get("capital_validation_status"),
                capital_state_at_entry=ft.get("capital_state_at_entry"),
                capital_intent_at_entry=ft.get("capital_intent_at_entry"),
                capital_strength_at_entry=ft.get("capital_strength_at_entry"),
                capital_score_at_entry=ft.get("capital_score_at_entry"),
                distribution_score_at_entry=ft.get("distribution_score_at_entry"),
                trap_score_at_entry=ft.get("trap_score_at_entry"),
                capital_quality_at_entry=ft.get("capital_quality_at_entry"),
                distribution_probability_at_entry=ft.get("distribution_probability_at_entry"),
                trap_probability_at_entry=ft.get("trap_probability_at_entry"),
                quality_label_at_entry=ft.get("quality_label_at_entry"),
                intent_probability_at_entry=ft.get("intent_probability_at_entry"),
                path_distribution_at_entry=ft.get("path_distribution_at_entry"),
                predicted_path=ft.get("predicted_path"),
                commit=False,
            )
            counts["forward_tracking"] += 1
        except Exception as e:
            fail_run(e)

    # Save runtime decision
    try:
        regime = None
        regime_data = metrics.get("regime")
        if regime_data and hasattr(regime_data, "name"):
            regime = regime_data.name
        elif isinstance(regime_data, str):
            regime = regime_data

        create_runtime_decision(
            db,
            output_date=output_date,
            run_name=metrics.get("run_name"),
            final_classification=metrics.get("final_classification"),
            paper_review_count=metrics.get("paper_review_count", 0),
            market_watchlist_count=metrics.get("market_watchlist_count", 0),
            universe_count=metrics.get("source_universe_included_symbols"),
            regime=regime,
            summary=metrics,
            commit=False,
        )
        counts["runtime_decisions"] += 1
    except Exception as e:
        fail_run(e)

    # Save market snapshot
    try:
        as_of = metrics.get("as_of_date")
        if as_of:
            market_summary = metrics.get("market_summary", {})
            upsert_market_snapshot(
                db,
                trade_date=date.fromisoformat(as_of),
                regime=regime,
                universe_count=metrics.get("source_universe_included_symbols"),
                commit=False,
            )
    except Exception as e:
        fail_run(e)

    # Save factor snapshots for top candidates
    for row in top_candidates:
        try:
            row = normalize_ticket(row)
            as_of = row.get("as_of_date")
            if as_of:
                upsert_factor_snapshot(
                    db,
                    trade_date=date.fromisoformat(as_of) if isinstance(as_of, str) else as_of,
                    symbol=row["symbol"],
                    prior_5d_momentum=row.get("prior_5d_momentum"),
                    prior_20d_momentum=row.get("prior_20d_momentum"),
                    five_day_acceleration=row.get("five_day_acceleration"),
                    relative_strength=row.get("relative_strength_vs_equal_weight"),
                    volume_weighted_momentum=row.get("volume_weighted_momentum"),
                    rsi_14=row.get("rsi_14"),
                    momentum_quality=row.get("momentum_quality"),
                    breakout_score=row.get("breakout_score"),
                    reversal_quality=row.get("reversal_quality"),
                    volume_confirmation=row.get("volume_confirmation_ratio"),
                    closing_strength_5d=row.get("closing_strength_5d"),
                    dollar_volume_20d=row.get("median_dollar_volume_20d"),
                    market_score=row.get("market_score"),
                    blended_score=row.get("blended_score"),
                    theme_strength=row.get("theme_strength"),
                    announcement_catalyst=row.get("announcement_catalyst"),
                    regime=regime,
                    commit=False,
                )
        except Exception as e:
            fail_run(e)

    # Save signals for top candidates
    SIGNAL_FIELDS = [
        "market_score", "catalyst_score", "ticket_score",
        "prior_20d_momentum", "five_day_acceleration",
        "relative_strength_vs_equal_weight", "volume_weighted_momentum",
        "volume_confirmation_ratio", "closing_strength_5d",
        "rsi_14", "momentum_quality", "breakout_score", "reversal_quality",
        "theme_strength", "announcement_catalyst",
    ]
    for row in top_candidates:
        try:
            row = normalize_ticket(row)
            as_of = row.get("as_of_date")
            if not as_of:
                continue
            trade_date = date.fromisoformat(as_of) if isinstance(as_of, str) else as_of
            symbol = row["symbol"]
            for signal_key in SIGNAL_FIELDS:
                signal_value = row.get(signal_key)
                if signal_value is not None:
                    from scripts.db.crud import upsert_signal
                    upsert_signal(db, trade_date, symbol, signal_key, float(signal_value))
        except Exception as e:
            fail_run(e)

    try:
        finish_research_run(db, run.run_id, status="done", commit=False)
        db.commit()
        return counts
    except Exception as exc:
        fail_run(exc)
