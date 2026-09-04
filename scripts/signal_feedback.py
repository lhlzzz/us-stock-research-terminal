#!/usr/bin/env python3
"""Signal feedback loop: analysis results → automatic weight adjustment."""
import json
from datetime import timedelta
from pathlib import Path

import numpy as np
import pandas as pd
from sqlalchemy import text

from scripts.db.engine import SessionLocal
from scripts.db.models import FactorSnapshot, ForwardTracking
from market_calendar import CALENDAR
from research.weight_mutation import KEEP_PREVIOUS_WEIGHT, request_weight_change

WEIGHTS_FILE = Path(__file__).resolve().parent.parent / "data" / "scoring_weights.json"
FEEDBACK_DIR = Path(__file__).resolve().parent.parent / "research" / "signal-feedback"

FACTORS = [
    "prior_20d_momentum", "five_day_acceleration",
    "relative_strength_vs_equal_weight", "volume_weighted_momentum",
    "closing_strength_5d", "volume_confirmation", "rsi_14",
]


def analyze_signal_effectiveness() -> dict:
    session = SessionLocal()
    try:
        cutoff = CALENDAR.previous_completed_session() - timedelta(days=90)
        factors = session.execute(text(
            "SELECT trade_date, symbol, " + ", ".join(FACTORS) + " "
            "FROM factor_snapshots WHERE trade_date >= :cutoff"
        ), {"cutoff": cutoff}).fetchall()
        tracking = session.execute(text(
            "SELECT as_of_date, symbol, forward_return "
            "FROM forward_tracking WHERE check_status = 'completed' "
            "AND as_of_date >= :cutoff AND horizon_days = 1"
        ), {"cutoff": cutoff}).fetchall()

        if not factors or not tracking:
            return {"status": "insufficient_data", "factors": {}}

        fdf = pd.DataFrame(factors, columns=["trade_date", "symbol"] + FACTORS)
        tdf = pd.DataFrame(tracking, columns=["as_of_date", "symbol", "forward_return"])
        merged = fdf.merge(tdf, left_on=["trade_date", "symbol"], right_on=["as_of_date", "symbol"], how="inner")

        results = {}
        for factor in FACTORS:
            valid = merged[[factor, "forward_return"]].dropna()
            if len(valid) < 10:
                results[factor] = {"ic": 0, "win_rate": 0, "count": 0}
                continue
            from scipy import stats
            ic, _ = stats.spearmanr(valid[factor], valid["forward_return"])
            median_val = valid[factor].median()
            above = valid[valid[factor] > median_val]
            win_rate = (above["forward_return"] > 0).mean() if len(above) > 0 else 0
            results[factor] = {"ic": round(float(ic), 4), "win_rate": round(float(win_rate), 4), "count": len(valid)}
        return {"status": "done", "factors": results}
    finally:
        session.close()


def generate_weight_adjustments(effectiveness: dict) -> dict:
    if effectiveness.get("status") != "done":
        return {}
    current = {}
    if WEIGHTS_FILE.exists():
        try:
            current = json.loads(WEIGHTS_FILE.read_text()).get("weights", {})
        except Exception:
            pass
    adjustments = {}
    for factor, data in effectiveness.get("factors", {}).items():
        ic = data.get("ic", 0)
        current_w = current.get(factor, 0.1)
        if ic > 0.05:
            adj = min(0.05, abs(ic) * 0.2)
            adjustments[factor] = round(min(0.6, current_w + adj), 4)
        elif ic < -0.05:
            adj = min(0.05, abs(ic) * 0.2)
            adjustments[factor] = round(max(-0.3, current_w - adj), 4)
        else:
            adjustments[factor] = current_w
    return adjustments


def apply_adjustments(adjustments: dict):
    if not adjustments:
        return {"status": KEEP_PREVIOUS_WEIGHT, "persisted": False, "production_apply": False}
    current = {}
    if WEIGHTS_FILE.exists():
        try:
            current = json.loads(WEIGHTS_FILE.read_text()).get("weights", {})
        except Exception:
            current = {}
    session = CALENDAR.previous_completed_session().isoformat()
    data = {
        "updated_at": session,
        "weights": adjustments,
        "source": "signal_feedback",
        "status": "PROPOSAL_ONLY",
        "production_apply": False,
    }
    mutation = request_weight_change(
        source="signal_feedback",
        previous=current,
        proposed=adjustments,
        persist=None,
        reason="signal_feedback",
    )
    FEEDBACK_DIR.mkdir(parents=True, exist_ok=True)
    log_file = FEEDBACK_DIR / f"feedback-{session}.json"
    log_file.write_text(json.dumps({**data, "weight_mutation": mutation}, indent=2))
    return mutation


def run_feedback_loop() -> dict:
    effectiveness = analyze_signal_effectiveness()
    adjustments = generate_weight_adjustments(effectiveness)
    mutation = apply_adjustments(adjustments)
    return {
        "effectiveness": effectiveness,
        "adjustments": adjustments,
        "weight_mutation": mutation,
        "production_apply": False,
        "decision": KEEP_PREVIOUS_WEIGHT,
    }


if __name__ == "__main__":
    result = run_feedback_loop()
    print(json.dumps(result, indent=2))
