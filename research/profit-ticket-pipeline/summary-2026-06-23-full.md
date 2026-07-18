# XIAOMEI US Profit Ticket Pipeline V0

RESEARCH_ONLY
NOT_TRADING_ADVICE
NO_BROKER
NO_ORDER
NO_LEDGER
NO_LIVE_TRADE

- output_date: 2026-06-23-full
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
- universe_total_symbols: 3
- universe_included_symbols: 3
- period_used: 1y
- classification: CANDIDATE_FOR_PAPER_REVIEW
- candidate_pool_size: 3
- top_k: 3
- paper_review_count: 1
- market_watchlist_count: 2
- zero_paper_review_is_valid_output: False
- artifact_summary: /root/hermes/company-ai-system/workspaces/xiaomei/research/profit-ticket-pipeline/summary-2026-06-23-full.md
- artifact_metrics: /root/hermes/company-ai-system/workspaces/xiaomei/research/profit-ticket-pipeline/metrics-2026-06-23-full.json
- artifact_candidates: /root/hermes/company-ai-system/workspaces/xiaomei/research/profit-ticket-pipeline/candidates-2026-06-23-full.csv
- artifact_forward_tracking: /root/hermes/company-ai-system/workspaces/xiaomei/research/profit-ticket-pipeline/forward-tracking-2026-06-23-full.csv
- artifact_runtime_context: /root/hermes/company-ai-system/workspaces/xiaomei/research/profit-ticket-pipeline/runtime-decision-context-2026-06-23-full.json
- artifact_runtime_ledger: /root/hermes/company-ai-system/workspaces/xiaomei/research/profit-ticket-pipeline/runtime-decision-ledger.jsonl

## Backtest Feedback Applied
- feedback_win_rate: 64%
- symbol_penalties: ADBE, ALNY, CPB, KIM

## Market Regime: BALANCED
- breadth: 50.0% (stocks with positive 20d return)
- momentum: +0.00% (median 20d return)
- volatility: 0.0200 (median daily |return|)
- advance_ratio: 50.0% (1d advancers)
- description: Relative strength dominant, acceleration reversed, tighter gates
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
- equal_weight_20d_benchmark: 0.25047388810536414
- median_20d_momentum: 0.2557130765975455
- median_5d_acceleration: -0.15491876918469716
- median_volume_confirmation: 0.9933267896002531
- median_relative_strength: 0.005239188492181357
- top_market_score_p90: 0.6606048673391398

## Paper Review Candidates
|rank|symbol|company|latest|intraday|source_gap|market_score|catalyst_score|ticket_score|narrative|business|gate_status|
|---|---|---|---|---|---|---|---|---|---|---|---|
|1|MRNA|Moderna Inc|59.345|-0.07215447154471544|0.0|0.6944564372045092|0.525|1.2394564372045092|found_relevant|found_relevant|CANDIDATE_FOR_PAPER_REVIEW|
  - ticket_card: research_only=true allow_trade=false auto_order=false no_broker_api=true
  - lifecycle_stage: paper_review_candidate
  - kline_source: EastMoney US historical kline
  - quote_source: EastMoney US realtime/delayed quote + kline | status=ok | prev_close=63.96 | cross_check_basis=latest_price | gap=0.0 | mismatch=false
  - eastmoney_tabs: detail=https://quote.eastmoney.com/us/MRNA.html | news=https://quote.eastmoney.com/us/MRNA.html#news | company=https://quote.eastmoney.com/us/MRNA.html#company
  - catalyst: Moderna Stock’s 6-Day Rally Ends in a Dive. Why It’s One of the S&P 500’s Biggest Losers Today.; Moderna just got a signal investors can’t ignore

