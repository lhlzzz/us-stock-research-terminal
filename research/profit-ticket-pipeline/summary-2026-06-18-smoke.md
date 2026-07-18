# XIAOMEI US Profit Ticket Pipeline V0

RESEARCH_ONLY
NOT_TRADING_ADVICE
NO_BROKER
NO_ORDER
NO_LEDGER
NO_LIVE_TRADE

- output_date: 2026-06-18-smoke
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
- artifact_summary: /root/hermes/company-ai-system/workspaces/xiaomei/research/profit-ticket-pipeline/summary-2026-06-18-smoke.md
- artifact_metrics: /root/hermes/company-ai-system/workspaces/xiaomei/research/profit-ticket-pipeline/metrics-2026-06-18-smoke.json
- artifact_candidates: /root/hermes/company-ai-system/workspaces/xiaomei/research/profit-ticket-pipeline/candidates-2026-06-18-smoke.csv
- artifact_forward_tracking: /root/hermes/company-ai-system/workspaces/xiaomei/research/profit-ticket-pipeline/forward-tracking-2026-06-18-smoke.csv

## Backtest Feedback Applied
- feedback_win_rate: 64%
- symbol_penalties: ADBE, ALNY, CPB, KIM

## Market Regime: BALANCED
- breadth: 50.0% (stocks with positive 20d return)
- momentum: +0.00% (median 20d return)
- volatility: 0.0200 (median daily |return|)
- advance_ratio: 50.0% (1d advancers)
- description: Heavy volume + closing strength weight, tighter gates
- scoring_weights: {'prior_20d_momentum': 0.08, 'five_day_acceleration': 0.1, 'volume_confirmation_ratio': 0.3, 'relative_strength_vs_equal_weight': 0.12, 'closing_strength_5d': 0.2, 'volume_weighted_momentum': 0.2}
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
- equal_weight_20d_benchmark: -0.04572321338968629
- median_20d_momentum: -0.05800550756739131
- median_5d_acceleration: 0.0589680021591269
- median_volume_confirmation: -0.16562893560224767
- median_relative_strength: -0.012282294177705023
- top_market_score_p90: 0.6642857142857143

## Paper Review Candidates
- none

## Market Watchlist Needs Evidence
|rank|symbol|company|latest|intraday|source_gap|market_score|catalyst_score|ticket_score|narrative|business|gate_status|
|---|---|---|---|---|---|---|---|---|---|---|---|
|1|TSLA|特斯拉|403.84|-0.002026392527059828|0.00014859879361162065|0.8442857142857141|0.0|0.8942857142857141|missing|missing|MARKET_WATCHLIST_NEEDS_EVIDENCE|
  - ticket_card: research_only=true allow_trade=false auto_order=false no_broker_api=true
  - kline_source: Yahoo Finance historical kline
  - quote_source: EastMoney US realtime/delayed quote + kline | status=ok | prev_close=404.66 | cross_check_basis=latest_price | gap=0.00014859879361162065 | mismatch=false
  - catalyst: No relevant public catalyst evidence found.
|2|AAPL|苹果|297.415|-0.006098783585082201|0.0001260941338396826|0.5442857142857143|0.0|0.5942857142857143|found_unrelated|missing|MARKET_WATCHLIST_NEEDS_EVIDENCE|
  - ticket_card: research_only=true allow_trade=false auto_order=false no_broker_api=true
  - kline_source: Yahoo Finance historical kline
  - quote_source: EastMoney US realtime/delayed quote + kline | status=ok | prev_close=299.24 | cross_check_basis=latest_price | gap=0.0001260941338396826 | mismatch=false
  - catalyst: No relevant public catalyst evidence found.
|3|GOOGL|谷歌-A|364.96|-0.022210314802411313|1.2064690085411556e-05|0.48714285714285716|0.0|0.5371428571428571|missing|missing|MARKET_WATCHLIST_NEEDS_EVIDENCE|
  - ticket_card: research_only=true allow_trade=false auto_order=false no_broker_api=true
  - kline_source: Yahoo Finance historical kline
  - quote_source: EastMoney US realtime/delayed quote + kline | status=ok | prev_close=373.25 | cross_check_basis=latest_price | gap=1.2064690085411556e-05 | mismatch=false
  - catalyst: No relevant public catalyst evidence found.

## Catalyst Summary
- candidates_with_narrative_relevant: 0
- candidates_with_business_relevant: 0
- top_shared_titles: []

