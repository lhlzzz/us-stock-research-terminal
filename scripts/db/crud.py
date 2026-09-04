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


def _flush_or_commit(db: Session, commit: bool):
    if commit:
        db.commit()
    else:
        db.flush()


def create_ticket(db: Session, *, commit: bool = True, **kwargs) -> Ticket:
    return upsert_ticket(db, commit=commit, **kwargs)


def upsert_ticket(db: Session, *, commit: bool = True, **kwargs) -> Ticket:
    output_date = kwargs.get("output_date")
    symbol = kwargs.get("symbol")
    as_of_date = kwargs.get("as_of_date")
    research_run_id = kwargs.get("research_run_id")
    obj = None
    if output_date is not None and symbol not in (None, "") and as_of_date is not None:
        query = db.query(Ticket).filter_by(output_date=output_date, symbol=symbol, as_of_date=as_of_date)
        if research_run_id is not None:
            query = query.filter_by(research_run_id=research_run_id)
        obj = query.order_by(Ticket.id.desc()).first()
    if obj:
        for k, v in kwargs.items():
            if v is not None:
                setattr(obj, k, v)
    else:
        obj = Ticket(**kwargs)
        db.add(obj)
    _flush_or_commit(db, commit)
    db.refresh(obj)
    return obj


def upsert_forward_tracking(
    db: Session,
    track_key: str,
    *,
    commit: bool = True,
    **kwargs,
) -> ForwardTracking:
    obj = db.query(ForwardTracking).filter_by(track_key=track_key).first()
    if obj:
        for k, v in kwargs.items():
            if v is not None:
                setattr(obj, k, v)
    else:
        obj = ForwardTracking(track_key=track_key, **kwargs)
        db.add(obj)
    _flush_or_commit(db, commit)
    db.refresh(obj)
    return obj


def link_unlinked_forward_tracking(db: Session) -> int:
    """Attach legacy tracking rows to one deterministic ticket identity."""
    result = db.execute(text("""
        WITH ranked AS (
            SELECT
                ft.id AS tracking_id,
                t.id AS ticket_id,
                ROW_NUMBER() OVER (
                    PARTITION BY ft.id
                    ORDER BY
                        CASE WHEN t.as_of_date = ft.as_of_date THEN 0 ELSE 1 END,
                        t.created_at DESC NULLS LAST,
                        t.id DESC
                ) AS rank
            FROM forward_tracking ft
            JOIN tickets t
              ON t.symbol = ft.symbol
             AND t.output_date = ft.output_date
            WHERE ft.ticket_id IS NULL
        )
        UPDATE forward_tracking ft
           SET ticket_id = ranked.ticket_id
          FROM ranked
         WHERE ranked.rank = 1
           AND ft.id = ranked.tracking_id
    """))
    db.commit()
    return int(result.rowcount or 0)


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


def create_runtime_decision(db: Session, *, commit: bool = True, **kwargs) -> RuntimeDecision:
    obj = RuntimeDecision(**kwargs)
    db.add(obj)
    _flush_or_commit(db, commit)
    db.refresh(obj)
    return obj


def upsert_market_snapshot(db: Session, trade_date: date, *, commit: bool = True, **kwargs):
    obj = db.get(MarketSnapshot, trade_date)
    if obj:
        for k, v in kwargs.items():
            if v is not None:
                setattr(obj, k, v)
    else:
        obj = MarketSnapshot(trade_date=trade_date, **kwargs)
        db.add(obj)
    _flush_or_commit(db, commit)
    return obj


def create_lifecycle_scoreboard(db: Session, **kwargs) -> LifecycleScoreboard:
    obj = LifecycleScoreboard(**kwargs)
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj


def create_research_run(db: Session, *, commit: bool = True, **kwargs) -> ResearchRun:
    obj = ResearchRun(**kwargs)
    db.add(obj)
    _flush_or_commit(db, commit)
    db.refresh(obj)
    return obj


def finish_research_run(
    db: Session,
    run_id: int,
    status: str = "done",
    *,
    commit: bool = True,
    **kwargs,
):
    obj = db.get(ResearchRun, run_id)
    if obj:
        obj.status = status
        obj.finished_at = datetime.utcnow()
        for k, v in kwargs.items():
            setattr(obj, k, v)
        _flush_or_commit(db, commit)
    return obj


def upsert_factor_snapshot(
    db: Session,
    trade_date: date,
    symbol: str,
    *,
    commit: bool = True,
    **kwargs,
):
    obj = db.query(FactorSnapshot).filter_by(trade_date=trade_date, symbol=symbol).first()
    if obj:
        for k, v in kwargs.items():
            if v is not None:
                setattr(obj, k, v)
    else:
        obj = FactorSnapshot(trade_date=trade_date, symbol=symbol, **kwargs)
        db.add(obj)
    _flush_or_commit(db, commit)
    return obj


def create_celery_task(db: Session, task_id: str, task_name: str = None, **kwargs) -> CeleryTask:
    obj = CeleryTask(task_id=task_id, task_name=task_name, **kwargs)
    db.add(obj)
    db.commit()
    return obj


def upsert_signal(db: Session, trade_date: date, symbol: str, signal_key: str, signal_value: float):
    """Upsert a signal value into the signals table."""
    result = db.execute(
        text("SELECT id FROM signals WHERE trade_date = :td AND symbol = :sym AND signal_key = :sk"),
        {"td": trade_date, "sym": symbol, "sk": signal_key}
    )
    row = result.fetchone()
    if row:
        db.execute(
            text("UPDATE signals SET signal_value = :sv WHERE id = :id"),
            {"sv": signal_value, "id": row[0]}
        )
    else:
        db.execute(
            text("INSERT INTO signals (trade_date, symbol, signal_key, signal_value) VALUES (:td, :sym, :sk, :sv)"),
            {"td": trade_date, "sym": symbol, "sk": signal_key, "sv": signal_value}
        )
    return True
