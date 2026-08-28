from datetime import datetime, date
from sqlalchemy import (
    Column, String, Integer, BigInteger, Numeric, Text, TIMESTAMP, Date, Boolean,
    ForeignKey, UniqueConstraint, Index, JSON
)
from sqlalchemy.dialects.postgresql import JSONB
from .engine import Base


class Universe(Base):
    __tablename__ = "universe"
    symbol = Column(String(10), primary_key=True)
    name = Column(String(100))
    sector = Column(String(50))
    market_type = Column(String(20), default="US_STOCK")
    total_shares = Column(BigInteger)
    float_shares = Column(BigInteger)
    added_at = Column(TIMESTAMP, default=datetime.utcnow)


class DailyKline(Base):
    __tablename__ = "daily_klines"
    symbol = Column(String(10), primary_key=True)
    trade_date = Column(Date, primary_key=True)
    open = Column(Numeric(12, 4))
    high = Column(Numeric(12, 4))
    low = Column(Numeric(12, 4))
    close = Column(Numeric(12, 4))
    adj_close = Column(Numeric(12, 4))
    volume = Column(BigInteger)
    amount = Column(Numeric(18, 2))
    pct_chg = Column(Numeric(8, 4))
    turnover_rate = Column(Numeric(8, 4))
    source = Column(String(50), default="eastmoney_cdp_image")
    fetched_at = Column(TIMESTAMP, default=datetime.utcnow)


class RealtimeQuote(Base):
    __tablename__ = "realtime_quotes"
    symbol = Column(String(10), primary_key=True)
    snap_time = Column(TIMESTAMP, primary_key=True)
    latest_price = Column(Numeric(12, 4))
    prev_close = Column(Numeric(12, 4))
    open = Column(Numeric(12, 4))
    high = Column(Numeric(12, 4))
    low = Column(Numeric(12, 4))
    volume = Column(BigInteger)
    amount = Column(Numeric(18, 2))
    pct_chg = Column(Numeric(8, 4))
    pe_ttm = Column(Numeric(10, 4))
    roe = Column(Numeric(10, 4))
    dividend_yield = Column(Numeric(10, 4))
    week52_high = Column(Numeric(12, 4))
    week52_low = Column(Numeric(12, 4))


class FundFlow(Base):
    __tablename__ = "fund_flow"
    symbol = Column(String(10), primary_key=True)
    trade_date = Column(Date, primary_key=True)
    main_net_inflow = Column(Numeric(18, 2))
    main_net_ratio = Column(Numeric(8, 4))
    net_inflow_5d = Column(Numeric(18, 2))
    score = Column(Numeric(6, 4))


class Ticket(Base):
    __tablename__ = "tickets"
    id = Column(Integer, primary_key=True, autoincrement=True)
    output_date = Column(Date, nullable=False)
    symbol = Column(String(10), nullable=False)
    as_of_date = Column(Date, nullable=False)
    ticket_rank = Column(Integer)
    market_score = Column(Numeric(8, 6))
    catalyst_score = Column(Numeric(8, 6))
    ticket_score = Column(Numeric(8, 6))
    classification = Column(String(50))
    evidence_gate_status = Column(String(50))
    risk_verdict = Column(String(20))
    quality_verdict = Column(String(20))
    lifecycle_stage = Column(String(30))
    run_name = Column(String(100))
    research_run_id = Column(Integer, ForeignKey("research_runs.run_id"))
    # 出票理由字段
    narrative_title = Column(Text)
    business_title = Column(Text)
    risk_summary = Column(Text)
    quality_summary = Column(Text)
    panel_verdict = Column(String(50))
    market_regime = Column(String(20))
    entry_reason = Column(Text)
    # 评分细分字段（用于回测分析）
    institutional_flow_score = Column(Numeric(8, 6))
    social_sentiment_score = Column(Numeric(8, 6))
    raw_market_score = Column(Numeric(8, 6))
    blended_score = Column(Numeric(8, 6))
    breakout_score = Column(Numeric(8, 6))
    risk_penalty = Column(Numeric(8, 6))
    confirmation_score = Column(Numeric(8, 6))
    capital_score = Column(Numeric(8, 6))
    capital_strength = Column(Numeric(8, 6))
    capital_state = Column(String(40))
    capital_state_confidence = Column(Numeric(8, 6))
    capital_intent = Column(String(40))
    capital_intent_confidence = Column(Numeric(8, 6))
    accumulation_score = Column(Numeric(8, 6))
    absorption_score = Column(Numeric(8, 6))
    supply_exhaustion_score = Column(Numeric(8, 6))
    demand_persistence_score = Column(Numeric(8, 6))
    markup_score = Column(Numeric(8, 6))
    distribution_score = Column(Numeric(8, 6))
    price_control_score = Column(Numeric(8, 6))
    crowding_score = Column(Numeric(8, 6))
    trap_score = Column(Numeric(8, 6))
    expected_direction = Column(String(16))
    path_type = Column(String(40))
    t1_probability = Column(Numeric(8, 6))
    t3_probability = Column(Numeric(8, 6))
    t5_probability = Column(Numeric(8, 6))
    capital_thesis = Column(Text)
    invalidation_condition = Column(Text)
    created_at = Column(TIMESTAMP, default=datetime.utcnow)


