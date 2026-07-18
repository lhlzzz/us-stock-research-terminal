# XIAOMEI US Profit Ticket Pipeline V0

RESEARCH_ONLY
NOT_TRADING_ADVICE
NO_BROKER
NO_ORDER
NO_LEDGER
NO_LIVE_TRADE

- output_date: 2026-06-16-live
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
- classification: CANDIDATE_FOR_PAPER_REVIEW
- candidate_pool_size: 5
- top_k: 5
- paper_review_count: 1
- market_watchlist_count: 4
- zero_paper_review_is_valid_output: False
- artifact_summary: /root/hermes/company-ai-system/workspaces/xiaomei/research/profit-ticket-pipeline-live/summary-2026-06-16-live.md
- artifact_metrics: /root/hermes/company-ai-system/workspaces/xiaomei/research/profit-ticket-pipeline-live/metrics-2026-06-16-live.json
- artifact_candidates: /root/hermes/company-ai-system/workspaces/xiaomei/research/profit-ticket-pipeline-live/candidates-2026-06-16-live.csv
- artifact_forward_tracking: /root/hermes/company-ai-system/workspaces/xiaomei/research/profit-ticket-pipeline-live/forward-tracking-2026-06-16-live.csv

## Backtest Feedback Applied
- feedback_win_rate: 53%
- symbol_penalties: ADBE, ALNY, CPB, HUBB, KLAC

## Market Regime: RISK_ON
- breadth: 73.9% (stocks with positive 20d return)
- momentum: +4.67% (median 20d return)
- volatility: 0.0137 (median daily |return|)
- advance_ratio: 59.1% (1d advancers)
- description: Volume-driven, momentum-light, wide stops in strong market
- scoring_weights: {'prior_20d_momentum': 0.15, 'five_day_acceleration': 0.2, 'volume_confirmation_ratio': 0.45, 'relative_strength_vs_equal_weight': 0.2}
- exhaustion_threshold: -0.25
- position_cap: 15%
- min_market_score_gate: 0.0
- kelly_fraction_cap: 100%
- stop_loss_multiplier: 1.2x
- take_profit_multiplier: 0.8x
- risk_per_trade: 3.0%
- max_single_position: 15%
- max_total_exposure: 60%
- max_consecutive_losses: 3
- daily_max_loss_r: 4.0R
- default_stop_loss: 3.0%

## Methodology References
- UZI-Skill: risk checklist and multi-dimensional review
- TradingAgents: role-based research synthesis
- Serenity Skill: theme and supply-chain catalyst mapping
- Buffett Skills: quality, margin-of-safety, bear-case framing
- QuantDinger: replay discipline and data-health guardrails

## Price-Volume Summary
- equal_weight_20d_benchmark: 0.05949411975228185
- median_20d_momentum: 0.05158408860339292
- median_5d_acceleration: -0.03177691161197371
- median_volume_confirmation: 0.04583028142266121
- median_relative_strength: -0.007910031148888934
- top_market_score_p90: 0.6997391304347828

## Paper Review Candidates
|rank|symbol|company|latest|intraday|source_gap|market_score|catalyst_score|ticket_score|narrative|business|gate_status|
|---|---|---|---|---|---|---|---|---|---|---|---|
|1|ASML|阿斯麦|1892.66|0.01562072388720459|1.8059073902954026e-08|0.7817391304347826|0.1875|0.9892391304347826|found_relevant|found_unrelated|CANDIDATE_FOR_PAPER_REVIEW|
  - ticket_card: research_only=true allow_trade=false auto_order=false no_broker_api=true
  - kline_source: Yahoo Finance historical kline
  - quote_source: EastMoney US realtime/delayed quote + kline | status=ok | prev_close=1863.55 | cross_check_basis=latest_price | gap=1.8059073902954026e-08 | mismatch=false
  - catalyst: ASML Becomes Europe's Most Valuable Stock Ever on AI Boom

## Market Watchlist Needs Evidence
|rank|symbol|company|latest|intraday|source_gap|market_score|catalyst_score|ticket_score|narrative|business|gate_status|
|---|---|---|---|---|---|---|---|---|---|---|---|
|2|HOOD|Robinhood Markets Inc-A|98.12|0.052902671960510794|2.7992070439353256e-08|0.7630434782608696|0.0|0.8130434782608696|found_unrelated|found_unrelated|MARKET_WATCHLIST_NEEDS_EVIDENCE|
  - ticket_card: research_only=true allow_trade=false auto_order=false no_broker_api=true
  - kline_source: Yahoo Finance historical kline
  - quote_source: EastMoney US realtime/delayed quote + kline | status=ok | prev_close=93.19 | cross_check_basis=latest_price | gap=2.7992070439353256e-08 | mismatch=false
  - catalyst: No relevant public catalyst evidence found.
