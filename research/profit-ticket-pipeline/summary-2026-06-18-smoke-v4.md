# XIAOMEI US Profit Ticket Pipeline V0

RESEARCH_ONLY
NOT_TRADING_ADVICE
NO_BROKER
NO_ORDER
NO_LEDGER
NO_LIVE_TRADE

- output_date: 2026-06-18-smoke-v4
- as_of_date: 2026-06-17
- market_data_source: Yahoo Finance historical kline + EastMoney US realtime quote
- kline_source: Yahoo Finance historical kline
- quote_source: EastMoney US realtime/delayed quote + kline
- data_source_mismatch_threshold: 0.01
- research_only: true
- allow_trade: false
- auto_order: false
- no_broker_api: true
- universe_source: explicit
- source_mode: live
- data_mode: historical_kline
- universe_key: explicit
- universe_total_symbols: 7
- universe_included_symbols: 7
- period_used: 1y
- classification: MARKET_WATCHLIST_NEEDS_EVIDENCE
- candidate_pool_size: 5
- top_k: 3
- paper_review_count: 0
- market_watchlist_count: 3
- zero_paper_review_is_valid_output: True
- artifact_summary: /root/hermes/company-ai-system/workspaces/xiaomei/research/profit-ticket-pipeline/summary-2026-06-18-smoke-v4.md
- artifact_metrics: /root/hermes/company-ai-system/workspaces/xiaomei/research/profit-ticket-pipeline/metrics-2026-06-18-smoke-v4.json
- artifact_candidates: /root/hermes/company-ai-system/workspaces/xiaomei/research/profit-ticket-pipeline/candidates-2026-06-18-smoke-v4.csv
- artifact_forward_tracking: /root/hermes/company-ai-system/workspaces/xiaomei/research/profit-ticket-pipeline/forward-tracking-2026-06-18-smoke-v4.csv

## Backtest Feedback Applied
- feedback_win_rate: 64%
- symbol_penalties: ADBE, ALNY, CPB, KIM

## Market Regime: BALANCED
- breadth: 50.0% (stocks with positive 20d return)
- momentum: +0.00% (median 20d return)
- volatility: 0.0200 (median daily |return|)
- advance_ratio: 50.0% (1d advancers)
- description: Relative strength dominant, acceleration reversed, tighter gates
- scoring_weights: {'prior_20d_momentum': 0.15, 'five_day_acceleration': -0.15, 'relative_strength_vs_equal_weight': 0.4, 'volume_weighted_momentum': 0.3, 'closing_strength_5d': 0.0, 'volume_confirmation_ratio': 0.0}
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
- default_stop_loss: 1.5%

## Methodology References
- UZI-Skill: risk checklist and multi-dimensional review
- TradingAgents: role-based research synthesis
- Serenity Skill: theme and supply-chain catalyst mapping
- Buffett Skills: quality, margin-of-safety, bear-case framing
- QuantDinger: replay discipline and data-health guardrails

## Price-Volume Summary
- equal_weight_20d_benchmark: -0.048704662357766874
- median_20d_momentum: -0.05894916685440077
- median_5d_acceleration: 0.058468543642606785
- median_volume_confirmation: -0.15351484176066732
- median_relative_strength: -0.010244504496633895
- top_market_score_p90: 0.6571428571428571

## Paper Review Candidates
- none

## Market Watchlist Needs Evidence
|rank|symbol|company|latest|intraday|source_gap|market_score|catalyst_score|ticket_score|narrative|business|gate_status|
|---|---|---|---|---|---|---|---|---|---|---|---|
|1|AAPL|苹果|296.36|-0.00962438176714342|0.00014845798776330632|0.7685714285714285|0.0|0.7885714285714285|found_unrelated|missing|MARKET_WATCHLIST_NEEDS_EVIDENCE|
  - ticket_card: research_only=true allow_trade=false auto_order=false no_broker_api=true
  - kline_source: Yahoo Finance historical kline
  - quote_source: EastMoney US realtime/delayed quote + kline | status=ok | prev_close=299.24 | cross_check_basis=latest_price | gap=0.00014845798776330632 | mismatch=false
  - catalyst: No relevant public catalyst evidence found.
