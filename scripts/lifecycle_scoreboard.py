#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pandas as pd

RESEARCH_BASE = Path(__file__).resolve().parent.parent / "research"
RUNTIME_LEDGER_GLOBS = [
    "*/runtime-decision-ledger.jsonl",
]
METRICS_GLOBS = [
    "*/metrics-*.json",
]
FORWARD_TRACKING_GLOBS = [
    "profit-ticket-pipeline/forward-tracking-*.csv",
    "profit-ticket-pipeline-opening/forward-tracking-*.csv",
    "profit-ticket-pipeline-daily/forward-tracking-*.csv",
    "profit-ticket-pipeline-live/forward-tracking-*.csv",
    "profit-ticket-pipeline-feedback/forward-tracking-*.csv",
    "profit-ticket-pipeline-regime/forward-tracking-*.csv",
    "profit-ticket-pipeline-regime-v2/forward-tracking-*.csv",
    "profit-ticket-pipeline-regime-v3/forward-tracking-*.csv",
    "profit-ticket-pipeline-opening-guard-smoke/forward-tracking-*.csv",
]
OUTPUT_JSON = RESEARCH_BASE / "lifecycle-scoreboard.json"
OUTPUT_MD = RESEARCH_BASE / "lifecycle-scoreboard.md"
OUTPUT_COMPLETED_JSON = RESEARCH_BASE / "lifecycle-scoreboard-completed.json"
OUTPUT_COMPLETED_MD = RESEARCH_BASE / "lifecycle-scoreboard-completed.md"


def load_runtime_ledger() -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for pattern in RUNTIME_LEDGER_GLOBS:
        for fpath in sorted(RESEARCH_BASE.glob(pattern)):
            for line in fpath.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if not line:
                    continue
                payload = json.loads(line)
                if payload.get("record_type") != "RUNTIME_DECISION":
                    continue
                output_date = str(payload.get("output_date") or "").strip()
                for candidate in payload.get("top_candidates", []):
                    rows.append(
                        {
                            "output_date": output_date,
                            "run_name": payload.get("run_name"),
                            "as_of_date": payload.get("as_of_date"),
                            "final_classification": payload.get("final_classification"),
                            "paper_review_count": payload.get("paper_review_count"),
                            "market_watchlist_count": payload.get("market_watchlist_count"),
                            "best_watch_candidate": payload.get("best_watch_candidate"),
                            "symbol": candidate.get("symbol"),
                            "ticket_rank": candidate.get("ticket_rank"),
                            "classification": candidate.get("classification"),
                            "lifecycle_stage": candidate.get("lifecycle_stage"),
                            "ticket_score": candidate.get("ticket_score"),
                            "market_score": candidate.get("market_score"),
                            "evidence_gate_status": candidate.get("evidence_gate_status"),
                            "risk_allowed": candidate.get("risk_allowed"),
                        }
                    )
    return pd.DataFrame(rows)


def load_forward_tracking() -> pd.DataFrame:
    rows: list[pd.DataFrame] = []
    for pattern in FORWARD_TRACKING_GLOBS:
        for fpath in sorted(RESEARCH_BASE.glob(pattern)):
            try:
                df = pd.read_csv(fpath, on_bad_lines="warn")
            except Exception:
                continue
            if df.empty:
                continue
            output_date = fpath.stem.replace("forward-tracking-", "")
            df["output_date"] = output_date
            df["_source_file"] = fpath.name
            rows.append(df)
    if not rows:
        return pd.DataFrame()
    return pd.concat(rows, ignore_index=True)



