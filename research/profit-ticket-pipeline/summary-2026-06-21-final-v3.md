# XIAOMEI US Profit Ticket Pipeline V0

RESEARCH_ONLY
NOT_TRADING_ADVICE
NO_BROKER
NO_ORDER
NO_LEDGER
NO_LIVE_TRADE

- output_date: 2026-06-21-final-v3
- as_of_date: 2026-06-18
- market_data_source: Yahoo Finance historical kline + EastMoney US realtime quote
- kline_source: Yahoo Finance historical kline
- quote_source: EastMoney US realtime/delayed quote + kline
- data_source_mismatch_threshold: 0.01
- eastmoney_required_tabs: us_quote_center
- eastmoney_enhanced_tabs: us_quote_detail, us_quote_news, us_quote_company
- eastmoney_evidence_domains: market_overview, quote_detail, company_detail, news_detail
- research_only: true
- allow_trade: false
- auto_order: false
- no_broker_api: true
- universe_source: nasdaq100_sp500_union
- source_mode: live
- data_mode: historical_kline
- universe_key: union
- universe_total_symbols: 515
- universe_included_symbols: 513
- period_used: 1y
- classification: CANDIDATE_FOR_PAPER_REVIEW
- candidate_pool_size: 10
- top_k: 5
- paper_review_count: 5
- market_watchlist_count: 0
- zero_paper_review_is_valid_output: False
- artifact_summary: /root/hermes/company-ai-system/workspaces/xiaomei/research/profit-ticket-pipeline/summary-2026-06-21-final-v3.md
- artifact_metrics: /root/hermes/company-ai-system/workspaces/xiaomei/research/profit-ticket-pipeline/metrics-2026-06-21-final-v3.json
- artifact_candidates: /root/hermes/company-ai-system/workspaces/xiaomei/research/profit-ticket-pipeline/candidates-2026-06-21-final-v3.csv
- artifact_forward_tracking: /root/hermes/company-ai-system/workspaces/xiaomei/research/profit-ticket-pipeline/forward-tracking-2026-06-21-final-v3.csv
- artifact_runtime_context: /root/hermes/company-ai-system/workspaces/xiaomei/research/profit-ticket-pipeline/runtime-decision-context-2026-06-21-final-v3.json
- artifact_runtime_ledger: /root/hermes/company-ai-system/workspaces/xiaomei/research/profit-ticket-pipeline/runtime-decision-ledger.jsonl

## Backtest Feedback Applied
- feedback_win_rate: 64%
- symbol_penalties: ADBE, ALNY, CPB, KIM

## Market Regime: ACTIVE
- breadth: 56.1% (stocks with positive 20d return)
- momentum: +1.17% (median 20d return)
- volatility: 0.0145 (median daily |return|)
- advance_ratio: 52.2% (1d advancers)
- description: Relative strength + volume-weighted momentum dominant, acceleration reversed
- scoring_weights: {'prior_20d_momentum': 0.1, 'five_day_acceleration': -0.15, 'relative_strength_vs_equal_weight': 0.45, 'volume_weighted_momentum': 0.3, 'closing_strength_5d': 0.0, 'volume_confirmation_ratio': 0.0}
- exhaustion_threshold: -0.2
- position_cap: 12%
- min_market_score_gate: 0.0
- kelly_fraction_cap: 80%
- stop_loss_multiplier: 1.0x
- take_profit_multiplier: 1.0x
- risk_per_trade: 2.0%
- max_single_position: 10%
- max_total_exposure: 50%
- max_consecutive_losses: 2
- daily_max_loss_r: 3.0R
- default_stop_loss: 1.8%

## Methodology References
- UZI-Skill: risk checklist and multi-dimensional review
- TradingAgents: role-based research synthesis
- Serenity Skill: theme and supply-chain catalyst mapping
- Buffett Skills: quality, margin-of-safety, bear-case framing
- QuantDinger: replay discipline and data-health guardrails
- Factor Analysis (300-day IC): scoring weight optimization based on historical information coefficient