|2|TSLA|特斯拉|400.395|-0.010539712351109731|8.745791217545928e-05|0.5828571428571427|0.0|0.6328571428571428|missing|missing|MARKET_WATCHLIST_NEEDS_EVIDENCE|
  - ticket_card: research_only=true allow_trade=false auto_order=false no_broker_api=true
  - kline_source: Yahoo Finance historical kline
  - quote_source: EastMoney US realtime/delayed quote + kline | status=ok | prev_close=404.66 | cross_check_basis=latest_price | gap=8.745791217545928e-05 | mismatch=false
  - catalyst: No relevant public catalyst evidence found.
|3|META|Meta Platforms Inc-A|576.88|-0.0388697289282085|0.00025144070001070773|0.48285714285714293|0.0|0.5328571428571429|missing|missing|MARKET_WATCHLIST_NEEDS_EVIDENCE|
  - ticket_card: research_only=true allow_trade=false auto_order=false no_broker_api=true
  - kline_source: Yahoo Finance historical kline
  - quote_source: EastMoney US realtime/delayed quote + kline | status=ok | prev_close=600.21 | cross_check_basis=latest_price | gap=0.00025144070001070773 | mismatch=false
  - catalyst: No relevant public catalyst evidence found.

## Catalyst Summary
- candidates_with_narrative_relevant: 0
- candidates_with_business_relevant: 0
- top_shared_titles: []

## Evidence Gaps
### 1. AAPL
- company: 苹果 (eastmoney_us)
- narrative query: AAPL 苹果 stock catalyst earnings news
- business query: AAPL 苹果 orders demand backlog guidance revenue customer contract
- narrative ranked candidates: 1 | status: found_unrelated | returncode: 0
- business ranked candidates: 0 | status: missing | returncode: 0
- evidence gap reason: found_unrelated_public_items;relevant_narrative_missing;relevant_business_missing
### 2. TSLA
- company: 特斯拉 (eastmoney_us)
- narrative query: TSLA 特斯拉 stock catalyst earnings news
- business query: TSLA 特斯拉 orders demand backlog guidance revenue customer contract
- narrative ranked candidates: 0 | status: missing | returncode: 0
- business ranked candidates: 0 | status: missing | returncode: 0
- evidence gap reason: last30days_returned_zero_ranked_candidates
### 3. META
- company: Meta Platforms Inc-A (eastmoney_us)
- narrative query: META meta platforms inc a stock catalyst earnings news
- business query: META meta platforms inc a orders demand backlog guidance revenue customer contract
- narrative ranked candidates: 0 | status: missing | returncode: 0
- business ranked candidates: 0 | status: missing | returncode: 0
- evidence gap reason: last30days_returned_zero_ranked_candidates

## Quality Check (Buffett Skills)
### AAPL: MODERATE (score=0.63)
  - roe: 1.00
  - pe_ttm: 0.38
  - dividend_yield: 0.00
  - price_position_52w: 0.76
  - liquidity_amount: 1.00
### TSLA: STRONG (score=0.95)
  - roe: 1.00
  - pe_ttm: 0.84
  - dividend_yield: 1.00
  - price_position_52w: 0.93
  - liquidity_amount: 1.00
### META: STRONG (score=0.79)
  - roe: 1.00
  - pe_ttm: 1.00
  - dividend_yield: 0.00
  - price_position_52w: 0.97
  - liquidity_amount: 1.00

