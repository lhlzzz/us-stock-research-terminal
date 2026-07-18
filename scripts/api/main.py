"""FastAPI application for xiaomei."""
from datetime import date
from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.orm import Session
from scripts.db.engine import get_db

app = FastAPI(title="xiaomei API", version="0.1.0")


@app.get("/api/health")
def health():
    return {"status": "ok", "service": "xiaomei"}


@app.get("/api/demo")
def get_demo():
    """Fixed portfolio data for offline review; not market data or a trade signal."""
    return {
        "mode": "demo",
        "research_only": True,
        "not_investment_advice": True,
        "tickets": [
            {
                "symbol": "SAMPLE",
                "ticket_score": 78.0,
                "classification": "research_candidate",
                "risk_class": "medium",
                "rejection_reason": None,
                "data_freshness": "sample",
            }
        ],
        "scoreboard": {"completed_tracks": 12, "positive_return_rate": 0.58, "sample": True},
    }


@app.get("/api/universe")
def list_universe(db: Session = Depends(get_db)):
    from scripts.db.models import Universe
    rows = db.query(Universe).all()
    return [{"symbol": r.symbol, "name": r.name, "sector": r.sector} for r in rows]


@app.get("/api/klines/{symbol}")
def get_klines(symbol: str, start: str = None, end: str = None, db: Session = Depends(get_db)):
    from scripts.db.models import DailyKline
    q = db.query(DailyKline).filter_by(symbol=symbol).order_by(DailyKline.trade_date)
    if start:
        q = q.filter(DailyKline.trade_date >= start)
    if end:
        q = q.filter(DailyKline.trade_date <= end)
    rows = q.all()
    return [{
        "date": str(r.trade_date), "open": r.open, "high": r.high,
        "low": r.low, "close": r.close, "volume": r.volume,
    } for r in rows]


@app.get("/api/tickets")
def list_tickets(output_date: str = None, db: Session = Depends(get_db)):
    from scripts.db.models import Ticket
    q = db.query(Ticket).order_by(Ticket.output_date.desc(), Ticket.ticket_rank)
    if output_date:
        q = q.filter(Ticket.output_date == output_date)
    rows = q.limit(100).all()
    return [{
        "id": r.id, "output_date": str(r.output_date), "symbol": r.symbol,
        "ticket_score": float(r.ticket_score) if r.ticket_score else None,
        "classification": r.classification, "lifecycle_stage": r.lifecycle_stage,
    } for r in rows]


@app.get("/api/forward-tracking")
def list_forward_tracking(status: str = None, db: Session = Depends(get_db)):
    from scripts.db.models import ForwardTracking
    q = db.query(ForwardTracking).order_by(ForwardTracking.due_date)
    if status:
        q = q.filter(ForwardTracking.check_status == status)
    rows = q.limit(200).all()
    return [{
        "track_key": r.track_key, "symbol": r.symbol,
        "horizon_days": r.horizon_days, "due_date": str(r.due_date),
        "check_status": r.check_status, "forward_return": float(r.forward_return) if r.forward_return else None,
    } for r in rows]


@app.get("/api/scoreboard")
def get_scoreboard(db: Session = Depends(get_db)):
    from scripts.db.models import LifecycleScoreboard
    row = db.query(LifecycleScoreboard).order_by(LifecycleScoreboard.generated_at.desc()).first()
    if not row:
        return {"overall": {}, "by_horizon": {}}
    return {"overall": row.overall, "by_horizon": row.by_horizon}


@app.get("/api/research-runs")
def list_research_runs(db: Session = Depends(get_db)):
    from scripts.db.models import ResearchRun
    rows = db.query(ResearchRun).order_by(ResearchRun.started_at.desc()).limit(50).all()
    return [{
        "run_id": r.run_id, "run_name": r.run_name, "output_date": str(r.output_date),
        "status": r.status, "candidate_count": r.candidate_count,
        "started_at": str(r.started_at) if r.started_at else None,
    } for r in rows]


@app.post("/api/pipeline/run")
def trigger_pipeline(output_date: str = None):
    from scripts.tasks.pipeline_tasks import run_pipeline
    task = run_pipeline.delay(output_date)
    return {"task_id": task.id, "status": "queued"}


@app.post("/api/backfill")
def trigger_backfill(target_date: str = None):
    from scripts.tasks.backfill_tasks import backfill_tracking
    task = backfill_tracking.delay(target_date)
    return {"task_id": task.id, "status": "queued"}


@app.post("/api/scoreboard/update")
def trigger_scoreboard():
    from scripts.tasks.backfill_tasks import update_scoreboard
    task = update_scoreboard.delay()
    return {"task_id": task.id, "status": "queued"}


@app.get("/api/tasks/{task_id}")
def get_task_status(task_id: str):
    from scripts.tasks.celery_app import app as celery_app
    result = celery_app.AsyncResult(task_id)
    return {
        "task_id": task_id,
        "status": result.status,
        "result": result.result if result.ready() else None,
    }