## Market Watchlist Needs Evidence
|rank|symbol|company|latest|intraday|source_gap|market_score|catalyst_score|ticket_score|narrative|business|gate_status|
|---|---|---|---|---|---|---|---|---|---|---|---|
|2|TER|泰瑞达|457.0|0.043569601753745024|0.0|0.5251985878776622|0.1875|0.7626985878776622|found_relevant|found_unrelated|MOMENTUM_EXHAUSTION_HARD_BLOCK|
  - ticket_card: research_only=true allow_trade=false auto_order=false no_broker_api=true
  - lifecycle_stage: market_watchlist
  - kline_source: EastMoney US historical kline
  - quote_source: EastMoney US realtime/delayed quote + kline | status=ok | prev_close=437.92 | cross_check_basis=latest_price | gap=0.0 | mismatch=false
  - eastmoney_tabs: detail=https://quote.eastmoney.com/us/TER.html | news=https://quote.eastmoney.com/us/TER.html#news | company=https://quote.eastmoney.com/us/TER.html#company
  - catalyst: Stocks To Watch Echo AI Theme. GE Vernova Among Five Stocks Near Buy Points.
|3|SW|Smurfit WestRock plc|45.39|0.026923076923076827|0.0|0.08890102116134752|0.2375|0.3764010211613475|found_relevant|found_unrelated|MOMENTUM_EXHAUSTION_HARD_BLOCK|
  - ticket_card: research_only=true allow_trade=false auto_order=false no_broker_api=true
  - lifecycle_stage: market_watchlist
  - kline_source: EastMoney US historical kline
  - quote_source: EastMoney US realtime/delayed quote + kline | status=ok | prev_close=44.2 | cross_check_basis=latest_price | gap=0.0 | mismatch=false
  - eastmoney_tabs: detail=https://quote.eastmoney.com/us/SW.html | news=https://quote.eastmoney.com/us/SW.html#news | company=https://quote.eastmoney.com/us/SW.html#company
  - catalyst: Smurfit Westrock Announces the Completion of Delisting from the LSE

## Catalyst Summary
- candidates_with_narrative_relevant: 3
- candidates_with_business_relevant: 1
- top_shared_titles: [["Moderna Stock’s 6-Day Rally Ends in a Dive. Why It’s One of the S&P 500’s Biggest Losers Today.", 1], ["Moderna just got a signal investors can’t ignore", 1], ["Stocks To Watch Echo AI Theme. GE Vernova Among Five Stocks Near Buy Points.", 1], ["Smurfit Westrock Announces the Completion of Delisting from the LSE", 1]]

## Lifecycle Snapshot
- paper_review_candidates: 1
- market_watchlist_candidates: 2
- blocked_by_risk_candidates: 0
- best_watch_candidate: TER
- best_watch_reason: classification=MARKET_WATCHLIST_NEEDS_EVIDENCE; risk=ELEVATED; evidence=MOMENTUM_EXHAUSTION_HARD_BLOCK

## Evidence Gaps
### 1. MRNA
- company: Moderna Inc (eastmoney_us)
- narrative query: MRNA moderna stock catalyst earnings news
- business query: MRNA moderna orders demand backlog guidance revenue customer contract
- narrative ranked candidates: 10 | status: found_relevant | returncode: 124
- business ranked candidates: 10 | status: found_relevant | returncode: 124
- evidence gap reason: paper_review_gate_passed
### 2. TER
- company: 泰瑞达 (eastmoney_us)
- narrative query: TER 泰瑞达 stock catalyst earnings news
- business query: TER 泰瑞达 orders demand backlog guidance revenue customer contract
- narrative ranked candidates: 10 | status: found_relevant | returncode: 124
- business ranked candidates: 10 | status: found_unrelated | returncode: 124
- evidence gap reason: paper_review_gate_passed
### 3. SW
- company: Smurfit WestRock plc (eastmoney_us)
- narrative query: SW smurfit westrock stock catalyst earnings news
- business query: SW smurfit westrock orders demand backlog guidance revenue customer contract
- narrative ranked candidates: 10 | status: found_relevant | returncode: 124
- business ranked candidates: 10 | status: found_unrelated | returncode: 124
- evidence gap reason: paper_review_gate_passed

## Quality Check (Buffett Skills)
### MRNA: MODERATE (score=0.57)
  - roe: 0.00
  - pe_ttm: 1.00
  - dividend_yield: 0.00
  - price_position_52w: 0.83
  - liquidity_amount: 1.00