## Risk Checklist (UZI-Skill)
### AAPL: WATCH (red=0, yellow=1)
  - price_extended_vs_52w: [GREEN] latest/52w_high=93.4%
  - intraday_gap: [GREEN] intraday_pct_chg=-0.96%
  - liquidity: [GREEN] amount=5,491,063,296
  - valuation: [GREEN] pe_ttm=40.87
  - quality_gap: [GREEN] roe=7954.00%
  - price_manipulation: [GREEN] 5d_accel=0.0251
  - news_red_flags: [YELLOW] narrative_status=found_unrelated
  - supply_chain_risk: [GREEN] business_status=missing
  - short_interest: [GREEN] provider_field_unavailable
  - dilution_risk: [GREEN] provider_field_unavailable
  - debt_covenant: [GREEN] provider_field_unavailable
  - earnings_quality: [GREEN] provider_field_unavailable
  - insider_selling: [GREEN] provider_field_unavailable
  - regulatory_risk: [GREEN] provider_field_unavailable
  - concentration_risk: [GREEN] provider_field_unavailable
### TSLA: CLEAN (red=0, yellow=0)
  - price_extended_vs_52w: [GREEN] latest/52w_high=80.3%
  - intraday_gap: [GREEN] intraday_pct_chg=-1.05%
  - liquidity: [GREEN] amount=10,311,897,600
  - valuation: [GREEN] pe_ttm=17.88
  - quality_gap: [GREEN] roe=57.00%
  - price_manipulation: [GREEN] 5d_accel=0.0585
  - news_red_flags: [GREEN] narrative_status=missing
  - supply_chain_risk: [GREEN] business_status=missing
  - short_interest: [GREEN] provider_field_unavailable
  - dilution_risk: [GREEN] provider_field_unavailable
  - debt_covenant: [GREEN] provider_field_unavailable
  - earnings_quality: [GREEN] provider_field_unavailable
  - insider_selling: [GREEN] provider_field_unavailable
  - regulatory_risk: [GREEN] provider_field_unavailable
  - concentration_risk: [GREEN] provider_field_unavailable
### META: CLEAN (red=0, yellow=0)
  - price_extended_vs_52w: [GREEN] latest/52w_high=72.6%
  - intraday_gap: [GREEN] intraday_pct_chg=-3.89%
  - liquidity: [GREEN] amount=5,771,751,936
  - valuation: [GREEN] pe_ttm=6.01
  - quality_gap: [GREEN] roe=1162.00%
  - price_manipulation: [GREEN] 5d_accel=0.0531
  - news_red_flags: [GREEN] narrative_status=missing
  - supply_chain_risk: [GREEN] business_status=missing
  - short_interest: [GREEN] provider_field_unavailable
  - dilution_risk: [GREEN] provider_field_unavailable
  - debt_covenant: [GREEN] provider_field_unavailable
  - earnings_quality: [GREEN] provider_field_unavailable
  - insider_selling: [GREEN] provider_field_unavailable
  - regulatory_risk: [GREEN] provider_field_unavailable
  - concentration_risk: [GREEN] provider_field_unavailable

## Research Panel (TradingAgents)
### AAPL: MIXED (pos=1, neg=1)
  - fundamental_analyst: Quality verdict: MODERATE (score=0.63)
  - news_analyst: News status: found_unrelated, relevance=0.00
  - sentiment_analyst: Business/sentiment status: missing, relevance=0.00
  - technical_analyst: Signals: negative_momentum
  - bull_case: Bull points: 1
  - bear_case: Bear points: 1
  - risk_manager: Risk: WATCH, Quality: MODERATE, Rec: PROCEED_WITH_MONITORING
### TSLA: MIXED (pos=1, neg=0)
  - fundamental_analyst: Quality verdict: STRONG (score=0.95)
  - news_analyst: News status: missing, relevance=0.00
  - sentiment_analyst: Business/sentiment status: missing, relevance=0.00
  - technical_analyst: Signals: negative_momentum, acceleration_bullish
  - bull_case: Bull points: 1
  - bear_case: Bear points: 0
  - risk_manager: Risk: CLEAN, Quality: STRONG, Rec: PROCEED
### META: MIXED (pos=1, neg=0)
  - fundamental_analyst: Quality verdict: STRONG (score=0.79)
  - news_analyst: News status: missing, relevance=0.00
  - sentiment_analyst: Business/sentiment status: missing, relevance=0.00
  - technical_analyst: Signals: negative_momentum, acceleration_bullish
  - bull_case: Bull points: 1
  - bear_case: Bear points: 0
  - risk_manager: Risk: CLEAN, Quality: STRONG, Rec: PROCEED