class ForwardTracking(Base):
    __tablename__ = "forward_tracking"
    id = Column(Integer, primary_key=True, autoincrement=True)
    output_date = Column(Date, nullable=False)
    symbol = Column(String(10), nullable=False)
    as_of_date = Column(Date, nullable=False)
    horizon_days = Column(Integer, nullable=False)
    due_date = Column(Date, nullable=False)
    as_of_close = Column(Numeric(12, 4))
    check_status = Column(String(20), default="pending")
    due_close = Column(Numeric(12, 4))
    forward_return = Column(Numeric(10, 6))
    completed_at = Column(TIMESTAMP)
    track_key = Column(String(100), unique=True)
    ticket_id = Column(Integer, ForeignKey("tickets.id"))
    # 亏损/收益分析
    loss_reason = Column(Text)
    outcome_classification = Column(String(20))
    outcome_reason = Column(Text)
    capital_model_version = Column(String(64))
    capital_validation_status = Column(String(64))
    capital_state_at_entry = Column(String(40))
    capital_intent_at_entry = Column(String(40))
    capital_strength_at_entry = Column(Numeric(8, 6))
    capital_score_at_entry = Column(Numeric(8, 6))
    distribution_score_at_entry = Column(Numeric(8, 6))
    trap_score_at_entry = Column(Numeric(8, 6))
    predicted_path = Column(String(40))
    state_after_1d = Column(String(40))
    state_after_3d = Column(String(40))
    state_after_5d = Column(String(40))
    actual_path = Column(String(40))
    state_correct = Column(Boolean)
    intent_correct = Column(Boolean)
    path_correct = Column(Boolean)
    created_at = Column(TIMESTAMP, default=datetime.utcnow)


class CapitalDailySnapshot(Base):
    __tablename__ = "capital_daily_snapshot"
    id = Column(BigInteger, primary_key=True)
    symbol = Column(String(10), nullable=False)
    as_of_date = Column(Date, nullable=False)
    research_run_id = Column(Integer, ForeignKey("research_runs.run_id"), nullable=False)
    model_version = Column(String(64), nullable=False)
    data_version = Column(String(64), nullable=False)
    validation_status = Column(String(64), nullable=False)
    statistical_score = Column(Numeric(8, 6))
    capital_score = Column(Numeric(8, 6))
    combined_score = Column(Numeric(8, 6))
    capital_strength = Column(Numeric(8, 6))
    dominant_direction = Column(String(16))
    dominant_pressure = Column(Numeric(8, 6))
    distribution_risk = Column(Numeric(8, 6))
    trap_risk = Column(Numeric(8, 6))
    evidence_json = Column(JSONB)
    created_at = Column(TIMESTAMP, default=datetime.utcnow)