## Price-Volume Summary
- equal_weight_20d_benchmark: 0.02353970504966914
- median_20d_momentum: 0.014405709528728883
- median_5d_acceleration: -0.019206583924398446
- median_volume_confirmation: 0.22530187555201242
- median_relative_strength: -0.009133995520940259
- top_market_score_p90: 0.6805653021442496

## Paper Review Candidates
|rank|symbol|company|latest|intraday|source_gap|market_score|catalyst_score|ticket_score|narrative|business|gate_status|
|---|---|---|---|---|---|---|---|---|---|---|---|
|1|TECH|Bio-Techne Corp|57.94|0.05345454545454542|2.3701951068488825e-08|0.8030214424951266|0.525|1.3780214424951267|found_relevant|found_relevant|CANDIDATE_FOR_PAPER_REVIEW|
  - ticket_card: research_only=true allow_trade=false auto_order=false no_broker_api=true
  - lifecycle_stage: paper_review_candidate
  - kline_source: Yahoo Finance historical kline
  - quote_source: EastMoney US realtime/delayed quote + kline | status=ok | prev_close=55.0 | cross_check_basis=latest_price | gap=2.3701951068488825e-08 | mismatch=false
  - eastmoney_tabs: detail=https://quote.eastmoney.com/us/TECH.html | news=https://quote.eastmoney.com/us/TECH.html#news | company=https://quote.eastmoney.com/us/TECH.html#company
  - catalyst: Bio-Techne (TECH) Stock Valuation After New Refeyn Bispecific Antibody Analysis Collaboration; 3 Reasons TECH is Risky and 1 Stock to Buy Instead
|2|SW|Smurfit WestRock plc|44.2|0.017964071856287456|1.7261073237406777e-08|0.7890838206627682|0.525|1.3640838206627681|found_relevant|found_relevant|CANDIDATE_FOR_PAPER_REVIEW|
  - ticket_card: research_only=true allow_trade=false auto_order=false no_broker_api=true
  - lifecycle_stage: paper_review_candidate
  - kline_source: Yahoo Finance historical kline
  - quote_source: EastMoney US realtime/delayed quote + kline | status=ok | prev_close=43.42 | cross_check_basis=latest_price | gap=1.7261073237406777e-08 | mismatch=false
  - eastmoney_tabs: detail=https://quote.eastmoney.com/us/SW.html | news=https://quote.eastmoney.com/us/SW.html#news | company=https://quote.eastmoney.com/us/SW.html#company
  - catalyst: Assessing Smurfit Westrock (SW) Valuation After Recent Mixed Share Performance; Smurfit WestRock PLC (SW): Best Stock to Buy According to George Soros
|3|MRNA|Moderna Inc|63.96|0.03495145631067964|1.4314061269615763e-08|0.7730019493177388|0.525|1.3480019493177389|found_relevant|found_relevant|CANDIDATE_FOR_PAPER_REVIEW|
  - ticket_card: research_only=true allow_trade=false auto_order=false no_broker_api=true
  - lifecycle_stage: paper_review_candidate
  - kline_source: Yahoo Finance historical kline
  - quote_source: EastMoney US realtime/delayed quote + kline | status=ok | prev_close=61.8 | cross_check_basis=latest_price | gap=1.4314061269615763e-08 | mismatch=false
  - eastmoney_tabs: detail=https://quote.eastmoney.com/us/MRNA.html | news=https://quote.eastmoney.com/us/MRNA.html#news | company=https://quote.eastmoney.com/us/MRNA.html#company
  - catalyst: Moderna Has Some Key Approvals Ahead. Is the Stock a Buy?; Moderna just got a signal investors can’t ignore
