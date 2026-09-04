"""
xiaomei bounded self-evolution.
Aligned with xiaogu's xiaogu_safe_self_evolve.py architecture.

Applies small scoring_config nudges when performance gate is READY.
Only modifies allowed knobs within bounded ranges.
"""

from __future__ import annotations

import json
import logging
import os
from datetime import date, datetime
from pathlib import Path

logger = logging.getLogger(__name__)

# Allowed knobs with bounded ranges
ALLOWED_KNOBS = {
    "min_market_score_gate": (0.40, 0.70),
    "top_k_tickets": (1, 10),
    "candidate_pool_size": (5, 20),
    "evidence_momentum_weight": (0.20, 0.50),
    "evidence_catalyst_boost_weight": (0.10, 0.35),
    "evidence_volume_weight": (0.05, 0.25),
    "evidence_reversal_weight": (0.05, 0.25),
}

FROZEN_KEYS = {
    "buffett_principles",
    "serenity_ontology",
    "fact_inference_semantics",
    "evidence_hierarchy",
    "no_lookahead_rules",
    "production_safety_boundary",
}

# Max proposals per day
MAX_PROPOSALS_PER_DAY = 3
STRATEGY_VERSION = "observable_footprint_v1"
VERSION_STATUS = "VERSIONED"


def _get_config(engine, key: str) -> str | None:
    """Get a config value from scoring_config table."""
    from sqlalchemy import text

    with engine.connect() as conn:
        result = conn.execute(text("""
            SELECT config_value FROM scoring_config WHERE config_key = :key
        """), {"key": key})
        row = result.fetchone()
        return row[0] if row else None


def _persist_config(engine, key: str, value: str):
    from sqlalchemy import text

    with engine.connect() as conn:
        conn.execute(text("""
            UPDATE scoring_config
            SET config_value = :value, updated_at = NOW()
            WHERE config_key = :key
        """), {"key": key, "value": value})
        conn.commit()


def _set_config(
    engine,
    key: str,
    value: str,
    reason: str = "",
    *,
    sample_count: int = 0,
    trading_days: int = 0,
    confirmations: int = 0,
    factor_coverage: float | None = None,
    average_loss: float | None = None,
):
    """Update scoring_config only through the weight mutation gateway."""
    from research.weight_mutation import request_weight_change

    current = _get_config(engine, key)
    previous = None if current in (None, "") else float(current)
    proposed = float(value)
    result = request_weight_change(
        source="self_evolve",
        previous=previous,
        proposed=proposed,
        persist=lambda: _persist_config(engine, key, str(value)),
        sample_count=sample_count,
        trading_days=trading_days,
        confirmations=confirmations,
        factor_coverage=factor_coverage,
        average_loss=average_loss,
        key=key,
        reason=reason,
    )
    if result["persisted"]:
        logger.info(f"Updated {key} = {value} (reason: {reason})")
    else:
        logger.warning(f"Blocked {key} = {value} via weight mutation gateway: {result['reasons']}")
    return result


