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

-- Every new ticket and candidate belongs to one reproducible research run.
ALTER TABLE tickets
    ADD COLUMN IF NOT EXISTS research_run_id INTEGER REFERENCES research_runs(run_id);
ALTER TABLE daily_candidates
    ADD COLUMN IF NOT EXISTS research_run_id INTEGER REFERENCES research_runs(run_id);
CREATE INDEX IF NOT EXISTS idx_tickets_research_run_id ON tickets(research_run_id);
CREATE INDEX IF NOT EXISTS idx_daily_candidates_research_run_id ON daily_candidates(research_run_id);

-- Historical rows without saved source snapshots must remain explicitly unavailable,
-- never be presented as measured news, sentiment, or institutional flow evidence.
UPDATE research_runs
SET config = jsonb_build_object('version_status', 'UNAVAILABLE_HISTORICAL')
WHERE config IS NULL OR config = '{}'::jsonb;

UPDATE daily_candidates
SET source_layers = jsonb_build_object(
        'news', jsonb_build_object('status', 'UNAVAILABLE_HISTORICAL'),
        'capital_flow_proxy', jsonb_build_object('status', 'UNAVAILABLE_HISTORICAL'),
        'social_sentiment', jsonb_build_object('status', 'UNAVAILABLE_HISTORICAL'),
        'price_volume', jsonb_build_object('status', 'UNAVAILABLE_HISTORICAL')
    ),
    factor_snapshot = COALESCE(
        factor_snapshot,
        jsonb_build_object('status', 'UNAVAILABLE_HISTORICAL')
    ),
    auxiliary_evidence_snapshot = COALESCE(
        auxiliary_evidence_snapshot,
        jsonb_build_object('status', 'UNAVAILABLE_HISTORICAL')
    )
WHERE source_layers IS NULL;

-- The 2026-08-15 closed-session run predates snapshot persistence but can be
-- tied to the committed scheduler lifecycle revision that produced it. Its
-- omitted evidence remains unavailable; only the derivable run identity is
-- reconstructed.
UPDATE research_runs
SET git_commit = '37693ec16f8ebbffdd29d758fa48ec458023b93b',
    config = COALESCE(config, '{}'::jsonb) || jsonb_build_object(
        'version_status', 'RECONSTRUCTED_FROM_DATABASE',
        'reconstruction_note', 'Ticket/run linkage and source revision reconstructed; candidate evidence was not persisted.'
    )
WHERE run_id = 143
  AND output_date = DATE '2026-08-15'
  AND run_name = 'profit-ticket-pipeline'
  AND git_commit IS NULL;

UPDATE tickets
SET research_run_id = 143
WHERE research_run_id IS NULL
  AND output_date = DATE '2026-08-15'
  AND run_name = 'profit-ticket-pipeline'
  AND EXISTS (
      SELECT 1
      FROM research_runs
      WHERE run_id = 143
        AND output_date = DATE '2026-08-15'
        AND run_name = 'profit-ticket-pipeline'
  );

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
CREATE TABLE IF NOT EXISTS research_record_archive (
    id BIGSERIAL PRIMARY KEY,
    source_table VARCHAR(64) NOT NULL,
    source_id BIGINT NOT NULL,
    archive_reason TEXT NOT NULL,
    payload JSONB NOT NULL,
    archived_at TIMESTAMP NOT NULL DEFAULT NOW(),
    UNIQUE(source_table, source_id)
);

CREATE INDEX IF NOT EXISTS idx_research_record_archive_source
    ON research_record_archive(source_table, source_id);

ALTER TABLE forward_tracking
    ADD COLUMN IF NOT EXISTS outcome_classification VARCHAR(20),
    ADD COLUMN IF NOT EXISTS outcome_reason TEXT;
ALTER TABLE trade_journal
    ADD COLUMN IF NOT EXISTS ticket_id INTEGER REFERENCES tickets(id);
ALTER TABLE paper_trades
    ADD COLUMN IF NOT EXISTS ticket_id INTEGER REFERENCES tickets(id);
ALTER TABLE paper_fills
    ADD COLUMN IF NOT EXISTS ticket_id INTEGER REFERENCES tickets(id);

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM forward_tracking WHERE ticket_id IS NULL) THEN
        ALTER TABLE forward_tracking
            ALTER COLUMN ticket_id SET NOT NULL;
    END IF;
    IF NOT EXISTS (SELECT 1 FROM paper_trades WHERE ticket_id IS NULL) THEN
        ALTER TABLE paper_trades
            ALTER COLUMN ticket_id SET NOT NULL;
    END IF;
    IF NOT EXISTS (SELECT 1 FROM trade_journal WHERE ticket_id IS NULL) THEN
        ALTER TABLE trade_journal
            ALTER COLUMN ticket_id SET NOT NULL;
    END IF;
END
$$;

CREATE INDEX IF NOT EXISTS idx_forward_tracking_ticket_id ON forward_tracking(ticket_id);
CREATE INDEX IF NOT EXISTS idx_trade_journal_ticket_id ON trade_journal(ticket_id);
CREATE INDEX IF NOT EXISTS idx_paper_trades_ticket_id ON paper_trades(ticket_id);
CREATE INDEX IF NOT EXISTS idx_paper_fills_ticket_id ON paper_fills(ticket_id);