|4|TER|泰瑞达|437.92|0.07186214999020946|3.0662527295000075e-08|0.8110136452241714|0.425|1.2560136452241715|found_relevant|found_relevant|CANDIDATE_FOR_PAPER_REVIEW|
  - ticket_card: research_only=true allow_trade=false auto_order=false no_broker_api=true
  - lifecycle_stage: paper_review_candidate
  - kline_source: Yahoo Finance historical kline
  - quote_source: EastMoney US realtime/delayed quote + kline | status=ok | prev_close=408.56 | cross_check_basis=latest_price | gap=3.0662527295000075e-08 | mismatch=false
  - eastmoney_tabs: detail=https://quote.eastmoney.com/us/TER.html | news=https://quote.eastmoney.com/us/TER.html#news | company=https://quote.eastmoney.com/us/TER.html#company
  - catalyst: Stocks To Watch Echo AI Theme. GE Vernova Among Five Stocks Near Buy Points.; NBIS Stock Rally Rolls On After Record High: Retail Sees 'Shorts Drowning In Losses' As Nasdaq-100 Inclusion Nears
|5|SWK|史丹利百得|86.75|0.05189765975506244|0.0|0.7789473684210526|0.425|1.2539473684210527|found_relevant|found_relevant|CANDIDATE_FOR_PAPER_REVIEW|
  - ticket_card: research_only=true allow_trade=false auto_order=false no_broker_api=true
  - lifecycle_stage: paper_review_candidate
  - kline_source: Yahoo Finance historical kline
  - quote_source: EastMoney US realtime/delayed quote + kline | status=ok | prev_close=82.47 | cross_check_basis=latest_price | gap=0.0 | mismatch=false
  - eastmoney_tabs: detail=https://quote.eastmoney.com/us/SWK.html | news=https://quote.eastmoney.com/us/SWK.html#news | company=https://quote.eastmoney.com/us/SWK.html#company
  - catalyst: Stanley Black & Decker Stock: Is SWK Outperforming the Industrial Sector?; Stanley Black's Engineered Fastening Growth Picks Up: More Upside to Come?

## Market Watchlist Needs Evidence
- none

## Catalyst Summary
- candidates_with_narrative_relevant: 5
- candidates_with_business_relevant: 5
- top_shared_titles: [["Bio-Techne (TECH) Stock Valuation After New Refeyn Bispecific Antibody Analysis Collaboration", 1], ["3 Reasons TECH is Risky and 1 Stock to Buy Instead", 1], ["Assessing Smurfit Westrock (SW) Valuation After Recent Mixed Share Performance", 1], ["Smurfit WestRock PLC (SW): Best Stock to Buy According to George Soros", 1], ["Moderna Has Some Key Approvals Ahead. Is the Stock a Buy?", 1]]

## Lifecycle Snapshot
- paper_review_candidates: 5
- market_watchlist_candidates: 0
- blocked_by_risk_candidates: 0
- best_watch_candidate: UAL
- best_watch_reason: classification=MARKET_WATCHLIST_NEEDS_EVIDENCE; risk=ELEVATED; evidence=MARKET_WATCHLIST_NEEDS_EVIDENCE

