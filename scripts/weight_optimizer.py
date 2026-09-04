#!/usr/bin/env python3
"""Weekly weight optimizer based on factor IC analysis.

Computes Information Coefficient (Spearman rank correlation) between
each factor and forward returns, then generates optimal scoring weights.
"""
import json
import sys
from datetime import timedelta
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

sys.path.insert(0, str(Path(__file__).resolve().parent))

from db.engine import SessionLocal
from db.models import FactorSnapshot, ForwardTracking
from market_calendar import CALENDAR
from research.weight_mutation import KEEP_PREVIOUS_WEIGHT, request_weight_change
from sqlalchemy import text

WEIGHTS_FILE = Path(__file__).resolve().parent.parent / "data" / "scoring_weights.json"
STRATEGY_VERSION = "observable_footprint_v1"
VERSION_STATUS = "VERSIONED"
MIN_VALIDATED_ROWS = 20
MIN_VALIDATED_TRADING_DAYS = 10
MIN_FACTOR_COVERAGE = 0.75
MAX_AVERAGE_LOSS = -0.05

DEFAULT_WEIGHTS = {
    "prior_20d_momentum": 0.10,
    "five_day_acceleration": -0.10,
    "relative_strength_vs_equal_weight": 0.45,
    "volume_weighted_momentum": 0.30,
    "closing_strength_5d": 0.0,
    "volume_confirmation_ratio": 0.0,
}

FACTORS = [
    "prior_20d_momentum", "five_day_acceleration",
    "relative_strength", "volume_weighted_momentum",
    "closing_strength_5d", "volume_confirmation", "rsi_14",
    "momentum_quality", "breakout_score", "reversal_quality",
    "theme_strength", "announcement_catalyst",
]


def load_versioned_feedback(session, lookback_days: int = 60) -> pd.DataFrame:
    """Load only reproducible observable-footprint 1d outcomes."""
    cutoff = CALENDAR.previous_completed_session() - timedelta(days=lookback_days)

    rows = session.execute(text(
        "SELECT fs.trade_date, fs.symbol, " + ", ".join(f"fs.{factor}" for factor in FACTORS) + ", "
        "ft.forward_return, ft.ticket_id "
        "FROM factor_snapshots fs "
        "JOIN forward_tracking ft "
        "  ON ft.symbol = fs.symbol "
        " AND ft.as_of_date = fs.trade_date "
        " AND ft.horizon_days = 1 "
        "JOIN tickets t ON t.id = ft.ticket_id "
        "JOIN research_runs rr ON rr.run_id = t.research_run_id "
        "WHERE fs.trade_date >= :cutoff "
        "  AND ft.check_status = 'completed' "
        "  AND ft.forward_return IS NOT NULL "
        "  AND rr.status = 'done' "
        "  AND rr.finished_at IS NOT NULL "
        "  AND rr.config->>'strategy_version' = :strategy_version "
        "  AND COALESCE(rr.config->>'version_status', '') = :version_status "
        "ORDER BY fs.trade_date, fs.symbol"
    ), {
        "cutoff": cutoff,
        "strategy_version": STRATEGY_VERSION,
        "version_status": VERSION_STATUS,
    }).fetchall()

    return pd.DataFrame(rows, columns=["trade_date", "symbol"] + FACTORS + ["forward_return", "ticket_id"])


