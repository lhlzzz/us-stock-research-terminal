# XIAOMEI US Profit Ticket Pipeline V0

RESEARCH_ONLY
NOT_TRADING_ADVICE
NO_BROKER
NO_ORDER
NO_LEDGER
NO_LIVE_TRADE

- output_date: 2026-06-16-feedback
- as_of_date: 2026-06-15
- market_data_source: Yahoo Finance historical kline + EastMoney US realtime quote
- kline_source: Yahoo Finance historical kline
- quote_source: EastMoney US realtime/delayed quote + kline
- data_source_mismatch_threshold: 0.01
- research_only: true
- allow_trade: false
- auto_order: false
- no_broker_api: true
- universe_source: nasdaq100_sp500_union
- source_mode: live
- data_mode: historical_kline
- universe_key: union
- universe_total_symbols: 516
- universe_included_symbols: 514
- period_used: 1y
- classification: MARKET_WATCHLIST_NEEDS_EVIDENCE
- candidate_pool_size: 3
- top_k: 3
- paper_review_count: 0
- market_watchlist_count: 3
- zero_paper_review_is_valid_output: True
- artifact_summary: /root/hermes/company-ai-system/workspaces/xiaomei/research/profit-ticket-pipeline-feedback/summary-2026-06-16-feedback.md
- artifact_metrics: /root/hermes/company-ai-system/workspaces/xiaomei/research/profit-ticket-pipeline-feedback/metrics-2026-06-16-feedback.json
- artifact_candidates: /root/hermes/company-ai-system/workspaces/xiaomei/research/profit-ticket-pipeline-feedback/candidates-2026-06-16-feedback.csv
- artifact_forward_tracking: /root/hermes/company-ai-system/workspaces/xiaomei/research/profit-ticket-pipeline-feedback/forward-tracking-2026-06-16-feedback.csv

## Backtest Feedback Applied
- feedback_win_rate: 53%
- symbol_penalties: ADBE, ALNY, CPB, HUBB, KLAC

## Methodology References
- UZI-Skill: risk checklist and multi-dimensional review
- TradingAgents: role-based research synthesis
- Serenity Skill: theme and supply-chain catalyst mapping
- Buffett Skills: quality, margin-of-safety, bear-case framing
- QuantDinger: replay discipline and data-health guardrails

## Price-Volume Summary
- equal_weight_20d_benchmark: 0.05354974917640132
- median_20d_momentum: 0.04272386339799983
- median_5d_acceleration: -0.023074008726640727
- median_volume_confirmation: -0.03666160141731828
- median_relative_strength: -0.01082588577840149
- top_market_score_p90: 0.681750972762646

## Paper Review Candidates
- none

## Market Watchlist Needs Evidence
|rank|symbol|company|latest|intraday|source_gap|market_score|catalyst_score|ticket_score|narrative|business|gate_status|
|---|---|---|---|---|---|---|---|---|---|---|---|
|1|INTC|英特尔|128.01|0.02761499558481173|0.004084518980444485|0.8284046692607003|0.0|0.8484046692607004|missing|missing|MARKET_WATCHLIST_NEEDS_EVIDENCE|
  - ticket_card: research_only=true allow_trade=false auto_order=false no_broker_api=true
  - kline_source: Yahoo Finance historical kline
  - quote_source: EastMoney US realtime/delayed quote + kline | status=ok | prev_close=124.57 | cross_check_basis=latest_price | gap=0.004084518980444485 | mismatch=false
  - catalyst: No relevant public catalyst evidence found.
|2|SJM|The J. M. Smucker Company|None|None|None|0.8404669260700388|0.0|0.8404669260700388|missing|missing|MARKET_WATCHLIST_NEEDS_EVIDENCE|
  - ticket_card: research_only=true allow_trade=false auto_order=false no_broker_api=true
  - kline_source: Yahoo Finance historical kline
  - quote_source: EastMoney US realtime/delayed quote + kline | status=unavailable | prev_close=None | cross_check_basis=unavailable | gap=None | mismatch=false
  - catalyst: No relevant public catalyst evidence found.
|3|CAH|CAH|None|None|None|0.7992217898832684|0.0|0.7992217898832684|found_unrelated|found_unrelated|MARKET_WATCHLIST_NEEDS_EVIDENCE|
  - ticket_card: research_only=true allow_trade=false auto_order=false no_broker_api=true
  - kline_source: Yahoo Finance historical kline
  - quote_source: EastMoney US realtime/delayed quote + kline | status=unavailable | prev_close=None | cross_check_basis=unavailable | gap=None | mismatch=false
  - catalyst: No relevant public catalyst evidence found.

## Catalyst Summary
- candidates_with_narrative_relevant: 0
- candidates_with_business_relevant: 0
- top_shared_titles: []