## Evidence Gaps
### 1. TECH
- company: Bio-Techne Corp (eastmoney_us)
- narrative query: TECH bio techne stock catalyst earnings news
- business query: TECH bio techne orders demand backlog guidance revenue customer contract
- narrative ranked candidates: 10 | status: found_relevant | returncode: 0
- business ranked candidates: 10 | status: found_relevant | returncode: 0
- evidence gap reason: paper_review_gate_passed
### 2. SW
- company: Smurfit WestRock plc (eastmoney_us)
- narrative query: SW smurfit westrock stock catalyst earnings news
- business query: SW smurfit westrock orders demand backlog guidance revenue customer contract
- narrative ranked candidates: 10 | status: found_relevant | returncode: 0
- business ranked candidates: 10 | status: found_relevant | returncode: 0
- evidence gap reason: paper_review_gate_passed
### 3. MRNA
- company: Moderna Inc (eastmoney_us)
- narrative query: MRNA moderna stock catalyst earnings news
- business query: MRNA moderna orders demand backlog guidance revenue customer contract
- narrative ranked candidates: 10 | status: found_relevant | returncode: 0
- business ranked candidates: 10 | status: found_relevant | returncode: 0
- evidence gap reason: paper_review_gate_passed
### 4. TER
- company: 泰瑞达 (eastmoney_us)
- narrative query: TER 泰瑞达 stock catalyst earnings news
- business query: TER 泰瑞达 orders demand backlog guidance revenue customer contract
- narrative ranked candidates: 10 | status: found_relevant | returncode: 0
- business ranked candidates: 10 | status: found_relevant | returncode: 0
- evidence gap reason: paper_review_gate_passed
### 5. SWK
- company: 史丹利百得 (eastmoney_us)
- narrative query: SWK 史丹利百得 stock catalyst earnings news
- business query: SWK 史丹利百得 orders demand backlog guidance revenue customer contract
- narrative ranked candidates: 10 | status: found_relevant | returncode: 0
- business ranked candidates: 10 | status: found_relevant | returncode: 0
- evidence gap reason: paper_review_gate_passed

## Quality Check (Buffett Skills)
### TECH: STRONG (score=0.79)
  - roe: 1.00
  - pe_ttm: 1.00
  - dividend_yield: 0.00
  - price_position_52w: 0.93
  - liquidity_amount: 1.00
### SW: STRONG (score=0.77)
  - roe: 1.00
  - pe_ttm: 1.00
  - dividend_yield: 0.00
  - price_position_52w: 0.86
  - liquidity_amount: 1.00
### MRNA: STRONG (score=0.75)
  - roe: 0.00
  - pe_ttm: 1.00
  - dividend_yield: 1.00
  - price_position_52w: 0.74
  - liquidity_amount: 1.00
### TER: MODERATE (score=0.69)
  - roe: 1.00
  - pe_ttm: 0.76
  - dividend_yield: 0.00
  - price_position_52w: 0.68
  - liquidity_amount: 1.00
### SWK: STRONG (score=0.75)
  - roe: 1.00
  - pe_ttm: 1.00
  - dividend_yield: 0.00
  - price_position_52w: 0.74
  - liquidity_amount: 1.00

## Risk Checklist (UZI-Skill)
### TECH: ELEVATED (red=1, yellow=0)
  - price_extended_vs_52w: [GREEN] latest/52w_high=80.5%
  - intraday_gap: [GREEN] intraday_pct_chg=5.35%
  - liquidity: [GREEN] amount=216,763,203
  - valuation: [GREEN] pe_ttm=4.35
  - quality_gap: [GREEN] roe=636.00%
  - price_manipulation: [RED] 5d_accel=-0.1681
  - news_red_flags: [GREEN] narrative_status=found_relevant
  - supply_chain_risk: [GREEN] business_status=found_relevant
  - short_interest: [GREEN] provider_field_unavailable
  - dilution_risk: [GREEN] provider_field_unavailable
  - debt_covenant: [GREEN] provider_field_unavailable
  - earnings_quality: [GREEN] provider_field_unavailable
  - insider_selling: [GREEN] provider_field_unavailable
  - regulatory_risk: [GREEN] provider_field_unavailable
  - concentration_risk: [GREEN] provider_field_unavailable
### SW: ELEVATED (red=1, yellow=0)
  - price_extended_vs_52w: [GREEN] latest/52w_high=85.4%
  - intraday_gap: [GREEN] intraday_pct_chg=1.80%
  - liquidity: [GREEN] amount=418,787,952
  - valuation: [GREEN] pe_ttm=1.28
  - quality_gap: [GREEN] roe=36.00%
  - price_manipulation: [RED] 5d_accel=-0.1550
  - news_red_flags: [GREEN] narrative_status=found_relevant
  - supply_chain_risk: [GREEN] business_status=found_relevant
  - short_interest: [GREEN] provider_field_unavailable
  - dilution_risk: [GREEN] provider_field_unavailable
  - debt_covenant: [GREEN] provider_field_unavailable
  - earnings_quality: [GREEN] provider_field_unavailable
  - insider_selling: [GREEN] provider_field_unavailable
  - regulatory_risk: [GREEN] provider_field_unavailable
  - concentration_risk: [GREEN] provider_field_unavailable