def _check_performance_gate(engine) -> dict:
    """Check if performance gate is ready for evolution.

    Returns: {status: READY|NOT_READY, metrics: {...}}
    """
    from sqlalchemy import text

    with engine.connect() as conn:
        # Get recent performance (last 20 trading days)
        result = conn.execute(text("""
            SELECT
                COUNT(*) as total_completed,
                SUM(CASE WHEN ft.forward_return > 0 THEN 1 ELSE 0 END)::float /
                    NULLIF(COUNT(*), 0) as win_rate,
                AVG(ft.forward_return) as avg_return,
                COUNT(DISTINCT t.output_date) as trading_days
            FROM forward_tracking ft
            JOIN tickets t ON ft.ticket_id = t.id
            JOIN research_runs rr ON rr.run_id = t.research_run_id
            WHERE ft.check_status = 'completed'
            AND rr.status = 'done'
            AND rr.finished_at IS NOT NULL
            AND rr.config->>'strategy_version' = :strategy_version
            AND COALESCE(rr.config->>'version_status', '') = :version_status
            AND t.output_date >= (
                SELECT MAX(output_date) - INTERVAL '30 days' FROM tickets
            )
        """), {
            "strategy_version": STRATEGY_VERSION,
            "version_status": VERSION_STATUS,
        })
        row = result.fetchone()

        if not row or not row[0]:
            return {"status": "NOT_READY", "reason": "insufficient_data"}

        metrics = {
            "total_completed": row[0],
            "win_rate": float(row[1]) if row[1] else 0,
            "avg_return": float(row[2]) if row[2] else 0,
            "trading_days": row[3],
        }

        # Gate conditions
        if metrics["trading_days"] < 10:
            return {"status": "NOT_READY", "reason": "too_few_trading_days", "metrics": metrics}

        if metrics["total_completed"] < 30:
            return {"status": "NOT_READY", "reason": "too_few_completed", "metrics": metrics}

        # Ready for small step changes if win rate is reasonable
        if metrics["win_rate"] >= 0.45:
            return {"status": "READY_FOR_SMALL_STEP_CHANGE", "metrics": metrics}

        # Ready for proposals if performance is declining
        if metrics["win_rate"] < 0.40:
            return {"status": "READY_FOR_PROPOSAL", "metrics": metrics}

        return {"status": "NOT_READY", "reason": "performance_ok", "metrics": metrics}


def _analyze_factor_performance(engine) -> dict:
    """Analyze which factors are performing well/poorly."""
    from sqlalchemy import text

    with engine.connect() as conn:
        # Get factor IC scores from recent signal effectiveness
        result = conn.execute(text("""
            SELECT signal_key, ic_score, win_rate, avg_return
            FROM signal_effectiveness
            WHERE analysis_date >= (
                SELECT MAX(analysis_date) - INTERVAL '14 days' FROM signal_effectiveness
            )
            AND data_version = :strategy_version
            AND ic_score IS NOT NULL
            ORDER BY ic_score DESC
        """), {"strategy_version": STRATEGY_VERSION})
        factors = [dict(row._mapping) for row in result.fetchall()]

    return {"factors": factors}


def _propose_weight_changes(
    engine,
    gate_status: str,
    factor_performance: dict,
) -> list[dict]:
    """Propose weight changes based on performance analysis.

    Returns: list of {key, current, proposed, reason}
    """
    proposals = []
    factors = factor_performance.get("factors", [])

    if not factors:
        return proposals

    # Find best and worst performing factors
    best_factor = factors[0] if factors else None
    worst_factor = factors[-1] if factors else None

    # If we have a strong positive factor, suggest increasing its weight
    if best_factor and best_factor.get("ic_score", 0) > 0.1:
        signal_key = best_factor["signal_key"]
        # Map signal_key to config key
        weight_key = f"evidence_{signal_key}_weight"
        if weight_key in ALLOWED_KNOBS:
            current = _get_config(engine, weight_key)
            if current:
                current_val = float(current)
                min_val, max_val = ALLOWED_KNOBS[weight_key]
                proposed_val = min(max_val, current_val * 1.1)  # 10% increase
                if proposed_val != current_val:
                    proposals.append({
                        "key": weight_key,
                        "current": current_val,
                        "proposed": round(proposed_val, 4),
                        "reason": f"Strong positive IC ({best_factor['ic_score']:.3f})",
                    })

    # If we have a weak negative factor, suggest decreasing its weight
    if worst_factor and worst_factor.get("ic_score", 0) < -0.05:
        signal_key = worst_factor["signal_key"]
        weight_key = f"evidence_{signal_key}_weight"
        if weight_key in ALLOWED_KNOBS:
            current = _get_config(engine, weight_key)
            if current:
                current_val = float(current)
                min_val, max_val = ALLOWED_KNOBS[weight_key]
                proposed_val = max(min_val, current_val * 0.9)  # 10% decrease
                if proposed_val != current_val:
                    proposals.append({
                        "key": weight_key,
                        "current": current_val,
                        "proposed": round(proposed_val, 4),
                        "reason": f"Weak negative IC ({worst_factor['ic_score']:.3f})",
                    })

    return proposals[:MAX_PROPOSALS_PER_DAY]