|3|POOL|Pool Corp|191.03|-0.02035897435897438|6.390112217147248e-09|0.758695652173913|0.0|0.808695652173913|found_unrelated|found_unrelated|MARKET_WATCHLIST_NEEDS_EVIDENCE|
  - ticket_card: research_only=true allow_trade=false auto_order=false no_broker_api=true
  - kline_source: Yahoo Finance historical kline
  - quote_source: EastMoney US realtime/delayed quote + kline | status=ok | prev_close=195.0 | cross_check_basis=latest_price | gap=6.390112217147248e-09 | mismatch=false
  - catalyst: No relevant public catalyst evidence found.
|4|FCX|FCX|None|None|None|0.7730434782608697|0.0|0.7730434782608697|found_unrelated|found_unrelated|MARKET_WATCHLIST_NEEDS_EVIDENCE|
  - ticket_card: research_only=true allow_trade=false auto_order=false no_broker_api=true
  - kline_source: Yahoo Finance historical kline
  - quote_source: EastMoney US realtime/delayed quote + kline | status=unavailable | prev_close=None | cross_check_basis=unavailable | gap=None | mismatch=false
  - catalyst: No relevant public catalyst evidence found.
|5|ARE|ARE|None|None|None|0.7634782608695653|0.0|0.7634782608695653|found_unrelated|found_unrelated|MARKET_WATCHLIST_NEEDS_EVIDENCE|
  - ticket_card: research_only=true allow_trade=false auto_order=false no_broker_api=true
  - kline_source: Yahoo Finance historical kline
  - quote_source: EastMoney US realtime/delayed quote + kline | status=unavailable | prev_close=None | cross_check_basis=unavailable | gap=None | mismatch=false
  - catalyst: No relevant public catalyst evidence found.

## Catalyst Summary
- candidates_with_narrative_relevant: 1
- candidates_with_business_relevant: 0
- top_shared_titles: [["ASML Becomes Europe's Most Valuable Stock Ever on AI Boom", 1]]

## Evidence Gaps
### 1. ASML
- company: 阿斯麦 (eastmoney_us)
- narrative query: ASML 阿斯麦 stock catalyst earnings news
- business query: ASML 阿斯麦 orders demand backlog guidance revenue customer contract
- narrative ranked candidates: 2 | status: found_relevant | returncode: 0
- business ranked candidates: 6 | status: found_unrelated | returncode: 0
- evidence gap reason: paper_review_gate_passed
### 2. HOOD
- company: Robinhood Markets Inc-A (eastmoney_us)
- narrative query: HOOD robinhood markets inc a stock catalyst earnings news
- business query: HOOD robinhood markets inc a orders demand backlog guidance revenue customer contract
- narrative ranked candidates: 2 | status: found_unrelated | returncode: 0
- business ranked candidates: 2 | status: found_unrelated | returncode: 0
- evidence gap reason: found_unrelated_public_items;relevant_narrative_missing;relevant_business_missing
### 3. POOL
- company: Pool Corp (eastmoney_us)
- narrative query: POOL pool stock catalyst earnings news
- business query: POOL pool orders demand backlog guidance revenue customer contract
- narrative ranked candidates: 7 | status: found_unrelated | returncode: 0
- business ranked candidates: 6 | status: found_unrelated | returncode: 0
- evidence gap reason: found_unrelated_public_items;relevant_narrative_missing;relevant_business_missing
### 4. FCX
- company: FCX (symbol)
- narrative query: FCX fcx stock catalyst earnings news
- business query: FCX fcx orders demand backlog guidance revenue customer contract
- narrative ranked candidates: 6 | status: found_unrelated | returncode: 0
- business ranked candidates: 6 | status: found_unrelated | returncode: 0
- evidence gap reason: found_unrelated_public_items;relevant_narrative_missing;relevant_business_missing
### 5. ARE
- company: ARE (symbol)
- narrative query: ARE are stock catalyst earnings news
- business query: ARE are orders demand backlog guidance revenue customer contract
- narrative ranked candidates: 6 | status: found_unrelated | returncode: 0
- business ranked candidates: 6 | status: found_unrelated | returncode: 0
- evidence gap reason: found_unrelated_public_items;relevant_narrative_missing;relevant_business_missing

