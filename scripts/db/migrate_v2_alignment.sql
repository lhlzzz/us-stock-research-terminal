-- xiaomei schema alignment with xiaogu architecture
-- Adds 6 new tables for full lifecycle closure

-- 1. daily_candidates: Full candidate pool with rich decision evidence
CREATE TABLE IF NOT EXISTS daily_candidates (
    id SERIAL PRIMARY KEY,
    trade_date DATE NOT NULL,
    symbol VARCHAR(10) NOT NULL,
    stock_name VARCHAR(50),
    rank INTEGER,
    final_score NUMERIC(8,4),
    is_official_pick BOOLEAN DEFAULT FALSE,
    decision VARCHAR(30) DEFAULT 'CANDIDATE',

    -- Price data
    open NUMERIC(12,4),
    high NUMERIC(12,4),
    low NUMERIC(12,4),
    close NUMERIC(12,4),
    volume BIGINT,
    amount NUMERIC(18,2),
    pct_chg NUMERIC(8,4),

    -- Catalyst scores
    sentiment_catalyst NUMERIC(8,4),
    theme_catalyst NUMERIC(8,4),
    news_catalyst NUMERIC(8,4),
    positive_catalyst NUMERIC(8,4),

    -- Decision reasons
    selection_reason TEXT,
    selection_outcome VARCHAR(30),
    selection_outcome_reason TEXT,
    candidate_entry_reason JSONB,
    ticket_reason JSONB,
    not_selected_reason JSONB,

    -- Factor scores
    signal_pct NUMERIC(8,4),
    close_position_score NUMERIC(8,4),
    fund_flow_momentum NUMERIC(8,4),
    sector_catalyst_score NUMERIC(8,4),
    early_opportunity_score NUMERIC(8,4),
    topic_propagation_score NUMERIC(8,4),
    market_score NUMERIC(8,4),
    catalyst_score NUMERIC(8,4),
    ticket_score NUMERIC(8,4),

    -- Market context
    market_regime VARCHAR(30),

    -- Rich evidence snapshots
    blockers JSONB,
    hard_gate_status JSONB,
    eligibility_snapshot JSONB,
    selection_diagnostics JSONB,
    source_layers JSONB,
    candidate_features JSONB,
    factor_snapshot JSONB,
    auxiliary_evidence_snapshot JSONB,
    ranking_basis JSONB,
    postmortem_snapshot JSONB,

    -- Cohort tracking
    cohort VARCHAR(30),
    cohort_quality VARCHAR(30),
    cohort_status_flags JSONB,
    reconstruction_provenance JSONB,

    -- Raw data
    raw_json JSONB,

    -- Timestamps
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),

    UNIQUE(trade_date, symbol)
);

CREATE INDEX IF NOT EXISTS idx_daily_candidates_date ON daily_candidates(trade_date);
CREATE INDEX IF NOT EXISTS idx_daily_candidates_symbol ON daily_candidates(symbol);
CREATE INDEX IF NOT EXISTS idx_daily_candidates_decision ON daily_candidates(decision);
CREATE INDEX IF NOT EXISTS idx_daily_candidates_is_pick ON daily_candidates(is_official_pick);