def load_pipeline_metrics() -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for pattern in METRICS_GLOBS:
        for fpath in sorted(RESEARCH_BASE.glob(pattern)):
            try:
                payload = json.loads(fpath.read_text(encoding="utf-8"))
            except Exception:
                continue
            output_date = str(payload.get("output_date") or fpath.stem.replace("metrics-", "")).strip()
            run_name = str(payload.get("run_name") or fpath.parent.name).strip()
            run_group = run_name if run_name and run_name != fpath.parent.name else str(fpath.parent.name).strip()
            rows.append(
                {
                    "output_date": output_date,
                    "run_name": run_name,
                    "run_group": run_group,
                    "task": payload.get("task"),
                    "data_mode": payload.get("data_mode"),
                    "source_mode": payload.get("source_mode"),
                    "run_category": payload.get("run_category"),
                    "regime": payload.get("regime"),
                    "regime_source": payload.get("regime_source"),
                    "regime_breadth": payload.get("regime_breadth"),
                    "regime_momentum": payload.get("regime_momentum"),
                    "regime_volatility": payload.get("regime_volatility"),
                    "regime_advance_ratio": payload.get("regime_advance_ratio"),
                    "final_classification": payload.get("final_classification"),
                    "paper_review_count": payload.get("paper_review_count"),
                    "market_watchlist_count": payload.get("market_watchlist_count"),
                    "metrics_file": fpath.name,
                }
            )
    if not rows:
        return pd.DataFrame()
    return pd.DataFrame(rows)