## Quality Check (Buffett Skills)
### ASML: MODERATE (score=0.65)
  - roe: 1.00
  - pe_ttm: 0.59
  - dividend_yield: 0.00
  - price_position_52w: 0.68
  - liquidity_amount: 1.00
### HOOD: STRONG (score=0.97)
  - roe: 1.00
  - pe_ttm: 1.00
  - dividend_yield: 1.00
  - price_position_52w: 0.85
  - liquidity_amount: 1.00
### POOL: STRONG (score=0.75)
  - roe: 1.00
  - pe_ttm: 1.00
  - dividend_yield: 0.00
  - price_position_52w: 0.75
  - liquidity_amount: 1.00
### FCX: POOR (score=0.00)
### ARE: POOR (score=0.00)

## Risk Checklist (UZI-Skill)
### ASML: ELEVATED (red=1, yellow=2)
  - price_extended_vs_52w: [YELLOW] latest/52w_high=98.9%
  - intraday_gap: [GREEN] intraday_pct_chg=1.56%
  - liquidity: [GREEN] amount=4,424,379,648
  - valuation: [GREEN] pe_ttm=30.39
  - quality_gap: [GREEN] roe=1363.00%
  - price_manipulation: [RED] 5d_accel=-0.1781
  - news_red_flags: [GREEN] narrative_status=found_relevant
  - supply_chain_risk: [YELLOW] business_status=found_unrelated
  - short_interest: [GREEN] provider_field_unavailable
  - dilution_risk: [GREEN] provider_field_unavailable
  - debt_covenant: [GREEN] provider_field_unavailable
  - earnings_quality: [GREEN] provider_field_unavailable
  - insider_selling: [GREEN] provider_field_unavailable
  - regulatory_risk: [GREEN] provider_field_unavailable
  - concentration_risk: [GREEN] provider_field_unavailable
### HOOD: ELEVATED (red=0, yellow=3)
  - price_extended_vs_52w: [GREEN] latest/52w_high=63.8%
  - intraday_gap: [GREEN] intraday_pct_chg=5.29%
  - liquidity: [GREEN] amount=3,627,264,416
  - valuation: [GREEN] pe_ttm=9.48
  - quality_gap: [GREEN] roe=379.00%
  - price_manipulation: [YELLOW] 5d_accel=-0.1182
  - news_red_flags: [YELLOW] narrative_status=found_unrelated
  - supply_chain_risk: [YELLOW] business_status=found_unrelated
  - short_interest: [GREEN] provider_field_unavailable
  - dilution_risk: [GREEN] provider_field_unavailable
  - debt_covenant: [GREEN] provider_field_unavailable
  - earnings_quality: [GREEN] provider_field_unavailable
  - insider_selling: [GREEN] provider_field_unavailable
  - regulatory_risk: [GREEN] provider_field_unavailable
  - concentration_risk: [GREEN] provider_field_unavailable
### POOL: WATCH (red=0, yellow=2)
  - price_extended_vs_52w: [GREEN] latest/52w_high=56.2%
  - intraday_gap: [GREEN] intraday_pct_chg=-2.04%
  - liquidity: [GREEN] amount=192,114,673
  - valuation: [GREEN] pe_ttm=6.14
  - quality_gap: [GREEN] roe=459.00%
  - price_manipulation: [GREEN] 5d_accel=-0.0337
  - news_red_flags: [YELLOW] narrative_status=found_unrelated
  - supply_chain_risk: [YELLOW] business_status=found_unrelated
  - short_interest: [GREEN] provider_field_unavailable
  - dilution_risk: [GREEN] provider_field_unavailable
  - debt_covenant: [GREEN] provider_field_unavailable
  - earnings_quality: [GREEN] provider_field_unavailable
  - insider_selling: [GREEN] provider_field_unavailable
  - regulatory_risk: [GREEN] provider_field_unavailable
  - concentration_risk: [GREEN] provider_field_unavailable
### FCX: WATCH (red=0, yellow=2)
  - price_extended_vs_52w: [GREEN] provider_field_unavailable
  - intraday_gap: [GREEN] provider_field_unavailable
  - liquidity: [GREEN] provider_field_unavailable
  - valuation: [GREEN] provider_field_unavailable
  - quality_gap: [GREEN] provider_field_unavailable
  - price_manipulation: [GREEN] 5d_accel=-0.0157
  - news_red_flags: [YELLOW] narrative_status=found_unrelated
  - supply_chain_risk: [YELLOW] business_status=found_unrelated
  - short_interest: [GREEN] provider_field_unavailable
  - dilution_risk: [GREEN] provider_field_unavailable
  - debt_covenant: [GREEN] provider_field_unavailable
  - earnings_quality: [GREEN] provider_field_unavailable
  - insider_selling: [GREEN] provider_field_unavailable
  - regulatory_risk: [GREEN] provider_field_unavailable
  - concentration_risk: [GREEN] provider_field_unavailable
