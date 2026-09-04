"""Immutable production-research run identity and artifact manifest."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping
from uuid import uuid4

from .boundary import PRODUCTION_BOUNDARY, freeze_snapshot
from .evidence import content_hash, utc_now
from .production_gate import _calendar_version, _git_commit

MANIFEST_DIR = Path(__file__).resolve().parents[2] / "research" / "run-manifests"
WEIGHTS_FILE = Path(__file__).resolve().parents[2] / "data" / "scoring_weights.json"


def load_weight_version(path: Path | None = None) -> str:
    target = path or WEIGHTS_FILE
    if not target.exists():
        return "missing"
    return content_hash(json.loads(target.read_text(encoding="utf-8")))


def build_run_identity(
    *,
    session_date: str,
    snapshot_hash: str | None = None,
    weight_version: str | None = None,
    provider_versions: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    freeze = freeze_snapshot()
    identity = {
        "run_id": str(uuid4()),
        "snapshot_id": snapshot_hash or str(uuid4()),
        "snapshot_hash": snapshot_hash,
        "session_date": session_date,
        "canonical_us_session_date": session_date,
        "strategy": freeze["strategy"],
        "strategy_status": freeze["strategy_status"],
        "weight_version": weight_version or load_weight_version(),
        "calendar_version": _calendar_version(),
        "provider_version": dict(provider_versions or {}),
        "provider_versions": dict(provider_versions or {}),
        "git_commit": _git_commit(),
        "code_commit": _git_commit(),
        "created_at": utc_now(),
        "production_boundary": PRODUCTION_BOUNDARY,
    }
    return identity


def write_run_manifest(
    identity: Mapping[str, Any],
    *,
    research_status: str,
    production_gate: str,
    extra: Mapping[str, Any] | None = None,
    directory: Path | None = None,
) -> Path:
    payload = {
        **dict(identity),
        "research_status": research_status,
        "production_gate": production_gate,
        **dict(extra or {}),
    }
    folder = directory or MANIFEST_DIR
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / f"run_manifest-{payload.get('session_date')}-{payload.get('run_id')}.json"
    path.write_text(json.dumps(payload, indent=2, default=str) + "\n", encoding="utf-8")
    return path


def assert_weight_version_immutable(start: str, finish: str) -> None:
    if start != finish:
        raise AssertionError(f"weight_version changed during run: {start} -> {finish}")


def assert_strategy_immutable(start: str, finish: str) -> None:
    if start != finish:
        raise AssertionError(f"strategy version changed during run: {start} -> {finish}")