-- 9. Capital Behavior Engine. These fields and tables are strictly parallel
-- research metadata derived from public price-volume data. They do not assert
-- participant identity and must not alter the production ranking by themselves.
ALTER TABLE tickets
    ADD COLUMN IF NOT EXISTS capital_score NUMERIC(8,6),
    ADD COLUMN IF NOT EXISTS capital_strength NUMERIC(8,6),
    ADD COLUMN IF NOT EXISTS capital_state VARCHAR(40),
    ADD COLUMN IF NOT EXISTS capital_state_confidence NUMERIC(8,6),
    ADD COLUMN IF NOT EXISTS capital_intent VARCHAR(40),
    ADD COLUMN IF NOT EXISTS capital_intent_confidence NUMERIC(8,6),
    ADD COLUMN IF NOT EXISTS accumulation_score NUMERIC(8,6),
    ADD COLUMN IF NOT EXISTS absorption_score NUMERIC(8,6),
    ADD COLUMN IF NOT EXISTS supply_exhaustion_score NUMERIC(8,6),
    ADD COLUMN IF NOT EXISTS demand_persistence_score NUMERIC(8,6),
    ADD COLUMN IF NOT EXISTS markup_score NUMERIC(8,6),
    ADD COLUMN IF NOT EXISTS distribution_score NUMERIC(8,6),
    ADD COLUMN IF NOT EXISTS price_control_score NUMERIC(8,6),
    ADD COLUMN IF NOT EXISTS crowding_score NUMERIC(8,6),
    ADD COLUMN IF NOT EXISTS trap_score NUMERIC(8,6),
    ADD COLUMN IF NOT EXISTS expected_direction VARCHAR(16),
    ADD COLUMN IF NOT EXISTS path_type VARCHAR(40),
    ADD COLUMN IF NOT EXISTS t1_probability NUMERIC(8,6),
    ADD COLUMN IF NOT EXISTS t3_probability NUMERIC(8,6),
    ADD COLUMN IF NOT EXISTS t5_probability NUMERIC(8,6),
    ADD COLUMN IF NOT EXISTS capital_thesis TEXT,
    ADD COLUMN IF NOT EXISTS invalidation_condition TEXT;

ALTER TABLE tickets
    ADD COLUMN IF NOT EXISTS capital_quality NUMERIC(8,6),
    ADD COLUMN IF NOT EXISTS quality_label VARCHAR(40),
    ADD COLUMN IF NOT EXISTS absorption_efficiency NUMERIC(8,6),
    ADD COLUMN IF NOT EXISTS absorption_persistence NUMERIC(8,6),
    ADD COLUMN IF NOT EXISTS upside_control_efficiency NUMERIC(8,6),
    ADD COLUMN IF NOT EXISTS downside_control_efficiency NUMERIC(8,6),
    ADD COLUMN IF NOT EXISTS control_asymmetry NUMERIC(8,6),
    ADD COLUMN IF NOT EXISTS distribution_probability NUMERIC(8,6),
    ADD COLUMN IF NOT EXISTS distribution_stage VARCHAR(32),
    ADD COLUMN IF NOT EXISTS distribution_acceleration NUMERIC(8,6),
    ADD COLUMN IF NOT EXISTS distribution_transition_risk NUMERIC(8,6),
    ADD COLUMN IF NOT EXISTS trap_probability NUMERIC(8,6),
    ADD COLUMN IF NOT EXISTS transition_score NUMERIC(8,6),
    ADD COLUMN IF NOT EXISTS late_state_risk NUMERIC(8,6),
    ADD COLUMN IF NOT EXISTS state_age_score NUMERIC(8,6),
    ADD COLUMN IF NOT EXISTS intent_probability NUMERIC(8,6),
    ADD COLUMN IF NOT EXISTS intent_probabilities JSONB,
    ADD COLUMN IF NOT EXISTS transition_probabilities JSONB,
    ADD COLUMN IF NOT EXISTS path_distribution JSONB;