### MRNA: WATCH (red=0, yellow=1)
  - price_extended_vs_52w: [GREEN] latest/52w_high=94.4%
  - intraday_gap: [GREEN] intraday_pct_chg=3.50%
  - liquidity: [GREEN] amount=1,533,602,192
  - valuation: [GREEN] pe_ttm=3.43
  - quality_gap: [YELLOW] roe=-1673.00%
  - price_manipulation: [GREEN] 5d_accel=-0.0407
  - news_red_flags: [GREEN] narrative_status=found_relevant
  - supply_chain_risk: [GREEN] business_status=found_relevant
  - short_interest: [GREEN] provider_field_unavailable
  - dilution_risk: [GREEN] provider_field_unavailable
  - debt_covenant: [GREEN] provider_field_unavailable
  - earnings_quality: [GREEN] provider_field_unavailable
  - insider_selling: [GREEN] provider_field_unavailable
  - regulatory_risk: [GREEN] provider_field_unavailable
  - concentration_risk: [GREEN] provider_field_unavailable
### TER: WATCH (red=0, yellow=2)
  - price_extended_vs_52w: [YELLOW] latest/52w_high=99.4%
  - intraday_gap: [GREEN] intraday_pct_chg=7.19%
  - liquidity: [GREEN] amount=7,844,158,464
  - valuation: [GREEN] pe_ttm=21.81
  - quality_gap: [GREEN] roe=1343.00%
  - price_manipulation: [YELLOW] 5d_accel=-0.1241
  - news_red_flags: [GREEN] narrative_status=found_relevant
  - supply_chain_risk: [GREEN] business_status=found_relevant
  - short_interest: [GREEN] provider_field_unavailable
  - dilution_risk: [GREEN] provider_field_unavailable
  - debt_covenant: [GREEN] provider_field_unavailable
  - earnings_quality: [GREEN] provider_field_unavailable
  - insider_selling: [GREEN] provider_field_unavailable
  - regulatory_risk: [GREEN] provider_field_unavailable
  - concentration_risk: [GREEN] provider_field_unavailable
### SWK: WATCH (red=0, yellow=1)
  - price_extended_vs_52w: [GREEN] latest/52w_high=94.6%
  - intraday_gap: [GREEN] intraday_pct_chg=5.19%
  - liquidity: [GREEN] amount=194,724,850
  - valuation: [GREEN] pe_ttm=1.50
  - quality_gap: [GREEN] roe=66.00%
  - price_manipulation: [YELLOW] 5d_accel=-0.1258
  - news_red_flags: [GREEN] narrative_status=found_relevant
  - supply_chain_risk: [GREEN] business_status=found_relevant
  - short_interest: [GREEN] provider_field_unavailable
  - dilution_risk: [GREEN] provider_field_unavailable
  - debt_covenant: [GREEN] provider_field_unavailable
  - earnings_quality: [GREEN] provider_field_unavailable
  - insider_selling: [GREEN] provider_field_unavailable
  - regulatory_risk: [GREEN] provider_field_unavailable
  - concentration_risk: [GREEN] provider_field_unavailable

## Research Panel (TradingAgents)
### TECH: NEUTRAL (pos=3, neg=2)
  - fundamental_analyst: Quality verdict: STRONG (score=0.79)
  - news_analyst: News status: found_relevant, relevance=0.95
  - sentiment_analyst: Business/sentiment status: found_relevant, relevance=0.95
  - technical_analyst: Signals: strong_momentum, deceleration_warning, outperforming_market
  - bull_case: Bull points: 4
  - bear_case: Bear points: 2
  - risk_manager: Risk: ELEVATED, Quality: STRONG, Rec: PROCEED_WITH_CAUTION
