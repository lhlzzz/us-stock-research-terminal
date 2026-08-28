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


def _learning_snapshot(engine=None) -> dict[str, Any]:
    """Read only persisted V3 diagnostics; missing rows stay unavailable."""
    if engine is None:
        from db.engine import DATABASE_URL
        from sqlalchemy import create_engine
        engine = create_engine(DATABASE_URL)
    from sqlalchemy import text

    with engine.connect() as connection:
        dataset = dict(connection.execute(text("""
            SELECT COUNT(*) AS total_samples,
                   COUNT(*) FILTER (WHERE eligibility_reason = 'VALID') AS valid_samples,
                   COUNT(*) FILTER (WHERE eligible_for_training) AS train_samples,
                   COUNT(*) FILTER (WHERE eligible_for_validation) AS validation_samples,
                   COUNT(*) FILTER (WHERE eligible_for_test) AS test_samples,
                   COUNT(DISTINCT as_of_date) AS trading_days,
                   COUNT(DISTINCT symbol) AS symbols,
                   COUNT(DISTINCT label_version) FILTER (WHERE label_version IS NOT NULL) AS label_versions,
                   COUNT(DISTINCT model_version) AS model_versions
            FROM capital_behavior_dataset
        """)).mappings().one())
        errors = int(connection.execute(text("SELECT COUNT(*) FROM capital_prediction_error")).scalar() or 0)
        drift_result = connection.execute(text("""
            SELECT model_version, window_start::text, window_end::text, status,
                   state_accuracy, path_accuracy, calibration_error,
                   distribution_warning_precision, metrics
            FROM capital_model_drift
            ORDER BY created_at DESC, id DESC
            LIMIT 20
        """)).mappings()
        drift_rows = [dict(row) for row in drift_result]
    return {
        "dataset": dataset,
        "prediction_error_count": errors,
        "drift_records": drift_rows,
        "status": "RESEARCH_ONLY",
        # Valid labels make rows usable for research, but do not by themselves
        # satisfy the independent fixed-chain or promotion gates.
        "validation_status": "UNVALIDATED_NO_FIXED_CHAIN",
        "production_action": "NO_PRODUCTION_WEIGHT_CHANGE",
    }


def record_capital_model_drift(engine=None, *, min_samples: int = 30) -> dict[str, Any]:
    """Persist a drift observation only when valid outcomes are sufficient."""
    if engine is None:
        from db.engine import DATABASE_URL
        from sqlalchemy import create_engine
        engine = create_engine(DATABASE_URL)
    from sqlalchemy import text
    from .evaluation import evaluate_model_drift

    with engine.connect() as connection:
        rows = [dict(row) for row in connection.execute(text("""
            SELECT as_of_date, capital_state, predicted_path,
                   path_distribution_t3, future_outcome
            FROM capital_behavior_dataset
            WHERE eligibility_reason = 'VALID'
            ORDER BY as_of_date, symbol, research_run_id
        """)).mappings()]
    outcomes = [row.get("future_outcome") or {} for row in rows]
    result = evaluate_model_drift(
        actual_state=[outcome.get("state_after_3d") for outcome in outcomes],
        predicted_state=[row.get("capital_state") for row in rows],
        actual_path=[outcome.get("path_after_3d") for outcome in outcomes],
        predicted_path=[(row.get("predicted_path") or {}).get("path_type") for row in rows],
        path_probabilities=[row.get("path_distribution_t3") or {} for row in rows],
        min_samples=min_samples,
        window_start=min((row["as_of_date"] for row in rows), default=None),
        window_end=max((row["as_of_date"] for row in rows), default=None),
    )
    if result["status"] != "RESEARCH_ONLY":
        return result
    with engine.begin() as connection:
        connection.execute(text("""
            INSERT INTO capital_model_drift (
                model_version, window_start, window_end, status,
                state_accuracy, path_accuracy, calibration_error, metrics
            ) VALUES (
                :model_version, :window_start, :window_end, :status,
                :state_accuracy, :path_accuracy, :calibration_error,
                CAST(:metrics AS jsonb)
            )
            ON CONFLICT (model_version, window_start, window_end) DO UPDATE SET
                status = EXCLUDED.status,
                state_accuracy = EXCLUDED.state_accuracy,
                path_accuracy = EXCLUDED.path_accuracy,
                calibration_error = EXCLUDED.calibration_error,
                metrics = EXCLUDED.metrics
        """), {
            "model_version": result["model_version"],
            "window_start": result["window_start"],
            "window_end": result["window_end"],
            "status": result["status"],
            "state_accuracy": result["state_accuracy"],
            "path_accuracy": result["path_accuracy"],
            "calibration_error": result["calibration_error"],
            "metrics": json.dumps(result["metrics"], ensure_ascii=True, sort_keys=True),
        })
    return result