ALTER TABLE forward_tracking
    ADD COLUMN IF NOT EXISTS capital_model_version VARCHAR(64),
    ADD COLUMN IF NOT EXISTS capital_validation_status VARCHAR(64),
    ADD COLUMN IF NOT EXISTS capital_state_at_entry VARCHAR(40),
    ADD COLUMN IF NOT EXISTS capital_intent_at_entry VARCHAR(40),
    ADD COLUMN IF NOT EXISTS capital_strength_at_entry NUMERIC(8,6),
    ADD COLUMN IF NOT EXISTS capital_score_at_entry NUMERIC(8,6),
    ADD COLUMN IF NOT EXISTS distribution_score_at_entry NUMERIC(8,6),
    ADD COLUMN IF NOT EXISTS trap_score_at_entry NUMERIC(8,6),
    ADD COLUMN IF NOT EXISTS predicted_path VARCHAR(40),
    ADD COLUMN IF NOT EXISTS state_after_1d VARCHAR(40),
    ADD COLUMN IF NOT EXISTS state_after_3d VARCHAR(40),
    ADD COLUMN IF NOT EXISTS state_after_5d VARCHAR(40),
    ADD COLUMN IF NOT EXISTS state_after_10d VARCHAR(40),
    ADD COLUMN IF NOT EXISTS return_1d NUMERIC(10,6),
    ADD COLUMN IF NOT EXISTS return_3d NUMERIC(10,6),
    ADD COLUMN IF NOT EXISTS return_5d NUMERIC(10,6),
    ADD COLUMN IF NOT EXISTS return_10d NUMERIC(10,6),
    ADD COLUMN IF NOT EXISTS path_after_1d VARCHAR(40),
    ADD COLUMN IF NOT EXISTS path_after_3d VARCHAR(40),
    ADD COLUMN IF NOT EXISTS path_after_5d VARCHAR(40),
    ADD COLUMN IF NOT EXISTS path_after_10d VARCHAR(40),
    ADD COLUMN IF NOT EXISTS transition_label VARCHAR(96),
    ADD COLUMN IF NOT EXISTS label_version VARCHAR(64),
    ADD COLUMN IF NOT EXISTS actual_path VARCHAR(40),
    ADD COLUMN IF NOT EXISTS actual_intent_proxy VARCHAR(40),
    ADD COLUMN IF NOT EXISTS actual_intent_semantic VARCHAR(32),
    ADD COLUMN IF NOT EXISTS state_correct BOOLEAN,
    ADD COLUMN IF NOT EXISTS intent_correct BOOLEAN,
    ADD COLUMN IF NOT EXISTS path_correct BOOLEAN;

ALTER TABLE forward_tracking
    ADD COLUMN IF NOT EXISTS capital_quality_at_entry NUMERIC(8,6),
    ADD COLUMN IF NOT EXISTS distribution_probability_at_entry NUMERIC(8,6),
    ADD COLUMN IF NOT EXISTS trap_probability_at_entry NUMERIC(8,6),
    ADD COLUMN IF NOT EXISTS quality_label_at_entry VARCHAR(40),
    ADD COLUMN IF NOT EXISTS intent_probability_at_entry NUMERIC(8,6),
    ADD COLUMN IF NOT EXISTS path_distribution_at_entry JSONB;

CREATE TABLE IF NOT EXISTS capital_daily_snapshot (
    id BIGSERIAL PRIMARY KEY,
    symbol VARCHAR(10) NOT NULL,
    as_of_date DATE NOT NULL,
    research_run_id INTEGER NOT NULL REFERENCES research_runs(run_id),
    model_version VARCHAR(64) NOT NULL,
    data_version VARCHAR(64) NOT NULL,
    validation_status VARCHAR(64) NOT NULL,
    statistical_score NUMERIC(8,6),
    capital_score NUMERIC(8,6),
    combined_score NUMERIC(8,6),
    capital_strength NUMERIC(8,6),
    dominant_direction VARCHAR(16),
    dominant_pressure NUMERIC(8,6),
    distribution_risk NUMERIC(8,6),
    trap_risk NUMERIC(8,6),
    capital_quality NUMERIC(8,6),
    quality_label VARCHAR(40),
    absorption_score NUMERIC(8,6),
    absorption_efficiency NUMERIC(8,6),
    absorption_persistence NUMERIC(8,6),
    upside_control_efficiency NUMERIC(8,6),
    downside_control_efficiency NUMERIC(8,6),
    control_asymmetry NUMERIC(8,6),
    control_regime VARCHAR(16),
    control_collapse_score NUMERIC(8,6),
    distribution_probability NUMERIC(8,6),
    distribution_stage VARCHAR(32),
    distribution_acceleration NUMERIC(8,6),
    distribution_transition_risk NUMERIC(8,6),
    trap_probability NUMERIC(8,6),
    transition_score NUMERIC(8,6),
    transition_acceleration NUMERIC(8,6),
    state_age_score NUMERIC(8,6),
    late_state_risk NUMERIC(8,6),
    intent_probability NUMERIC(8,6),
    intent_probabilities JSONB,
    transition_probabilities JSONB,
    path_distribution JSONB,
    evidence_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    UNIQUE(symbol, as_of_date, research_run_id)
);

ALTER TABLE capital_daily_snapshot
    ADD COLUMN IF NOT EXISTS capital_quality NUMERIC(8,6),
    ADD COLUMN IF NOT EXISTS quality_label VARCHAR(40),
    ADD COLUMN IF NOT EXISTS absorption_score NUMERIC(8,6),
    ADD COLUMN IF NOT EXISTS absorption_efficiency NUMERIC(8,6),
    ADD COLUMN IF NOT EXISTS absorption_persistence NUMERIC(8,6),
    ADD COLUMN IF NOT EXISTS upside_control_efficiency NUMERIC(8,6),
    ADD COLUMN IF NOT EXISTS downside_control_efficiency NUMERIC(8,6),
    ADD COLUMN IF NOT EXISTS control_asymmetry NUMERIC(8,6),
    ADD COLUMN IF NOT EXISTS control_regime VARCHAR(16),
    ADD COLUMN IF NOT EXISTS control_collapse_score NUMERIC(8,6),
    ADD COLUMN IF NOT EXISTS distribution_probability NUMERIC(8,6),
    ADD COLUMN IF NOT EXISTS distribution_stage VARCHAR(32),
    ADD COLUMN IF NOT EXISTS distribution_acceleration NUMERIC(8,6),
    ADD COLUMN IF NOT EXISTS distribution_transition_risk NUMERIC(8,6),
    ADD COLUMN IF NOT EXISTS trap_probability NUMERIC(8,6),
    ADD COLUMN IF NOT EXISTS transition_score NUMERIC(8,6),
    ADD COLUMN IF NOT EXISTS transition_acceleration NUMERIC(8,6),
    ADD COLUMN IF NOT EXISTS state_age_score NUMERIC(8,6),
    ADD COLUMN IF NOT EXISTS late_state_risk NUMERIC(8,6),
    ADD COLUMN IF NOT EXISTS intent_probability NUMERIC(8,6),
    ADD COLUMN IF NOT EXISTS intent_probabilities JSONB,
    ADD COLUMN IF NOT EXISTS transition_probabilities JSONB,
    ADD COLUMN IF NOT EXISTS path_distribution JSONB;

