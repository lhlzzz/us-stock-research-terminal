"""Backfill tasks."""
from datetime import date
from scripts.tasks.celery_app import app


@app.task(bind=True, max_retries=2)
def backfill_tracking(self, target_date: str = None):
    """Backfill forward tracking rows with actual close prices."""
    from scripts.db.engine import SessionLocal
    from scripts.db.crud import get_pending_forward_tracking, complete_forward_tracking
    from scripts.eastmoney_us_cdp import fetch_realtime_quote

    db = SessionLocal()
    try:
        target = date.fromisoformat(target_date) if target_date else date.today()
        pending = get_pending_forward_tracking(db, due_date=target)

        filled = 0
        for row in pending:
            if row.due_date > target:
                continue
            q = fetch_realtime_quote(row.symbol)
            if q and q.get("latest_price") and row.as_of_close:
                close = float(q["latest_price"])
                as_of = float(row.as_of_close)
                ret = (close - as_of) / as_of if as_of else 0
                complete_forward_tracking(db, row.track_key, close, ret)
                filled += 1

        db.commit()
        return {"status": "done", "filled": filled, "target_date": str(target)}
    except Exception as exc:
        db.rollback()
        self.retry(exc=exc)
    finally:
        db.close()


@app.task(bind=True)
def update_scoreboard(self):
    """Recompute lifecycle scoreboard from database."""
    from scripts.db.engine import SessionLocal
    from scripts.db.crud import create_lifecycle_scoreboard
    from sqlalchemy import text

    db = SessionLocal()
    try:
        result = db.execute(text("""
            SELECT
                COUNT(*) as total,
                COUNT(CASE WHEN forward_return > 0 THEN 1 END) as wins,
                AVG(forward_return) as avg_return
            FROM forward_tracking
            WHERE check_status = 'completed'
        """)).fetchone()

        overall = {
            "total": result[0],
            "wins": result[1],
            "win_rate": round(result[1] / result[0] * 100, 2) if result[0] else 0,
            "avg_return": round(float(result[2]) * 100, 4) if result[2] else 0,
        }

        horizon_result = db.execute(text("""
            SELECT horizon_days,
                   COUNT(*) as total,
                   COUNT(CASE WHEN forward_return > 0 THEN 1 END) as wins,
                   AVG(forward_return) as avg_return
            FROM forward_tracking
            WHERE check_status = 'completed'
            GROUP BY horizon_days
            ORDER BY horizon_days
        """)).fetchall()

        by_horizon = {}
        for row in horizon_result:
            by_horizon[f"{row[0]}d"] = {
                "total": row[1],
                "wins": row[2],
                "win_rate": round(row[2] / row[1] * 100, 2) if row[1] else 0,
                "avg_return": round(float(row[3]) * 100, 4) if row[3] else 0,
            }

        create_lifecycle_scoreboard(db, overall=overall, by_horizon=by_horizon)
        return {"status": "done", "overall": overall}
    except Exception as exc:
        db.rollback()
        raise
    finally:
        db.close()