### TER: STRONG (score=0.88)
  - roe: 1.00
  - pe_ttm: 0.74
  - dividend_yield: 1.00
  - price_position_52w: 0.67
  - liquidity_amount: 1.00
### SW: STRONG (score=0.77)
  - roe: 1.00
  - pe_ttm: 1.00
  - dividend_yield: 0.00
  - price_position_52w: 0.83
  - liquidity_amount: 1.00

## Risk Checklist (UZI-Skill)
### MRNA: WATCH (red=0, yellow=1)
  - price_extended_vs_52w: [GREEN] latest/52w_high=87.6%
  - intraday_gap: [GREEN] intraday_pct_chg=-7.22%
  - liquidity: [GREEN] amount=499,932,048
  - valuation: [GREEN] pe_ttm=3.18
  - quality_gap: [YELLOW] roe=-1673.00%
  - price_manipulation: [GREEN] 5d_accel=-0.0667
  - news_red_flags: [GREEN] narrative_status=found_relevant
  - supply_chain_risk: [GREEN] business_status=found_relevant
  - short_interest: [GREEN] provider_field_unavailable
  - dilution_risk: [GREEN] provider_field_unavailable
  - debt_covenant: [GREEN] provider_field_unavailable
  - earnings_quality: [GREEN] provider_field_unavailable
  - insider_selling: [GREEN] provider_field_unavailable
  - regulatory_risk: [GREEN] provider_field_unavailable
  - concentration_risk: [GREEN] provider_field_unavailable
### TER: ELEVATED (red=1, yellow=2)
  - price_extended_vs_52w: [YELLOW] latest/52w_high=99.5%
  - intraday_gap: [GREEN] intraday_pct_chg=4.36%
  - liquidity: [GREEN] amount=1,957,491,728
  - valuation: [GREEN] pe_ttm=22.76
  - quality_gap: [GREEN] roe=1343.00%
  - price_manipulation: [RED] 5d_accel=-0.1596
  - news_red_flags: [GREEN] narrative_status=found_relevant
  - supply_chain_risk: [YELLOW] business_status=found_unrelated
  - short_interest: [GREEN] provider_field_unavailable
  - dilution_risk: [GREEN] provider_field_unavailable
  - debt_covenant: [GREEN] provider_field_unavailable
  - earnings_quality: [GREEN] provider_field_unavailable
  - insider_selling: [GREEN] provider_field_unavailable
  - regulatory_risk: [GREEN] provider_field_unavailable
  - concentration_risk: [GREEN] provider_field_unavailable
### SW: ELEVATED (red=1, yellow=1)
  - price_extended_vs_52w: [GREEN] latest/52w_high=87.7%
  - intraday_gap: [GREEN] intraday_pct_chg=2.69%
  - liquidity: [GREEN] amount=285,649,792
  - valuation: [GREEN] pe_ttm=1.32
  - quality_gap: [GREEN] roe=36.00%
  - price_manipulation: [RED] 5d_accel=-0.1549
  - news_red_flags: [GREEN] narrative_status=found_relevant
  - supply_chain_risk: [YELLOW] business_status=found_unrelated
  - short_interest: [GREEN] provider_field_unavailable
  - dilution_risk: [GREEN] provider_field_unavailable
  - debt_covenant: [GREEN] provider_field_unavailable
  - earnings_quality: [GREEN] provider_field_unavailable
  - insider_selling: [GREEN] provider_field_unavailable
  - regulatory_risk: [GREEN] provider_field_unavailable
  - concentration_risk: [GREEN] provider_field_unavailable

## Research Panel (TradingAgents)
### MRNA: BULLISH_CONSENSUS (pos=3, neg=0)
  - fundamental_analyst: Quality verdict: MODERATE (score=0.57)
  - news_analyst: News status: found_relevant, relevance=0.95
  - sentiment_analyst: Business/sentiment status: found_relevant, relevance=0.95
  - technical_analyst: Signals: strong_momentum, volume_confirmed
  - bull_case: Bull points: 4
  - bear_case: Bear points: 0
  - risk_manager: Risk: WATCH, Quality: MODERATE, Rec: PROCEED_WITH_MONITORING