CREATE TABLE IF NOT EXISTS capital_evidence (
    id BIGSERIAL PRIMARY KEY,
    symbol VARCHAR(10) NOT NULL,
    as_of_date DATE NOT NULL,
    research_run_id INTEGER NOT NULL REFERENCES research_runs(run_id),
    model_version VARCHAR(64) NOT NULL,
    data_version VARCHAR(64) NOT NULL,
    evidence_type VARCHAR(64) NOT NULL,
    value NUMERIC(8,6),
    confidence NUMERIC(8,6),
    availability VARCHAR(40) NOT NULL,
    source VARCHAR(128),
    lookback VARCHAR(64),
    semantic VARCHAR(16) NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    UNIQUE(symbol, as_of_date, research_run_id, evidence_type)
);

CREATE TABLE IF NOT EXISTS capital_state_history (
    id BIGSERIAL PRIMARY KEY,
    symbol VARCHAR(10) NOT NULL,
    as_of_date DATE NOT NULL,
    research_run_id INTEGER NOT NULL REFERENCES research_runs(run_id),
    model_version VARCHAR(64) NOT NULL,
    data_version VARCHAR(64) NOT NULL,
    capital_state VARCHAR(40) NOT NULL,
    previous_capital_state VARCHAR(40),
    state_transition VARCHAR(96),
    state_duration INTEGER NOT NULL DEFAULT 0,
    state_confidence NUMERIC(8,6),
    state_reason TEXT,
    state_momentum NUMERIC(8,6),
    transition_score NUMERIC(8,6),
    transition_acceleration NUMERIC(8,6),
    evidence_persistence NUMERIC(8,6),
    expected_duration INTEGER,
    duration_percentile NUMERIC(8,6),
    late_state_risk NUMERIC(8,6),
    state_age_score NUMERIC(8,6),
    transition_probabilities JSONB,
    transition_matrix JSONB,
    semantic VARCHAR(16) NOT NULL DEFAULT 'INFERRED',
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    UNIQUE(symbol, as_of_date, research_run_id)
);

ALTER TABLE capital_state_history
    ADD COLUMN IF NOT EXISTS state_momentum NUMERIC(8,6),
    ADD COLUMN IF NOT EXISTS transition_score NUMERIC(8,6),
    ADD COLUMN IF NOT EXISTS transition_acceleration NUMERIC(8,6),
    ADD COLUMN IF NOT EXISTS evidence_persistence NUMERIC(8,6),
    ADD COLUMN IF NOT EXISTS expected_duration INTEGER,
    ADD COLUMN IF NOT EXISTS duration_percentile NUMERIC(8,6),
    ADD COLUMN IF NOT EXISTS late_state_risk NUMERIC(8,6),
    ADD COLUMN IF NOT EXISTS state_age_score NUMERIC(8,6),
    ADD COLUMN IF NOT EXISTS transition_probabilities JSONB,
    ADD COLUMN IF NOT EXISTS transition_matrix JSONB;

CREATE TABLE IF NOT EXISTS capital_intent (
    id BIGSERIAL PRIMARY KEY,
    symbol VARCHAR(10) NOT NULL,
    as_of_date DATE NOT NULL,
    research_run_id INTEGER NOT NULL REFERENCES research_runs(run_id),
    model_version VARCHAR(64) NOT NULL,
    data_version VARCHAR(64) NOT NULL,
    capital_intent VARCHAR(40) NOT NULL,
    intent_confidence NUMERIC(8,6),
    expected_direction VARCHAR(16),
    continuation_condition TEXT,
    invalidation_condition TEXT,
    intent_probability NUMERIC(8,6),
    intent_probabilities JSONB,
    intent_alternatives JSONB,
    previous_intent VARCHAR(40),
    current_intent VARCHAR(40),
    intent_transition VARCHAR(96),
    semantic VARCHAR(16) NOT NULL DEFAULT 'INFERRED',
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    UNIQUE(symbol, as_of_date, research_run_id)
);

ALTER TABLE capital_intent
    ADD COLUMN IF NOT EXISTS intent_probability NUMERIC(8,6),
    ADD COLUMN IF NOT EXISTS intent_probabilities JSONB,
    ADD COLUMN IF NOT EXISTS intent_alternatives JSONB,
    ADD COLUMN IF NOT EXISTS previous_intent VARCHAR(40),
    ADD COLUMN IF NOT EXISTS current_intent VARCHAR(40),
    ADD COLUMN IF NOT EXISTS intent_transition VARCHAR(96);

