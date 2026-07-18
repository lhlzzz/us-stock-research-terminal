# VERSION_LOG

## v1.0.0 - 2026-06-25 (Initial Release)

### Pipeline Core
- `us_profit_ticket_pipeline.py`: Main pipeline for US stock ticket generation
- `historical_replay_baseline.py`: Historical data fetch and universe management
- `eastmoney_us.py`: EastMoney US stock data API
- `backfill_forward_tracking.py`: Forward tracking backfill script
- `lifecycle_scoreboard.py`: Performance tracking scoreboard
- `market_regime.py`: Market regime detection
- `risk_manager.py`: Risk management module
- `research_panel.py`: Multi-framework research analysis

### Structured Signals (8 dimensions)
1. `volume_price_alignment`: Volume trend confirms price trend
2. `closing_consistency`: Consistent strong closes (5d rolling)
3. `momentum_health`: Positive acceleration with reasonable magnitude
4. `dollar_volume_quality`: High dollar volume = institutional interest
5. `trend_stability`: Low volatility relative to momentum
6. `fund_flow_momentum`: EastMoney main fund net inflow (f178)
7. `news_quality`: Evidence source diversity + relevance (from last30days)
8. `sector_propagation`: Sector-level momentum + evidence density

### Performance Optimizations
- **kline parallelization**: `download_history_batch` from ~670s to ~75s (9x speedup)
- **fund flow parallelization**: `fetch_fund_flow_scores` from serial to 16-thread parallel
- **evidence gate relaxation**: Market score ≥1.0 can bypass evidence requirements
- **backfill fix**: Include anchor_date itself in target_dates

### Scoring Formula
- `blended_score = raw_market_score * 0.6 + structured_score * 0.4`
- `ticket_score = market_score + catalyst_score + quality_bonus + news_quality * 0.1 + sector_propagation_bonus`
- Feedback penalties applied for consistently losing symbols

### Symbol Penalties
- STX: -0.06 (0% win rate, -5.35% avg)
- TER: -0.07 (0% win rate, -6.61% avg)
- SW: -0.03 (20% win rate, -1.44% avg)
- SWK: -0.04 (0% win rate, -3.14% avg)
- ADBE: -0.05 (0% win rate)
- ALNY: -0.05 (0% win rate)
- CPB: -0.05 (0% win rate)
- KIM: -0.0417 (17% win rate)

### Market Regime
- ACTIVE: Moderate accel gate, balanced risk
- Scoring weights: RS 0.45, VWM 0.30, accel -0.15, mom 0.10
- Exhaustion threshold: -0.22
- Position cap: 12%

### Lifecycle Performance (as of 2026-06-25)
- **PAPER_REVIEW**: 62.3% win rate, -0.10% avg return
- **WATCHLIST**: 34.8% win rate, -3.31% avg return
- Overall: 51.3% win rate, -1.38% avg return

### Key Files Modified
- `scripts/historical_replay_baseline.py:340` - Parallel kline fetching
- `scripts/us_profit_ticket_pipeline.py:918` - Parallel fund flow fetching
- `scripts/us_profit_ticket_pipeline.py:1015` - Structured scores with 8 signals
- `scripts/us_profit_ticket_pipeline.py:1516` - Relaxed evidence gate
- `scripts/us_profit_ticket_pipeline.py:2395` - Evidence collection + news_quality + sector_propagation
- `scripts/backfill_forward_tracking.py:170` - Fixed target_dates to include anchor_date
- `research/backtest-review-feedback.json` - Symbol penalties

### Output Artifacts
- `summary-{date}.md`: Human-readable summary
- `metrics-{date}.json`: Machine-readable metrics
- `candidates-{date}.csv`: Candidate details with all signals
- `forward-tracking-{date}.csv`: Forward tracking with due dates
- `runtime-decision-context-{date}.json`: Decision context
- `runtime-decision-ledger.jsonl`: Append-only decision log
