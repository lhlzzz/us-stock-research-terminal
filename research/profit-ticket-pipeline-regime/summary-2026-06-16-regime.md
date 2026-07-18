# XIAOMEI US Profit Ticket Pipeline V0

RESEARCH_ONLY
NOT_TRADING_ADVICE
NO_BROKER
NO_ORDER
NO_LEDGER
NO_LIVE_TRADE

- output_date: 2026-06-16-regime
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
- universe_included_symbols: 511
- period_used: 1y
- classification: MARKET_WATCHLIST_NEEDS_EVIDENCE
- candidate_pool_size: 3
- top_k: 3
- paper_review_count: 0
- market_watchlist_count: 3
- zero_paper_review_is_valid_output: True
- artifact_summary: /root/hermes/company-ai-system/workspaces/xiaomei/research/profit-ticket-pipeline-regime/summary-2026-06-16-regime.md
- artifact_metrics: /root/hermes/company-ai-system/workspaces/xiaomei/research/profit-ticket-pipeline-regime/metrics-2026-06-16-regime.json
- artifact_candidates: /root/hermes/company-ai-system/workspaces/xiaomei/research/profit-ticket-pipeline-regime/candidates-2026-06-16-regime.csv
- artifact_forward_tracking: /root/hermes/company-ai-system/workspaces/xiaomei/research/profit-ticket-pipeline-regime/forward-tracking-2026-06-16-regime.csv

## Backtest Feedback Applied
- feedback_win_rate: 53%
- symbol_penalties: ADBE, ALNY, CPB, HUBB, KLAC

## Market Regime: RISK_ON
- breadth: 72.4% (stocks with positive 20d return)
- momentum: +3.96% (median 20d return)
- volatility: 0.0144 (median daily |return|)
- advance_ratio: 52.1% (1d advancers)
- description: Broad strength, loose thresholds, wider stops
- scoring_weights: {'prior_20d_momentum': 0.25, 'five_day_acceleration': 0.1, 'volume_confirmation_ratio': 0.35, 'relative_strength_vs_equal_weight': 0.3}
- exhaustion_threshold: -0.2
- position_cap: 15%
- min_market_score_gate: 0.0
- kelly_fraction_cap: 100%
- stop_loss_multiplier: 1.2x
- take_profit_multiplier: 0.8x

## Methodology References
- UZI-Skill: risk checklist and multi-dimensional review
- TradingAgents: role-based research synthesis
- Serenity Skill: theme and supply-chain catalyst mapping
- Buffett Skills: quality, margin-of-safety, bear-case framing
- QuantDinger: replay discipline and data-health guardrails

## Price-Volume Summary
- equal_weight_20d_benchmark: 0.05299990534012941
- median_20d_momentum: 0.04364606366640045
- median_5d_acceleration: -0.023783268155786796
- median_volume_confirmation: 0.008946442567714374
- median_relative_strength: -0.009353841673728963
- top_market_score_p90: 0.7395303326810176

## Paper Review Candidates
- none

## Market Watchlist Needs Evidence
|rank|symbol|company|latest|intraday|source_gap|market_score|catalyst_score|ticket_score|narrative|business|gate_status|
|---|---|---|---|---|---|---|---|---|---|---|---|
|1|AMAT|应用材料|585.78|0.032666372851476444|5.001344116628559e-08|0.8875733855185909|0.0|0.9375733855185909|missing|missing|MARKET_WATCHLIST_NEEDS_EVIDENCE|
  - ticket_card: research_only=true allow_trade=false auto_order=false no_broker_api=true
  - kline_source: Yahoo Finance historical kline
  - quote_source: EastMoney US realtime/delayed quote + kline | status=ok | prev_close=567.25 | cross_check_basis=latest_price | gap=5.001344116628559e-08 | mismatch=false
  - catalyst: No relevant public catalyst evidence found.
|2|LRCX|拉姆研究|388.92|0.060276437392655646|3.4525696523957095e-08|0.8905088062622308|0.0|0.9105088062622309|missing|missing|MARKET_WATCHLIST_NEEDS_EVIDENCE|
  - ticket_card: research_only=true allow_trade=false auto_order=false no_broker_api=true
  - kline_source: Yahoo Finance historical kline
  - quote_source: EastMoney US realtime/delayed quote + kline | status=ok | prev_close=366.81 | cross_check_basis=latest_price | gap=3.4525696523957095e-08 | mismatch=false
  - catalyst: No relevant public catalyst evidence found.
|3|SJM|The J. M. Smucker Company|None|None|None|0.886986301369863|0.0|0.886986301369863|found_unrelated|missing|MARKET_WATCHLIST_NEEDS_EVIDENCE|
  - ticket_card: research_only=true allow_trade=false auto_order=false no_broker_api=true
  - kline_source: Yahoo Finance historical kline
  - quote_source: EastMoney US realtime/delayed quote + kline | status=unavailable | prev_close=None | cross_check_basis=unavailable | gap=None | mismatch=false
  - catalyst: No relevant public catalyst evidence found.

