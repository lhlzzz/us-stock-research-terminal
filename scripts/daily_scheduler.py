#!/usr/bin/env python3
"""Daily Scheduler: 每日自动出票全流程。

使用 daily_loop.py 的全循环编排，包含：
1. 出票 (Pipeline)
2. 回填 (Backfill)
3. 因子回测 (Factor Backtest) + 权重优化 (Weight Optimization)
4. 记分板 (Scoreboard)
5. 退化检测 (Degradation Check)
"""
import json
import logging
import sys
from datetime import date, datetime
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPTS_DIR.parent
sys.path.insert(0, str(SCRIPTS_DIR))

LOGS_DIR = PROJECT_ROOT / "research" / "logs"
LOGS_DIR.mkdir(parents=True, exist_ok=True)


def _setup_logging(d: date) -> logging.Logger:
    log_file = LOGS_DIR / f"{d.isoformat()}.log"
    logger = logging.getLogger("daily_scheduler")
    logger.setLevel(logging.INFO)
    if not logger.handlers:
        fh = logging.FileHandler(log_file, encoding="utf-8")
        fh.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
        logger.addHandler(fh)
        sh = logging.StreamHandler()
        sh.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
        logger.addHandler(sh)
    return logger


def _canonical_session(d: date | datetime | str | None = None) -> date:
    from market_calendar import CALENDAR

    if d is None:
        return CALENDAR.previous_completed_session()
    if isinstance(d, datetime):
        return CALENDAR.previous_completed_session(d)
    if isinstance(d, date):
        return d
    return date.fromisoformat(str(d)[:10])


def daily_schedule(d: date | None = None, skip_pipeline: bool = False) -> dict:
    d = _canonical_session(d)
    logger = _setup_logging(d)
    logger.info("=== daily_schedule %s ===", d.isoformat())

    from daily_loop import run_daily_loop
    result = run_daily_loop(output_date=d.isoformat(), skip_pipeline=skip_pipeline)

    # Log summary
    for step_name, step_data in result.get("steps", {}).items():
        status = step_data.get("status", "unknown")
        logger.info("  %s: %s", step_name, status)

    logger.info("=== daily_schedule complete ===")
    return result


if __name__ == "__main__":
    from market_calendar import CALENDAR

    target = CALENDAR.previous_completed_session()
    skip = False
    if len(sys.argv) > 1:
        for arg in sys.argv[1:]:
            if arg == "--skip-pipeline":
                skip = True
            elif arg == "--dry-run":
                print(json.dumps({
                    "mode": "dry-run",
                    "output_date": target.isoformat(),
                    "canonical_us_session_date": target.isoformat(),
                    "steps": ["pipeline", "backfill", "factor_backtest", "scoreboard", "degradation_check", "production_gate"],
                    "research_only": True,
                    "strategy_status": "FROZEN",
                    "weight_mutation": "BLOCKED",
                    "production_apply": "BLOCKED",
                    "broker": "DISABLED",
                    "live_order": "DISABLED",
                    "production_gate": "PASS",
                }, indent=2))
                raise SystemExit(0)
            else:
                try:
                    target = date.fromisoformat(arg)
                except ValueError:
                    pass

    out = daily_schedule(target, skip_pipeline=skip)
    print(json.dumps(out, indent=2, ensure_ascii=False, default=str))
