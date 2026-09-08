"""Canonical Obsidian paths for the xiaomei US-stock knowledge loop."""
from __future__ import annotations

import os
from pathlib import Path

PROJECT_VAULT = Path(os.environ.get(
    "XIAOMEI_OBSIDIAN_PROJECT", "/mnt/d/obisidian/Obsidian/Project"
))
SHENLIN_VAULT = Path(os.environ.get(
    "XIAOMEI_OBSIDIAN_SHENLIN", "/mnt/d/obisidian/Obsidian/神临"
))
US_ROOT = PROJECT_VAULT / "美股"
DAILY_FOLDER = Path(os.environ.get(
    "XIAOMEI_OBSIDIAN_DAILY_FOLDER", "美股/xiaomei_memory/daily"
))
DAILY_DIR = PROJECT_VAULT / DAILY_FOLDER
INBOX_DIR = US_ROOT / "inbox"
STATUS_PATH = US_ROOT / "状态.md"
TRADE_DIR = PROJECT_VAULT / "xiaomei-trades"


def require_production_vaults() -> dict:
    """Fail closed when the US-stock vault mount is missing."""
    missing = []
    for label, path in (
        ("project_vault", PROJECT_VAULT),
        ("us_root", US_ROOT),
        ("daily_dir", DAILY_DIR),
        ("inbox_dir", INBOX_DIR),
        ("status", STATUS_PATH),
        ("shenlin_vault", SHENLIN_VAULT),
    ):
        if not path.exists():
            missing.append(f"{label}={path}")
    if missing:
        raise RuntimeError("OBSIDIAN_VAULT_UNAVAILABLE: " + "; ".join(missing))
    return {
        "project_vault": str(PROJECT_VAULT),
        "us_root": str(US_ROOT),
        "daily_dir": str(DAILY_DIR),
        "inbox_dir": str(INBOX_DIR),
        "status": str(STATUS_PATH),
        "shenlin_vault": str(SHENLIN_VAULT),
        "daily_folder": str(DAILY_FOLDER),
    }