### ARE: ELEVATED (red=0, yellow=3)
  - price_extended_vs_52w: [GREEN] provider_field_unavailable
  - intraday_gap: [GREEN] provider_field_unavailable
  - liquidity: [GREEN] provider_field_unavailable
  - valuation: [GREEN] provider_field_unavailable
  - quality_gap: [GREEN] provider_field_unavailable
  - price_manipulation: [YELLOW] 5d_accel=-0.1226
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
### ASML: BEARISH_CONSENSUS (pos=2, neg=3)
  - fundamental_analyst: Quality verdict: MODERATE (score=0.65)
  - news_analyst: News status: found_relevant, relevance=0.75
  - sentiment_analyst: Business/sentiment status: found_unrelated, relevance=0.00
  - technical_analyst: Signals: strong_momentum, deceleration_warning, outperforming_market, volume_confirmed
  - bull_case: Bull points: 4
  - bear_case: Bear points: 3
  - risk_manager: Risk: ELEVATED, Quality: MODERATE, Rec: PROCEED_WITH_CAUTION
### HOOD: BEARISH_CONSENSUS (pos=1, neg=3)
  - fundamental_analyst: Quality verdict: STRONG (score=0.97)
  - news_analyst: News status: found_unrelated, relevance=0.00
  - sentiment_analyst: Business/sentiment status: found_unrelated, relevance=0.00
  - technical_analyst: Signals: strong_momentum, deceleration_warning, outperforming_market, volume_confirmed
  - bull_case: Bull points: 3
  - bear_case: Bear points: 3
  - risk_manager: Risk: ELEVATED, Quality: STRONG, Rec: PROCEED_WITH_CAUTION
### POOL: MIXED (pos=1, neg=2)
  - fundamental_analyst: Quality verdict: STRONG (score=0.75)
  - news_analyst: News status: found_unrelated, relevance=0.00
  - sentiment_analyst: Business/sentiment status: found_unrelated, relevance=0.00
  - technical_analyst: Signals: moderate_momentum, volume_confirmed
  - bull_case: Bull points: 2
  - bear_case: Bear points: 2
  - risk_manager: Risk: WATCH, Quality: STRONG, Rec: PROCEED_WITH_MONITORING
### FCX: BEARISH_CONSENSUS (pos=0, neg=3)
  - fundamental_analyst: Quality verdict: POOR (score=0.00)
  - news_analyst: News status: found_unrelated, relevance=0.00
  - sentiment_analyst: Business/sentiment status: found_unrelated, relevance=0.00
  - technical_analyst: Signals: strong_momentum, outperforming_market
  - bull_case: Bull points: 1
  - bear_case: Bear points: 3
  - risk_manager: Risk: WATCH, Quality: POOR, Rec: PROCEED_WITH_MONITORING
### ARE: BEARISH_CONSENSUS (pos=0, neg=4)
  - fundamental_analyst: Quality verdict: POOR (score=0.00)
  - news_analyst: News status: found_unrelated, relevance=0.00
  - sentiment_analyst: Business/sentiment status: found_unrelated, relevance=0.00
  - technical_analyst: Signals: strong_momentum, deceleration_warning, outperforming_market, volume_confirmed
  - bull_case: Bull points: 2
  - bear_case: Bear points: 4
  - risk_manager: Risk: ELEVATED, Quality: POOR, Rec: PROCEED_WITH_CAUTION

## Supply Chain Map (Serenity Skill)
- ASML: no_supply_chain_data | themes=[]
- HOOD: no_supply_chain_data | themes=[]
- POOL: no_supply_chain_data | themes=[]
- FCX: no_supply_chain_data | themes=[]
- ARE: no_supply_chain_data | themes=[]

## Replay Hypothesis (QuantDinger)
- ASML: Entry=avoid_deceleration, SL=0.0%, TP=0.0%, Period=N/A, Conf=10%
- HOOD: Entry=no_entry, SL=0.0%, TP=0.0%, Period=N/A, Conf=20%
- POOL: Entry=no_entry, SL=0.0%, TP=0.0%, Period=N/A, Conf=20%
- FCX: Entry=no_entry, SL=0.0%, TP=0.0%, Period=N/A, Conf=20%
- ARE: Entry=no_entry, SL=0.0%, TP=0.0%, Period=N/A, Conf=20%

