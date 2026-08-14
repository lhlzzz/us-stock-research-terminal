"""
xiaomei timezone-aware scheduler.
Aligned with xiaogu's xiaogu_scheduler.py architecture.

Timeline (Beijing time):
  A股:  09:30 开盘 ──────────── 15:00 收盘
  美股:                          21:30 开盘 ──────────── 04:00(+1) 收盘
        |---白天---|---空窗---|---夜间美股交易---|--凌晨--|
        06:00    09:30    15:00    21:30    04:00    06:00

Jobs:
  05:00  Daily pipeline (after US market close)
  09:00  Pre-market health check
  15:00  A-share close monitoring
  20:00  Signal effectiveness analysis
"""

from __future__ import annotations

import logging
import os
import subprocess
import sys
from datetime import datetime, time
from pathlib import Path

logger = logging.getLogger(__name__)

# Configuration
PROJECT_DIR = Path(__file__).resolve().parent.parent
PIPELINE_SCRIPT = PROJECT_DIR / "scripts" / "daily_pipeline.sh"
LOG_DIR = PROJECT_DIR / "logs"

# Beijing time timezone
try:
    from zoneinfo import ZoneInfo
    BEIJING_TZ = ZoneInfo("Asia/Shanghai")
except ImportError:
    # Python < 3.9 fallback
    import pytz
    BEIJING_TZ = pytz.timezone("Asia/Shanghai")


from datetime import date as date_cls

# ── US market holidays (fixed + floating, 2025-2027) ──────────────
# New Year, MLK Day, Presidents Day, Good Friday, Memorial Day,
# Juneteenth, Independence Day, Labor Day, Thanksgiving, Christmas
US_HOLIDAYS: set[date_cls] = {
    # 2025
    date_cls(2025, 1, 1), date_cls(2025, 1, 20), date_cls(2025, 2, 17),
    date_cls(2025, 4, 18), date_cls(2025, 5, 26), date_cls(2025, 6, 19),
    date_cls(2025, 7, 4), date_cls(2025, 9, 1), date_cls(2025, 11, 27),
    date_cls(2025, 12, 25),
    # 2026
    date_cls(2026, 1, 1), date_cls(2026, 1, 19), date_cls(2026, 2, 16),
    date_cls(2026, 4, 3), date_cls(2026, 5, 25), date_cls(2026, 6, 19),
    date_cls(2026, 7, 3), date_cls(2026, 9, 7), date_cls(2026, 11, 26),
    date_cls(2026, 12, 25),
    # 2027
    date_cls(2027, 1, 1), date_cls(2027, 1, 18), date_cls(2027, 2, 15),
    date_cls(2027, 3, 26), date_cls(2027, 5, 31), date_cls(2027, 6, 18),
    date_cls(2027, 7, 5), date_cls(2027, 9, 6), date_cls(2027, 11, 25),
    date_cls(2027, 12, 24),
}