class CapitalEvidence(Base):
    __tablename__ = "capital_evidence"
    id = Column(BigInteger, primary_key=True)
    symbol = Column(String(10), nullable=False)
    as_of_date = Column(Date, nullable=False)
    research_run_id = Column(Integer, ForeignKey("research_runs.run_id"), nullable=False)
    model_version = Column(String(64), nullable=False)
    data_version = Column(String(64), nullable=False)
    evidence_type = Column(String(64), nullable=False)
    value = Column(Numeric(8, 6))
    confidence = Column(Numeric(8, 6))
    availability = Column(String(40), nullable=False)
    source = Column(String(128))
    lookback = Column(String(64))
    semantic = Column(String(16), nullable=False)
    created_at = Column(TIMESTAMP, default=datetime.utcnow)


class CapitalStateHistory(Base):
    __tablename__ = "capital_state_history"
    id = Column(BigInteger, primary_key=True)
    symbol = Column(String(10), nullable=False)
    as_of_date = Column(Date, nullable=False)
    research_run_id = Column(Integer, ForeignKey("research_runs.run_id"), nullable=False)
    model_version = Column(String(64), nullable=False)
    data_version = Column(String(64), nullable=False)
    capital_state = Column(String(40), nullable=False)
    previous_capital_state = Column(String(40))
    state_transition = Column(String(96))
    state_duration = Column(Integer, nullable=False)
    state_confidence = Column(Numeric(8, 6))
    state_reason = Column(Text)
    semantic = Column(String(16), nullable=False)
    created_at = Column(TIMESTAMP, default=datetime.utcnow)


class CapitalIntent(Base):
    __tablename__ = "capital_intent"
    id = Column(BigInteger, primary_key=True)
    symbol = Column(String(10), nullable=False)
    as_of_date = Column(Date, nullable=False)
    research_run_id = Column(Integer, ForeignKey("research_runs.run_id"), nullable=False)
    model_version = Column(String(64), nullable=False)
    data_version = Column(String(64), nullable=False)
    capital_intent = Column(String(40), nullable=False)
    intent_confidence = Column(Numeric(8, 6))
    expected_direction = Column(String(16))
    continuation_condition = Column(Text)
    invalidation_condition = Column(Text)
    semantic = Column(String(16), nullable=False)
    created_at = Column(TIMESTAMP, default=datetime.utcnow)


class CapitalPathPrediction(Base):
    __tablename__ = "capital_path_prediction"
    id = Column(BigInteger, primary_key=True)
    symbol = Column(String(10), nullable=False)
    as_of_date = Column(Date, nullable=False)
    research_run_id = Column(Integer, ForeignKey("research_runs.run_id"), nullable=False)
    model_version = Column(String(64), nullable=False)
    data_version = Column(String(64), nullable=False)
    path_type = Column(String(40), nullable=False)
    t1_probability = Column(Numeric(8, 6))
    t3_probability = Column(Numeric(8, 6))
    t5_probability = Column(Numeric(8, 6))
    path_confidence = Column(Numeric(8, 6))
    semantic = Column(String(16), nullable=False)
    created_at = Column(TIMESTAMP, default=datetime.utcnow)


class CapitalPredictionOutcome(Base):
    __tablename__ = "capital_prediction_outcome"
    id = Column(BigInteger, primary_key=True)
    forward_tracking_id = Column(Integer, ForeignKey("forward_tracking.id"), nullable=False)
    symbol = Column(String(10), nullable=False)
    as_of_date = Column(Date, nullable=False)
    research_run_id = Column(Integer, ForeignKey("research_runs.run_id"))
    model_version = Column(String(64))
    data_version = Column(String(64))
    state_after_1d = Column(String(40))
    state_after_3d = Column(String(40))
    state_after_5d = Column(String(40))
    actual_path = Column(String(40))
    state_correct = Column(Boolean)
    intent_correct = Column(Boolean)
    path_correct = Column(Boolean)
    semantic = Column(String(16), nullable=False)
    created_at = Column(TIMESTAMP, default=datetime.utcnow)
    updated_at = Column(TIMESTAMP, default=datetime.utcnow)


