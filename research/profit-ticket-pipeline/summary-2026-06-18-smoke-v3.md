# XIAOMEI US Profit Ticket Pipeline V0

RESEARCH_ONLY
NOT_TRADING_ADVICE
NO_BROKER
NO_ORDER
NO_LEDGER
NO_LIVE_TRADE

- output_date: 2026-06-18-smoke-v3
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
- classification: CANDIDATE_FOR_PAPER_REVIEW
- candidate_pool_size: 5
- top_k: 3
- paper_review_count: 1
- market_watchlist_count: 2
- zero_paper_review_is_valid_output: False
- artifact_summary: /root/hermes/company-ai-system/workspaces/xiaomei/research/profit-ticket-pipeline/summary-2026-06-18-smoke-v3.md
- artifact_metrics: /root/hermes/company-ai-system/workspaces/xiaomei/research/profit-ticket-pipeline/metrics-2026-06-18-smoke-v3.json
- artifact_candidates: /root/hermes/company-ai-system/workspaces/xiaomei/research/profit-ticket-pipeline/candidates-2026-06-18-smoke-v3.csv
- artifact_forward_tracking: /root/hermes/company-ai-system/workspaces/xiaomei/research/profit-ticket-pipeline/forward-tracking-2026-06-18-smoke-v3.csv

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
- equal_weight_20d_benchmark: -0.04581794655992825
- median_20d_momentum: -0.058716875432247906
- median_5d_acceleration: 0.058954128187646226
- median_volume_confirmation: -0.16473058656291495
- median_relative_strength: -0.012898928872319658
- top_market_score_p90: 0.6471428571428571

## Paper Review Candidates
|rank|symbol|company|latest|intraday|source_gap|market_score|catalyst_score|ticket_score|narrative|business|gate_status|
|---|---|---|---|---|---|---|---|---|---|---|---|
|2|GOOGL|谷歌-A|364.62|-0.023121232417950388|0.00016450772454246199|0.4585714285714286|0.2375|0.7460714285714286|missing|found_relevant|CANDIDATE_FOR_PAPER_REVIEW|
  - ticket_card: research_only=true allow_trade=false auto_order=false no_broker_api=true
  - kline_source: Yahoo Finance historical kline
  - quote_source: EastMoney US realtime/delayed quote + kline | status=ok | prev_close=373.25 | cross_check_basis=latest_price | gap=0.00016450772454246199 | mismatch=false
  - catalyst: The $100 Billion Moat: Why no one can build the next credible Neocloud.

## Market Watchlist Needs Evidence
|rank|symbol|company|latest|intraday|source_gap|market_score|catalyst_score|ticket_score|narrative|business|gate_status|
|---|---|---|---|---|---|---|---|---|---|---|---|
|1|TSLA|特斯拉|403.7|-0.0023723619828993625|3.716373285356234e-05|0.8442857142857141|0.0|0.8942857142857141|missing|missing|MARKET_WATCHLIST_NEEDS_EVIDENCE|
  - ticket_card: research_only=true allow_trade=false auto_order=false no_broker_api=true
  - kline_source: Yahoo Finance historical kline
  - quote_source: EastMoney US realtime/delayed quote + kline | status=ok | prev_close=404.66 | cross_check_basis=latest_price | gap=3.716373285356234e-05 | mismatch=false
  - catalyst: No relevant public catalyst evidence found.
|3|AAPL|苹果|297.26|-0.006616762464911163|5.0479850153717365e-05|0.5157142857142856|0.0|0.5657142857142856|missing|missing|MARKET_WATCHLIST_NEEDS_EVIDENCE|
  - ticket_card: research_only=true allow_trade=false auto_order=false no_broker_api=true
  - kline_source: Yahoo Finance historical kline
  - quote_source: EastMoney US realtime/delayed quote + kline | status=ok | prev_close=299.24 | cross_check_basis=latest_price | gap=5.0479850153717365e-05 | mismatch=false
  - catalyst: No relevant public catalyst evidence found.

## Catalyst Summary
- candidates_with_narrative_relevant: 0
- candidates_with_business_relevant: 1
- top_shared_titles: [["The $100 Billion Moat: Why no one can build the next credible Neocloud.", 1]]

