# XIAOMEI US Profit Ticket Pipeline V0

RESEARCH_ONLY
NOT_TRADING_ADVICE
NO_BROKER
NO_ORDER
NO_LEDGER
NO_LIVE_TRADE

- output_date: 2026-06-13-realtime-test
- as_of_date: 2026-06-14
- market_data_source: EastMoney US realtime/delayed quote + kline
- research_only: true
- allow_trade: false
- auto_order: false
- no_broker_api: true
- universe_source: explicit
- source_mode: live
- data_mode: realtime_intraday
- universe_key: explicit
- universe_total_symbols: 3
- universe_included_symbols: 3
- period_used: realtime_intraday
- classification: MARKET_WATCHLIST_NEEDS_EVIDENCE
- candidate_pool_size: 3
- top_k: 3
- paper_review_count: 0
- market_watchlist_count: 3
- zero_paper_review_is_valid_output: True
- artifact_summary: /root/hermes/company-ai-system/workspaces/xiaomei/research/profit-ticket-pipeline/summary-2026-06-13-realtime-test.md
- artifact_metrics: /root/hermes/company-ai-system/workspaces/xiaomei/research/profit-ticket-pipeline/metrics-2026-06-13-realtime-test.json
- artifact_candidates: /root/hermes/company-ai-system/workspaces/xiaomei/research/profit-ticket-pipeline/candidates-2026-06-13-realtime-test.csv
- artifact_forward_tracking: /root/hermes/company-ai-system/workspaces/xiaomei/research/profit-ticket-pipeline/forward-tracking-2026-06-13-realtime-test.csv

## Methodology References
- UZI-Skill: risk checklist and multi-dimensional review
- TradingAgents: role-based research synthesis
- Serenity Skill: theme and supply-chain catalyst mapping
- Buffett Skills: quality, margin-of-safety, bear-case framing
- QuantDinger: replay discipline and data-health guardrails

## Price-Volume Summary
- equal_weight_20d_benchmark: nan
- median_20d_momentum: None
- median_5d_acceleration: None
- median_volume_confirmation: None
- median_relative_strength: None
- top_market_score_p90: None

## Paper Review Candidates
- none

## Market Watchlist Needs Evidence
|rank|symbol|company|latest|intraday|market_score|catalyst_score|ticket_score|narrative|business|gate_status|
|---|---|---|---|---|---|---|---|---|---|---|
|1|NVDA|英伟达|205.19|0.0015619661248595929|None|0.0|None|missing|missing|MARKET_WATCHLIST_NEEDS_EVIDENCE|
  - ticket_card: research_only=true allow_trade=false auto_order=false no_broker_api=true
  - quote_source: EastMoney US realtime/delayed quote + kline | status=ok | prev_close=204.87
  - catalyst: No relevant public catalyst evidence found.
|2|MSFT|微软|390.74|0.0010247476558897795|None|0.0|None|missing|missing|MARKET_WATCHLIST_NEEDS_EVIDENCE|
  - ticket_card: research_only=true allow_trade=false auto_order=false no_broker_api=true
  - quote_source: EastMoney US realtime/delayed quote + kline | status=ok | prev_close=390.34
  - catalyst: No relevant public catalyst evidence found.
|3|AAPL|苹果|291.13|-0.015221729865034006|None|0.0|None|found_unrelated|missing|MARKET_WATCHLIST_NEEDS_EVIDENCE|
  - ticket_card: research_only=true allow_trade=false auto_order=false no_broker_api=true
  - quote_source: EastMoney US realtime/delayed quote + kline | status=ok | prev_close=295.63
  - catalyst: No relevant public catalyst evidence found.

## Catalyst Summary
- candidates_with_narrative_relevant: 0
- candidates_with_business_relevant: 0
- top_shared_titles: []