# ── A-share / China market holidays (2025-2027) ──────────────────
# Spring Festival, Qingming, Labor Day, Dragon Boat, Mid-Autumn, National Day
CN_HOLIDAYS: set[date_cls] = {
    # 2025
    date_cls(2025, 1, 1), date_cls(2025, 1, 28), date_cls(2025, 1, 29),
    date_cls(2025, 1, 30), date_cls(2025, 1, 31), date_cls(2025, 2, 1),
    date_cls(2025, 2, 2), date_cls(2025, 2, 3), date_cls(2025, 2, 4),
    date_cls(2025, 4, 4), date_cls(2025, 5, 1), date_cls(2025, 5, 2),
    date_cls(2025, 5, 3), date_cls(2025, 5, 4), date_cls(2025, 5, 5),
    date_cls(2025, 5, 31), date_cls(2025, 6, 1), date_cls(2025, 6, 2),
    date_cls(2025, 10, 1), date_cls(2025, 10, 2), date_cls(2025, 10, 3),
    date_cls(2025, 10, 4), date_cls(2025, 10, 5), date_cls(2025, 10, 6),
    date_cls(2025, 10, 7),
    # 2026
    date_cls(2026, 1, 1), date_cls(2026, 1, 2), date_cls(2026, 1, 3),
    date_cls(2026, 2, 16), date_cls(2026, 2, 17), date_cls(2026, 2, 18),
    date_cls(2026, 2, 19), date_cls(2026, 2, 20), date_cls(2026, 2, 21),
    date_cls(2026, 2, 22),
    date_cls(2026, 4, 5), date_cls(2026, 4, 6), date_cls(2026, 4, 7),
    date_cls(2026, 5, 1), date_cls(2026, 5, 2), date_cls(2026, 5, 3),
    date_cls(2026, 5, 4), date_cls(2026, 5, 5),
    date_cls(2026, 6, 19), date_cls(2026, 6, 20), date_cls(2026, 6, 21),
    date_cls(2026, 9, 25),
    date_cls(2026, 10, 1), date_cls(2026, 10, 2), date_cls(2026, 10, 3),
    date_cls(2026, 10, 4), date_cls(2026, 10, 5), date_cls(2026, 10, 6),
    date_cls(2026, 10, 7),
    # 2027 (preliminary)
    date_cls(2027, 1, 1), date_cls(2027, 1, 2), date_cls(2027, 1, 3),
    date_cls(2027, 2, 6), date_cls(2027, 2, 7), date_cls(2027, 2, 8),
    date_cls(2027, 2, 9), date_cls(2027, 2, 10), date_cls(2027, 2, 11),
    date_cls(2027, 2, 12),
    date_cls(2027, 4, 5), date_cls(2027, 4, 6), date_cls(2027, 4, 7),
    date_cls(2027, 5, 1), date_cls(2027, 5, 2), date_cls(2027, 5, 3),
    date_cls(2027, 6, 12), date_cls(2027, 6, 13), date_cls(2027, 6, 14),
    date_cls(2027, 9, 15),
    date_cls(2027, 10, 1), date_cls(2027, 10, 2), date_cls(2027, 10, 3),
    date_cls(2027, 10, 4), date_cls(2027, 10, 5), date_cls(2027, 10, 6),
    date_cls(2027, 10, 7),
}


def is_trading_day() -> bool:
    """Check if today is a US trading day (Mon-Fri, excluding holidays)."""
    now = datetime.now(BEIJING_TZ)
    today = now.date()
    if now.weekday() >= 5:
        return False
    if today in US_HOLIDAYS:
        return False
    return True


def is_a_share_trading_day() -> bool:
    """Check if today is an A-share trading day."""
    now = datetime.now(BEIJING_TZ)
    today = now.date()
    if now.weekday() >= 5:
        return False
    if today in CN_HOLIDAYS:
        return False
    return True


def run_pipeline(mode: str = "full") -> dict:
    """Run the daily pipeline with specified mode."""
    log_file = LOG_DIR / f"scheduler-{datetime.now(BEIJING_TZ).strftime('%Y-%m-%d')}.log"
    LOG_DIR.mkdir(parents=True, exist_ok=True)

    logger.info(f"Running pipeline mode={mode}")

    try:
        result = subprocess.run(
            ["bash", str(PIPELINE_SCRIPT), f"--{mode}"],
            cwd=str(PROJECT_DIR),
            capture_output=True,
            text=True,
            timeout=3600,  # 1 hour timeout
        )

        # Log output
        with open(log_file, "a") as f:
            f.write(f"\n=== Pipeline run at {datetime.now(BEIJING_TZ).isoformat()} ===\n")
            f.write(result.stdout)
            if result.stderr:
                f.write(f"\nSTDERR:\n{result.stderr}")

        success = result.returncode == 0
        logger.info(f"Pipeline {'succeeded' if success else 'failed'}: returncode={result.returncode}")

        return {
            "success": success,
            "returncode": result.returncode,
            "stdout": result.stdout[-1000:] if result.stdout else "",
            "stderr": result.stderr[-500:] if result.stderr else "",
        }

    except subprocess.TimeoutExpired:
        logger.error("Pipeline timed out after 1 hour")
        return {"success": False, "error": "timeout"}
    except Exception as e:
        logger.error(f"Pipeline error: {e}")
        return {"success": False, "error": str(e)}