CREATE TABLE IF NOT EXISTS capital_path_prediction (
    id BIGSERIAL PRIMARY KEY,
    symbol VARCHAR(10) NOT NULL,
    as_of_date DATE NOT NULL,
    research_run_id INTEGER NOT NULL REFERENCES research_runs(run_id),
    model_version VARCHAR(64) NOT NULL,
    data_version VARCHAR(64) NOT NULL,
    path_type VARCHAR(40) NOT NULL,
    t1_probability NUMERIC(8,6),
    t3_probability NUMERIC(8,6),
    t5_probability NUMERIC(8,6),
    path_confidence NUMERIC(8,6),
    path_distribution JSONB,
    path_sequence JSONB,
    path_invalidation JSONB,
    semantic VARCHAR(16) NOT NULL DEFAULT 'PREDICTED',
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    UNIQUE(symbol, as_of_date, research_run_id)
);

ALTER TABLE capital_path_prediction
    ADD COLUMN IF NOT EXISTS path_distribution JSONB,
    ADD COLUMN IF NOT EXISTS path_sequence JSONB,
    ADD COLUMN IF NOT EXISTS path_invalidation JSONB;

CREATE TABLE IF NOT EXISTS capital_prediction_outcome (
    id BIGSERIAL PRIMARY KEY,
    forward_tracking_id INTEGER NOT NULL REFERENCES forward_tracking(id),
    symbol VARCHAR(10) NOT NULL,
    as_of_date DATE NOT NULL,
    research_run_id INTEGER REFERENCES research_runs(run_id),
    model_version VARCHAR(64),
    data_version VARCHAR(64),
    state_after_1d VARCHAR(40),
    state_after_3d VARCHAR(40),
    state_after_5d VARCHAR(40),
    actual_path VARCHAR(40),
    actual_intent_proxy VARCHAR(40),
    actual_intent_semantic VARCHAR(32),
    state_correct BOOLEAN,
    intent_correct BOOLEAN,
    path_correct BOOLEAN,
    semantic VARCHAR(16) NOT NULL DEFAULT 'DERIVED',
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW(),
    UNIQUE(forward_tracking_id)
);

ALTER TABLE capital_prediction_outcome
    ADD COLUMN IF NOT EXISTS actual_intent_proxy VARCHAR(40),
    ADD COLUMN IF NOT EXISTS actual_intent_semantic VARCHAR(32);

CREATE INDEX IF NOT EXISTS idx_capital_daily_snapshot_symbol_date
    ON capital_daily_snapshot(symbol, as_of_date DESC);
CREATE INDEX IF NOT EXISTS idx_capital_state_history_symbol_date
    ON capital_state_history(symbol, as_of_date DESC);
CREATE INDEX IF NOT EXISTS idx_capital_path_prediction_symbol_date
    ON capital_path_prediction(symbol, as_of_date DESC);
CREATE INDEX IF NOT EXISTS idx_capital_prediction_outcome_symbol_date
    ON capital_prediction_outcome(symbol, as_of_date DESC);

-- 11. Capital Behavior V3 empirical dataset and audit projections. These
-- tables are research-only and never participate in production ranking.
CREATE TABLE IF NOT EXISTS capital_behavior_dataset (
    id BIGSERIAL PRIMARY KEY,
    symbol VARCHAR(10) NOT NULL,
    as_of_date DATE NOT NULL,
    research_run_id INTEGER NOT NULL REFERENCES research_runs(run_id),
    data_version VARCHAR(64) NOT NULL,
    model_version VARCHAR(64) NOT NULL,
    feature_version VARCHAR(64) NOT NULL,
    label_version VARCHAR(64),
    capital_model_version VARCHAR(64),
    state_model_version VARCHAR(64),
    intent_model_version VARCHAR(64),
    path_model_version VARCHAR(64),
    calibration_version VARCHAR(64),
    price NUMERIC(12,4),
    volume BIGINT,
    liquidity NUMERIC(12,6),
    upward_pressure NUMERIC(8,6),
    downward_pressure NUMERIC(8,6),
    selling_activity NUMERIC(8,6),
    price_damage NUMERIC(8,6),
    expected_price_damage NUMERIC(8,6),
    damage_efficiency NUMERIC(8,6),
    absorption NUMERIC(8,6),
    absorption_efficiency NUMERIC(8,6),
    absorption_persistence NUMERIC(8,6),
    absorption_failure NUMERIC(8,6),
    demand_persistence NUMERIC(8,6),
    supply_exhaustion NUMERIC(8,6),
    markup NUMERIC(8,6),
    distribution NUMERIC(8,6),
    crowding NUMERIC(8,6),
    trap NUMERIC(8,6),
    price_response_efficiency NUMERIC(8,6),
    upside_control_efficiency NUMERIC(8,6),
    downside_control_efficiency NUMERIC(8,6),
    control_asymmetry NUMERIC(8,6),
    control_collapse NUMERIC(8,6),
    capital_state VARCHAR(40),
    capital_state_confidence NUMERIC(8,6),
    capital_intent VARCHAR(40),
    intent_probability NUMERIC(8,6),
    capital_strength NUMERIC(8,6),
    capital_quality NUMERIC(8,6),
    path_distribution_t1 JSONB NOT NULL DEFAULT '{}'::jsonb,
    path_distribution_t3 JSONB NOT NULL DEFAULT '{}'::jsonb,
    path_distribution_t5 JSONB NOT NULL DEFAULT '{}'::jsonb,
    observed_inputs JSONB NOT NULL DEFAULT '{}'::jsonb,
    derived_features JSONB NOT NULL DEFAULT '{}'::jsonb,
    inferred_state JSONB NOT NULL DEFAULT '{}'::jsonb,
    inferred_intent JSONB NOT NULL DEFAULT '{}'::jsonb,
    predicted_path JSONB NOT NULL DEFAULT '{}'::jsonb,
    future_outcome JSONB NOT NULL DEFAULT '{}'::jsonb,
    source_lineage JSONB NOT NULL DEFAULT '{}'::jsonb,
    eligible_for_training BOOLEAN NOT NULL DEFAULT FALSE,
    eligible_for_validation BOOLEAN NOT NULL DEFAULT FALSE,
    eligible_for_test BOOLEAN NOT NULL DEFAULT FALSE,
    eligibility_reason VARCHAR(64) NOT NULL,
    dataset_split VARCHAR(16),
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW(),
    UNIQUE(symbol, as_of_date, research_run_id, model_version)
);