## Evidence Gaps
### 1. TSLA
- company: 特斯拉 (eastmoney_us)
- narrative query: TSLA 特斯拉 stock catalyst earnings news
- business query: TSLA 特斯拉 orders demand backlog guidance revenue customer contract
- narrative ranked candidates: 0 | status: missing | returncode: 0
- business ranked candidates: 0 | status: missing | returncode: 0
- evidence gap reason: last30days_returned_zero_ranked_candidates
### 2. AAPL
- company: 苹果 (eastmoney_us)
- narrative query: AAPL 苹果 stock catalyst earnings news
- business query: AAPL 苹果 orders demand backlog guidance revenue customer contract
- narrative ranked candidates: 1 | status: found_unrelated | returncode: 0
- business ranked candidates: 0 | status: missing | returncode: 0
- evidence gap reason: found_unrelated_public_items;relevant_narrative_missing;relevant_business_missing
### 3. GOOGL
- company: 谷歌-A (eastmoney_us)
- narrative query: GOOGL a stock catalyst earnings news
- business query: GOOGL a orders demand backlog guidance revenue customer contract
- narrative ranked candidates: 0 | status: missing | returncode: 0
- business ranked candidates: 0 | status: missing | returncode: 0
- evidence gap reason: last30days_returned_zero_ranked_candidates

## Quality Check (Buffett Skills)
### TSLA: STRONG (score=0.95)
  - roe: 1.00
  - pe_ttm: 0.84
  - dividend_yield: 1.00
  - price_position_52w: 0.92
  - liquidity_amount: 1.00
### AAPL: STRONG (score=0.83)
  - roe: 1.00
  - pe_ttm: 0.38
  - dividend_yield: 1.00
  - price_position_52w: 0.75
  - liquidity_amount: 1.00
### GOOGL: STRONG (score=0.96)
  - roe: 1.00
  - pe_ttm: 1.00
  - dividend_yield: 1.00
  - price_position_52w: 0.81
  - liquidity_amount: 1.00

## Risk Checklist (UZI-Skill)
### TSLA: CLEAN (red=0, yellow=0)
  - price_extended_vs_52w: [GREEN] latest/52w_high=81.0%
  - intraday_gap: [GREEN] intraday_pct_chg=-0.20%
  - liquidity: [GREEN] amount=8,781,663,232
  - valuation: [GREEN] pe_ttm=18.03
  - quality_gap: [GREEN] roe=57.00%
  - price_manipulation: [GREEN] 5d_accel=0.0590
  - news_red_flags: [GREEN] narrative_status=missing
  - supply_chain_risk: [GREEN] business_status=missing
  - short_interest: [GREEN] provider_field_unavailable
  - dilution_risk: [GREEN] provider_field_unavailable
  - debt_covenant: [GREEN] provider_field_unavailable
  - earnings_quality: [GREEN] provider_field_unavailable
  - insider_selling: [GREEN] provider_field_unavailable
  - regulatory_risk: [GREEN] provider_field_unavailable
  - concentration_risk: [GREEN] provider_field_unavailable
### AAPL: WATCH (red=0, yellow=1)
  - price_extended_vs_52w: [GREEN] latest/52w_high=93.7%
  - intraday_gap: [GREEN] intraday_pct_chg=-0.61%
  - liquidity: [GREEN] amount=4,642,432,256
  - valuation: [GREEN] pe_ttm=41.02
  - quality_gap: [GREEN] roe=7954.00%
  - price_manipulation: [GREEN] 5d_accel=0.0252
  - news_red_flags: [YELLOW] narrative_status=found_unrelated
  - supply_chain_risk: [GREEN] business_status=missing
  - short_interest: [GREEN] provider_field_unavailable
  - dilution_risk: [GREEN] provider_field_unavailable
  - debt_covenant: [GREEN] provider_field_unavailable
  - earnings_quality: [GREEN] provider_field_unavailable
  - insider_selling: [GREEN] provider_field_unavailable
  - regulatory_risk: [GREEN] provider_field_unavailable
  - concentration_risk: [GREEN] provider_field_unavailable
### GOOGL: WATCH (red=0, yellow=1)
  - price_extended_vs_52w: [GREEN] latest/52w_high=89.4%
  - intraday_gap: [GREEN] intraday_pct_chg=-2.22%
  - liquidity: [GREEN] amount=3,854,963,136
  - valuation: [GREEN] pe_ttm=9.27
  - quality_gap: [GREEN] roe=1400.00%
  - price_manipulation: [YELLOW] 5d_accel=0.0821
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
### TSLA: MIXED (pos=1, neg=0)
  - fundamental_analyst: Quality verdict: STRONG (score=0.95)
  - news_analyst: News status: missing, relevance=0.00
  - sentiment_analyst: Business/sentiment status: missing, relevance=0.00
  - technical_analyst: Signals: negative_momentum, acceleration_bullish
  - bull_case: Bull points: 1
  - bear_case: Bear points: 0
  - risk_manager: Risk: CLEAN, Quality: STRONG, Rec: PROCEED
