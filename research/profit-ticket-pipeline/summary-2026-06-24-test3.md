# XIAOMEI US Profit Ticket Pipeline V0

RESEARCH_ONLY
NOT_TRADING_ADVICE
NO_BROKER
NO_ORDER
NO_LEDGER
NO_LIVE_TRADE

- output_date: 2026-06-24-test3
- as_of_date: 2026-06-22
- market_data_source: EastMoney US historical kline (via akshare) + EastMoney US realtime quote
- kline_source: EastMoney US historical kline
- quote_source: EastMoney US realtime/delayed quote + kline
- data_source_mismatch_threshold: 0.01
- eastmoney_required_tabs: us_quote_center
- eastmoney_enhanced_tabs: us_quote_detail, us_quote_news, us_quote_company
- eastmoney_evidence_domains: market_overview, quote_detail, company_detail, news_detail
- research_only: true
- allow_trade: false
- auto_order: false
- no_broker_api: true
- universe_source: explicit
- source_mode: live
- data_mode: historical_kline
- universe_key: explicit
- universe_total_symbols: 1
- universe_included_symbols: 1
- period_used: 1y
- classification: CANDIDATE_FOR_PAPER_REVIEW
- candidate_pool_size: 1
- top_k: 1
- paper_review_count: 1
- market_watchlist_count: 0
- zero_paper_review_is_valid_output: False
- artifact_summary: /root/hermes/company-ai-system/workspaces/xiaomei/research/profit-ticket-pipeline/summary-2026-06-24-test3.md
- artifact_metrics: /root/hermes/company-ai-system/workspaces/xiaomei/research/profit-ticket-pipeline/metrics-2026-06-24-test3.json
- artifact_candidates: /root/hermes/company-ai-system/workspaces/xiaomei/research/profit-ticket-pipeline/candidates-2026-06-24-test3.csv
- artifact_forward_tracking: /root/hermes/company-ai-system/workspaces/xiaomei/research/profit-ticket-pipeline/forward-tracking-2026-06-24-test3.csv
- artifact_runtime_context: /root/hermes/company-ai-system/workspaces/xiaomei/research/profit-ticket-pipeline/runtime-decision-context-2026-06-24-test3.json
- artifact_runtime_ledger: /root/hermes/company-ai-system/workspaces/xiaomei/research/profit-ticket-pipeline/runtime-decision-ledger.jsonl

## Backtest Feedback Applied
- feedback_win_rate: 64%
- symbol_penalties: ADBE, ALNY, CPB, KIM

## Market Regime: BALANCED
- breadth: 50.0% (stocks with positive 20d return)
- momentum: +0.00% (median 20d return)
- volatility: 0.0200 (median daily |return|)
- advance_ratio: 50.0% (1d advancers)
- description: Standard accel gate, tighter risk
- scoring_weights: {'prior_20d_momentum': 0.1, 'five_day_acceleration': -0.15, 'relative_strength_vs_equal_weight': 0.45, 'volume_weighted_momentum': 0.3, 'closing_strength_5d': 0.0, 'volume_confirmation_ratio': 0.0}
- exhaustion_threshold: -0.15
- position_cap: 10%
- min_market_score_gate: 0.55
- kelly_fraction_cap: 60%
- stop_loss_multiplier: 0.8x
- take_profit_multiplier: 1.2x
- risk_per_trade: 1.5%
- max_single_position: 8%
- max_total_exposure: 40%
- max_consecutive_losses: 2
- daily_max_loss_r: 2.5R
- default_stop_loss: 1.2%

## Methodology References
- UZI-Skill: risk checklist and multi-dimensional review
- TradingAgents: role-based research synthesis
- Serenity Skill: theme and supply-chain catalyst mapping
- Buffett Skills: quality, margin-of-safety, bear-case framing
- QuantDinger: replay discipline and data-health guardrails
- Factor Analysis (300-day IC): scoring weight optimization based on historical information coefficient

## Price-Volume Summary
- equal_weight_20d_benchmark: 0.2557130765975455
- median_20d_momentum: 0.2557130765975455
- median_5d_acceleration: -0.06667280410706256
- median_volume_confirmation: 1.6932672054489761
- median_relative_strength: 0.0
- top_market_score_p90: 1.0553427499383203

## Paper Review Candidates
|rank|symbol|company|latest|intraday|source_gap|market_score|catalyst_score|ticket_score|narrative|business|gate_status|
|---|---|---|---|---|---|---|---|---|---|---|---|
|1|MRNA|Moderna Inc|61.811|0.04155362709579569|0.0|1.0553427499383203|0.2375|1.3128427499383204|found_unrelated|found_relevant|CANDIDATE_FOR_PAPER_REVIEW|
  - ticket_card: research_only=true allow_trade=false auto_order=false no_broker_api=true
  - lifecycle_stage: paper_review_candidate
  - kline_source: EastMoney US historical kline
  - quote_source: EastMoney US realtime/delayed quote + kline | status=ok | prev_close=59.345 | cross_check_basis=prev_close | gap=0.0 | mismatch=false
  - eastmoney_tabs: detail=https://quote.eastmoney.com/us/MRNA.html | news=https://quote.eastmoney.com/us/MRNA.html#news | company=https://quote.eastmoney.com/us/MRNA.html#company
  - catalyst: Moderna just got a signal investors can’t ignore