CREATE INDEX IF NOT EXISTS idx_capital_dataset_date
    ON capital_behavior_dataset(as_of_date, symbol);
CREATE INDEX IF NOT EXISTS idx_capital_dataset_split
    ON capital_behavior_dataset(dataset_split, eligible_for_training, eligible_for_validation, eligible_for_test);
CREATE INDEX IF NOT EXISTS idx_capital_dataset_state
    ON capital_behavior_dataset(capital_state, as_of_date);

CREATE TABLE IF NOT EXISTS capital_prediction_error (
    id BIGSERIAL PRIMARY KEY,
    dataset_sample_id BIGINT REFERENCES capital_behavior_dataset(id),
    model_version VARCHAR(64) NOT NULL,
    prediction_date DATE NOT NULL,
    symbol VARCHAR(10) NOT NULL,
    predicted_state VARCHAR(40),
    actual_state VARCHAR(40),
    predicted_intent VARCHAR(40),
    actual_intent_proxy VARCHAR(40),
    predicted_path VARCHAR(40),
    actual_path VARCHAR(40),
    error_type VARCHAR(64) NOT NULL,
    error_magnitude NUMERIC(12,6),
    confidence NUMERIC(8,6),
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    UNIQUE(dataset_sample_id, error_type)
);

CREATE INDEX IF NOT EXISTS idx_capital_prediction_error_symbol_date
    ON capital_prediction_error(symbol, prediction_date DESC);
CREATE INDEX IF NOT EXISTS idx_capital_prediction_error_type
    ON capital_prediction_error(error_type, prediction_date DESC);

CREATE TABLE IF NOT EXISTS capital_model_drift (
    id BIGSERIAL PRIMARY KEY,
    model_version VARCHAR(64) NOT NULL,
    window_start DATE,
    window_end DATE,
    status VARCHAR(32) NOT NULL,
    state_accuracy NUMERIC(8,6),
    path_accuracy NUMERIC(8,6),
    calibration_error NUMERIC(8,6),
    distribution_warning_precision NUMERIC(8,6),
    metrics JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    UNIQUE(model_version, window_start, window_end)
);

ALTER TABLE capital_prediction_outcome
    ADD COLUMN IF NOT EXISTS state_after_10d VARCHAR(40),
    ADD COLUMN IF NOT EXISTS return_1d NUMERIC(10,6),
    ADD COLUMN IF NOT EXISTS return_3d NUMERIC(10,6),
    ADD COLUMN IF NOT EXISTS return_5d NUMERIC(10,6),
    ADD COLUMN IF NOT EXISTS return_10d NUMERIC(10,6),
    ADD COLUMN IF NOT EXISTS path_after_1d VARCHAR(40),
    ADD COLUMN IF NOT EXISTS path_after_3d VARCHAR(40),
    ADD COLUMN IF NOT EXISTS path_after_5d VARCHAR(40),
    ADD COLUMN IF NOT EXISTS path_after_10d VARCHAR(40),
    ADD COLUMN IF NOT EXISTS transition_label VARCHAR(96),
    ADD COLUMN IF NOT EXISTS label_version VARCHAR(64);

-- 10. Intraday paper strategy lifecycle. These records intentionally do not
-- reuse ticket-bound tables: daily tickets and intraday decisions have
-- different time semantics and lineage requirements.
CREATE TABLE IF NOT EXISTS intraday_strategy_runs (
    id BIGSERIAL PRIMARY KEY,
    session_date DATE NOT NULL,
    strategy_version VARCHAR(64) NOT NULL,
    context_research_run_id INTEGER REFERENCES research_runs(run_id),
    status VARCHAR(32) NOT NULL,
    candidate_count INTEGER NOT NULL DEFAULT 0,
    source_state JSONB NOT NULL DEFAULT '{}'::jsonb,
    started_at TIMESTAMP NOT NULL DEFAULT NOW(),
    finished_at TIMESTAMP,
    error_message TEXT
);