## Evidence Gaps
### 1. TSLA
- company: 特斯拉 (eastmoney_us)
- narrative query: TSLA 特斯拉 stock catalyst earnings news
- business query: TSLA 特斯拉 orders demand backlog guidance revenue customer contract
- narrative ranked candidates: 0 | status: missing | returncode: 0
- business ranked candidates: 0 | status: missing | returncode: 0
- evidence gap reason: last30days_returned_zero_ranked_candidates
### 2. GOOGL
- company: 谷歌-A (eastmoney_us)
- narrative query: GOOGL a stock catalyst earnings news
- business query: GOOGL a orders demand backlog guidance revenue customer contract
- narrative ranked candidates: 0 | status: missing | returncode: 0
- business ranked candidates: 6 | status: found_relevant | returncode: 0
- evidence gap reason: paper_review_gate_passed
### 3. AAPL
- company: 苹果 (eastmoney_us)
- narrative query: AAPL 苹果 stock catalyst earnings news
- business query: AAPL 苹果 orders demand backlog guidance revenue customer contract
- narrative ranked candidates: 0 | status: missing | returncode: 0
- business ranked candidates: 0 | status: missing | returncode: 0
- evidence gap reason: last30days_returned_zero_ranked_candidates

## Quality Check (Buffett Skills)
### TSLA: STRONG (score=0.75)
  - roe: 1.00
  - pe_ttm: 0.84
  - dividend_yield: 0.00
  - price_position_52w: 0.92
  - liquidity_amount: 1.00
### GOOGL: STRONG (score=0.76)
  - roe: 1.00
  - pe_ttm: 1.00
  - dividend_yield: 0.00
  - price_position_52w: 0.81
  - liquidity_amount: 1.00
### AAPL: STRONG (score=0.83)
  - roe: 1.00
  - pe_ttm: 0.38
  - dividend_yield: 1.00
  - price_position_52w: 0.75
  - liquidity_amount: 1.00

## Risk Checklist (UZI-Skill)
### TSLA: CLEAN (red=0, yellow=0)
  - price_extended_vs_52w: [GREEN] latest/52w_high=80.9%
  - intraday_gap: [GREEN] intraday_pct_chg=-0.24%
  - liquidity: [GREEN] amount=8,902,120,192
  - valuation: [GREEN] pe_ttm=18.02
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
### GOOGL: WATCH (red=0, yellow=1)
  - price_extended_vs_52w: [GREEN] latest/52w_high=89.3%
  - intraday_gap: [GREEN] intraday_pct_chg=-2.31%
  - liquidity: [GREEN] amount=3,907,246,640
  - valuation: [GREEN] pe_ttm=9.27
  - quality_gap: [GREEN] roe=1400.00%
  - price_manipulation: [YELLOW] 5d_accel=0.0820
  - news_red_flags: [GREEN] narrative_status=missing
  - supply_chain_risk: [GREEN] business_status=found_relevant
  - short_interest: [GREEN] provider_field_unavailable
  - dilution_risk: [GREEN] provider_field_unavailable
  - debt_covenant: [GREEN] provider_field_unavailable
  - earnings_quality: [GREEN] provider_field_unavailable
  - insider_selling: [GREEN] provider_field_unavailable
  - regulatory_risk: [GREEN] provider_field_unavailable
  - concentration_risk: [GREEN] provider_field_unavailable
### AAPL: CLEAN (red=0, yellow=0)
  - price_extended_vs_52w: [GREEN] latest/52w_high=93.7%
  - intraday_gap: [GREEN] intraday_pct_chg=-0.66%
  - liquidity: [GREEN] amount=4,712,765,696
  - valuation: [GREEN] pe_ttm=41.00
  - quality_gap: [GREEN] roe=7954.00%
  - price_manipulation: [GREEN] 5d_accel=0.0252
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
  - fundamental_analyst: Quality verdict: STRONG (score=0.75)
  - news_analyst: News status: missing, relevance=0.00
  - sentiment_analyst: Business/sentiment status: missing, relevance=0.00
  - technical_analyst: Signals: negative_momentum, acceleration_bullish
  - bull_case: Bull points: 1
  - bear_case: Bear points: 0
  - risk_manager: Risk: CLEAN, Quality: STRONG, Rec: PROCEED