def build_scoreboard(runtime_df: pd.DataFrame, tracking_df: pd.DataFrame, metrics_df: pd.DataFrame, completed_only: bool = False) -> dict[str, Any]:
    if runtime_df.empty:
        return {
            "status": "NO_RUNTIME_LEDGER",
            "generated_at": datetime.now().isoformat(),
            "message": "No runtime decision ledger rows found",
        }

    if tracking_df.empty:
        return {
            "status": "NO_FORWARD_TRACKING",
            "generated_at": datetime.now().isoformat(),
            "message": "No forward tracking rows found",
        }

    tracking = tracking_df.copy()
    tracking["forward_return"] = pd.to_numeric(tracking.get("forward_return"), errors="coerce")
    tracking["ticket_rank"] = pd.to_numeric(tracking.get("ticket_rank"), errors="coerce")
    tracking["risk_allowed"] = tracking.get("risk_allowed")

    merged = runtime_df.merge(
        tracking,
        on=["output_date", "symbol"],
        how="left",
        suffixes=("_runtime", "_tracking"),
    )

    merged_completed = merged[merged["check_status"] == "completed"].copy()
    merged_completed["is_win"] = merged_completed["forward_return"] > 0

    base_df = merged_completed if completed_only else merged

    by_output_date = []
    for output_date, group in base_df.groupby("output_date", dropna=False):
        top_symbols = group[["symbol", "classification_runtime", "lifecycle_stage", "ticket_rank_runtime"]].drop_duplicates()
        top_symbols = top_symbols.rename(columns={
            "classification_runtime": "classification",
        })
        completed = group[group["check_status"] == "completed"].copy()
        if not completed.empty:
            completed["is_win"] = completed["forward_return"] > 0
        by_output_date.append(
            {
                "output_date": output_date,
                "final_classification": _first_non_null(group.get("final_classification")),
                "paper_review_count": _to_int(_first_non_null(group.get("paper_review_count"))),
                "market_watchlist_count": _to_int(_first_non_null(group.get("market_watchlist_count"))),
                "best_watch_candidate": _first_non_null(group.get("best_watch_candidate")),
                "top_symbols": top_symbols.to_dict(orient="records"),
                "completed_rows": int(len(completed)),
                "avg_forward_return": _safe_float(completed["forward_return"].mean()) if not completed.empty else None,
                "win_rate": _safe_float(completed["is_win"].mean()) if not completed.empty else None,
            }
        )

    by_horizon = {}
    if not merged_completed.empty:
        for horizon, group in merged_completed.groupby("review_window"):
            by_horizon[str(horizon)] = {
                "count": int(len(group)),
                "win_rate": _safe_float(group["is_win"].mean()),
                "avg_forward_return": _safe_float(group["forward_return"].mean()),
                "median_forward_return": _safe_float(group["forward_return"].median()),
            }

    by_lifecycle_stage = {}
    if not merged_completed.empty:
        for stage, group in merged_completed.groupby("lifecycle_stage"):
            by_lifecycle_stage[str(stage)] = {
                "count": int(len(group)),
                "win_rate": _safe_float(group["is_win"].mean()),
                "avg_forward_return": _safe_float(group["forward_return"].mean()),
            }

    by_symbol = {}
    if not merged_completed.empty:
        for symbol, group in merged_completed.groupby("symbol"):
            by_symbol[str(symbol)] = {
                "count": int(len(group)),
                "win_rate": _safe_float(group["is_win"].mean()),
                "avg_forward_return": _safe_float(group["forward_return"].mean()),
                "best_output_date": _first_non_null(group.get("output_date")),
            }

    metrics_summary: list[dict[str, Any]] = []
    metrics_groups: list[dict[str, Any]] = []
    if not metrics_df.empty:
        seen_metrics_files: set[tuple[str, str]] = set()
        for _, metrics_row in metrics_df.sort_values("output_date").iterrows():
            metrics_file = str(metrics_row.get("metrics_file") or "").strip()
            dedup_key = (str(metrics_row.get("output_date") or ""), str(metrics_row.get("run_name") or ""))
            if not metrics_file or dedup_key in seen_metrics_files:
                continue
            seen_metrics_files.add(dedup_key)
            output_date_value = metrics_row.get("output_date")
            matched = merged[merged["output_date"] == output_date_value].copy()
            matched_completed = matched[matched["check_status"] == "completed"].copy()
            if not matched_completed.empty:
                matched_completed["is_win"] = matched_completed["forward_return"] > 0
            metrics_summary.append(
                {
                    "output_date": output_date_value,
                    "run_name": metrics_row.get("run_name"),
                    "run_group": metrics_row.get("run_group"),
                    "run_category": metrics_row.get("run_category"),
                    "task": metrics_row.get("task"),
                    "data_mode": metrics_row.get("data_mode"),
                    "source_mode": metrics_row.get("source_mode"),
                    "regime": metrics_row.get("regime"),
                    "regime_source": metrics_row.get("regime_source"),
                    "final_classification_metrics": metrics_row.get("final_classification"),
                    "final_classification": _first_non_null(matched.get("final_classification_runtime") if "final_classification_runtime" in matched.columns else matched.get("final_classification_metrics") if "final_classification_metrics" in matched.columns else matched.get("final_classification")),
                    "paper_review_count": _to_int(_first_non_null(matched.get("paper_review_count_runtime") if "paper_review_count_runtime" in matched.columns else matched.get("paper_review_count"))),
                    "tracking_rows": int(len(matched)),
                    "completed_rows": int(len(matched_completed)),
                    "win_rate": _safe_float(matched_completed["is_win"].mean()) if not matched_completed.empty else None,
                    "avg_forward_return": _safe_float(matched_completed["forward_return"].mean()) if not matched_completed.empty else None,
                    "metrics_file": metrics_file,
                }
            )

        merged_with_metrics = merged.merge(metrics_df, on="output_date", how="left", suffixes=("_base", "_metrics"))
        merged_completed_with_metrics = merged_with_metrics[merged_with_metrics["check_status"] == "completed"].copy()
        if not merged_completed_with_metrics.empty:
            merged_completed_with_metrics["is_win"] = merged_completed_with_metrics["forward_return"] > 0

        if not merged_completed_with_metrics.empty:
            normalized_completed = merged_completed_with_metrics.copy()
            for col in ["run_group", "data_mode", "source_mode", "regime"]:
                if col in normalized_completed.columns:
                    normalized_completed[col] = normalized_completed[col].where(normalized_completed[col].notna(), "unknown")
            group_cols = [col for col in ["run_group", "data_mode", "source_mode", "regime"] if col in normalized_completed.columns]
            for keys, group in normalized_completed.groupby(group_cols, dropna=False):
                if not isinstance(keys, tuple):
                    keys = (keys,)
                group_record = {col: value for col, value in zip(group_cols, keys)}
                group_record.update(
                    {
                        "completed_rows": int(len(group)),
                        "win_rate": _safe_float(group["is_win"].mean()),
                        "avg_forward_return": _safe_float(group["forward_return"].mean()),
                        "median_forward_return": _safe_float(group["forward_return"].median()),
                    }
                )
                metrics_groups.append(group_record)

    regime_source_groups: list[dict[str, Any]] = []
    if not merged_completed_with_metrics.empty:
        normalized_for_source = merged_completed_with_metrics.copy()
        for col in ["regime_source", "run_category", "regime"]:
            if col in normalized_for_source.columns:
                normalized_for_source[col] = normalized_for_source[col].where(normalized_for_source[col].notna(), "unknown")
        source_group_cols = [col for col in ["regime_source", "run_category", "regime"] if col in normalized_for_source.columns]
        for keys, group in normalized_for_source.groupby(source_group_cols, dropna=False):
            if not isinstance(keys, tuple):
                keys = (keys,)
            source_group_record = {col: value for col, value in zip(source_group_cols, keys)}
            source_group_record.update(
                {
                    "completed_rows": int(len(group)),
                    "win_rate": _safe_float(group["is_win"].mean()),
                    "avg_forward_return": _safe_float(group["forward_return"].mean()),
                    "median_forward_return": _safe_float(group["forward_return"].median()),
                }
            )
            regime_source_groups.append(source_group_record)

    summary = {
        "status": "OK",
        "generated_at": datetime.now().isoformat(),
        "completed_only": bool(completed_only),
        "runtime_records": int(len(runtime_df)),
        "tracking_rows": int(len(tracking_df)),
        "completed_rows": int(len(merged_completed)),
        "win_rate": _safe_float(merged_completed["is_win"].mean()) if not merged_completed.empty else None,
        "avg_forward_return": _safe_float(merged_completed["forward_return"].mean()) if not merged_completed.empty else None,
        "by_output_date": by_output_date,
        "by_horizon": by_horizon,
        "by_lifecycle_stage": by_lifecycle_stage,
        "by_symbol": by_symbol,
        "by_metrics_summary": metrics_summary,
        "by_metrics_variant": metrics_groups,
        "by_regime_source": regime_source_groups,
    }
    return summary