### SW: NEUTRAL (pos=3, neg=2)
  - fundamental_analyst: Quality verdict: STRONG (score=0.77)
  - news_analyst: News status: found_relevant, relevance=0.95
  - sentiment_analyst: Business/sentiment status: found_relevant, relevance=0.95
  - technical_analyst: Signals: strong_momentum, deceleration_warning, outperforming_market, volume_confirmed
  - bull_case: Bull points: 5
  - bear_case: Bear points: 2
  - risk_manager: Risk: ELEVATED, Quality: STRONG, Rec: PROCEED_WITH_CAUTION
### MRNA: BULLISH_CONSENSUS (pos=3, neg=0)
  - fundamental_analyst: Quality verdict: STRONG (score=0.75)
  - news_analyst: News status: found_relevant, relevance=0.95
  - sentiment_analyst: Business/sentiment status: found_relevant, relevance=0.95
  - technical_analyst: Signals: strong_momentum, outperforming_market, volume_confirmed
  - bull_case: Bull points: 5
  - bear_case: Bear points: 0
  - risk_manager: Risk: WATCH, Quality: STRONG, Rec: PROCEED_WITH_MONITORING
### TER: NEUTRAL (pos=3, neg=2)
  - fundamental_analyst: Quality verdict: MODERATE (score=0.69)
  - news_analyst: News status: found_relevant, relevance=0.75
  - sentiment_analyst: Business/sentiment status: found_relevant, relevance=0.75
  - technical_analyst: Signals: strong_momentum, deceleration_warning, outperforming_market, volume_confirmed
  - bull_case: Bull points: 5
  - bear_case: Bear points: 2
  - risk_manager: Risk: WATCH, Quality: MODERATE, Rec: PROCEED_WITH_MONITORING
### SWK: BULLISH_CONSENSUS (pos=3, neg=1)
  - fundamental_analyst: Quality verdict: STRONG (score=0.75)
  - news_analyst: News status: found_relevant, relevance=0.75
  - sentiment_analyst: Business/sentiment status: found_relevant, relevance=0.75
  - technical_analyst: Signals: strong_momentum, deceleration_warning, outperforming_market, volume_confirmed
  - bull_case: Bull points: 5
  - bear_case: Bear points: 1
  - risk_manager: Risk: WATCH, Quality: STRONG, Rec: PROCEED_WITH_MONITORING

## Supply Chain Map (Serenity Skill)
- TECH: no_supply_chain_data | themes=[]
- SW: no_supply_chain_data | themes=[]
- MRNA: no_supply_chain_data | themes=[]
- TER: no_supply_chain_data | themes=[]
- SWK: no_supply_chain_data | themes=[]

## Replay Hypothesis (QuantDinger)
- TECH: Entry=avoid_deceleration, SL=-3.0%, TP=5.0%, Period=3d_5d, Conf=20%
- SW: Entry=avoid_deceleration, SL=-3.0%, TP=5.0%, Period=3d_5d, Conf=20%
- MRNA: Entry=momentum_continuation, SL=-5.0%, TP=8.0%, Period=5d_10d, Conf=70%
- TER: Entry=pullback_entry, SL=-3.0%, TP=5.0%, Period=3d_5d, Conf=50%
- SWK: Entry=momentum_continuation, SL=-5.0%, TP=8.0%, Period=5d_10d, Conf=70%

## Risk Management (Cross-Platform Best Practices)
### TECH: ALLOWED
  - stop_loss: $56.25
  - take_profit: $61.31
  - risk_reward: 2.00
  - kelly_fraction: 0.174
  - risk_score: N/A
  - confidence: 1.00
### SW: ALLOWED
  - stop_loss: $42.91
  - take_profit: $46.77
  - risk_reward: 2.00
  - kelly_fraction: 0.174
  - risk_score: N/A
  - confidence: 1.00