## Evidence Gaps
### 1. INTC
- company: 英特尔 (eastmoney_us)
- narrative query: INTC 英特尔 stock catalyst earnings news
- business query: INTC 英特尔 orders demand backlog guidance revenue customer contract
- narrative ranked candidates: 0 | status: missing | returncode: 0
- business ranked candidates: 0 | status: missing | returncode: 0
- evidence gap reason: last30days_returned_zero_ranked_candidates
### 2. SJM
- company: The J. M. Smucker Company (fallback)
- narrative query: SJM j m smucker stock catalyst earnings news
- business query: SJM j m smucker orders demand backlog guidance revenue customer contract
- narrative ranked candidates: 0 | status: missing | returncode: 0
- business ranked candidates: 0 | status: missing | returncode: 0
- evidence gap reason: last30days_returned_zero_ranked_candidates
### 3. CAH
- company: CAH (symbol)
- narrative query: CAH cah stock catalyst earnings news
- business query: CAH cah orders demand backlog guidance revenue customer contract
- narrative ranked candidates: 6 | status: found_unrelated | returncode: 0
- business ranked candidates: 6 | status: found_unrelated | returncode: 0
- evidence gap reason: found_unrelated_public_items;relevant_narrative_missing;relevant_business_missing

## Quality Check (Buffett Skills)
### INTC: MODERATE (score=0.54)
  - roe: 0.00
  - pe_ttm: 1.00
  - dividend_yield: 0.00
  - price_position_52w: 0.71
  - liquidity_amount: 1.00
### SJM: POOR (score=0.00)
### CAH: POOR (score=0.00)

## Risk Checklist (UZI-Skill)
### INTC: WATCH (red=0, yellow=2)
  - price_extended_vs_52w: [YELLOW] latest/52w_high=96.4%
  - intraday_gap: [GREEN] intraday_pct_chg=2.76%
  - liquidity: [GREEN] amount=13,652,849,920
  - valuation: [GREEN] pe_ttm=5.78
  - quality_gap: [YELLOW] roe=-330.00%
  - price_manipulation: [GREEN] 5d_accel=-0.0161
  - news_red_flags: [GREEN] narrative_status=missing
  - supply_chain_risk: [GREEN] business_status=missing
  - short_interest: [GREEN] provider_field_unavailable
  - dilution_risk: [GREEN] provider_field_unavailable
  - debt_covenant: [GREEN] provider_field_unavailable
  - earnings_quality: [GREEN] provider_field_unavailable
  - insider_selling: [GREEN] provider_field_unavailable
  - regulatory_risk: [GREEN] provider_field_unavailable
  - concentration_risk: [GREEN] provider_field_unavailable
### SJM: CLEAN (red=0, yellow=0)
  - price_extended_vs_52w: [GREEN] provider_field_unavailable
  - intraday_gap: [GREEN] provider_field_unavailable
  - liquidity: [GREEN] provider_field_unavailable
  - valuation: [GREEN] provider_field_unavailable
  - quality_gap: [GREEN] provider_field_unavailable
  - price_manipulation: [GREEN] 5d_accel=-0.0139
  - news_red_flags: [GREEN] narrative_status=missing
  - supply_chain_risk: [GREEN] business_status=missing
  - short_interest: [GREEN] provider_field_unavailable
  - dilution_risk: [GREEN] provider_field_unavailable
  - debt_covenant: [GREEN] provider_field_unavailable
  - earnings_quality: [GREEN] provider_field_unavailable
  - insider_selling: [GREEN] provider_field_unavailable
  - regulatory_risk: [GREEN] provider_field_unavailable
  - concentration_risk: [GREEN] provider_field_unavailable
### CAH: WATCH (red=0, yellow=2)
  - price_extended_vs_52w: [GREEN] provider_field_unavailable
  - intraday_gap: [GREEN] provider_field_unavailable
  - liquidity: [GREEN] provider_field_unavailable
  - valuation: [GREEN] provider_field_unavailable
  - quality_gap: [GREEN] provider_field_unavailable
  - price_manipulation: [GREEN] 5d_accel=-0.0526
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
### INTC: MIXED (pos=1, neg=1)
  - fundamental_analyst: Quality verdict: MODERATE (score=0.54)
  - news_analyst: News status: missing, relevance=0.00
  - sentiment_analyst: Business/sentiment status: missing, relevance=0.00
  - technical_analyst: Signals: strong_momentum, outperforming_market
  - bull_case: Bull points: 1
  - bear_case: Bear points: 1
  - risk_manager: Risk: WATCH, Quality: MODERATE, Rec: PROCEED_WITH_MONITORING
### SJM: MIXED (pos=0, neg=1)
  - fundamental_analyst: Quality verdict: POOR (score=0.00)
  - news_analyst: News status: missing, relevance=0.00
  - sentiment_analyst: Business/sentiment status: missing, relevance=0.00
  - technical_analyst: Signals: strong_momentum, outperforming_market, volume_confirmed
  - bull_case: Bull points: 2
  - bear_case: Bear points: 1
  - risk_manager: Risk: CLEAN, Quality: POOR, Rec: PROCEED