def _first_non_null(series: pd.Series | None) -> Any:
    if series is None:
        return None
    for value in series.tolist():
        if pd.notna(value):
            return value
    return None


def _safe_float(value: Any) -> float | None:
    if value is None or pd.isna(value):
        return None
    return round(float(value), 6)


def _to_int(value: Any) -> int | None:
    if value is None or pd.isna(value):
        return None
    return int(value)


def format_markdown(scoreboard: dict[str, Any]) -> str:
    lines = [
        "# Lifecycle Scoreboard",
        f"- Generated: {scoreboard.get('generated_at', 'N/A')}",
        f"- Status: {scoreboard.get('status', 'UNKNOWN')}",
        f"- Completed-only: {scoreboard.get('completed_only', False)}",
        "",
    ]

    if scoreboard.get("status") != "OK":
        lines.append(f"- {scoreboard.get('message', 'No data')}")
        return "\n".join(lines) + "\n"

    lines.extend([
        "## Overall",
        f"- runtime_records: {scoreboard['runtime_records']}",
        f"- tracking_rows: {scoreboard['tracking_rows']}",
        f"- completed_rows: {scoreboard['completed_rows']}",
        f"- win_rate: {scoreboard['win_rate']}",
        f"- avg_forward_return: {scoreboard['avg_forward_return']}",
        "",
        "## By Output Date",
    ])
    for row in scoreboard.get("by_output_date", []):
        lines.extend([
            f"### {row['output_date']}",
            f"- final_classification: {row['final_classification']}",
            f"- paper_review_count: {row['paper_review_count']}",
            f"- market_watchlist_count: {row['market_watchlist_count']}",
            f"- best_watch_candidate: {row['best_watch_candidate']}",
            f"- completed_rows: {row['completed_rows']}",
            f"- avg_forward_return: {row['avg_forward_return']}",
            f"- win_rate: {row['win_rate']}",
        ])

    if scoreboard.get("completed_only"):
        lines.extend([
            "",
            "## Completed-only By Output Date Table",
            "|output_date|final_classification|paper_review_count|market_watchlist_count|best_watch_candidate|completed_rows|win_rate|avg_forward_return|",
            "|---|---|---|---|---|---|---|---|",
        ])
        for row in scoreboard.get("by_output_date", []):
            lines.append(
                f"|{row['output_date']}|{row['final_classification']}|{row['paper_review_count']}|{row['market_watchlist_count']}|{row['best_watch_candidate']}|{row['completed_rows']}|{row['win_rate']}|{row['avg_forward_return']}|"
            )

    lines.extend([
        "",
        "## By Horizon",
        "|horizon|count|win_rate|avg_forward_return|median_forward_return|",
        "|---|---|---|---|---|",
    ])
    for horizon, row in sorted(scoreboard.get("by_horizon", {}).items()):
        lines.append(f"|{horizon}|{row['count']}|{row['win_rate']}|{row['avg_forward_return']}|{row['median_forward_return']}|")

    lines.extend([
        "",
        "## By Lifecycle Stage",
        "|stage|count|win_rate|avg_forward_return|",
        "|---|---|---|---|",
    ])
    for stage, row in sorted(scoreboard.get("by_lifecycle_stage", {}).items()):
        lines.append(f"|{stage}|{row['count']}|{row['win_rate']}|{row['avg_forward_return']}|")

    lines.extend([
        "",
        "## By Symbol",
        "|symbol|count|win_rate|avg_forward_return|best_output_date|",
        "|---|---|---|---|---|",
    ])
    for symbol, row in sorted(scoreboard.get("by_symbol", {}).items()):
        lines.append(f"|{symbol}|{row['count']}|{row['win_rate']}|{row['avg_forward_return']}|{row['best_output_date']}|")

    metrics_summary = scoreboard.get("by_metrics_summary") or []
    metrics_variant = scoreboard.get("by_metrics_variant") or []
    if metrics_summary:
        lines.extend([
            "",
            "## By Metrics Summary",
            "|output_date|run_group|run_category|data_mode|regime|regime_source|final_classification|completed_rows|win_rate|avg_forward_return|metrics_file|",
            "|---|---|---|---|---|---|---|---|---|---|---|",
        ])
        for row in metrics_summary:
            lines.append(
                f"|{row.get('output_date')}|{row.get('run_group')}|{row.get('run_category')}|{row.get('data_mode')}|{row.get('regime')}|{row.get('regime_source')}|{row.get('final_classification')}|{row.get('completed_rows')}|{row.get('win_rate')}|{row.get('avg_forward_return')}|{row.get('metrics_file')}|"
            )

    if metrics_variant:
        lines.extend([
            "",
            "## By Metrics Variant",
        ])
        for row in metrics_variant:
            lines.extend([
                f"### {row.get('run_group') or 'unknown'} / {row.get('data_mode') or 'unknown'} / regime={row.get('regime') or 'unknown'}",
                f"- completed_rows: {row.get('completed_rows')}",
                f"- win_rate: {row.get('win_rate')}",
                f"- avg_forward_return: {row.get('avg_forward_return')}",
                f"- median_forward_return: {row.get('median_forward_return')}",
            ])

    regime_source_view = scoreboard.get("by_regime_source") or []
    if regime_source_view:
        lines.extend([
            "",
            "## By Regime Source",
        ])
        for row in regime_source_view:
            lines.extend([
                f"### regime_source={row.get('regime_source') or 'unknown'} / run_category={row.get('run_category') or 'unknown'} / regime={row.get('regime') or 'unknown'}",
                f"- completed_rows: {row.get('completed_rows')}",
                f"- win_rate: {row.get('win_rate')}",
                f"- avg_forward_return: {row.get('avg_forward_return')}",
                f"- median_forward_return: {row.get('median_forward_return')}",
            ])

    return "\n".join(lines) + "\n"


