#!/usr/bin/env python3
"""Weekly weight optimizer based on factor IC analysis.

Computes Information Coefficient (Spearman rank correlation) between
each factor and forward returns, then generates optimal scoring weights.
"""
import json
import sys
from datetime import date, timedelta
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

sys.path.insert(0, str(Path(__file__).resolve().parent))

from db.engine import SessionLocal
from db.models import FactorSnapshot, ForwardTracking
from sqlalchemy import text

WEIGHTS_FILE = Path(__file__).resolve().parent.parent / "data" / "scoring_weights.json"

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
]


def compute_factor_ic(session, lookback_days: int = 60) -> dict[str, float]:
    """Compute IC (rank correlation) for each factor vs 1d forward return."""
    cutoff = date.today() - timedelta(days=lookback_days)

    factors = session.execute(text(
        "SELECT trade_date, symbol, " + ", ".join(FACTORS) + " "
        "FROM factor_snapshots WHERE trade_date >= :cutoff ORDER BY trade_date, symbol"
    ), {"cutoff": cutoff}).fetchall()

    tracking = session.execute(text(
        "SELECT as_of_date, symbol, forward_return "
        "FROM forward_tracking WHERE check_status = 'completed' "
        "AND as_of_date >= :cutoff AND horizon_days = 1"
    ), {"cutoff": cutoff}).fetchall()

    if not factors or not tracking:
        return {}

    factor_df = pd.DataFrame(factors, columns=["trade_date", "symbol"] + FACTORS)
    track_df = pd.DataFrame(tracking, columns=["as_of_date", "symbol", "forward_return"])

    merged = factor_df.merge(track_df, left_on=["trade_date", "symbol"], right_on=["as_of_date", "symbol"], how="inner")

    if len(merged) < 20:
        return {}

    ic_scores = {}
    for factor in FACTORS:
        valid = merged[[factor, "forward_return"]].dropna()
        if len(valid) < 10:
            continue
        ic, _ = stats.spearmanr(valid[factor], valid["forward_return"])
        ic_scores[factor] = round(float(ic), 4)

    return ic_scores


def compute_optimal_weights(ic_scores: dict[str, float]) -> dict[str, float]:
    """Convert IC scores to normalized weights."""
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

    weights = {}
    for factor in FACTORS:
        ic = valid_ic.get(factor, 0)
        abs_val = abs_ic.get(factor, 0)
        raw_weight = abs_val / total
        weights[factor] = round(raw_weight * (1 if ic >= 0 else -1), 4)

    return weights


def save_weights(weights: dict[str, float], ic_scores: dict[str, float]):
    """Save weights and IC scores to file."""
    WEIGHTS_FILE.parent.mkdir(parents=True, exist_ok=True)
    data = {
        "updated_at": date.today().isoformat(),
        "weights": weights,
        "ic_scores": ic_scores,
        "source": "weekly_ic_analysis",
    }
    WEIGHTS_FILE.write_text(json.dumps(data, indent=2))


def load_weights() -> dict[str, float]:
    """Load weights from file, fallback to defaults."""
    if WEIGHTS_FILE.exists():
        try:
            data = json.loads(WEIGHTS_FILE.read_text())
            return data.get("weights", DEFAULT_WEIGHTS)
        except Exception:
            pass
    return DEFAULT_WEIGHTS.copy()


def load_horizon_weights(horizon: int = 5) -> dict[str, float]:
    """Load horizon-specific weights from file, fallback to general weights.
    
    Different horizons have different optimal factors:
    - 1d: relative_strength dominant (IC=-0.708)
    - 3d: relative_strength + closing_strength
    - 5d: volume_weighted_momentum + closing_strength
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
    """Run full weekly weight optimization."""
    session = SessionLocal()
    try:
        ic_scores = compute_factor_ic(session)
        weights = compute_optimal_weights(ic_scores)
        save_weights(weights, ic_scores)
        return {
            "status": "done",
            "ic_scores": ic_scores,
            "weights": weights,
            "weights_file": str(WEIGHTS_FILE),
        }
    finally:
        session.close()


if __name__ == "__main__":
    result = run_weekly_optimization()
    print(json.dumps(result, indent=2))
