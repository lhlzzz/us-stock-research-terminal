"""CRUD operations for xiaomei database."""
from datetime import date, datetime
from typing import Optional
from sqlalchemy.orm import Session
from sqlalchemy import text
from db.models import (
    Universe, DailyKline, RealtimeQuote, FundFlow, Ticket,
    ForwardTracking, RuntimeDecision, MarketSnapshot,
    LifecycleScoreboard, ResearchRun, FactorSnapshot, CeleryTask,
)


def upsert_universe(db: Session, symbol: str, name: str, sector: str = None, **kwargs):
    obj = db.get(Universe, symbol)
    if obj:
        for k, v in kwargs.items():
            if v is not None:
                setattr(obj, k, v)
    else:
        obj = Universe(symbol=symbol, name=name, sector=sector, **kwargs)
        db.add(obj)
    db.commit()
    return obj


def upsert_kline(db: Session, symbol: str, trade_date: date, **kwargs):
    obj = db.get(DailyKline, (symbol, trade_date))
    if obj:
        for k, v in kwargs.items():
            if v is not None:
                setattr(obj, k, v)
    else:
        obj = DailyKline(symbol=symbol, trade_date=trade_date, **kwargs)
        db.add(obj)
    db.commit()
    return obj


def upsert_realtime_quote(db: Session, symbol: str, snap_time: datetime, **kwargs):
    obj = db.get(RealtimeQuote, (symbol, snap_time))
    if obj:
        for k, v in kwargs.items():
            if v is not None:
                setattr(obj, k, v)
    else:
        obj = RealtimeQuote(symbol=symbol, snap_time=snap_time, **kwargs)
        db.add(obj)
    db.commit()
    return obj


def upsert_fund_flow(db: Session, symbol: str, trade_date: date, **kwargs):
    obj = db.get(FundFlow, (symbol, trade_date))
    if obj:
        for k, v in kwargs.items():
            if v is not None:
                setattr(obj, k, v)
    else:
        obj = FundFlow(symbol=symbol, trade_date=trade_date, **kwargs)
        db.add(obj)
    db.commit()
    return obj


def create_ticket(db: Session, **kwargs) -> Ticket:
    obj = Ticket(**kwargs)
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj


def upsert_forward_tracking(db: Session, track_key: str, **kwargs) -> ForwardTracking:
    obj = db.query(ForwardTracking).filter_by(track_key=track_key).first()
    if obj:
        for k, v in kwargs.items():
            if v is not None:
                setattr(obj, k, v)
    else:
        obj = ForwardTracking(track_key=track_key, **kwargs)
        db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj


def get_pending_forward_tracking(db: Session, due_date: date = None):
    q = db.query(ForwardTracking).filter_by(check_status="pending")
    if due_date:
        q = q.filter(ForwardTracking.due_date <= due_date)
    return q.all()


def complete_forward_tracking(db: Session, track_key: str, due_close: float, forward_return: float):
    obj = db.query(ForwardTracking).filter_by(track_key=track_key).first()
    if obj:
        obj.due_close = due_close
        obj.forward_return = forward_return
        obj.check_status = "completed"
        obj.completed_at = datetime.utcnow()
        db.commit()
    return obj


def create_runtime_decision(db: Session, **kwargs) -> RuntimeDecision:
    obj = RuntimeDecision(**kwargs)
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj


def upsert_market_snapshot(db: Session, trade_date: date, **kwargs):
    obj = db.get(MarketSnapshot, trade_date)
    if obj:
        for k, v in kwargs.items():
            if v is not None:
                setattr(obj, k, v)
    else:
        obj = MarketSnapshot(trade_date=trade_date, **kwargs)
        db.add(obj)
    db.commit()
    return obj


def create_lifecycle_scoreboard(db: Session, **kwargs) -> LifecycleScoreboard:
    obj = LifecycleScoreboard(**kwargs)
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj


def create_research_run(db: Session, **kwargs) -> ResearchRun:
    obj = ResearchRun(**kwargs)
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj


def finish_research_run(db: Session, run_id: int, status: str = "done", **kwargs):
    obj = db.get(ResearchRun, run_id)
    if obj:
        obj.status = status
        obj.finished_at = datetime.utcnow()
        for k, v in kwargs.items():
            setattr(obj, k, v)
        db.commit()
    return obj


def upsert_factor_snapshot(db: Session, trade_date: date, symbol: str, **kwargs):
    obj = db.query(FactorSnapshot).filter_by(trade_date=trade_date, symbol=symbol).first()
    if obj:
        for k, v in kwargs.items():
            if v is not None:
                setattr(obj, k, v)
    else:
        obj = FactorSnapshot(trade_date=trade_date, symbol=symbol, **kwargs)
        db.add(obj)
    db.commit()
    return obj


def create_celery_task(db: Session, task_id: str, task_name: str = None, **kwargs) -> CeleryTask:
    obj = CeleryTask(task_id=task_id, task_name=task_name, **kwargs)
    db.add(obj)
    db.commit()
    return obj