def main() -> None:
    import sys
    use_db = "--db" in sys.argv

    if use_db:
        scoreboard = build_scoreboard_from_db(completed_only=False)
        completed_scoreboard = build_scoreboard_from_db(completed_only=True)
    else:
        runtime_df = load_runtime_ledger()
        tracking_df = load_forward_tracking()
        metrics_df = load_pipeline_metrics()
        scoreboard = build_scoreboard(runtime_df, tracking_df, metrics_df, completed_only=False)
        completed_scoreboard = build_scoreboard(runtime_df, tracking_df, metrics_df, completed_only=True)

    OUTPUT_JSON.write_text(json.dumps(scoreboard, indent=2, ensure_ascii=False), encoding="utf-8")
    OUTPUT_MD.write_text(format_markdown(scoreboard), encoding="utf-8")
    OUTPUT_COMPLETED_JSON.write_text(json.dumps(completed_scoreboard, indent=2, ensure_ascii=False), encoding="utf-8")
    OUTPUT_COMPLETED_MD.write_text(format_markdown(completed_scoreboard), encoding="utf-8")
    print(json.dumps(scoreboard, indent=2, ensure_ascii=False))
    print(f"\nMarkdown: {OUTPUT_MD}")
    print(f"JSON: {OUTPUT_JSON}")
    print(f"Completed Markdown: {OUTPUT_COMPLETED_MD}")
    print(f"Completed JSON: {OUTPUT_COMPLETED_JSON}")