def write_capital_case_libraries(root: Path, engine=None) -> dict[str, Path]:
    """Export complete public-data cases and deterministic counterexamples."""
    if engine is None:
        from db.engine import DATABASE_URL
        from sqlalchemy import create_engine
        engine = create_engine(DATABASE_URL)
    from sqlalchemy import text
    from .case_retrieval import classify_case

    with engine.connect() as connection:
        rows = [dict(row) for row in connection.execute(text("""
            SELECT symbol, as_of_date::text, capital_state, capital_intent,
                   capital_strength, capital_quality, derived_features,
                   inferred_state, inferred_intent, predicted_path, future_outcome
            FROM capital_behavior_dataset
            WHERE eligibility_reason = 'VALID'
            ORDER BY as_of_date, symbol, id
        """)).mappings()]
    cases = []
    counterexamples = []
    for row in rows:
        outcome = row.get("future_outcome") or {}
        case = {
            "symbol": row.get("symbol"),
            "date": row.get("as_of_date"),
            "state": row.get("capital_state"),
            "intent": row.get("capital_intent"),
            "path": outcome.get("path_after_3d") or outcome.get("actual_path"),
            "evidence": row.get("derived_features") or {},
            "outcome": outcome,
            "return_3d": outcome.get("return_3d"),
            "regime": (row.get("derived_features") or {}).get("regime"),
            "similarity": None,
        }
        case_type = classify_case(row)
        if case_type:
            case["counterexample_type"] = case_type
            counterexamples.append(case)
        else:
            cases.append(case)
    case_root = root / "capital-cases"
    counterexample_root = root / "capital-counterexamples"
    case_root.mkdir(parents=True, exist_ok=True)
    counterexample_root.mkdir(parents=True, exist_ok=True)
    cases_path = case_root / "cases.jsonl"
    counterexamples_path = counterexample_root / "cases.jsonl"
    cases_path.write_text("".join(json.dumps(row, ensure_ascii=True, sort_keys=True, default=str) + "\n" for row in cases), encoding="utf-8")
    counterexamples_path.write_text("".join(json.dumps(row, ensure_ascii=True, sort_keys=True, default=str) + "\n" for row in counterexamples), encoding="utf-8")
    return {"cases": cases_path, "counterexamples": counterexamples_path}