### MRNA: ALLOWED
  - stop_loss: $62.10
  - take_profit: $67.68
  - risk_reward: 2.00
  - kelly_fraction: 0.174
  - risk_score: N/A
  - confidence: 1.00
### TER: ALLOWED
  - stop_loss: $425.18
  - take_profit: $463.40
  - risk_reward: 2.00
  - kelly_fraction: 0.174
  - risk_score: N/A
  - confidence: 1.00
### SWK: ALLOWED
  - stop_loss: $84.23
  - take_profit: $91.80
  - risk_reward: 2.00
  - kelly_fraction: 0.174
  - risk_score: N/A
  - confidence: 1.00

## Forward Tracking
|symbol|rank|horizon|due_date|status|
|---|---|---|---|---|
|TECH|1|1d|2026-06-19|pending|
|TECH|1|3d|2026-06-23|pending|
|TECH|1|5d|2026-06-25|pending|
|TECH|1|10d|2026-07-02|pending|
|SW|2|1d|2026-06-19|pending|
|SW|2|3d|2026-06-23|pending|
|SW|2|5d|2026-06-25|pending|
|SW|2|10d|2026-07-02|pending|
|MRNA|3|1d|2026-06-19|pending|
|MRNA|3|3d|2026-06-23|pending|
|MRNA|3|5d|2026-06-25|pending|
|MRNA|3|10d|2026-07-02|pending|
|TER|4|1d|2026-06-19|pending|
|TER|4|3d|2026-06-23|pending|
|TER|4|5d|2026-06-25|pending|
|TER|4|10d|2026-07-02|pending|
|SWK|5|1d|2026-06-19|pending|
|SWK|5|3d|2026-06-23|pending|
|SWK|5|5d|2026-06-25|pending|
|SWK|5|10d|2026-07-02|pending|

## Market Snapshot Top 10
- momentum_exhaustion_guard_threshold: -0.2
- momentum_exhaustion_guard_adjustment: -0.05
|rank|symbol|raw_market_score|market_score|rule|prior_20d|accel_5d|volume_confirm|closing_strength|vwmomentum|
|---|---|---|---|---|---|---|---|---|---|
|1|TER|0.8110136452241714|0.8110136452241714||0.2722466642427086|-0.12405573494083222|1.048622694926614|0.4780345979736347|0.40954109635168107|
|2|TECH|0.8030214424951266|0.8030214424951266||0.24068517516362564|-0.16811949327307807|0.09210759396828339|0.566203704831384|0.23197751672637393|
|3|IP|0.8010721247563353|0.8010721247563353||0.21014470494881965|-0.1566397295249653|0.5285985141398781|0.34298474347062335|0.2643176165949118|
|4|LUV|0.798635477582846|0.798635477582846||0.21358878403114345|-0.13050004550990235|0.40489136654158076|0.3450198030212107|0.26829287725221035|
|5|UAL|0.7942495126705653|0.7942495126705653||0.20710062994267364|-0.15639466196892182|0.16208655225955915|0.2872581745112556|0.22308017497282592|
|6|SW|0.7890838206627682|0.7890838206627682||0.1904120520183734|-0.15504071950945786|0.3237297345818575|0.3086006213068684|0.2194903442984176|
|7|GE|0.784307992202729|0.784307992202729||0.19145816920363012|-0.11668955472878273|0.279623876165465|0.473682609164396|0.21529913613954435|
|8|AMD|0.7806042884990254|0.7806042884990254||0.20061220617250397|-0.10045869672920538|0.08368971579930928|0.4536843986961613|0.2064137183227848|
|9|SWK|0.7789473684210526|0.7789473684210526||0.1693420326391597|-0.12579574530383564|0.4740980328098454|0.3072619923484503|0.21483525958431063|
|10|MRNA|0.7730019493177388|0.7730019493177388||0.32917706783430867|-0.04070003578562553|1.6580098105942134|0.6202020216322905|0.5748540200603898|

## Final Classification
- CANDIDATE_FOR_PAPER_REVIEW
