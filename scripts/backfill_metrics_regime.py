#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

import pandas as pd

RESEARCH_BASE = Path(__file__).resolve().parent.parent / "research"
METRICS_GLOBS = [
    "*/metrics-*.json",
]
SCOREBOARD_SCRIPT = Path(__file__).resolve().parent / "lifecycle_scoreboard.py"


def load_pipeline_metrics() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for pattern in METRICS_GLOBS:
        for fpath in sorted(RESEARCH_BASE.glob(pattern)):
            try:
                payload = json.loads(fpath.read_text(encoding="utf-8"))
            except Exception:
                continue
            run_name = str(payload.get("run_name") or fpath.parent.name).strip()
            run_group = str(payload.get("run_group") or fpath.parent.name).strip()
            output_date = str(payload.get("output_date") or fpath.stem.replace("metrics-", "")).strip()
            data_mode = payload.get("data_mode")
            source_mode = payload.get("source_mode")
            if not output_date:
                output_date = fpath.stem.replace("metrics-", "")
            if not run_name:
                run_name = fpath.parent.name
            if not run_group:
                run_group = fpath.parent.name
            if not data_mode and str(payload.get("data_source") or "").lower().find("yfinance") != -1:
                data_mode = "historical_kline"
            if not source_mode:
                source_mode = "unknown"
            if run_group == "universe-expansion-replay" and source_mode == "unknown":
                source_mode = "live"
            rows.append(
                {
                    "path": fpath,
                    "output_date": output_date.strip(),
                    "run_name": run_name.strip(),
                    "run_group": run_group.strip(),
                    "generated_at": str(payload.get("generated_at") or "").strip(),
                    "data_mode": data_mode,
                    "source_mode": source_mode,
                    "run_category": payload.get("run_category"),
                    "regime": payload.get("regime"),
                    "regime_source": payload.get("regime_source"),
                }
            )
    return rows


def infer_run_category(metrics_row: dict[str, Any]) -> str:
    run_group = str(metrics_row.get("run_group") or metrics_row.get("run_name") or "").strip().lower()
    if run_group.startswith("profit-ticket-pipeline"):
        return "pipeline"
    if run_group == "historical-replay-baseline":
        return "replay_baseline"
    if run_group == "universe-expansion-replay":
        return "replay_expansion"
    if "guard-smoke" in run_group:
        return "guard_smoke"
    return "other"


def infer_regime(metrics_row: dict[str, Any]) -> str | None:
    run_group = str(metrics_row.get("run_group") or metrics_row.get("run_name") or "").strip().lower()
    data_mode = (str(metrics_row["data_mode"]) if metrics_row.get("data_mode") is not None else "").strip().lower()
    source_mode = (str(metrics_row["source_mode"]) if metrics_row.get("source_mode") is not None else "").strip().lower()

    if run_group == "historical-replay-baseline":
        return "active"
    if "guard-smoke" in run_group:
        return "unsupported"
    if source_mode == "cached_local":
        return "unsupported"
    if data_mode == "historical_kline" and source_mode == "live":
        return "active"
    if run_group.startswith("profit-ticket-pipeline"):
        return "active"
    return "unknown"


def rerun_scoreboard() -> None:
    try:
        subprocess.run(
            [sys.executable, str(SCOREBOARD_SCRIPT)],
            check=False,
            capture_output=True,
            text=True,
        )
    except Exception:
        pass


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Backfill pipeline metrics with stable regime fields and recompute scoreboard.")
    parser.add_argument("--lookback", default="all", help="Number of recent metrics files to consider, or 'all' to target all missing files.")
    parser.add_argument("--apply", action="store_true", help="Write regime fields in place; default is dry-run.")
    return parser.parse_args()



def main() -> None:
    args = parse_args()
    metrics_rows = load_pipeline_metrics()
    if not metrics_rows:
        print(json.dumps({"status": "NO_METRICS", "message": "No metrics files found"}, ensure_ascii=False))
        return

    for row in metrics_rows:
        row["sort_key"] = row["generated_at"] or row["output_date"]

    sorted_rows = sorted(metrics_rows, key=lambda row: row["sort_key"])
    lookback_raw = str(args.lookback).strip().lower()
    if lookback_raw == "all":
        target_rows = [row for row in sorted_rows if row.get("regime") in {"", "unknown", None} or not row.get("run_category") or not row.get("regime_source")]
    else:
        try:
            lookback_count = int(lookback_raw)
        except ValueError:
            lookback_count = 10
        target_rows = [row for row in sorted_rows[-max(1, lookback_count):] if row.get("regime") in {"", "unknown", None} or not row.get("run_category") or not row.get("regime_source")]


    manifest: list[dict[str, Any]] = []
    updated_count = 0
    for row in target_rows:
        new_regime = infer_regime(row)
        new_run_category = infer_run_category(row)
        new_regime_source = "market_snapshot" if row.get("run_group", "").startswith("profit-ticket-pipeline") else "rule_based_rebuild"

        if not new_regime:
            manifest.append(
                {
                    "file": str(row["path"]),
                    "output_date": row["output_date"],
                    "old_regime": row.get("regime"),
                    "new_regime": None,
                    "status": "SKIPPED_NO_INFERRED_REGIME",
                }
            )
            continue

        payload = json.loads(row["path"].read_text(encoding="utf-8"))
        old_regime = payload.get("regime")
        old_norm = str(old_regime or "").strip().lower()
        new_norm = str(new_regime).strip().lower()
        changed = old_norm != new_norm or old_norm in {"", "unknown"} or payload.get("run_category") != new_run_category or payload.get("regime_source") != new_regime_source

        if args.apply and changed:
            payload["run_category"] = new_run_category
            payload["regime"] = new_regime
            payload["regime_source"] = new_regime_source
            row["path"].write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
            updated_count += 1

        manifest.append(
            {
                "file": str(row["path"]),
                "output_date": row["output_date"],
                "old_regime": old_regime,
                "new_regime": new_regime,
                "changed": bool(changed),
                "status": "APPLIED" if (args.apply and changed) else ("DRY_RUN" if not args.apply else "NO_CHANGE"),
            }
        )

    summary = {
        "status": "OK",
        "apply_mode": bool(args.apply),
        "lookback": lookback_raw,
        "considered_files": int(len(target_rows)),
        "updated_files": int(updated_count),
        "manifest": manifest,
    }
    print(json.dumps(summary, indent=2, ensure_ascii=False))

    if args.apply:
        rerun_scoreboard()


if __name__ == "__main__":
    main()