def write_capital_learning_artifacts(root: Path, output_date: str, engine=None) -> dict[str, Path]:
    """Write the dated V3 learning artifact and a deterministic weekly review."""
    artifact_root = root / "capital-learning"
    artifact_root.mkdir(parents=True, exist_ok=True)
    record_capital_model_drift(engine)
    case_paths = write_capital_case_libraries(root, engine)
    snapshot = _learning_snapshot(engine)
    payload = {
        "artifact_version": "capital_learning_artifact_v1",
        "as_of_date": output_date,
        "status": snapshot["status"],
        "validation_status": snapshot["validation_status"],
        "production_action": snapshot["production_action"],
        "dataset": snapshot["dataset"],
        "prediction_error_count": snapshot["prediction_error_count"],
        "drift_records": snapshot["drift_records"],
        "metrics": {
            "state_accuracy": "NOT_READY",
            "transition_accuracy": "NOT_READY",
            "intent_accuracy": "NOT_READY",
            "path_calibration": "NOT_READY",
            "distribution_warning": "NOT_READY",
            "reversal_detection": "NOT_READY",
            "economic_outcome": "NOT_READY",
            "model_drift": "NOT_READY" if not snapshot["drift_records"] else "RESEARCH_ONLY",
        },
    }
    json_path = artifact_root / f"{output_date}.json"
    md_path = artifact_root / f"{output_date}.md"
    json_path.write_text(json.dumps(payload, indent=2, ensure_ascii=True, default=str) + "\n", encoding="utf-8")
    lines = [
        f"# Capital Learning - {output_date}",
        "",
        "- Status: `RESEARCH_ONLY`",
        f"- Validation: `{payload['validation_status']}`",
        "- Production action: `NO_PRODUCTION_WEIGHT_CHANGE`",
        "",
        "## Dataset",
        "",
        f"- Total samples: `{payload['dataset']['total_samples']}`",
        f"- Valid samples: `{payload['dataset']['valid_samples']}`",
        f"- Train / validation / test: `{payload['dataset']['train_samples']}` / `{payload['dataset']['validation_samples']}` / `{payload['dataset']['test_samples']}`",
        f"- Symbols / trading days: `{payload['dataset']['symbols']}` / `{payload['dataset']['trading_days']}`",
        f"- Prediction errors: `{payload['prediction_error_count']}`",
        "",
        "## Metrics",
        "",
        "All model metrics remain `NOT_READY` until versioned fixed-chain samples pass the eligibility gate.",
        "",
    ]
    md_path.write_text("\n".join(lines), encoding="utf-8")

    iso_week = datetime.fromisoformat(f"{output_date}T00:00:00").date().isocalendar()
    weekly_json = artifact_root / f"weekly-model-review-{iso_week.year}-{iso_week.week:02d}.json"
    weekly_md = artifact_root / f"weekly-model-review-{iso_week.year}-{iso_week.week:02d}.md"
    weekly_payload = {
        "artifact_version": "capital_weekly_model_review_v1",
        "week": f"{iso_week.year}-W{iso_week.week:02d}",
        "status": payload["status"],
        "validation_status": payload["validation_status"],
        "sample_growth": payload["dataset"],
        "state_accuracy": "NOT_READY",
        "transition_accuracy": "NOT_READY",
        "intent_accuracy": "NOT_READY",
        "path_calibration": "NOT_READY",
        "distribution_warning": "NOT_READY",
        "reversal_detection": "NOT_READY",
        "economic_outcome": "NOT_READY",
        "model_drift": "NOT_READY" if not snapshot["drift_records"] else snapshot["drift_records"],
        "production_action": "NO_PRODUCTION_WEIGHT_CHANGE",
    }
    weekly_json.write_text(json.dumps(weekly_payload, indent=2, ensure_ascii=True, default=str) + "\n", encoding="utf-8")
    weekly_md.write_text(
        f"# Weekly Capital Model Review {weekly_payload['week']}\n\n"
        f"- Status: `RESEARCH_ONLY`\n"
        f"- Validation: `{weekly_payload['validation_status']}`\n"
        f"- Samples: `{payload['dataset']['total_samples']}` total, `{payload['dataset']['valid_samples']}` valid\n"
        "- State / transition / intent / path calibration: `NOT_READY`\n"
        "- Production action: `NO_PRODUCTION_WEIGHT_CHANGE`\n",
        encoding="utf-8",
    )
    return {
        "json": json_path,
        "markdown": md_path,
        "weekly_json": weekly_json,
        "weekly_markdown": weekly_md,
        **case_paths,
    }