## Catalyst Summary
- candidates_with_narrative_relevant: 0
- candidates_with_business_relevant: 0
- top_shared_titles: []

## Evidence Gaps
### 1. AMAT
- company: 应用材料 (eastmoney_us)
- narrative query: AMAT 应用材料 stock catalyst earnings news
- business query: AMAT 应用材料 orders demand backlog guidance revenue customer contract
- narrative ranked candidates: 0 | status: missing | returncode: 0
- business ranked candidates: 0 | status: missing | returncode: 0
- evidence gap reason: last30days_returned_zero_ranked_candidates
### 2. LRCX
- company: 拉姆研究 (eastmoney_us)
- narrative query: LRCX 拉姆研究 stock catalyst earnings news
- business query: LRCX 拉姆研究 orders demand backlog guidance revenue customer contract
- narrative ranked candidates: 0 | status: missing | returncode: 0
- business ranked candidates: 0 | status: missing | returncode: 0
- evidence gap reason: last30days_returned_zero_ranked_candidates
### 3. SJM
- company: The J. M. Smucker Company (fallback)
- narrative query: SJM j m smucker stock catalyst earnings news
- business query: SJM j m smucker orders demand backlog guidance revenue customer contract
- narrative ranked candidates: 2 | status: found_unrelated | returncode: 0
- business ranked candidates: 0 | status: missing | returncode: 0
- evidence gap reason: found_unrelated_public_items;relevant_narrative_missing;relevant_business_missing

## Quality Check (Buffett Skills)
### AMAT: STRONG (score=0.70)
  - roe: 1.00
  - pe_ttm: 0.81
  - dividend_yield: 0.00
  - price_position_52w: 0.70
  - liquidity_amount: 1.00
### LRCX: MODERATE (score=0.59)
  - roe: 1.00
  - pe_ttm: 0.28
  - dividend_yield: 0.00
  - price_position_52w: 0.68
  - liquidity_amount: 1.00
### SJM: POOR (score=0.00)

## Risk Checklist (UZI-Skill)
### AMAT: ELEVATED (red=1, yellow=1)
  - price_extended_vs_52w: [YELLOW] latest/52w_high=97.7%
  - intraday_gap: [GREEN] intraday_pct_chg=3.27%
  - liquidity: [GREEN] amount=6,830,765,824
  - valuation: [GREEN] pe_ttm=19.45
  - quality_gap: [GREEN] roe=2180.00%
  - price_manipulation: [RED] 5d_accel=-0.1531
  - news_red_flags: [GREEN] narrative_status=missing
  - supply_chain_risk: [GREEN] business_status=missing
  - short_interest: [GREEN] provider_field_unavailable
  - dilution_risk: [GREEN] provider_field_unavailable
  - debt_covenant: [GREEN] provider_field_unavailable
  - earnings_quality: [GREEN] provider_field_unavailable
  - insider_selling: [GREEN] provider_field_unavailable
  - regulatory_risk: [GREEN] provider_field_unavailable
  - concentration_risk: [GREEN] provider_field_unavailable
### LRCX: ELEVATED (red=1, yellow=1)
  - price_extended_vs_52w: [YELLOW] latest/52w_high=98.9%
  - intraday_gap: [GREEN] intraday_pct_chg=6.03%
  - liquidity: [GREEN] amount=5,200,483,328
  - valuation: [GREEN] pe_ttm=45.95
  - quality_gap: [GREEN] roe=4879.00%
  - price_manipulation: [RED] 5d_accel=-0.1673
  - news_red_flags: [GREEN] narrative_status=missing
  - supply_chain_risk: [GREEN] business_status=missing
  - short_interest: [GREEN] provider_field_unavailable
  - dilution_risk: [GREEN] provider_field_unavailable
  - debt_covenant: [GREEN] provider_field_unavailable
  - earnings_quality: [GREEN] provider_field_unavailable
  - insider_selling: [GREEN] provider_field_unavailable
  - regulatory_risk: [GREEN] provider_field_unavailable
  - concentration_risk: [GREEN] provider_field_unavailable
### SJM: WATCH (red=0, yellow=1)
  - price_extended_vs_52w: [GREEN] provider_field_unavailable
  - intraday_gap: [GREEN] provider_field_unavailable
  - liquidity: [GREEN] provider_field_unavailable
  - valuation: [GREEN] provider_field_unavailable
  - quality_gap: [GREEN] provider_field_unavailable
  - price_manipulation: [GREEN] 5d_accel=-0.0139
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
### AMAT: MIXED (pos=1, neg=2)
  - fundamental_analyst: Quality verdict: STRONG (score=0.70)
  - news_analyst: News status: missing, relevance=0.00
  - sentiment_analyst: Business/sentiment status: missing, relevance=0.00
  - technical_analyst: Signals: strong_momentum, deceleration_warning, outperforming_market, volume_confirmed
  - bull_case: Bull points: 3
  - bear_case: Bear points: 2
  - risk_manager: Risk: ELEVATED, Quality: STRONG, Rec: PROCEED_WITH_CAUTION