## Evidence Gaps
### 1. NVDA
- company: 英伟达 (eastmoney_us)
- narrative query: NVDA 英伟达 stock catalyst earnings news
- business query: NVDA 英伟达 orders demand backlog guidance revenue customer contract
- narrative ranked candidates: 0 | status: missing | returncode: 0
- business ranked candidates: 0 | status: missing | returncode: 0
- evidence gap reason: last30days_returned_zero_ranked_candidates
### 2. MSFT
- company: 微软 (eastmoney_us)
- narrative query: MSFT 微软 stock catalyst earnings news
- business query: MSFT 微软 orders demand backlog guidance revenue customer contract
- narrative ranked candidates: 0 | status: missing | returncode: 0
- business ranked candidates: 0 | status: missing | returncode: 0
- evidence gap reason: last30days_returned_zero_ranked_candidates
### 3. AAPL
- company: 苹果 (eastmoney_us)
- narrative query: AAPL 苹果 stock catalyst earnings news
- business query: AAPL 苹果 orders demand backlog guidance revenue customer contract
- narrative ranked candidates: 1 | status: found_unrelated | returncode: 0
- business ranked candidates: 0 | status: missing | returncode: 0
- evidence gap reason: found_unrelated_public_items;relevant_narrative_missing;relevant_business_missing

## Quality Check (Buffett Skills)
### NVDA: STRONG (score=0.71)
  - roe: 1.00
  - pe_ttm: 0.69
  - dividend_yield: 0.00
  - price_position_52w: 0.84
  - liquidity_amount: 1.00
### MSFT: STRONG (score=0.79)
  - roe: 1.00
  - pe_ttm: 1.00
  - dividend_yield: 0.00
  - price_position_52w: 0.94
  - liquidity_amount: 1.00
### AAPL: STRONG (score=0.83)
  - roe: 1.00
  - pe_ttm: 0.40
  - dividend_yield: 1.00
  - price_position_52w: 0.78
  - liquidity_amount: 1.00

## Risk Checklist (UZI-Skill)
### NVDA: CLEAN (red=0, yellow=0)
  - price_extended_vs_52w: [GREEN] latest/52w_high=86.8%
  - intraday_gap: [GREEN] intraday_pct_chg=0.16%
  - liquidity: [GREEN] amount=23,043,493,632
  - valuation: [GREEN] pe_ttm=25.40
  - quality_gap: [GREEN] roe=3306.00%
  - price_manipulation: [GREEN] N/A
  - news_red_flags: [GREEN] narrative_status=missing
  - supply_chain_risk: [GREEN] business_status=missing
  - short_interest: [GREEN] provider_field_unavailable
  - dilution_risk: [GREEN] provider_field_unavailable
  - debt_covenant: [GREEN] provider_field_unavailable
  - earnings_quality: [GREEN] provider_field_unavailable
  - insider_selling: [GREEN] provider_field_unavailable
  - regulatory_risk: [GREEN] provider_field_unavailable
  - concentration_risk: [GREEN] provider_field_unavailable
### MSFT: CLEAN (red=0, yellow=0)
  - price_extended_vs_52w: [GREEN] latest/52w_high=70.8%
  - intraday_gap: [GREEN] intraday_pct_chg=0.10%
  - liquidity: [GREEN] amount=13,531,622,400
  - valuation: [GREEN] pe_ttm=7.00
  - quality_gap: [GREEN] roe=2586.00%
  - price_manipulation: [GREEN] N/A
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
  - price_extended_vs_52w: [GREEN] latest/52w_high=91.7%
  - intraday_gap: [GREEN] intraday_pct_chg=-1.52%
  - liquidity: [GREEN] amount=11,309,703,936
  - valuation: [GREEN] pe_ttm=40.15
  - quality_gap: [GREEN] roe=7954.00%
  - price_manipulation: [GREEN] N/A
  - news_red_flags: [YELLOW] narrative_status=found_unrelated
  - supply_chain_risk: [GREEN] business_status=missing
  - short_interest: [GREEN] provider_field_unavailable
  - dilution_risk: [GREEN] provider_field_unavailable
  - debt_covenant: [GREEN] provider_field_unavailable
  - earnings_quality: [GREEN] provider_field_unavailable
  - insider_selling: [GREEN] provider_field_unavailable
  - regulatory_risk: [GREEN] provider_field_unavailable
  - concentration_risk: [GREEN] provider_field_unavailable

