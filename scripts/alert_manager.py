#!/usr/bin/env python3
import logging
import sys
from datetime import date, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LOGS_DIR = ROOT / "research" / "logs"
LOGS_DIR.mkdir(parents=True, exist_ok=True)

ALERT_LOG = LOGS_DIR / "alerts.log"


def _setup_logger() -> logging.Logger:
    logger = logging.getLogger("alert_manager")
    logger.setLevel(logging.INFO)
    if not logger.handlers:
        fh = logging.FileHandler(ALERT_LOG, encoding="utf-8")
        fh.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
        logger.addHandler(fh)
        sh = logging.StreamHandler()
        sh.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
        logger.addHandler(sh)
    return logger


def send_alert(message: str, level: str = "WARNING") -> None:
    logger = _setup_logger()
    lvl = getattr(logging, level.upper(), logging.WARNING)
    logger.log(lvl, "[%s] %s", level.upper(), message)


def is_us_trading_day(d: date | None = None) -> bool:
    d = d or date.today()
    return d.weekday() < 5


def check_pipeline_health(d: date | None = None) -> list[dict]:
    d = d or date.today()
    issues = []

    log_file = LOGS_DIR / f"{d.isoformat()}.log"
    if not log_file.exists():
        issues.append({"check": "pipeline_log", "ok": False, "msg": f"No pipeline log for {d.isoformat()}"})
    else:
        content = log_file.read_text(errors="replace")
        if "FAIL pipeline" in content:
            issues.append({"check": "pipeline_log", "ok": False, "msg": "Pipeline logged failure"})
        elif "DONE pipeline" in content:
            issues.append({"check": "pipeline_log", "ok": True, "msg": "Pipeline completed"})
        else:
            issues.append({"check": "pipeline_log", "ok": False, "msg": "Pipeline status unknown in log"})

    ticket_dir = ROOT / "research" / "profit-ticket-pipeline"
    today_csvs = list(ticket_dir.glob(f"*{d.isoformat()}*")) if ticket_dir.exists() else []
    if today_csvs:
        issues.append({"check": "tickets_generated", "ok": True, "msg": f"{len(today_csvs)} ticket files found"})
    else:
        issues.append({"check": "tickets_generated", "ok": False, "msg": "No ticket files for today"})

    try:
        sys.path.insert(0, str(ROOT))
        from scripts.db.engine import query_rows
        rows = query_rows(
            "SELECT COUNT(*) as cnt FROM forward_tracking WHERE output_date = :d",
            {"d": d},
        )
        cnt = rows[0]["cnt"] if rows else 0
        if cnt > 0:
            issues.append({"check": "db_data", "ok": True, "msg": f"{cnt} forward_tracking rows"})
        else:
            issues.append({"check": "db_data", "ok": False, "msg": "No forward_tracking data for today"})
    except Exception as e:
        issues.append({"check": "db_data", "ok": False, "msg": f"DB check failed: {e}"})

    return issues


def run_health_check(d: date | None = None) -> dict:
    d = d or date.today()
    logger = _setup_logger()

    if not is_us_trading_day(d):
        logger.info("Not a trading day (%s), skipping health check", d.strftime("%A"))
        return {"skipped": True, "reason": "not_trading_day"}

    logger.info("=== Health check %s ===", d.isoformat())
    issues = check_pipeline_health(d)

    failures = [i for i in issues if not i["ok"]]
    for f in failures:
        send_alert(f"Health check FAIL [{f['check']}]: {f['msg']}", "WARNING")

    if not failures:
        logger.info("All health checks passed")

    return {"date": d.isoformat(), "checks": issues, "failures": len(failures)}


if __name__ == "__main__":
    import json
    target = date.today()
    if len(sys.argv) > 1:
        target = date.fromisoformat(sys.argv[1])
    out = run_health_check(target)
    print(json.dumps(out, indent=2, ensure_ascii=False))