## Supply Chain Map (Serenity Skill)
- AAPL: no_supply_chain_data | themes=[]
- TSLA: no_supply_chain_data | themes=[]
- META: no_supply_chain_data | themes=[]

## Replay Hypothesis (QuantDinger)
- AAPL: Entry=no_entry, SL=0.0%, TP=0.0%, Period=N/A, Conf=20%
- TSLA: Entry=no_entry, SL=0.0%, TP=0.0%, Period=N/A, Conf=20%
- META: Entry=no_entry, SL=0.0%, TP=0.0%, Period=N/A, Conf=20%

## Risk Management (Cross-Platform Best Practices)
### AAPL: ALLOWED
  - stop_loss: $289.42
  - take_profit: $317.01
  - risk_reward: 2.00
  - kelly_fraction: 0.174
  - risk_score: N/A
  - confidence: 1.00
### TSLA: ALLOWED
  - stop_loss: $391.04
  - take_profit: $428.32
  - risk_reward: 2.00
  - kelly_fraction: 0.174
  - risk_score: N/A
  - confidence: 1.00
### META: ALLOWED
  - stop_loss: $563.31
  - take_profit: $617.01
  - risk_reward: 2.00
  - kelly_fraction: 0.174
  - risk_score: N/A
  - confidence: 1.00

## Forward Tracking
|symbol|rank|horizon|due_date|status|
|---|---|---|---|---|
|AAPL|1|1d|2026-06-18|pending|
|AAPL|1|3d|2026-06-22|pending|
|AAPL|1|5d|2026-06-24|pending|
|AAPL|1|10d|2026-07-01|pending|
|TSLA|2|1d|2026-06-18|pending|
|TSLA|2|3d|2026-06-22|pending|
|TSLA|2|5d|2026-06-24|pending|
|TSLA|2|10d|2026-07-01|pending|
|META|3|1d|2026-06-18|pending|
|META|3|3d|2026-06-22|pending|
|META|3|5d|2026-06-24|pending|
|META|3|10d|2026-07-01|pending|

## Market Snapshot Top 10
- momentum_exhaustion_guard_threshold: -0.15
- momentum_exhaustion_guard_adjustment: -0.08
|rank|symbol|raw_market_score|market_score|rule|prior_20d|accel_5d|volume_confirm|closing_strength|vwmomentum|
|---|---|---|---|---|---|---|---|---|---|
|1|AAPL|0.8285714285714285|0.7685714285714285||-0.00887711706319172|0.025119737158261102|-0.24013930872056255|0.520909052912285|-0.006697932165247163|
|2|TSLA|0.6428571428571428|0.5828571428571427||-0.00927965191639013|0.058468543642606785|-0.055015994081493935|0.6203153095610675|-0.009005612656240319|
|3|META|0.5428571428571429|0.48285714285714293||-0.04205121238602516|0.053066511102925706|-0.19807045602137396|0.4803709072016528|-0.03355765777504181|
|4|GOOGL|0.3357142857142857|0.2757142857142857||-0.05894916685440077|0.08198635003693588|-0.15351484176066732|0.5299750773768507|-0.04700592140848286|
|5|NVDA|0.2571428571428571|0.19714285714285712||-0.06354877126106895|0.0931366766035866|-0.30297553250454146|0.49055663724229764|-0.04543086508942709|
|6|MSFT|0.12142857142857141|0.061428571428571416||-0.07919920330926766|0.044394524725364426|-0.01123613335729734|0.5414587805146225|-0.0725954445235858|
|7|AMZN|0.07142857142857142|0.011428571428571427||-0.07902751371402372|0.08257793901109567|-0.08565624532166194|0.3947160470723778|-0.0740811392858793|

## Final Classification
- MARKET_WATCHLIST_NEEDS_EVIDENCE