CREATE TABLE IF NOT EXISTS intraday_strategy_decisions (
    id BIGSERIAL PRIMARY KEY,
    run_id BIGINT NOT NULL REFERENCES intraday_strategy_runs(id) ON DELETE CASCADE,
    session_date DATE NOT NULL,
    symbol VARCHAR(10) NOT NULL,
    direction VARCHAR(8) NOT NULL DEFAULT 'LONG'
        CHECK (direction IN ('LONG', 'SHORT')),
    decision VARCHAR(32) NOT NULL,
    decision_status VARCHAR(32) NOT NULL,
    strategy_score NUMERIC(8, 6),
    score_components JSONB NOT NULL DEFAULT '{}'::jsonb,
    quote_snapshot JSONB NOT NULL DEFAULT '{}'::jsonb,
    quote_source VARCHAR(64),
    quote_age_seconds NUMERIC(12, 3),
    context_research_run_id INTEGER REFERENCES research_runs(run_id),
    reason TEXT,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    UNIQUE(run_id, symbol, direction)
);

ALTER TABLE intraday_strategy_decisions
    ADD COLUMN IF NOT EXISTS direction VARCHAR(8) NOT NULL DEFAULT 'LONG';
ALTER TABLE intraday_strategy_decisions
    DROP CONSTRAINT IF EXISTS intraday_strategy_decisions_direction_check;
ALTER TABLE intraday_strategy_decisions
    ADD CONSTRAINT intraday_strategy_decisions_direction_check
    CHECK (direction IN ('LONG', 'SHORT'));
ALTER TABLE intraday_strategy_decisions
    DROP CONSTRAINT IF EXISTS intraday_strategy_decisions_run_id_symbol_key;
CREATE UNIQUE INDEX IF NOT EXISTS idx_intraday_strategy_decisions_run_symbol_direction
    ON intraday_strategy_decisions(run_id, symbol, direction);

CREATE TABLE IF NOT EXISTS intraday_paper_positions (
    id BIGSERIAL PRIMARY KEY,
    decision_id BIGINT NOT NULL REFERENCES intraday_strategy_decisions(id),
    session_date DATE NOT NULL,
    symbol VARCHAR(10) NOT NULL,
    direction VARCHAR(8) NOT NULL DEFAULT 'LONG'
        CHECK (direction IN ('LONG', 'SHORT')),
    status VARCHAR(16) NOT NULL DEFAULT 'OPEN',
    entry_price NUMERIC(12, 4) NOT NULL,
    current_price NUMERIC(12, 4) NOT NULL,
    quantity NUMERIC(12, 6) NOT NULL,
    stop_loss_price NUMERIC(12, 4) NOT NULL,
    take_profit_price NUMERIC(12, 4) NOT NULL,
    exit_price NUMERIC(12, 4),
    exit_reason VARCHAR(32),
    realized_pnl NUMERIC(12, 2),
    entry_fees NUMERIC(12, 4) NOT NULL DEFAULT 0,
    exit_fees NUMERIC(12, 4) NOT NULL DEFAULT 0,
    borrow_rate_daily NUMERIC(12, 8) NOT NULL DEFAULT 0,
    accrued_borrow_cost NUMERIC(12, 4) NOT NULL DEFAULT 0,
    squeeze_risk_score NUMERIC(8, 6),
    source_snapshot JSONB NOT NULL DEFAULT '{}'::jsonb,
    opened_at TIMESTAMP NOT NULL DEFAULT NOW(),
    closed_at TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT NOW(),
    UNIQUE(session_date, symbol)
);

ALTER TABLE intraday_paper_positions
    ADD COLUMN IF NOT EXISTS entry_fees NUMERIC(12, 4) NOT NULL DEFAULT 0,
    ADD COLUMN IF NOT EXISTS exit_fees NUMERIC(12, 4) NOT NULL DEFAULT 0,
    ADD COLUMN IF NOT EXISTS direction VARCHAR(8) NOT NULL DEFAULT 'LONG',
    ADD COLUMN IF NOT EXISTS borrow_rate_daily NUMERIC(12, 8) NOT NULL DEFAULT 0,
    ADD COLUMN IF NOT EXISTS accrued_borrow_cost NUMERIC(12, 4) NOT NULL DEFAULT 0,
    ADD COLUMN IF NOT EXISTS squeeze_risk_score NUMERIC(8, 6);

ALTER TABLE intraday_paper_positions
    DROP CONSTRAINT IF EXISTS intraday_paper_positions_direction_check;
ALTER TABLE intraday_paper_positions
    ADD CONSTRAINT intraday_paper_positions_direction_check
    CHECK (direction IN ('LONG', 'SHORT'));