def evaluate_validation_gate(feedback: pd.DataFrame) -> dict:
    """Block weight changes until independent versioned evidence is sufficient."""
    if feedback.empty:
        return {
            "status": "UNVALIDATED_NO_FIXED_CHAIN",
            "reason": "no_versioned_completed_returns",
            "strategy_version": STRATEGY_VERSION,
            "sample_count": 0,
            "trading_days": 0,
            "factor_coverage": 0.0,
        }

    factor_coverage = float(feedback[FACTORS].notna().mean().mean())
    negative_returns = feedback.loc[feedback["forward_return"] < 0, "forward_return"]
    average_loss = float(negative_returns.mean()) if not negative_returns.empty else 0.0
    metrics = {
        "strategy_version": STRATEGY_VERSION,
        "sample_count": int(len(feedback)),
        "trading_days": int(feedback["trade_date"].nunique()),
        "average_return": float(feedback["forward_return"].mean()),
        "average_loss": average_loss,
        "factor_coverage": factor_coverage,
    }

    if metrics["sample_count"] < MIN_VALIDATED_ROWS:
        return {"status": "UNVALIDATED_NO_FIXED_CHAIN", "reason": "too_few_completed_returns", **metrics}
    if metrics["trading_days"] < MIN_VALIDATED_TRADING_DAYS:
        return {"status": "UNVALIDATED_NO_FIXED_CHAIN", "reason": "too_few_trading_days", **metrics}
    if metrics["average_return"] <= 0:
        return {"status": "UNVALIDATED_NO_FIXED_CHAIN", "reason": "non_positive_average_return", **metrics}
    if metrics["average_loss"] < MAX_AVERAGE_LOSS:
        return {"status": "UNVALIDATED_NO_FIXED_CHAIN", "reason": "average_loss_exceeds_limit", **metrics}
    if metrics["factor_coverage"] < MIN_FACTOR_COVERAGE:
        return {"status": "UNVALIDATED_NO_FIXED_CHAIN", "reason": "insufficient_factor_coverage", **metrics}
    return {"status": "VALIDATED_FOR_WEIGHT_UPDATE", **metrics}


def compute_factor_ic(feedback: pd.DataFrame) -> dict[str, float]:
    """Compute IC for one validated feedback population."""
    if len(feedback) < MIN_VALIDATED_ROWS:
        return {}

    ic_scores = {}
    for factor in FACTORS:
        valid = feedback[[factor, "forward_return"]].dropna()
        if len(valid) < 10:
            continue
        ic, _ = stats.spearmanr(valid[factor], valid["forward_return"])
        if np.isfinite(ic):
            ic_scores[factor] = round(float(ic), 4)

    return ic_scores


def compute_optimal_weights(ic_scores: dict[str, float]) -> dict[str, float]:
    """Convert IC scores to normalized weights with minimum floor."""
    if not ic_scores:
        return DEFAULT_WEIGHTS.copy()

    # Filter out NaN values
    valid_ic = {k: v for k, v in ic_scores.items() if not (v != v)}  # NaN check
    if not valid_ic:
        return DEFAULT_WEIGHTS.copy()

    abs_ic = {k: abs(v) for k, v in valid_ic.items()}
    total = sum(abs_ic.values())
    if total == 0:
        return DEFAULT_WEIGHTS.copy()

    # First pass: raw weights from IC
    raw_weights = {}
    for factor in FACTORS:
        ic = valid_ic.get(factor, 0)
        abs_val = abs_ic.get(factor, 0)
        raw_weight = abs_val / total
        raw_weights[factor] = raw_weight * (1 if ic >= 0 else -1)

    # Apply minimum floor (5%) to avoid single-factor concentration
    MIN_WEIGHT = 0.05
    weights = {}
    for factor in FACTORS:
        w = raw_weights.get(factor, 0)
        if abs(w) < MIN_WEIGHT and w != 0:
            w = MIN_WEIGHT if w > 0 else -MIN_WEIGHT
        weights[factor] = round(w, 4)

    # Re-normalize to sum to 1.0
    total_abs = sum(abs(v) for v in weights.values())
    if total_abs > 0:
        for factor in weights:
            weights[factor] = round(weights[factor] / total_abs, 4)

    return weights


def _load_weights_artifact() -> dict:
    if not WEIGHTS_FILE.exists():
        return {"weights": DEFAULT_WEIGHTS.copy()}
    try:
        return json.loads(WEIGHTS_FILE.read_text())
    except Exception:
        return {"weights": DEFAULT_WEIGHTS.copy()}


COLUMN_MAPPING = {
    "relative_strength": "relative_strength_vs_equal_weight",
    "volume_confirmation": "volume_confirmation_ratio",
}


def _map_factor_keys(values: dict[str, float]) -> dict[str, float]:
    return {COLUMN_MAPPING.get(k, k): v for k, v in values.items()}


def save_validation_decision(decision: dict):
    """Record validation evidence in-memory only. Production weights stay frozen."""
    data = _load_weights_artifact()
    data["strategy_decision"] = decision
    data["updated_at"] = CALENDAR.previous_completed_session().isoformat()
    return data