def run_self_evolution(engine, dry_run: bool = False) -> dict:
    """Run self-evolution cycle.

    Returns: {gate_status, proposals_applied, proposals_skipped}
    """
    # Check performance gate
    gate = _check_performance_gate(engine)
    gate_status = gate["status"]

    if gate_status == "NOT_READY":
        logger.info(f"Gate not ready: {gate.get('reason')}")
        return {
            "gate_status": gate_status,
            "reason": gate.get("reason"),
            "metrics": gate.get("metrics"),
            "proposals_applied": 0,
            "proposals_skipped": 0,
        }

    # Analyze factor performance
    factor_perf = _analyze_factor_performance(engine)

    # Propose changes
    proposals = _propose_weight_changes(engine, gate_status, factor_perf)

    if not proposals:
        logger.info("No proposals generated")
        return {
            "gate_status": gate_status,
            "metrics": gate.get("metrics"),
            "proposals_applied": 0,
            "proposals_skipped": 0,
        }

    # Apply proposals
    applied = 0
    skipped = 0

    for proposal in proposals:
        key = proposal["key"]
        proposed = proposal["proposed"]
        reason = proposal["reason"]

        if key in FROZEN_KEYS:
            logger.warning(f"Proposal {key} is frozen and cannot be evolved")
            skipped += 1
            continue
        if key not in ALLOWED_KNOBS:
            logger.warning(f"Proposal {key} is not an allowed knob")
            skipped += 1
            continue
        min_val, max_val = ALLOWED_KNOBS[key]
        if not (min_val <= proposed <= max_val):
            logger.warning(f"Proposal {key}={proposed} out of bounds [{min_val}, {max_val}]")
            skipped += 1
            continue

        current = proposal.get("current")
        ledger = {
            "version": STRATEGY_VERSION,
            "before": current,
            "after": proposed,
            "evidence": reason,
            "validation": gate_status,
            "rollback": current,
        }
        proposal["ledger"] = ledger
        metrics = gate.get("metrics") or {}
        if dry_run:
            logger.info(f"[DRY RUN] Would update {key} = {proposed} ({reason})")
            applied += 1
        else:
            mutation = _set_config(
                engine,
                key,
                str(proposed),
                reason,
                sample_count=int(metrics.get("total_completed") or 0),
                trading_days=int(metrics.get("trading_days") or 0),
                confirmations=int(metrics.get("confirmations") or 0),
                factor_coverage=metrics.get("factor_coverage"),
                average_loss=metrics.get("avg_return"),
            )
            proposal["weight_mutation"] = mutation
            if mutation.get("persisted"):
                applied += 1
            else:
                skipped += 1

    result = {
        "gate_status": gate_status,
        "metrics": gate.get("metrics"),
        "proposals": proposals,
        "proposals_applied": applied,
        "proposals_skipped": skipped,
    }

    # Log evolution result
    _log_evolution(result)

    return result


def _log_evolution(result: dict):
    """Log evolution result to file."""
    log_dir = Path(__file__).resolve().parent.parent / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)

    log_file = log_dir / f"evolution-{date.today().isoformat()}.jsonl"

    entry = {
        "timestamp": datetime.now().isoformat(),
        **result,
    }

    with open(log_file, "a") as f:
        f.write(json.dumps(entry, default=str) + "\n")


if __name__ == "__main__":
    import argparse
    from sqlalchemy import create_engine
    from db.engine import DATABASE_URL

    logging.basicConfig(level=logging.INFO)

    parser = argparse.ArgumentParser(description="xiaomei self-evolution")
    parser.add_argument("--dry-run", action="store_true", help="Dry run mode")
    parser.add_argument("--check-gate", action="store_true", help="Check gate only")
    args = parser.parse_args()

    engine = create_engine(DATABASE_URL)

    if args.check_gate:
        gate = _check_performance_gate(engine)
        print(json.dumps(gate, indent=2, default=str))
    else:
        result = run_self_evolution(engine, dry_run=args.dry_run)
        print(json.dumps(result, indent=2, default=str))