def build_scoreboard_from_db(completed_only: bool = False) -> dict[str, Any]:
    """Build scoreboard from PostgreSQL database."""
    from scripts.db.engine import SessionLocal
    from sqlalchemy import text

    db = SessionLocal()
    try:
        # Overall stats
        where = "WHERE check_status = 'completed'" if completed_only else ""
        overall = db.execute(text(f"""
            SELECT COUNT(*) as total,
                   COUNT(CASE WHEN forward_return > 0 THEN 1 END) as wins,
                   AVG(forward_return) as avg_return,
                   PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY forward_return) as median_return
            FROM forward_tracking {where}
        """)).fetchone()

        overall_dict = {
            "runtime_records": 0,
            "tracking_rows": overall[0] if overall else 0,
            "completed_rows": overall[0] if overall else 0,
            "win_rate": round((overall[1] / overall[0] * 100), 2) if overall and overall[0] else 0,
            "avg_forward_return": round(float(overall[2]) * 100, 6) if overall and overall[2] else 0,
            "median_forward_return": round(float(overall[3]) * 100, 6) if overall and overall[3] else 0,
        }

        # By horizon
        horizon_rows = db.execute(text(f"""
            SELECT horizon_days, COUNT(*) as total,
                   COUNT(CASE WHEN forward_return > 0 THEN 1 END) as wins,
                   AVG(forward_return) as avg_return,
                   PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY forward_return) as median_return
            FROM forward_tracking {where}
            GROUP BY horizon_days ORDER BY horizon_days
        """)).fetchall()

        by_horizon = []
        for row in horizon_rows:
            by_horizon.append({
                "horizon": f"{row[0]}d",
                "count": row[1],
                "win_rate": round((row[2] / row[1] * 100), 2) if row[1] else 0,
                "avg_forward_return": round(float(row[3]) * 100, 6) if row[3] else 0,
                "median_forward_return": round(float(row[4]) * 100, 6) if row[4] else 0,
            })

        # By symbol
        symbol_rows = db.execute(text(f"""
            SELECT symbol, COUNT(*) as total,
                   COUNT(CASE WHEN forward_return > 0 THEN 1 END) as wins,
                   AVG(forward_return) as avg_return
            FROM forward_tracking {where}
            GROUP BY symbol ORDER BY total DESC
        """)).fetchall()

        by_symbol = []
        for row in symbol_rows:
            by_symbol.append({
                "symbol": row[0],
                "count": row[1],
                "win_rate": round((row[2] / row[1] * 100), 2) if row[1] else 0,
                "avg_forward_return": round(float(row[3]) * 100, 6) if row[3] else 0,
            })

        # By lifecycle stage
        stage_rows = db.execute(text("""
            SELECT t.lifecycle_stage, COUNT(*) as total,
                   COUNT(CASE WHEN ft.forward_return > 0 THEN 1 END) as wins,
                   AVG(ft.forward_return) as avg_return
            FROM forward_tracking ft
            JOIN tickets t ON ft.ticket_id = t.id
            WHERE ft.check_status = 'completed'
            GROUP BY t.lifecycle_stage
        """)).fetchall()

        by_stage = []
        for row in stage_rows:
            by_stage.append({
                "stage": row[0],
                "count": row[1],
                "win_rate": round((row[2] / row[1] * 100), 2) if row[1] else 0,
                "avg_forward_return": round(float(row[3]) * 100, 6) if row[3] else 0,
            })

        return {
            "overall": overall_dict,
            "by_horizon": by_horizon,
            "by_symbol": by_symbol,
            "by_stage": by_stage,
        }
    finally:
        db.close()


if __name__ == "__main__":
    main()