### CAH: BEARISH_CONSENSUS (pos=0, neg=3)
  - fundamental_analyst: Quality verdict: POOR (score=0.00)
  - news_analyst: News status: found_unrelated, relevance=0.00
  - sentiment_analyst: Business/sentiment status: found_unrelated, relevance=0.00
  - technical_analyst: Signals: strong_momentum, outperforming_market, volume_confirmed
  - bull_case: Bull points: 2
  - bear_case: Bear points: 3
  - risk_manager: Risk: WATCH, Quality: POOR, Rec: PROCEED_WITH_MONITORING

## Supply Chain Map (Serenity Skill)
- INTC: no_supply_chain_data | themes=[]
- SJM: no_supply_chain_data | themes=[]
- CAH: no_supply_chain_data | themes=[]

## Replay Hypothesis (QuantDinger)
- INTC: Entry=no_entry, SL=0.0%, TP=0.0%, Period=N/A, Conf=20%
- SJM: Entry=no_entry, SL=0.0%, TP=0.0%, Period=N/A, Conf=20%
- CAH: Entry=no_entry, SL=0.0%, TP=0.0%, Period=N/A, Conf=20%

## Risk Management (Cross-Platform Best Practices)
### INTC: ALLOWED
  - stop_loss: $117.76
  - take_profit: $150.09
  - risk_reward: 2.00
  - kelly_fraction: N/A
  - risk_score: 0.40
  - confidence: 0.60
### SJM: ALLOWED
  - stop_loss: $106.06
  - take_profit: $135.19
  - risk_reward: 2.00
  - kelly_fraction: N/A
  - risk_score: 0.40
  - confidence: 0.60
### CAH: ALLOWED
  - stop_loss: $207.30
  - take_profit: $264.23
  - risk_reward: 2.00
  - kelly_fraction: N/A
  - risk_score: 0.40
  - confidence: 0.60

## Forward Tracking
|symbol|rank|horizon|due_date|status|
|---|---|---|---|---|
|INTC|1|1d|2026-06-16|pending|
|INTC|1|3d|2026-06-18|pending|
|INTC|1|5d|2026-06-22|pending|
|INTC|1|10d|2026-06-29|pending|
|SJM|2|1d|2026-06-16|pending|
|SJM|2|3d|2026-06-18|pending|
|SJM|2|5d|2026-06-22|pending|
|SJM|2|10d|2026-06-29|pending|
|CAH|3|1d|2026-06-16|pending|
|CAH|3|3d|2026-06-18|pending|
|CAH|3|5d|2026-06-22|pending|
|CAH|3|10d|2026-06-29|pending|

## Market Snapshot Top 10
- momentum_exhaustion_guard_threshold: -0.15
- momentum_exhaustion_guard_adjustment: -0.08
|rank|symbol|raw_market_score|market_score|rule|prior_20d|accel_5d|volume_confirm|rs_vs_equal_weight|
|---|---|---|---|---|---|---|---|---|
|1|SJM|0.8404669260700388|0.8404669260700388||0.1514819533404932|-0.013916851033360267|0.6023320007350368|0.09793220416409187|
|2|INTC|0.8284046692607003|0.8284046692607003||0.18171377796307864|-0.016074822897494734|0.19824348488042687|0.12816402878667732|
|3|CAH|0.7992217898832684|0.7992217898832684||0.15919568357617253|-0.0526082489892401|0.5242654516592298|0.10564593439977121|
|4|SW|0.7863813229571985|0.7863813229571985||0.19823907139600916|-0.08935018627472258|0.5199160765466626|0.14468932221960784|
|5|HOOD|0.7844357976653696|0.7844357976653696||0.279621465718066|-0.11887360563132732|0.3273857451399318|0.2260717165416647|
|6|IP|0.7770428015564204|0.7770428015564204||0.23343018312838093|-0.11428834372457897|0.3376268091918724|0.1798804339519796|
|7|WDC|0.772373540856031|0.772373540856031||0.3524541068883902|-0.11559152686176977|0.09926152866229732|0.29890435771198887|
|8|SWK|0.7642023346303503|0.7642023346303503||0.14412037858955595|-0.060967457657403745|0.2789512476446647|0.09057062941315464|
|9|CCL|0.7634241245136186|0.7634241245136186||0.2386688186190873|-0.11556630742268248|0.202768217116154|0.18511906944268597|
|10|STX|0.7536964980544747|0.7536964980544747||0.26839479535762356|-0.11761414795073177|0.07907112522246362|0.21484504618122224|

## Final Classification
- MARKET_WATCHLIST_NEEDS_EVIDENCE
