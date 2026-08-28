#!/usr/bin/env python3
"""Evaluate Capital Brain evidence without changing production scoring weights."""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats
from sqlalchemy import create_engine, text

from db.engine import DATABASE_URL


ROOT = Path(__file__).resolve().parent.parent
FEATURES = (
    "upward_pressure", "downward_pressure", "volume_pressure",
    "demand_persistence", "supply_exhaustion", "absorption", "accumulation",
    "markup", "distribution", "crowding", "trap", "price_impact",
)
MIN_ROWS = 30


def evaluate_capital_features(engine=None) -> dict:
    engine = engine or create_engine(DATABASE_URL)
    rows = pd.read_sql(text("""
        SELECT ce.evidence_type, ce.value, ft.forward_return,
               ft.capital_validation_status,
               rr.config->>'version_status' AS version_status
        FROM capital_evidence ce
        JOIN forward_tracking ft
          ON ft.symbol = ce.symbol
         AND ft.as_of_date = ce.as_of_date
        JOIN tickets t ON t.id = ft.ticket_id
        JOIN research_runs rr ON rr.run_id = t.research_run_id
        WHERE ft.check_status = 'completed'
          AND ft.forward_return IS NOT NULL
          AND ft.horizon_days = 1
          AND ce.model_version = 'capital_behavior_v1'
    """), engine)
    fixed = rows[
        (rows["capital_validation_status"] == "VALIDATED_FOR_BENCHMARK")
        & (rows["version_status"] == "VERSIONED")
    ]
    result = {
        "status": "UNVALIDATED_NO_FIXED_CHAIN" if len(fixed) < MIN_ROWS else "RESEARCH_ONLY",
        "sample_count": int(len(fixed)),
        "production_action": "NO_WEIGHT_CHANGE",
        "feature_ic": {},
    }
    for feature in FEATURES:
        cohort = fixed[fixed["evidence_type"] == feature][["value", "forward_return"]].dropna()
        if len(cohort) < 10:
            continue
        ic, pvalue = stats.spearmanr(cohort["value"], cohort["forward_return"])
        if np.isfinite(ic):
            result["feature_ic"][feature] = {
                "sample_count": int(len(cohort)),
                "ic": round(float(ic), 6),
                "pvalue": round(float(pvalue), 6),
            }
    return result


def main() -> int:
    result = evaluate_capital_features()
    path = ROOT / "research" / "capital-feature-optimizer.json"
    path.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"artifact": str(path), **result}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