### AAPL: MIXED (pos=1, neg=1)
  - fundamental_analyst: Quality verdict: STRONG (score=0.83)
  - news_analyst: News status: found_unrelated, relevance=0.00
  - sentiment_analyst: Business/sentiment status: missing, relevance=0.00
  - technical_analyst: Signals: negative_momentum
  - bull_case: Bull points: 1
  - bear_case: Bear points: 1
  - risk_manager: Risk: WATCH, Quality: STRONG, Rec: PROCEED_WITH_MONITORING
### GOOGL: MIXED (pos=1, neg=0)
  - fundamental_analyst: Quality verdict: STRONG (score=0.96)
  - news_analyst: News status: missing, relevance=0.00
  - sentiment_analyst: Business/sentiment status: missing, relevance=0.00
  - technical_analyst: Signals: negative_momentum, acceleration_bullish
  - bull_case: Bull points: 1
  - bear_case: Bear points: 0
  - risk_manager: Risk: WATCH, Quality: STRONG, Rec: PROCEED_WITH_MONITORING

## Supply Chain Map (Serenity Skill)
- TSLA: no_supply_chain_data | themes=[]
- AAPL: no_supply_chain_data | themes=[]
- GOOGL: no_supply_chain_data | themes=[]

## Replay Hypothesis (QuantDinger)
- TSLA: Entry=no_entry, SL=0.0%, TP=0.0%, Period=N/A, Conf=20%
- AAPL: Entry=no_entry, SL=0.0%, TP=0.0%, Period=N/A, Conf=20%
- GOOGL: Entry=no_entry, SL=0.0%, TP=0.0%, Period=N/A, Conf=20%

## Risk Management (Cross-Platform Best Practices)
### TSLA: ALLOWED
  - stop_loss: $394.38
  - take_profit: $431.97
  - risk_reward: 2.00
  - kelly_fraction: 0.174
  - risk_score: N/A
  - confidence: 1.00
### AAPL: ALLOWED
  - stop_loss: $290.46
  - take_profit: $318.14
  - risk_reward: 2.00
  - kelly_fraction: 0.174
  - risk_score: N/A
  - confidence: 1.00
### GOOGL: ALLOWED
  - stop_loss: $356.46
  - take_profit: $390.44
  - risk_reward: 2.00
  - kelly_fraction: 0.174
  - risk_score: N/A
  - confidence: 1.00

## Forward Tracking
|symbol|rank|horizon|due_date|status|
|---|---|---|---|---|
|TSLA|1|1d|2026-06-18|pending|
|TSLA|1|3d|2026-06-22|pending|
|TSLA|1|5d|2026-06-24|pending|
|TSLA|1|10d|2026-07-01|pending|
|AAPL|2|1d|2026-06-18|pending|
|AAPL|2|3d|2026-06-22|pending|
|AAPL|2|5d|2026-06-24|pending|
|AAPL|2|10d|2026-07-01|pending|
|GOOGL|3|1d|2026-06-18|pending|
|GOOGL|3|3d|2026-06-22|pending|
|GOOGL|3|5d|2026-06-24|pending|
|GOOGL|3|10d|2026-07-01|pending|

## Market Snapshot Top 10
- momentum_exhaustion_guard_threshold: -0.15
- momentum_exhaustion_guard_adjustment: -0.08
|rank|symbol|raw_market_score|market_score|rule|prior_20d|accel_5d|volume_confirm|closing_strength|vwmomentum|
|---|---|---|---|---|---|---|---|---|---|
|1|TSLA|0.9142857142857141|0.8442857142857141||-0.0008165761407220584|0.0589680021591269|-0.0702959183165085|0.7187496766381216|-0.0007820941883329699|
|2|AAPL|0.6142857142857143|0.5442857142857143||-0.00532661729536299|0.02520972359938134|-0.25165226802923524|0.5475140356445312|-0.003968587136083899|
|3|GOOGL|0.5571428571428572|0.48714285714285716||-0.05800550756739131|0.08206856364102122|-0.16562893560224767|0.537552296385677|-0.0457190074506717|
|4|MSFT|0.5285714285714286|0.4585714285714286||-0.07845494340825898|0.044430407692338525|-0.02827548164420224|0.5376710361461514|-0.0709279534684273|
|5|META|0.5142857142857143|0.44428571428571434||-0.04036528717500576|0.05315990458082975|-0.21451527707883866|0.48282899097866305|-0.031672299806909346|
|6|AMZN|0.44285714285714284|0.37285714285714283||-0.07654041461026428|0.08280094189246612|-0.10355148615741028|0.40149970381397004|-0.07063962417857182|
|7|NVDA|0.42857142857142855|0.35857142857142854||-0.06055314753079866|0.09343461250246732|-0.31209582585565665|0.5306839017056442|-0.04281077227058749|

## Final Classification
- MARKET_WATCHLIST_NEEDS_EVIDENCE