### TER: BEARISH_CONSENSUS (pos=2, neg=3)
  - fundamental_analyst: Quality verdict: STRONG (score=0.88)
  - news_analyst: News status: found_relevant, relevance=0.75
  - sentiment_analyst: Business/sentiment status: found_unrelated, relevance=0.00
  - technical_analyst: Signals: strong_momentum, deceleration_warning, volume_confirmed
  - bull_case: Bull points: 4
  - bear_case: Bear points: 3
  - risk_manager: Risk: ELEVATED, Quality: STRONG, Rec: PROCEED_WITH_CAUTION
### SW: NEUTRAL (pos=2, neg=2)
  - fundamental_analyst: Quality verdict: STRONG (score=0.77)
  - news_analyst: News status: found_relevant, relevance=0.95
  - sentiment_analyst: Business/sentiment status: found_unrelated, relevance=0.00
  - technical_analyst: Signals: strong_momentum, deceleration_warning
  - bull_case: Bull points: 3
  - bear_case: Bear points: 2
  - risk_manager: Risk: ELEVATED, Quality: STRONG, Rec: PROCEED_WITH_CAUTION

## Supply Chain Map (Serenity Skill)
- MRNA: no_supply_chain_data | themes=[]
- TER: no_supply_chain_data | themes=[]
- SW: no_supply_chain_data | themes=[]

## Replay Hypothesis (QuantDinger)
- MRNA: Entry=momentum_continuation, SL=-5.0%, TP=8.0%, Period=5d_10d, Conf=70%
- TER: Entry=avoid_deceleration, SL=0.0%, TP=0.0%, Period=N/A, Conf=10%
- SW: Entry=avoid_deceleration, SL=-3.0%, TP=5.0%, Period=3d_5d, Conf=20%

## Risk Management (Cross-Platform Best Practices)
### MRNA: ALLOWED
  - stop_loss: $57.96
  - take_profit: $63.49
  - risk_reward: 2.00
  - kelly_fraction: 0.174
  - risk_score: N/A
  - confidence: 1.00
### TER: ALLOWED
  - stop_loss: $446.36
  - take_profit: $488.91
  - risk_reward: 2.00
  - kelly_fraction: 0.174
  - risk_score: N/A
  - confidence: 1.00
### SW: ALLOWED
  - stop_loss: $44.33
  - take_profit: $48.56
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
|TER|2|1d|2026-06-23|pending|
|TER|2|3d|2026-06-25|pending|
|TER|2|5d|2026-06-29|pending|
|TER|2|10d|2026-07-06|pending|
|SW|3|1d|2026-06-23|pending|
|SW|3|3d|2026-06-25|pending|
|SW|3|5d|2026-06-29|pending|
|SW|3|10d|2026-07-06|pending|

## Market Snapshot Top 10
- momentum_exhaustion_guard_threshold: -0.15
- momentum_exhaustion_guard_adjustment: -0.08
|rank|symbol|raw_market_score|market_score|rule|prior_20d|accel_5d|volume_confirm|closing_strength|vwmomentum|
|---|---|---|---|---|---|---|---|---|---|
|1|MRNA|0.5166666666666666|0.6944564372045092||0.2557130765975455|-0.06667280410706256|1.6932672054489761|0.6390387983896992|0.4587835076394849|
|2|TER|0.7|0.5251985878776622|momentum_exhaustion_guard|0.29300588501584435|-0.15957334533330458|0.9933267896002531|0.48998234847077526|0.45027025829646344|
|3|SW|0.18333333333333335|0.08890102116134752|momentum_exhaustion_guard|0.20270270270270263|-0.15491876918469716|0.26918556693789|0.32792943118351087|0.2317070871891023|

## Final Classification
- CANDIDATE_FOR_PAPER_REVIEW