## Market Watchlist Needs Evidence
- none

## Catalyst Summary
- candidates_with_narrative_relevant: 0
- candidates_with_business_relevant: 1
- top_shared_titles: [["Moderna just got a signal investors can’t ignore", 1]]

## Lifecycle Snapshot
- paper_review_candidates: 1
- market_watchlist_candidates: 0
- blocked_by_risk_candidates: 0
- best_watch_candidate: none
- best_watch_reason: none

## Evidence Gaps
### 1. MRNA
- company: Moderna Inc (eastmoney_us)
- narrative query: MRNA moderna stock catalyst earnings news
- business query: MRNA moderna orders demand backlog guidance revenue customer contract
- narrative ranked candidates: 1 | status: found_unrelated | returncode: 0
- business ranked candidates: 10 | status: found_relevant | returncode: 0
- evidence gap reason: paper_review_gate_passed

## Quality Check (Buffett Skills)
### MRNA: MODERATE (score=0.56)
  - roe: 0.00
  - pe_ttm: 1.00
  - dividend_yield: 0.00
  - price_position_52w: 0.78
  - liquidity_amount: 1.00

## Risk Checklist (UZI-Skill)
### MRNA: WATCH (red=0, yellow=2)
  - price_extended_vs_52w: [GREEN] latest/52w_high=91.2%
  - intraday_gap: [GREEN] intraday_pct_chg=4.16%
  - liquidity: [GREEN] amount=283,532,080
  - valuation: [GREEN] pe_ttm=3.31
  - quality_gap: [YELLOW] roe=-1673.00%
  - price_manipulation: [GREEN] 5d_accel=-0.0667
  - news_red_flags: [YELLOW] narrative_status=found_unrelated
  - supply_chain_risk: [GREEN] business_status=found_relevant
  - short_interest: [GREEN] provider_field_unavailable
  - dilution_risk: [GREEN] provider_field_unavailable
  - debt_covenant: [GREEN] provider_field_unavailable
  - earnings_quality: [GREEN] provider_field_unavailable
  - insider_selling: [GREEN] provider_field_unavailable
  - regulatory_risk: [GREEN] provider_field_unavailable
  - concentration_risk: [GREEN] provider_field_unavailable

## Research Panel (TradingAgents)
### MRNA: NEUTRAL (pos=2, neg=2)
  - fundamental_analyst: Quality verdict: MODERATE (score=0.56)
  - news_analyst: News status: found_unrelated, relevance=0.00
  - sentiment_analyst: Business/sentiment status: found_relevant, relevance=0.95
  - technical_analyst: Signals: strong_momentum, volume_confirmed
  - bull_case: Bull points: 3
  - bear_case: Bear points: 2
  - risk_manager: Risk: WATCH, Quality: MODERATE, Rec: PROCEED_WITH_MONITORING

## Supply Chain Map (Serenity Skill)
- MRNA: no_supply_chain_data | themes=[]

## Replay Hypothesis (QuantDinger)
- MRNA: Entry=pullback_entry, SL=-3.0%, TP=5.0%, Period=3d_5d, Conf=50%

## Risk Management (Cross-Platform Best Practices)
### MRNA: ALLOWED
  - stop_loss: $57.96
  - take_profit: $63.49
  - risk_reward: 2.00
  - kelly_fraction: 0.174
  - risk_score: N/A
  - confidence: 1.00

## Forward Tracking
|symbol|rank|horizon|due_date|status|
|---|---|---|---|---|
|MRNA|1|1d|2026-06-23|pending|
|MRNA|1|3d|2026-06-25|pending|
|MRNA|1|5d|2026-06-29|pending|
|MRNA|1|10d|2026-07-06|pending|

## Market Snapshot Top 10
- momentum_exhaustion_guard_threshold: -0.15
- momentum_exhaustion_guard_adjustment: -0.08
|rank|symbol|raw_market_score|market_score|rule|prior_20d|accel_5d|volume_confirm|closing_strength|vwmomentum|
|---|---|---|---|---|---|---|---|---|---|
|1|MRNA|1.192313829787234|1.0553427499383203||0.2557130765975455|-0.06667280410706256|1.6932672054489761|0.6390387983896992|0.4587835076394849|

## Final Classification
- CANDIDATE_FOR_PAPER_REVIEW