CREATE TABLE IF NOT EXISTS intraday_paper_orders (
    id BIGSERIAL PRIMARY KEY,
    decision_id BIGINT NOT NULL REFERENCES intraday_strategy_decisions(id),
    position_id BIGINT REFERENCES intraday_paper_positions(id),
    session_date DATE NOT NULL,
    symbol VARCHAR(10) NOT NULL,
    side VARCHAR(16) NOT NULL CHECK (
        side IN ('LONG_ENTRY', 'LONG_EXIT', 'SHORT_ENTRY', 'SHORT_EXIT')
    ),
    order_type VARCHAR(16) NOT NULL CHECK (order_type IN ('MARKET', 'LIMIT', 'STOP')),
    requested_quantity NUMERIC(12, 6) NOT NULL,
    remaining_quantity NUMERIC(12, 6) NOT NULL,
    limit_price NUMERIC(12, 4),
    stop_price NUMERIC(12, 4),
    status VARCHAR(16) NOT NULL,
    reason TEXT NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW()
);

ALTER TABLE intraday_paper_orders
    DROP CONSTRAINT IF EXISTS intraday_paper_orders_side_check;
ALTER TABLE intraday_paper_orders
    ADD CONSTRAINT intraday_paper_orders_side_check
    CHECK (side IN ('LONG_ENTRY', 'LONG_EXIT', 'SHORT_ENTRY', 'SHORT_EXIT'));

CREATE TABLE IF NOT EXISTS intraday_paper_fills (
    id BIGSERIAL PRIMARY KEY,
    order_id BIGINT NOT NULL REFERENCES intraday_paper_orders(id) ON DELETE CASCADE,
    decision_id BIGINT NOT NULL REFERENCES intraday_strategy_decisions(id),
    symbol VARCHAR(10) NOT NULL,
    quantity NUMERIC(12, 6) NOT NULL,
    price NUMERIC(12, 4) NOT NULL,
    commission NUMERIC(12, 4) NOT NULL,
    sec_fee NUMERIC(12, 4) NOT NULL DEFAULT 0,
    finra_fee NUMERIC(12, 4) NOT NULL DEFAULT 0,
    slippage NUMERIC(12, 4) NOT NULL,
    source_snapshot JSONB NOT NULL DEFAULT '{}'::jsonb,
    filled_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_intraday_strategy_runs_session
    ON intraday_strategy_runs(session_date, started_at DESC);
CREATE INDEX IF NOT EXISTS idx_intraday_strategy_decisions_symbol
    ON intraday_strategy_decisions(session_date, symbol, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_intraday_paper_positions_open
    ON intraday_paper_positions(status, session_date);
CREATE INDEX IF NOT EXISTS idx_intraday_paper_orders_open
    ON intraday_paper_orders(status, session_date, symbol);
CREATE INDEX IF NOT EXISTS idx_intraday_paper_fills_order
    ON intraday_paper_fills(order_id, filled_at);

-- Capital historical lineage audit. Recovers ticket → research_run without
-- mutating tickets.research_run_id. Ambiguous matches stay NULL.
CREATE TABLE IF NOT EXISTS capital_historical_lineage (
    ticket_id INTEGER PRIMARY KEY REFERENCES tickets(id),
    research_run_id INTEGER REFERENCES research_runs(run_id),
    lineage_status VARCHAR(32) NOT NULL,
    lineage_method VARCHAR(64),
    lineage_source VARCHAR(64) NOT NULL,
    confidence NUMERIC(6, 4) NOT NULL DEFAULT 0,
    evidence JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_capital_historical_lineage_run
    ON capital_historical_lineage(research_run_id);

CREATE INDEX IF NOT EXISTS idx_capital_historical_lineage_status
    ON capital_historical_lineage(lineage_status);

-- As-of historical OHLCV for Capital replay. Never written into daily_klines.
CREATE TABLE IF NOT EXISTS capital_historical_ohlcv (
    id BIGSERIAL PRIMARY KEY,
    symbol VARCHAR(10) NOT NULL,
    trade_date DATE NOT NULL,
    open NUMERIC(12, 4),
    high NUMERIC(12, 4),
    low NUMERIC(12, 4),
    close NUMERIC(12, 4),
    volume BIGINT,
    source_provider VARCHAR(64) NOT NULL,
    price_semantics VARCHAR(64) NOT NULL,
    adjustment_mode VARCHAR(32) NOT NULL,
    timezone VARCHAR(64) NOT NULL DEFAULT 'America/New_York',
    frequency VARCHAR(16) NOT NULL DEFAULT '1D',
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    UNIQUE(symbol, trade_date, source_provider)
);

CREATE INDEX IF NOT EXISTS idx_capital_historical_ohlcv_symbol_date
    ON capital_historical_ohlcv(symbol, trade_date);

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
    COALESCE(
        NULLIF(t.lifecycle_stage, ''),
        NULLIF(t.classification, ''),
        'ISSUED'
    )::text AS lifecycle_stage,
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
    COALESCE(
        NULLIF(t.lifecycle_stage, ''),
        NULLIF(t.classification, ''),
        'ISSUED'
    )::text,
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
    CASE
        WHEN t.id IS NULL THEN 'UNRESOLVED_NO_TICKET'
        ELSE COALESCE(
            NULLIF(t.lifecycle_stage, ''),
            NULLIF(t.classification, ''),
            'ISSUED'
        )
    END::text,
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
    CASE
        WHEN t.id IS NULL THEN 'UNRESOLVED_NO_TICKET'
        ELSE COALESCE(
            NULLIF(t.lifecycle_stage, ''),
            NULLIF(t.classification, ''),
            'ISSUED'
        )
    END::text,
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