## Risk Management (Cross-Platform Best Practices)
### ASML: ALLOWED
  - stop_loss: $1702.20
  - take_profit: $2146.61
  - risk_reward: 2.00
  - kelly_fraction: N/A
  - risk_score: 0.40
  - confidence: 0.60
### HOOD: ALLOWED
  - stop_loss: $88.25
  - take_profit: $111.29
  - risk_reward: 2.00
  - kelly_fraction: N/A
  - risk_score: 0.40
  - confidence: 0.60
### POOL: ALLOWED
  - stop_loss: $171.81
  - take_profit: $216.66
  - risk_reward: 2.00
  - kelly_fraction: N/A
  - risk_score: 0.40
  - confidence: 0.60
### FCX: ALLOWED
  - stop_loss: $63.07
  - take_profit: $79.54
  - risk_reward: 2.00
  - kelly_fraction: N/A
  - risk_score: 0.40
  - confidence: 0.60
### ARE: ALLOWED
  - stop_loss: $47.11
  - take_profit: $59.41
  - risk_reward: 2.00
  - kelly_fraction: N/A
  - risk_score: 0.40
  - confidence: 0.60

## Forward Tracking
|symbol|rank|horizon|due_date|status|
|---|---|---|---|---|
|ASML|1|1d|2026-06-16|pending|
|ASML|1|3d|2026-06-18|pending|
|ASML|1|5d|2026-06-22|pending|
|ASML|1|10d|2026-06-29|pending|
|HOOD|2|1d|2026-06-16|pending|
|HOOD|2|3d|2026-06-18|pending|
|HOOD|2|5d|2026-06-22|pending|
|HOOD|2|10d|2026-06-29|pending|
|POOL|3|1d|2026-06-16|pending|
|POOL|3|3d|2026-06-18|pending|
|POOL|3|5d|2026-06-22|pending|
|POOL|3|10d|2026-06-29|pending|
|FCX|4|1d|2026-06-16|pending|
|FCX|4|3d|2026-06-18|pending|
|FCX|4|5d|2026-06-22|pending|
|FCX|4|10d|2026-06-29|pending|
|ARE|5|1d|2026-06-16|pending|
|ARE|5|3d|2026-06-18|pending|
|ARE|5|5d|2026-06-22|pending|
|ARE|5|10d|2026-06-29|pending|

## Market Snapshot Top 10
- momentum_exhaustion_guard_threshold: -0.25
- momentum_exhaustion_guard_adjustment: -0.03
|rank|symbol|raw_market_score|market_score|rule|prior_20d|accel_5d|volume_confirm|rs_vs_equal_weight|
|---|---|---|---|---|---|---|---|---|
|1|ASML|0.7817391304347826|0.7817391304347826||0.26025260208465895|-0.17813899009772638|0.832415034445328|0.2007584823323771|
|2|FCX|0.7730434782608697|0.7730434782608697||0.11299792289395372|-0.015673600865220072|0.21819968743806273|0.053503803141671864|
|3|ARE|0.7634782608695653|0.7634782608695653||0.16477650981251735|-0.12259579319132818|0.473584993071702|0.10528239006023549|
|4|HOOD|0.7630434782608696|0.7630434782608696||0.2719730817077106|-0.11816309005393077|0.36028083866502203|0.21247896195542876|
|5|POOL|0.758695652173913|0.758695652173913||0.0894211128029545|-0.03371510561281399|0.372661536331788|0.029926993050672653|
|6|ALLE|0.7486956521739131|0.7486956521739131||0.06845320132170163|-0.016575477851513254|0.3656882588554857|0.008959081569419776|
|7|BXP|0.742608695652174|0.742608695652174||0.12786330524672818|-0.10539306496986134|0.28128305594157865|0.06836918549444632|
|8|KLAC|0.792608695652174|0.7426086956521739||0.42295866650171776|-0.20657956095110763|0.701968910793763|0.3634645467494359|
|9|SPG|0.7313043478260869|0.7313043478260869||0.09002078548318604|-0.038482399833188685|0.27102929908099327|0.030526665730904186|
|10|HSIC|0.7265217391304348|0.7265217391304348||0.11509894082351302|-0.07614963695075239|0.24334864651043397|0.055604821071231166|

## Final Classification
- CANDIDATE_FOR_PAPER_REVIEW
