"""Capital report and scorecard utilities."""
from __future__ import annotations

import json
from .calibration import evaluate_calibration
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any


def capital_summary_row(row: dict[str, Any]) -> dict[str, Any]:
    fields = [
        "symbol", "capital_state", "capital_intent", "capital_score", "capital_strength",
        "capital_quality", "quality_label", "distribution_score", "distribution_probability",
        "distribution_stage", "trap_score", "trap_probability", "crowding_score",
        "state_duration", "state_age_score", "late_state_risk", "path_type",
        "t1_probability", "t3_probability", "t5_probability", "combined_score",
        "path_distribution", "intent_probabilities", "transition_probabilities",
    ]
    return {field: row.get(field) for field in fields}


def write_daily_capital_report(root: Path, output_date: str, rows: list[dict[str, Any]]) -> dict[str, Path]:
    """Write daily public-data capital report beside existing research artifacts."""
    report_root = root / "daily-capital"
    report_root.mkdir(parents=True, exist_ok=True)
    summaries = [capital_summary_row(row) for row in rows if row.get("capital_state")]
    groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in summaries:
        groups[str(row["capital_state"])].append(row)
    for group in groups.values():
        group.sort(key=lambda item: float(item.get("capital_score") or 0.0), reverse=True)
    payload = {
        "status": "RESEARCH_ONLY",
        "model_version": "capital_behavior_v2",
        "validation_status": "UNVALIDATED_NO_FIXED_CHAIN",
        "as_of_date": output_date,
        "semantic_contract": {
            "volume": "OBSERVED",
            "evidence": "DERIVED",
            "state_and_intent": "INFERRED",
            "path_probabilities": "PREDICTED",
        },
        "by_state": dict(groups),
    }
    json_path = report_root / f"{output_date}.json"
    md_path = report_root / f"{output_date}.md"
    json_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False, default=str) + "\n", encoding="utf-8")
    lines = [
        f"# Daily Capital Behavior - {output_date}",
        "",
        "- Status: `RESEARCH_ONLY`",
        "- Validation: `UNVALIDATED_NO_FIXED_CHAIN`",
        "- Evidence is derived from public price-volume observations; no participant identity is asserted.",
        "",
    ]
    for state, group in sorted(groups.items()):
        lines.extend([f"## {state}", "", "| Symbol | Capital | Distribution | Trap | Path |", "|---|---:|---:|---:|---|"])
        for row in group[:10]:
            lines.append(
                f"| {row['symbol']} | {float(row.get('capital_score') or 0):.2f} | "
                f"{float(row.get('distribution_score') or 0):.2f} | {float(row.get('trap_score') or 0):.2f} | "
                f"{row.get('path_type') or 'UNKNOWN'} |"
            )
        lines.append("")
    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return {"json": json_path, "markdown": md_path}


def _ratio(numerator: int | float, denominator: int | float) -> float | None:
    return round(float(numerator) / float(denominator), 6) if denominator else None