### LRCX: MIXED (pos=1, neg=2)
  - fundamental_analyst: Quality verdict: MODERATE (score=0.59)
  - news_analyst: News status: missing, relevance=0.00
  - sentiment_analyst: Business/sentiment status: missing, relevance=0.00
  - technical_analyst: Signals: strong_momentum, deceleration_warning, outperforming_market, volume_confirmed
  - bull_case: Bull points: 2
  - bear_case: Bear points: 2
  - risk_manager: Risk: ELEVATED, Quality: MODERATE, Rec: PROCEED_WITH_CAUTION
### SJM: MIXED (pos=0, neg=2)
  - fundamental_analyst: Quality verdict: POOR (score=0.00)
  - news_analyst: News status: found_unrelated, relevance=0.00
  - sentiment_analyst: Business/sentiment status: missing, relevance=0.00
  - technical_analyst: Signals: strong_momentum, outperforming_market, volume_confirmed
  - bull_case: Bull points: 2
  - bear_case: Bear points: 2
  - risk_manager: Risk: WATCH, Quality: POOR, Rec: PROCEED_WITH_MONITORING

## Supply Chain Map (Serenity Skill)
- AMAT: no_supply_chain_data | themes=[]
- LRCX: no_supply_chain_data | themes=[]
- SJM: no_supply_chain_data | themes=[]

## Replay Hypothesis (QuantDinger)
- AMAT: Entry=avoid_deceleration, SL=0.0%, TP=0.0%, Period=N/A, Conf=10%
- LRCX: Entry=avoid_deceleration, SL=0.0%, TP=0.0%, Period=N/A, Conf=10%
- SJM: Entry=no_entry, SL=0.0%, TP=0.0%, Period=N/A, Conf=20%

## Risk Management (Cross-Platform Best Practices)
### AMAT: ALLOWED
  - stop_loss: $526.83
  - take_profit: $664.38
  - risk_reward: 2.00
  - kelly_fraction: N/A
  - risk_score: 0.40
  - confidence: 0.60
### LRCX: ALLOWED
  - stop_loss: $349.78
  - take_profit: $441.10
  - risk_reward: 2.00
  - kelly_fraction: N/A
  - risk_score: 0.40
  - confidence: 0.60
### SJM: ALLOWED
  - stop_loss: $104.27
  - take_profit: $131.50
  - risk_reward: 2.00
  - kelly_fraction: N/A
  - risk_score: 0.40
  - confidence: 0.60

## Forward Tracking
|symbol|rank|horizon|due_date|status|
|---|---|---|---|---|
|AMAT|1|1d|2026-06-16|pending|
|AMAT|1|3d|2026-06-18|pending|
|AMAT|1|5d|2026-06-22|pending|
|AMAT|1|10d|2026-06-29|pending|
|LRCX|2|1d|2026-06-16|pending|
|LRCX|2|3d|2026-06-18|pending|
|LRCX|2|5d|2026-06-22|pending|
|LRCX|2|10d|2026-06-29|pending|
|SJM|3|1d|2026-06-16|pending|
|SJM|3|3d|2026-06-18|pending|
|SJM|3|5d|2026-06-22|pending|
|SJM|3|10d|2026-06-29|pending|

## Market Snapshot Top 10
- momentum_exhaustion_guard_threshold: -0.15
- momentum_exhaustion_guard_adjustment: -0.08
|rank|symbol|raw_market_score|market_score|rule|prior_20d|accel_5d|volume_confirm|rs_vs_equal_weight|
|---|---|---|---|---|---|---|---|---|
|1|LRCX|0.8905088062622308|0.8905088062622308||0.365973629391283|-0.16726813148683273|0.5693143621799925|0.31297372405115353|
|2|AMAT|0.8875733855185909|0.8875733855185909||0.3432922306045041|-0.1530936949050401|0.5565129297469631|0.29029232526437465|
|3|SJM|0.886986301369863|0.886986301369863||0.15317288030281428|-0.013937287635579443|0.6331985990406861|0.10017297496268487|
|4|ASML|0.8748532289628179|0.8748532289628179||0.26025260208465895|-0.17813899009772638|0.8289640013840638|0.20725269674452954|
|5|SW|0.8637964774951075|0.8637964774951075||0.1875666719625957|-0.08855436772720804|0.5541627148370136|0.13456676662246628|
|6|HOOD|0.8632093933463796|0.8632093933463796||0.2719730817077106|-0.11816309005393077|0.35820610742775627|0.2189731763675812|
|7|CAH|0.861545988258317|0.861545988258317||0.15983605243864307|-0.05263731110967318|0.5197478053521933|0.10683614709851366|
|8|INTC|0.8503913894324853|0.8503913894324853||0.17550799445117082|-0.01599040577995381|0.18841131115787224|0.12250808911104141|
|9|IP|0.8478473581213307|0.8478473581213307||0.22051724673974782|-0.1130918446177267|0.3336729299592116|0.1675173413996184|
|10|WDC|0.8443248532289628|0.8443248532289628||0.3561686950951046|-0.11590900522964187|0.16728418506342035|0.3031687897549752|

## Final Classification
- MARKET_WATCHLIST_NEEDS_EVIDENCE