def morning_health_check():
    """Pre-market health check (09:00 Beijing time)."""
    logger.info("Running morning health check...")

    checks = {
        "postgres": False,
        "redis": False,
        "pipeline_script": False,
        "disk_space": False,
    }

    # Check PostgreSQL
    try:
        result = subprocess.run(
            ["pg_isready", "-h", "localhost", "-p", "5432"],
            capture_output=True, timeout=10
        )
        checks["postgres"] = result.returncode == 0
    except Exception:
        pass

    # Check Redis
    try:
        result = subprocess.run(
            ["redis-cli", "ping"],
            capture_output=True, timeout=10
        )
        checks["redis"] = result.returncode == 0
    except Exception:
        pass

    # Check pipeline script
    checks["pipeline_script"] = PIPELINE_SCRIPT.exists()

    # Check disk space
    try:
        stat = os.statvfs(str(PROJECT_DIR))
        free_gb = (stat.f_bavail * stat.f_frsize) / (1024**3)
        checks["disk_space"] = free_gb > 5  # At least 5GB free
    except Exception:
        pass

    all_ok = all(checks.values())
    logger.info(f"Health check: {'OK' if all_ok else 'FAILED'} - {checks}")

    return {"healthy": all_ok, "checks": checks}


def daily_pipeline_job():
    """Daily pipeline job (05:00 Beijing time, after US market close)."""
    now = datetime.now(BEIJING_TZ)

    if not is_trading_day():
        logger.info("Not a trading day, skipping pipeline")
        return

    # Check if it's safe to run (after US market close)
    if now.hour < 5:
        logger.warning(f"Too early to run pipeline: {now.hour}:00 Beijing time")
        return

    logger.info("Starting daily pipeline job")
    result = run_pipeline("full")

    if result.get("success"):
        logger.info("Daily pipeline completed successfully")
    else:
        logger.error(f"Daily pipeline failed: {result}")


def signal_effectiveness_job():
    """Signal effectiveness analysis job (20:00 Beijing time)."""
    logger.info("Running signal effectiveness analysis")

    try:
        subprocess.run(
            [sys.executable, str(PROJECT_DIR / "scripts" / "signal_effectiveness.py")],
            cwd=str(PROJECT_DIR),
            capture_output=True,
            timeout=600
        )
        logger.info("Signal effectiveness analysis complete")
    except Exception as e:
        logger.error(f"Signal effectiveness error: {e}")


def knowledge_export_job():
    """Knowledge export job (runs after daily pipeline)."""
    logger.info("Running knowledge export")

    try:
        subprocess.run(
            [sys.executable, str(PROJECT_DIR / "scripts" / "knowledge_asset_export.py")],
            cwd=str(PROJECT_DIR),
            capture_output=True,
            timeout=300
        )
        logger.info("Knowledge export complete")
    except Exception as e:
        logger.error(f"Knowledge export error: {e}")


def run_scheduler():
    """Run the APScheduler-based scheduler."""
    try:
        from apscheduler.schedulers.blocking import BlockingScheduler
        from apscheduler.triggers.cron import CronTrigger
    except ImportError:
        logger.error("APScheduler not installed. Install with: pip install apscheduler")
        sys.exit(1)

    scheduler = BlockingScheduler(timezone="Asia/Shanghai")

    # Daily pipeline at 05:00 (after US market close)
    scheduler.add_job(
        daily_pipeline_job,
        CronTrigger(hour=5, minute=0, day_of_week="mon-fri"),
        id="daily_pipeline",
        name="Daily Pipeline",
        misfire_grace_time=3600,
    )

    # Morning health check at 09:00
    scheduler.add_job(
        morning_health_check,
        CronTrigger(hour=9, minute=0, day_of_week="mon-fri"),
        id="morning_health",
        name="Morning Health Check",
        misfire_grace_time=300,
    )

    # Signal effectiveness at 20:00
    scheduler.add_job(
        signal_effectiveness_job,
        CronTrigger(hour=20, minute=0, day_of_week="mon-fri"),
        id="signal_effectiveness",
        name="Signal Effectiveness",
        misfire_grace_time=600,
    )

    logger.info("Scheduler started with jobs:")
    for job in scheduler.get_jobs():
        logger.info(f"  - {job.name}: {job.trigger}")

    try:
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        logger.info("Scheduler stopped")


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s"
    )

    import argparse

    parser = argparse.ArgumentParser(description="xiaomei scheduler")
    parser.add_argument("--run", choices=["full", "backfill", "tickets", "knowledge"],
                       help="Run pipeline once with specified mode")
    parser.add_argument("--health", action="store_true", help="Run health check")
    parser.add_argument("--daemon", action="store_true", help="Run as daemon scheduler")
    args = parser.parse_args()

    if args.run:
        result = run_pipeline(args.run)
        print(result)
    elif args.health:
        result = morning_health_check()
        print(result)
    elif args.daemon:
        run_scheduler()
    else:
        parser.print_help()