### GOOGL: NEUTRAL (pos=2, neg=0)
  - fundamental_analyst: Quality verdict: STRONG (score=0.76)
  - news_analyst: News status: missing, relevance=0.00
  - sentiment_analyst: Business/sentiment status: found_relevant, relevance=0.95
  - technical_analyst: Signals: negative_momentum, acceleration_bullish
  - bull_case: Bull points: 2
  - bear_case: Bear points: 0
  - risk_manager: Risk: WATCH, Quality: STRONG, Rec: PROCEED_WITH_MONITORING
### AAPL: MIXED (pos=1, neg=0)
  - fundamental_analyst: Quality verdict: STRONG (score=0.83)
  - news_analyst: News status: missing, relevance=0.00
  - sentiment_analyst: Business/sentiment status: missing, relevance=0.00
  - technical_analyst: Signals: negative_momentum
  - bull_case: Bull points: 1
  - bear_case: Bear points: 0
  - risk_manager: Risk: CLEAN, Quality: STRONG, Rec: PROCEED

## Supply Chain Map (Serenity Skill)
- TSLA: no_supply_chain_data | themes=[]
- GOOGL: no_supply_chain_data | themes=[]
- AAPL: no_supply_chain_data | themes=[]

## Replay Hypothesis (QuantDinger)
- TSLA: Entry=no_entry, SL=0.0%, TP=0.0%, Period=N/A, Conf=20%
- GOOGL: Entry=pullback_entry, SL=-3.0%, TP=5.0%, Period=3d_5d, Conf=50%
- AAPL: Entry=no_entry, SL=0.0%, TP=0.0%, Period=N/A, Conf=20%

## Risk Management (Cross-Platform Best Practices)
### TSLA: ALLOWED
  - stop_loss: $394.29
  - take_profit: $431.87
  - risk_reward: 2.00
  - kelly_fraction: 0.174
  - risk_score: N/A
  - confidence: 1.00
### GOOGL: ALLOWED
  - stop_loss: $356.19
  - take_profit: $390.14
  - risk_reward: 2.00
  - kelly_fraction: 0.174
  - risk_score: N/A
  - confidence: 1.00
### AAPL: ALLOWED
  - stop_loss: $290.33
  - take_profit: $318.00
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
|GOOGL|2|1d|2026-06-18|pending|
|GOOGL|2|3d|2026-06-22|pending|
|GOOGL|2|5d|2026-06-24|pending|
|GOOGL|2|10d|2026-07-01|pending|
|AAPL|3|1d|2026-06-18|pending|
|AAPL|3|3d|2026-06-22|pending|
|AAPL|3|5d|2026-06-24|pending|
|AAPL|3|10d|2026-07-01|pending|

## Market Snapshot Top 10
- momentum_exhaustion_guard_threshold: -0.15
- momentum_exhaustion_guard_adjustment: -0.08
|rank|symbol|raw_market_score|market_score|rule|prior_20d|accel_5d|volume_confirm|closing_strength|vwmomentum|
|---|---|---|---|---|---|---|---|---|---|
|1|TSLA|0.9142857142857141|0.8442857142857141||-0.0010516636766573217|0.058954128187646226|-0.06904583350482574|0.7162129251142779|-0.0010083066624362582|
|2|AAPL|0.5857142857142856|0.5157142857142856||-0.005769830071486681|0.02519849049334255|-0.25070665513632406|0.5426334646334594|-0.004303332396515909|
|3|MSFT|0.557142857142857|0.48714285714285704||-0.07841266757021192|0.04443244593529416|-0.026775947456306515|0.5428461732201566|-0.07097595727718654|
|4|GOOGL|0.5285714285714286|0.4585714285714286||-0.058716875432247906|0.08200658775967773|-0.16473058656291495|0.5318402876320284|-0.04632207220562944|
|5|META|0.5142857142857143|0.44428571428571434||-0.040116098710262116|0.053173708619836835|-0.21356483584352914|0.48465967163735063|-0.031506746131878594|
|6|NVDA|0.4571428571428571|0.38714285714285707||-0.0603494229581113|0.09345487434746291|-0.31143362151882836|0.5334128525158884|-0.04269997361739783|
|7|AMZN|0.44285714285714284|0.37285714285714283||-0.07630906750052047|0.08282168536504919|-0.10207746396480166|0.4033014313095597|-0.07051484122856491|

## Final Classification
- CANDIDATE_FOR_PAPER_REVIEW
