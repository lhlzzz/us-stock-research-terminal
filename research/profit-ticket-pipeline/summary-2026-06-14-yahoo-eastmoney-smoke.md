# XIAOMEI US Profit Ticket Pipeline V0

RESEARCH_ONLY
NOT_TRADING_ADVICE
NO_BROKER
NO_ORDER
NO_LEDGER
NO_LIVE_TRADE

- output_date: 2026-06-14-yahoo-eastmoney-smoke
- as_of_date: 2026-06-12
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
- universe_total_symbols: 3
- universe_included_symbols: 3
- period_used: 1y
- classification: MARKET_WATCHLIST_NEEDS_EVIDENCE
- candidate_pool_size: 1
- top_k: 1
- paper_review_count: 0
- market_watchlist_count: 1
- zero_paper_review_is_valid_output: True
- artifact_summary: /root/hermes/company-ai-system/workspaces/xiaomei/research/profit-ticket-pipeline/summary-2026-06-14-yahoo-eastmoney-smoke.md
- artifact_metrics: /root/hermes/company-ai-system/workspaces/xiaomei/research/profit-ticket-pipeline/metrics-2026-06-14-yahoo-eastmoney-smoke.json
- artifact_candidates: /root/hermes/company-ai-system/workspaces/xiaomei/research/profit-ticket-pipeline/candidates-2026-06-14-yahoo-eastmoney-smoke.csv
- artifact_forward_tracking: /root/hermes/company-ai-system/workspaces/xiaomei/research/profit-ticket-pipeline/forward-tracking-2026-06-14-yahoo-eastmoney-smoke.csv

## Methodology References
- UZI-Skill: risk checklist and multi-dimensional review
- TradingAgents: role-based research synthesis
- Serenity Skill: theme and supply-chain catalyst mapping
- Buffett Skills: quality, margin-of-safety, bear-case framing
- QuantDinger: replay discipline and data-health guardrails

## Price-Volume Summary
- equal_weight_20d_benchmark: -0.06530031327774795
- median_20d_momentum: -0.0435818315201969
- median_5d_acceleration: -0.018649724285910052
- median_volume_confirmation: 0.05110280537784284
- median_relative_strength: 0.021718481757551047
- top_market_score_p90: 0.8266666666666667

## Paper Review Candidates
- none

## Market Watchlist Needs Evidence
|rank|symbol|company|latest|intraday|source_gap|market_score|catalyst_score|ticket_score|narrative|business|gate_status|
|---|---|---|---|---|---|---|---|---|---|---|---|
|1|AAPL|苹果|291.13|-0.015221729865034006|1.6771931510284332e-08|0.8666666666666667|0.0|0.9166666666666667|found_unrelated|found_unrelated|MARKET_WATCHLIST_NEEDS_EVIDENCE|
  - ticket_card: research_only=true allow_trade=false auto_order=false no_broker_api=true
  - kline_source: Yahoo Finance historical kline
  - quote_source: EastMoney US realtime/delayed quote + kline | status=ok | prev_close=295.63 | cross_check_basis=latest_price | gap=1.6771931510284332e-08 | mismatch=false
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
- business ranked candidates: 6 | status: found_unrelated | returncode: 0
- evidence gap reason: found_unrelated_public_items;relevant_narrative_missing;relevant_business_missing

## Quality Check (Buffett Skills)
### AAPL: STRONG (score=0.83)
  - roe: 1.00
  - pe_ttm: 0.40
  - dividend_yield: 1.00
  - price_position_52w: 0.78
  - liquidity_amount: 1.00

## Risk Checklist (UZI-Skill)
### AAPL: WATCH (red=0, yellow=2)
  - price_extended_vs_52w: [GREEN] latest/52w_high=91.7%
  - intraday_gap: [GREEN] intraday_pct_chg=-1.52%
  - liquidity: [GREEN] amount=11,309,703,936
  - valuation: [GREEN] pe_ttm=40.15
  - quality_gap: [GREEN] roe=7954.00%
  - price_manipulation: [GREEN] 5d_accel=-0.0290
  - news_red_flags: [YELLOW] narrative_status=found_unrelated
  - supply_chain_risk: [YELLOW] business_status=found_unrelated
  - short_interest: [GREEN] provider_field_unavailable
  - dilution_risk: [GREEN] provider_field_unavailable
  - debt_covenant: [GREEN] provider_field_unavailable
  - earnings_quality: [GREEN] provider_field_unavailable
  - insider_selling: [GREEN] provider_field_unavailable
  - regulatory_risk: [GREEN] provider_field_unavailable
  - concentration_risk: [GREEN] provider_field_unavailable

## Research Panel (TradingAgents)
### AAPL: MIXED (pos=1, neg=2)
  - fundamental_analyst: Quality verdict: STRONG (score=0.83)
  - news_analyst: News status: found_unrelated, relevance=0.00
  - sentiment_analyst: Business/sentiment status: found_unrelated, relevance=0.00
  - technical_analyst: Signals: negative_momentum
  - bull_case: Bull points: 1
  - bear_case: Bear points: 2
  - risk_manager: Risk: WATCH, Quality: STRONG, Rec: PROCEED_WITH_MONITORING

## Supply Chain Map (Serenity Skill)
- AAPL: no_supply_chain_data | themes=[]

## Replay Hypothesis (QuantDinger)
- AAPL: Entry=no_entry, SL=0.0%, TP=0.0%, Period=N/A, Conf=20%

## Forward Tracking
|symbol|rank|horizon|due_date|status|
|---|---|---|---|---|
|AAPL|1|1d|2026-06-15|pending|
|AAPL|1|3d|2026-06-17|pending|
|AAPL|1|5d|2026-06-19|pending|
|AAPL|1|10d|2026-06-26|pending|

## Market Snapshot Top 10
- momentum_exhaustion_guard_threshold: -0.15
- momentum_exhaustion_guard_adjustment: -0.08
|rank|symbol|raw_market_score|market_score|rule|prior_20d|accel_5d|volume_confirm|rs_vs_equal_weight|
|---|---|---|---|---|---|---|---|---|
|1|AAPL|0.8666666666666667|0.8666666666666667||-0.023741614215270657|-0.02900124922010472|0.11725932158908803|0.04155869906247729|
|2|MSFT|0.6666666666666666|0.6666666666666666||-0.0435818315201969|-0.018649724285910052|0.05110280537784284|0.021718481757551047|
|3|NVDA|0.4666666666666666|0.4666666666666666||-0.1285774940977763|0.12901628656590136|-0.158436681794626|-0.06327718082002835|

## Final Classification
- MARKET_WATCHLIST_NEEDS_EVIDENCE