## Research Panel (TradingAgents)
### NVDA: MIXED (pos=1, neg=0)
  - fundamental_analyst: Quality verdict: STRONG (score=0.71)
  - news_analyst: News status: missing, relevance=0.00
  - sentiment_analyst: Business/sentiment status: missing, relevance=0.00
  - technical_analyst: Signals: neutral
  - bull_case: Bull points: 1
  - bear_case: Bear points: 0
  - risk_manager: Risk: CLEAN, Quality: STRONG, Rec: PROCEED
### MSFT: MIXED (pos=1, neg=0)
  - fundamental_analyst: Quality verdict: STRONG (score=0.79)
  - news_analyst: News status: missing, relevance=0.00
  - sentiment_analyst: Business/sentiment status: missing, relevance=0.00
  - technical_analyst: Signals: neutral
  - bull_case: Bull points: 1
  - bear_case: Bear points: 0
  - risk_manager: Risk: CLEAN, Quality: STRONG, Rec: PROCEED
### AAPL: MIXED (pos=1, neg=1)
  - fundamental_analyst: Quality verdict: STRONG (score=0.83)
  - news_analyst: News status: found_unrelated, relevance=0.00
  - sentiment_analyst: Business/sentiment status: missing, relevance=0.00
  - technical_analyst: Signals: neutral
  - bull_case: Bull points: 1
  - bear_case: Bear points: 1
  - risk_manager: Risk: WATCH, Quality: STRONG, Rec: PROCEED_WITH_MONITORING

## Supply Chain Map (Serenity Skill)
- NVDA: no_supply_chain_data | themes=[]
- MSFT: no_supply_chain_data | themes=[]
- AAPL: no_supply_chain_data | themes=[]

## Replay Hypothesis (QuantDinger)
- NVDA: Entry=no_entry, SL=0.0%, TP=0.0%, Period=N/A, Conf=20%
- MSFT: Entry=no_entry, SL=0.0%, TP=0.0%, Period=N/A, Conf=20%
- AAPL: Entry=no_entry, SL=0.0%, TP=0.0%, Period=N/A, Conf=20%

## Forward Tracking
|symbol|rank|horizon|due_date|status|
|---|---|---|---|---|
|NVDA|1|1d|2026-06-15|pending|
|NVDA|1|3d|2026-06-17|pending|
|NVDA|1|5d|2026-06-19|pending|
|NVDA|1|10d|2026-06-26|pending|
|MSFT|2|1d|2026-06-15|pending|
|MSFT|2|3d|2026-06-17|pending|
|MSFT|2|5d|2026-06-19|pending|
|MSFT|2|10d|2026-06-26|pending|
|AAPL|3|1d|2026-06-15|pending|
|AAPL|3|3d|2026-06-17|pending|
|AAPL|3|5d|2026-06-19|pending|
|AAPL|3|10d|2026-06-26|pending|

## Market Snapshot Top 10
- momentum_exhaustion_guard_threshold: -0.15
- momentum_exhaustion_guard_adjustment: -0.08
|rank|symbol|raw_market_score|market_score|rule|prior_20d|accel_5d|volume_confirm|rs_vs_equal_weight|
|---|---|---|---|---|---|---|---|---|
|1|AAPL|None|None||None|None|None|None|
|2|NVDA|None|None||None|None|None|None|
|3|MSFT|None|None||None|None|None|None|

## Final Classification
- MARKET_WATCHLIST_NEEDS_EVIDENCE