def write_capital_scoreboard(root: Path, engine=None) -> dict[str, Path]:
    """Write research-only capital outcome diagnostics from versioned rows."""
    root.mkdir(parents=True, exist_ok=True)
    if engine is None:
        from db.engine import DATABASE_URL
        from sqlalchemy import create_engine
        engine = create_engine(DATABASE_URL)
    from sqlalchemy import text

    with engine.connect() as connection:
        rows = [
            dict(row)
            for row in connection.execute(text("""
                SELECT ft.id, ft.symbol, ft.horizon_days, ft.forward_return,
                       ft.capital_state_at_entry, ft.capital_intent_at_entry,
                       ft.capital_validation_status,
                       ft.distribution_score_at_entry, ft.trap_score_at_entry,
                       t.expected_direction, cpo.state_correct, cpo.intent_correct,
                       cpo.path_correct, cpo.actual_path
                FROM forward_tracking ft
                LEFT JOIN tickets t ON t.id = ft.ticket_id
                LEFT JOIN capital_prediction_outcome cpo
                  ON cpo.forward_tracking_id = ft.id
                WHERE ft.check_status = 'completed'
                  AND ft.forward_return IS NOT NULL
                  AND ft.capital_model_version = 'capital_behavior_v2'
                  AND ft.capital_validation_status = 'VALIDATED_FOR_BENCHMARK'
                ORDER BY ft.as_of_date, ft.id
            """)).mappings()
        ]

    returns = [float(row["forward_return"]) for row in rows]
    wins = [value for value in returns if value > 0]
    losses = [value for value in returns if value < 0]
    profit_factor = (
        round(sum(wins) / abs(sum(losses)), 6)
        if losses and sum(losses) != 0
        else None
    )

    by_horizon: dict[str, dict[str, Any]] = {}
    for horizon in (1, 3, 5):
        cohort = [row for row in rows if int(row["horizon_days"]) == horizon]
        cohort_returns = [float(row["forward_return"]) for row in cohort]
        expected = [
            row for row in cohort
            if row.get("expected_direction") in {"LONG", "SHORT"}
        ]
        direction_hits = [
            row for row in expected
            if (
                row["expected_direction"] == "LONG" and float(row["forward_return"]) > 0
            ) or (
                row["expected_direction"] == "SHORT" and float(row["forward_return"]) < 0
            )
        ]
        by_horizon[f"t{horizon}"] = {
            "sample_count": len(cohort),
            "direction_accuracy": _ratio(len(direction_hits), len(expected)),
            "win_rate": _ratio(sum(value > 0 for value in cohort_returns), len(cohort_returns)),
            "avg_return": round(sum(cohort_returns) / len(cohort_returns), 6) if cohort_returns else None,
        }

    def accuracy(column: str) -> float | None:
        measured = [row[column] for row in rows if row.get(column) is not None]
        return _ratio(sum(bool(value) for value in measured), len(measured))

    risk_rows = [
        row for row in rows
        if float(row.get("distribution_score_at_entry") or 0) >= 0.70
        or float(row.get("trap_score_at_entry") or 0) >= 0.70
    ]
    distribution_warning_rows = [
        row for row in rows if float(row.get("distribution_score_at_entry") or 0) >= 0.70
    ]
    trap_warning_rows = [
        row for row in rows if float(row.get("trap_score_at_entry") or 0) >= 0.70
    ]
    high_momentum = [
        row for row in rows
        if row.get("capital_state_at_entry") in {
            "ACTIVE_MARKUP", "SECONDARY_MARKUP", "LATE_MARKUP",
        }
    ]
    actual_paths = defaultdict(int)
    for row in high_momentum:
        actual_paths[str(row.get("actual_path") or "UNAVAILABLE")] += 1

    payload = {
        "status": "RESEARCH_ONLY",
        "model_version": "capital_behavior_v2",
        "validation_status": "UNVALIDATED_NO_FIXED_CHAIN",
        "generated_at": datetime.utcnow().isoformat() + "Z",
        "sample_count": len(rows),
        "capital_state_accuracy": accuracy("state_correct"),
        "intent_accuracy": accuracy("intent_correct"),
        "path_accuracy": accuracy("path_correct"),
        "t1_accuracy": by_horizon["t1"]["direction_accuracy"],
        "t3_accuracy": by_horizon["t3"]["direction_accuracy"],
        "t5_accuracy": by_horizon["t5"]["direction_accuracy"],
        "win_rate": _ratio(len(wins), len(returns)),
        "avg_return": round(sum(returns) / len(returns), 6) if returns else None,
        "median_return": sorted(returns)[len(returns) // 2] if returns else None,
        "profit_factor": profit_factor,
        "mfe": "UNAVAILABLE_NOT_PERSISTED",
        "mae": "UNAVAILABLE_NOT_PERSISTED",
        "distribution_avoidance": "UNAVAILABLE_NO_PRODUCTION_GATE",
        "trap_avoidance": "UNAVAILABLE_NO_PRODUCTION_GATE",
        "distribution_warning_precision": _ratio(
            sum(float(row["forward_return"]) <= 0 for row in distribution_warning_rows),
            len(distribution_warning_rows),
        ),
        "trap_warning_precision": _ratio(
            sum(float(row["forward_return"]) <= 0 for row in trap_warning_rows),
            len(trap_warning_rows),
        ),
        "risk_warning_sample_count": len(risk_rows),
        "calibration": {
            "path_t1": evaluate_calibration(
                [row.get("t1_probability") for row in rows],
                [1.0 if row.get("actual_path") == row.get("predicted_path") else 0.0 for row in rows],
            ),
            "path_t3": {"status": "UNAVAILABLE_NO_FIXED_CHAIN", "sample_count": 0},
            "path_t5": {"status": "UNAVAILABLE_NO_FIXED_CHAIN", "sample_count": 0},
        },
        "by_horizon": by_horizon,
        "high_momentum_distribution_analysis": {
            "sample_count": len(high_momentum),
            "actual_path_counts": dict(sorted(actual_paths.items())),
            "continue_up_count": actual_paths["CONTINUE_UP"] + actual_paths["ACCELERATE_UP"],
            "late_markup_count": actual_paths["LATE_MARKUP"],
            "distribution_count": actual_paths["DISTRIBUTION"],
            "markdown_count": actual_paths["BREAKDOWN"],
        },
    }
    json_path = root / "capital-behavior-scoreboard.json"
    markdown_path = root / "capital-behavior-scoreboard.md"
    json_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    lines = [
        "# Capital Behavior Scoreboard",
        "",
        "- Status: `RESEARCH_ONLY`",
        "- Validation: `UNVALIDATED_NO_FIXED_CHAIN`",
        f"- Sample count: `{payload['sample_count']}`",
        f"- State accuracy: `{payload['capital_state_accuracy']}`",
        f"- Intent accuracy: `{payload['intent_accuracy']}`",
        f"- Path accuracy: `{payload['path_accuracy']}`",
        f"- Win rate: `{payload['win_rate']}`",
        f"- Avg return: `{payload['avg_return']}`",
        f"- Profit factor: `{payload['profit_factor']}`",
        "- MFE/MAE: `UNAVAILABLE_NOT_PERSISTED`",
        "- Distribution/trap avoidance: `UNAVAILABLE_NO_PRODUCTION_GATE`",
        "",
        "## High Momentum Outcomes",
        "",
        "| Outcome | Count |",
        "|---|---:|",
    ]
    for name, count in payload["high_momentum_distribution_analysis"]["actual_path_counts"].items():
        lines.append(f"| {name} | {count} |")
    markdown_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return {"json": json_path, "markdown": markdown_path}
