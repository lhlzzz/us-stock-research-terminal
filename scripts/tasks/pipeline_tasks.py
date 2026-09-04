"""Pipeline tasks."""
import os
from datetime import date
from pathlib import Path

from scripts.tasks.celery_app import app

PROJECT_DIR = str(Path(os.environ.get('XIAOMEI_HOME') or Path(__file__).resolve().parents[2]))


@app.task(bind=True, max_retries=2)
def run_pipeline(self, output_date: str = None):
    """Run the xiaomei ticket pipeline and store results in PostgreSQL."""
    from scripts.db.engine import SessionLocal
    from scripts.db.crud import upsert_ticket, create_runtime_decision, create_research_run, finish_research_run
    import subprocess
    import json

    db = SessionLocal()
    run_record = None
    try:
        target_date = output_date or date.today().isoformat()
        run_record = create_research_run(db, run_name="pipeline", output_date=target_date, status="running")
        db.commit()

        result = subprocess.run(
            ["python3", "scripts/us_profit_ticket_pipeline.py",
             "--output-date", f"{target_date}-final",
             "--skip-last30days"],
            capture_output=True, text=True, timeout=600,
            cwd=PROJECT_DIR
        )

        if result.returncode == 0:
            try:
                output = json.loads(result.stdout.strip().split("\n")[-1])
                for sym_data in output.get("top_candidates", []):
                    upsert_ticket(db, output_date=target_date, symbol=sym_data,
                                  as_of_date=target_date, lifecycle_stage="paper_review_candidate")
                create_runtime_decision(db, output_date=target_date, run_name="pipeline",
                                        final_classification=output.get("final_classification"),
                                        paper_review_count=output.get("paper_review_count", 0),
                                        market_watchlist_count=output.get("market_watchlist_count", 0))
                finish_research_run(db, run_record.run_id, status="done",
                                    candidate_count=output.get("paper_review_count", 0) + output.get("market_watchlist_count", 0))
            except (json.JSONDecodeError, KeyError):
                finish_research_run(db, run_record.run_id, status="partial", error_message="Parse error")
        else:
            finish_research_run(db, run_record.run_id, status="failed", error_message=result.stderr[:500])

        db.commit()
        return {"status": "done", "output_date": target_date, "returncode": result.returncode}
    except Exception as exc:
        if run_record:
            finish_research_run(db, run_record.run_id, status="failed", error_message=str(exc)[:500])
            db.commit()
        self.retry(exc=exc)
    finally:
        db.close()