class RuntimeDecision(Base):
    __tablename__ = "runtime_decisions"
    id = Column(Integer, primary_key=True, autoincrement=True)
    output_date = Column(Date, nullable=False)
    run_name = Column(String(100))
    final_classification = Column(String(50))
    paper_review_count = Column(Integer)
    market_watchlist_count = Column(Integer)
    universe_count = Column(Integer)
    regime = Column(String(20))
    summary = Column(JSONB)
    created_at = Column(TIMESTAMP, default=datetime.utcnow)


class MarketSnapshot(Base):
    __tablename__ = "market_snapshots"
    trade_date = Column(Date, primary_key=True)
    regime = Column(String(20))
    breadth = Column(Numeric(6, 4))
    momentum = Column(Numeric(8, 6))
    volatility = Column(Numeric(8, 6))
    advance_ratio = Column(Numeric(6, 4))
    equal_weight_benchmark = Column(Numeric(8, 6))
    universe_count = Column(Integer)
    created_at = Column(TIMESTAMP, default=datetime.utcnow)


class LifecycleScoreboard(Base):
    __tablename__ = "lifecycle_scoreboard"
    id = Column(Integer, primary_key=True, autoincrement=True)
    generated_at = Column(TIMESTAMP, default=datetime.utcnow)
    overall = Column(JSONB)
    by_horizon = Column(JSONB)
    by_stage = Column(JSONB)
    by_symbol = Column(JSONB)
    by_regime = Column(JSONB)


class ResearchRun(Base):
    __tablename__ = "research_runs"
    run_id = Column(Integer, primary_key=True, autoincrement=True)
    run_name = Column(String(100), nullable=False)
    output_date = Column(Date, nullable=False)
    started_at = Column(TIMESTAMP, default=datetime.utcnow)
    finished_at = Column(TIMESTAMP)
    candidate_count = Column(Integer)
    pass_count = Column(Integer)
    status = Column(String(20), default="running")
    git_commit = Column(String(40))
    config = Column(JSONB)
    error_message = Column(Text)


class FactorSnapshot(Base):
    __tablename__ = "factor_snapshots"
    id = Column(Integer, primary_key=True, autoincrement=True)
    trade_date = Column(Date, nullable=False)
    symbol = Column(String(10), nullable=False)
    prior_5d_momentum = Column(Numeric(8, 6))
    prior_20d_momentum = Column(Numeric(8, 6))
    five_day_acceleration = Column(Numeric(8, 6))
    relative_strength = Column(Numeric(8, 6))
    volume_weighted_momentum = Column(Numeric(8, 6))
    rsi_14 = Column(Numeric(6, 2))
    momentum_quality = Column(Numeric(6, 4))
    breakout_score = Column(Numeric(6, 4))
    reversal_quality = Column(Numeric(6, 4))
    volume_confirmation = Column(Numeric(8, 6))
    closing_strength_5d = Column(Numeric(6, 4))
    dollar_volume_20d = Column(Numeric(18, 2))
    market_score = Column(Numeric(8, 6))
    structured_score = Column(Numeric(8, 6))
    blended_score = Column(Numeric(8, 6))
    theme_strength = Column(Numeric(8, 6))
    announcement_catalyst = Column(Numeric(8, 6))
    regime = Column(String(20))
    created_at = Column(TIMESTAMP, default=datetime.utcnow)
    __table_args__ = (
        UniqueConstraint("trade_date", "symbol", name="uq_factor_snapshots_date_symbol"),
    )


class CeleryTask(Base):
    __tablename__ = "celery_tasks"
    task_id = Column(String(55), primary_key=True)
    task_name = Column(String(100))
    status = Column(String(20), default="pending")
    started_at = Column(TIMESTAMP)
    finished_at = Column(TIMESTAMP)
    result = Column(JSONB)
    error_message = Column(Text)
    retry_count = Column(Integer, default=0)
    created_at = Column(TIMESTAMP, default=datetime.utcnow)