-- 2. scoring_config: Tunable closed-loop parameters
CREATE TABLE IF NOT EXISTS scoring_config (
    id SERIAL PRIMARY KEY,
    config_key VARCHAR(100) UNIQUE NOT NULL,
    config_value TEXT NOT NULL,
    description TEXT,
    data_version VARCHAR(20) DEFAULT 'v1',
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Seed default scoring parameters
INSERT INTO scoring_config (config_key, config_value, description) VALUES
    ('max_score_cap', '88', 'Maximum score cap for any candidate'),
    ('min_market_score_gate', '0.55', 'Minimum market score to pass gate'),
    ('top_k_tickets', '3', 'Number of top tickets to output per day'),
    ('candidate_pool_size', '10', 'Size of candidate pool for selection'),
    ('follow_on_t1_weight', '1.0', 'Weight for T+1 return in follow-on scoring'),
    ('follow_on_t2_weight', '0.45', 'Weight for T+2 return in follow-on scoring'),
    ('follow_on_t3_weight', '0.25', 'Weight for T+3 return in follow-on scoring'),
    ('limit_up_threshold', '0.095', 'Threshold for limit-up detection'),
    ('stale_repeat_window_days', '5', 'Window for stale repeat detection'),
    ('stale_decay_factor', '0.65', 'Decay factor for stale candidates'),
    ('evidence_momentum_weight', '0.35', 'Weight for momentum evidence'),
    ('evidence_catalyst_boost_weight', '0.20', 'Weight for catalyst boost evidence'),
    ('evidence_volume_weight', '0.15', 'Weight for volume evidence'),
    ('evidence_reversal_weight', '0.15', 'Weight for reversal evidence'),
    ('evidence_breakout_weight', '0.10', 'Weight for breakout evidence'),
    ('evidence_fund_flow_weight', '0.05', 'Weight for fund flow evidence'),
    ('weekday_blocklist', '', 'Comma-separated weekdays to block (0=Mon,6=Sun)'),
    ('us_market_close_hour', '4', 'US market close hour in Beijing time (summer)'),
    ('us_market_open_hour', '21', 'US market open hour in Beijing time (summer)'),
    ('pipeline_run_after_hour', '5', 'Minimum Beijing hour to run pipeline (after US close)')
ON CONFLICT (config_key) DO NOTHING;

-- 3. signal_effectiveness: Daily signal analysis snapshots
CREATE TABLE IF NOT EXISTS signal_effectiveness (
    id SERIAL PRIMARY KEY,
    analysis_date DATE NOT NULL,
    signal_key VARCHAR(100) NOT NULL,
    present_count INTEGER,
    win_rate NUMERIC(8,4),
    avg_return NUMERIC(8,6),
    weight_suggestion NUMERIC(8,4),
    ic_score NUMERIC(8,6),
    p_value NUMERIC(8,6),
    data_version VARCHAR(20) DEFAULT 'v1',
    created_at TIMESTAMP DEFAULT NOW(),

    UNIQUE(analysis_date, signal_key)
);

CREATE INDEX IF NOT EXISTS idx_signal_effectiveness_date ON signal_effectiveness(analysis_date);
CREATE INDEX IF NOT EXISTS idx_signal_effectiveness_key ON signal_effectiveness(signal_key);

-- 4. signals: Per-stock raw signal snapshots
CREATE TABLE IF NOT EXISTS signals (
    id SERIAL PRIMARY KEY,
    trade_date DATE NOT NULL,
    symbol VARCHAR(10) NOT NULL,
    signal_key VARCHAR(100) NOT NULL,
    signal_value NUMERIC(12,6),
    raw_json JSONB,
    created_at TIMESTAMP DEFAULT NOW(),

    UNIQUE(trade_date, symbol, signal_key)
);

CREATE INDEX IF NOT EXISTS idx_signals_date ON signals(trade_date);
CREATE INDEX IF NOT EXISTS idx_signals_symbol ON signals(symbol);
CREATE INDEX IF NOT EXISTS idx_signals_key ON signals(signal_key);

-- 5. scan_sessions: Scanner session metadata
CREATE TABLE IF NOT EXISTS scan_sessions (
    id SERIAL PRIMARY KEY,
    trade_date DATE NOT NULL,
    scan_time TIMESTAMP NOT NULL,
    quotes_count INTEGER,
    scored_count INTEGER,
    passed_count INTEGER,
    scan_dir VARCHAR(200),
    status VARCHAR(30) DEFAULT 'running',
    error_message TEXT,
    market_snapshot JSONB,
    source_status JSONB,
    source_counts JSONB,
    source_diagnostics JSONB,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_scan_sessions_date ON scan_sessions(trade_date);

-- 6. pick_case_embeddings: Neural/vector embeddings for case similarity
CREATE TABLE IF NOT EXISTS pick_case_embeddings (
    id SERIAL PRIMARY KEY,
    trade_date DATE NOT NULL,
    symbol VARCHAR(10) NOT NULL,
    decision VARCHAR(30) DEFAULT 'PAPER_PICK',
    stock_name VARCHAR(50),
    final_score NUMERIC(8,4),
    case_text TEXT,
    embedding VECTOR(384),  -- sentence-transformers dimension
    metadata JSONB,
    t1_return NUMERIC(8,6),
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),

    UNIQUE(trade_date, symbol, decision)
);

CREATE INDEX IF NOT EXISTS idx_pick_case_embeddings_date ON pick_case_embeddings(trade_date);
CREATE INDEX IF NOT EXISTS idx_pick_case_embeddings_symbol ON pick_case_embeddings(symbol);

-- Create HNSW index for vector similarity search
CREATE INDEX IF NOT EXISTS idx_pick_case_embeddings_hnsw
    ON pick_case_embeddings USING hnsw (embedding vector_cosine_ops)
    WITH (m = 16, ef_construction = 64);

-- Enable pgvector extension if not already enabled
CREATE EXTENSION IF NOT EXISTS vector;

COMMENT ON TABLE daily_candidates IS 'Full daily candidate pool with rich decision evidence (xiaogu aligned)';
COMMENT ON TABLE scoring_config IS 'Tunable closed-loop parameters for self-evolution';
COMMENT ON TABLE signal_effectiveness IS 'Daily signal analysis snapshots';
COMMENT ON TABLE signals IS 'Per-stock raw signal snapshots';
COMMENT ON TABLE scan_sessions IS 'Scanner session metadata';
COMMENT ON TABLE pick_case_embeddings IS 'Neural/vector embeddings for case similarity search';

-- 7. Stable research lifecycle links and deterministic outcome attribution.
ALTER TABLE forward_tracking
    ADD COLUMN IF NOT EXISTS outcome_classification VARCHAR(20),
    ADD COLUMN IF NOT EXISTS outcome_reason TEXT;
ALTER TABLE trade_journal
    ADD COLUMN IF NOT EXISTS ticket_id INTEGER REFERENCES tickets(id);
ALTER TABLE paper_trades
    ADD COLUMN IF NOT EXISTS ticket_id INTEGER REFERENCES tickets(id);
ALTER TABLE paper_fills
    ADD COLUMN IF NOT EXISTS ticket_id INTEGER REFERENCES tickets(id);

CREATE INDEX IF NOT EXISTS idx_forward_tracking_ticket_id ON forward_tracking(ticket_id);
CREATE INDEX IF NOT EXISTS idx_trade_journal_ticket_id ON trade_journal(ticket_id);
CREATE INDEX IF NOT EXISTS idx_paper_trades_ticket_id ON paper_trades(ticket_id);
CREATE INDEX IF NOT EXISTS idx_paper_fills_ticket_id ON paper_fills(ticket_id);

-- Read-only projection: one trace id for issuance, outcome, and paper evidence.
CREATE OR REPLACE VIEW research_trade_trace AS
SELECT
    'ticket'::text AS record_type,
    ('ticket:' || t.id)::text AS trace_id,
    t.id::bigint AS record_id,
    t.id AS ticket_id,
    NULL::integer AS tracking_id,
    t.output_date,
    t.symbol,
    NULL::integer AS horizon_days,
    COALESCE(t.lifecycle_stage, t.classification)::text AS lifecycle_stage,
    'ISSUED'::text AS record_status,
    NULL::numeric AS forward_return,
    NULL::numeric AS pnl,
    t.entry_reason AS selection_reason,
    NULL::text AS outcome_classification,
    NULL::text AS outcome_reason,
    NULL::text AS paper_reason
FROM tickets t
UNION ALL
SELECT
    'forward_tracking'::text,
    ('ticket:' || t.id || ':tracking:' || ft.id)::text,
    ft.id::bigint,
    t.id,
    ft.id,
    ft.output_date,
    ft.symbol,
    ft.horizon_days,
    COALESCE(t.lifecycle_stage, t.classification)::text,
    ft.check_status::text,
    ft.forward_return,
    NULL::numeric,
    t.entry_reason,
    ft.outcome_classification,
    COALESCE(ft.outcome_reason, ft.loss_reason),
    NULL::text
FROM forward_tracking ft
JOIN tickets t ON t.id = ft.ticket_id
UNION ALL
SELECT
    'paper_trade'::text,
    ('paper_trade:' || pt.id)::text,
    pt.id::bigint,
    pt.ticket_id,
    NULL::integer,
    pt.trade_date,
    pt.symbol,
    NULL::integer,
    COALESCE(
        t.lifecycle_stage,
        t.classification,
        'UNRESOLVED_NO_TICKET'
    )::text,
    COALESCE(pt.status, 'UNKNOWN')::text,
    pt.realized_pnl_pct,
    pt.realized_pnl,
    t.entry_reason,
    CASE
        WHEN pt.realized_pnl > 0 THEN 'WIN'
        WHEN pt.realized_pnl < 0 THEN 'LOSS'
        WHEN pt.status = 'closed' THEN 'FLAT'
        ELSE NULL
    END,
    pt.exit_reason,
    CASE
        WHEN pt.ticket_id IS NULL THEN 'UNRESOLVED_NO_TICKET'
        ELSE NULL
    END::text
FROM paper_trades pt
LEFT JOIN tickets t ON t.id = pt.ticket_id
UNION ALL
SELECT
    'trade_journal'::text,
    ('trade_journal:' || tj.id)::text,
    tj.id::bigint,
    tj.ticket_id,
    NULL::integer,
    tj.trade_date,
    tj.symbol,
    NULL::integer,
    COALESCE(
        t.lifecycle_stage,
        t.classification,
        'UNRESOLVED_NO_TICKET'
    )::text,
    COALESCE(tj.status, 'UNKNOWN')::text,
    tj.pnl_pct,
    tj.pnl_dollar,
    t.entry_reason,
    CASE
        WHEN tj.pnl_dollar > 0 THEN 'WIN'
        WHEN tj.pnl_dollar < 0 THEN 'LOSS'
        WHEN LOWER(COALESCE(tj.status, '')) = 'closed' THEN 'FLAT'
        ELSE NULL
    END,
    NULL::text,
    tj.reason_summary
FROM trade_journal tj
LEFT JOIN tickets t ON t.id = tj.ticket_id
UNION ALL
SELECT
    'unlinked_forward_tracking'::text,
    ('tracking:' || ft.id)::text,
    ft.id::bigint,
    NULL::integer,
    ft.id,
    ft.output_date,
    ft.symbol,
    ft.horizon_days,
    'UNRESOLVED_NO_TICKET'::text,
    ft.check_status::text,
    ft.forward_return,
    NULL::numeric,
    NULL::text,
    ft.outcome_classification,
    COALESCE(
        ft.outcome_reason,
        ft.loss_reason,
        'UNRESOLVED_NO_SOURCE_EXPLANATION'
    ),
    NULL::text
FROM forward_tracking ft
WHERE ft.ticket_id IS NULL;