def save_weights(weights: dict[str, float], ic_scores: dict[str, float], decision: dict):
    """Build a weight payload. Persistence is owned by the mutation gateway."""
    mapped_weights = _map_factor_keys(weights)
    mapped_ic = _map_factor_keys(ic_scores)
    data = _load_weights_artifact()
    data.update({
        "updated_at": CALENDAR.previous_completed_session().isoformat(),
        "weights": mapped_weights,
        "ic_scores": mapped_ic,
        "source": "versioned_observable_footprint_ic_analysis",
        "strategy_decision": decision,
        "production_apply": False,
    })
    return data


def load_weights() -> dict[str, float]:
    """Load weights from file, fallback to defaults."""
    if WEIGHTS_FILE.exists():
        try:
            data = json.loads(WEIGHTS_FILE.read_text())
            return data.get("weights", DEFAULT_WEIGHTS)
        except Exception:
            pass
    return DEFAULT_WEIGHTS.copy()


def load_horizon_weights(horizon: int = 3) -> dict[str, float]:
    """Load horizon-specific weights from file, fallback to general weights.

    Different horizons have different optimal factors:
    - 1d: relative_strength dominant (IC=-0.708)
    - 3d: relative_strength + closing_strength
    - 10d: closing_strength dominant (IC=-0.419)
    """
    if WEIGHTS_FILE.exists():
        try:
            data = json.loads(WEIGHTS_FILE.read_text())
            horizon_key = f"{horizon}d"
            horizon_weights = data.get("horizon_specific_weights", {}).get(horizon_key)
            if horizon_weights:
                return horizon_weights
        except Exception:
            pass
    # Fallback to general weights
    return load_weights()


def run_weekly_optimization() -> dict:
    """Optimize only after the versioned validation gate passes."""
    session = SessionLocal()
    try:
        feedback = load_versioned_feedback(session)
        decision = evaluate_validation_gate(feedback)
        if decision["status"] != "VALIDATED_FOR_WEIGHT_UPDATE":
            save_validation_decision(decision)
            return {
                "status": KEEP_PREVIOUS_WEIGHT,
                "decision": {**decision, "weight_change_guard": KEEP_PREVIOUS_WEIGHT},
                "weights": load_weights(),
                "production_apply": False,
                "weights_file": str(WEIGHTS_FILE),
            }

        ic_scores = compute_factor_ic(feedback)
        if not ic_scores:
            decision = {
                **decision,
                "status": KEEP_PREVIOUS_WEIGHT,
                "reason": "insufficient_valid_factor_pairs",
            }
            save_validation_decision(decision)
            return {
                "status": KEEP_PREVIOUS_WEIGHT,
                "decision": decision,
                "weights": load_weights(),
                "production_apply": False,
                "weights_file": str(WEIGHTS_FILE),
            }

        weights = compute_optimal_weights(ic_scores)
        from research.stability import factor_stability

        previous = load_weights()
        mapped_proposed = _map_factor_keys(weights)
        stability_rows = [
            factor_stability({
                "factor": factor,
                "current_ic": ic_scores.get(factor),
                "sample_count": decision.get("sample_count") or 0,
                "coverage": decision.get("factor_coverage"),
            })
            for factor in weights
        ]
        mutation = request_weight_change(
            source="weight_optimizer",
            previous=previous,
            proposed=mapped_proposed,
            persist=None,
            sample_count=int(decision.get("sample_count") or 0),
            trading_days=int(decision.get("trading_days") or 0),
            factor_coverage=decision.get("factor_coverage"),
            confirmations=int(decision.get("confirmations") or 0),
            average_loss=decision.get("average_loss"),
            reason="optimizer_ic",
        )
        decision = {
            **decision,
            "weight_change_guard": KEEP_PREVIOUS_WEIGHT,
            "kept_factors": list(previous),
            "weight_mutation": mutation,
            "production_apply": False,
        }
        save_validation_decision(decision)
        return {
            "status": KEEP_PREVIOUS_WEIGHT,
            "ic_scores": ic_scores,
            "weights": previous,
            "proposed_weight": mapped_proposed,
            "current_weight": previous,
            "decision": decision,
            "stability": stability_rows,
            "production_apply": False,
            "weights_file": str(WEIGHTS_FILE),
        }
    finally:
        session.close()


if __name__ == "__main__":
    result = run_weekly_optimization()
    print(json.dumps(result, indent=2))
