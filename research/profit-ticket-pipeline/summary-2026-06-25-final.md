# XIAOMEI US Profit Ticket Pipeline V0

RESEARCH_ONLY
NOT_TRADING_ADVICE
NO_BROKER
NO_ORDER
NO_LEDGER
NO_LIVE_TRADE

- output_date: 2026-06-25-final
- as_of_date: 2026-06-24
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
- universe_source: nasdaq100_sp500_union
- source_mode: cached_local
- data_mode: historical_kline
- universe_key: union
- universe_total_symbols: 508
- universe_included_symbols: 508
- period_used: 1y
- classification: CANDIDATE_FOR_PAPER_REVIEW
- candidate_pool_size: 8
- top_k: 5
- paper_review_count: 5
- market_watchlist_count: 0
- zero_paper_review_is_valid_output: False
- artifact_summary: /workspace/workspaces/xiaomei/research/profit-ticket-pipeline/summary-2026-06-25-final.md
- artifact_metrics: /workspace/workspaces/xiaomei/research/profit-ticket-pipeline/metrics-2026-06-25-final.json
- artifact_candidates: /workspace/workspaces/xiaomei/research/profit-ticket-pipeline/candidates-2026-06-25-final.csv
- artifact_forward_tracking: /workspace/workspaces/xiaomei/research/profit-ticket-pipeline/forward-tracking-2026-06-25-final.csv
- artifact_runtime_context: /workspace/workspaces/xiaomei/research/profit-ticket-pipeline/runtime-decision-context-2026-06-25-final.json
- artifact_runtime_ledger: /workspace/workspaces/xiaomei/research/profit-ticket-pipeline/runtime-decision-ledger.jsonl

## Backtest Feedback Applied
- feedback_win_rate: 64%
- symbol_penalties: ADBE, ALNY, CPB, KIM, STX, TER, SW, SWK

## Market Regime: ACTIVE
- breadth: 58.9% (stocks with positive 20d return)
- momentum: +1.50% (median 20d return)
- volatility: 0.0154 (median daily |return|)
- advance_ratio: 63.8% (1d advancers)
- description: Moderate accel gate, balanced risk
- scoring_weights: {'prior_20d_momentum': 0.1, 'five_day_acceleration': -0.1, 'relative_strength_vs_equal_weight': 0.45, 'volume_weighted_momentum': 0.3, 'closing_strength_5d': 0.0, 'volume_confirmation_ratio': 0.0}
- exhaustion_threshold: -0.22
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
- equal_weight_20d_benchmark: 0.011067008258664841
- median_20d_momentum: 0.015041168906686497
- median_5d_acceleration: -0.015968001693355327
- median_volume_confirmation: 0.27722745136338256
- median_relative_strength: 0.003974160648021656
- top_market_score_p90: 0.9998392950003343

## Paper Review Candidates
|rank|symbol|company|latest|intraday|source_gap|market_score|catalyst_score|ticket_score|narrative|business|gate_status|
|---|---|---|---|---|---|---|---|---|---|---|---|
|1|DAL|达美航空|94.45|0.04191947049089895|0.0|1.1424859997819437|0.0|1.1924859997819437|missing|missing|CANDIDATE_FOR_PAPER_REVIEW|
  - ticket_card: research_only=true allow_trade=false auto_order=false no_broker_api=true
  - lifecycle_stage: paper_review_candidate
  - kline_source: EastMoney US historical kline
  - quote_source: EastMoney US realtime/delayed quote + kline | status=ok | prev_close=90.65 | cross_check_basis=prev_close | gap=0.0 | mismatch=false
  - eastmoney_tabs: detail=https://quote.eastmoney.com/us/DAL.html | news=https://quote.eastmoney.com/us/DAL.html#news | company=https://quote.eastmoney.com/us/DAL.html#company
  - catalyst: No relevant public catalyst evidence found.
|2|CAT|卡特彼勒|1047.34|0.05318517773643716|0.0|1.1315821881448007|0.0|1.1815821881448008|missing|missing|CANDIDATE_FOR_PAPER_REVIEW|
  - ticket_card: research_only=true allow_trade=false auto_order=false no_broker_api=true
  - lifecycle_stage: paper_review_candidate
  - kline_source: EastMoney US historical kline
  - quote_source: EastMoney US realtime/delayed quote + kline | status=ok | prev_close=994.45 | cross_check_basis=prev_close | gap=0.0 | mismatch=false
  - eastmoney_tabs: detail=https://quote.eastmoney.com/us/CAT.html | news=https://quote.eastmoney.com/us/CAT.html#news | company=https://quote.eastmoney.com/us/CAT.html#company
  - catalyst: No relevant public catalyst evidence found.
|3|MU|美光科技|1179.25|0.12469122850521219|0.0|1.131567104275804|0.0|1.181567104275804|missing|missing|CANDIDATE_FOR_PAPER_REVIEW|
  - ticket_card: research_only=true allow_trade=false auto_order=false no_broker_api=true
  - lifecycle_stage: paper_review_candidate
  - kline_source: EastMoney US historical kline
  - quote_source: EastMoney US realtime/delayed quote + kline | status=ok | prev_close=1048.51 | cross_check_basis=prev_close | gap=0.0 | mismatch=false
  - eastmoney_tabs: detail=https://quote.eastmoney.com/us/MU.html | news=https://quote.eastmoney.com/us/MU.html#news | company=https://quote.eastmoney.com/us/MU.html#company
  - catalyst: No relevant public catalyst evidence found.
|4|UAL|联合航空|136.745|0.047533323119350435|0.0|1.1010935224355447|0.0|1.1510935224355447|missing|missing|CANDIDATE_FOR_PAPER_REVIEW|
  - ticket_card: research_only=true allow_trade=false auto_order=false no_broker_api=true
  - lifecycle_stage: paper_review_candidate
  - kline_source: EastMoney US historical kline
  - quote_source: EastMoney US realtime/delayed quote + kline | status=ok | prev_close=130.54 | cross_check_basis=prev_close | gap=0.0 | mismatch=false
  - eastmoney_tabs: detail=https://quote.eastmoney.com/us/UAL.html | news=https://quote.eastmoney.com/us/UAL.html#news | company=https://quote.eastmoney.com/us/UAL.html#company
  - catalyst: No relevant public catalyst evidence found.
|5|FLEX|伟创力|162.735|0.07971735668789814|0.0|1.0990413988795704|0.0|1.1490413988795705|missing|missing|CANDIDATE_FOR_PAPER_REVIEW|
  - ticket_card: research_only=true allow_trade=false auto_order=false no_broker_api=true
  - lifecycle_stage: paper_review_candidate
  - kline_source: EastMoney US historical kline
  - quote_source: EastMoney US realtime/delayed quote + kline | status=ok | prev_close=150.72 | cross_check_basis=prev_close | gap=0.0 | mismatch=false
  - eastmoney_tabs: detail=https://quote.eastmoney.com/us/FLEX.html | news=https://quote.eastmoney.com/us/FLEX.html#news | company=https://quote.eastmoney.com/us/FLEX.html#company
  - catalyst: No relevant public catalyst evidence found.

## Market Watchlist Needs Evidence
- none

## Catalyst Summary
- candidates_with_narrative_relevant: 0
- candidates_with_business_relevant: 0
- top_shared_titles: []

## Lifecycle Snapshot
- paper_review_candidates: 5
- market_watchlist_candidates: 0
- blocked_by_risk_candidates: 0
- best_watch_candidate: none
- best_watch_reason: none

## Evidence Gaps
### 1. DAL
- company: 达美航空 (eastmoney_us)
- narrative query: DAL 达美航空 stock catalyst earnings news
- business query: DAL 达美航空 orders demand backlog guidance revenue customer contract
- narrative ranked candidates: 0 | status: missing | returncode: 0
- business ranked candidates: 0 | status: missing | returncode: 0
- evidence gap reason: paper_review_gate_passed
### 2. CAT
- company: 卡特彼勒 (eastmoney_us)
- narrative query: CAT 卡特彼勒 stock catalyst earnings news
- business query: CAT 卡特彼勒 orders demand backlog guidance revenue customer contract
- narrative ranked candidates: 0 | status: missing | returncode: 0
- business ranked candidates: 0 | status: missing | returncode: 0
- evidence gap reason: paper_review_gate_passed
### 3. MU
- company: 美光科技 (eastmoney_us)
- narrative query: MU 美光科技 stock catalyst earnings news
- business query: MU 美光科技 orders demand backlog guidance revenue customer contract
- narrative ranked candidates: 0 | status: missing | returncode: 0
- business ranked candidates: 0 | status: missing | returncode: 0
- evidence gap reason: paper_review_gate_passed
### 4. UAL
- company: 联合航空 (eastmoney_us)
- narrative query: UAL 联合航空 stock catalyst earnings news
- business query: UAL 联合航空 orders demand backlog guidance revenue customer contract
- narrative ranked candidates: 0 | status: missing | returncode: 0
- business ranked candidates: 0 | status: missing | returncode: 0
- evidence gap reason: paper_review_gate_passed
### 5. FLEX
- company: 伟创力 (eastmoney_us)
- narrative query: FLEX 伟创力 stock catalyst earnings news
- business query: FLEX 伟创力 orders demand backlog guidance revenue customer contract
- narrative ranked candidates: 0 | status: missing | returncode: 0
- business ranked candidates: 0 | status: missing | returncode: 0
- evidence gap reason: paper_review_gate_passed

## Quality Check (Buffett Skills)
### DAL: STRONG (score=0.74)
  - roe: 0.00
  - pe_ttm: 1.00
  - dividend_yield: 1.00
  - price_position_52w: 0.68
  - liquidity_amount: 1.00
### CAT: STRONG (score=0.87)
  - roe: 1.00
  - pe_ttm: 0.68
  - dividend_yield: 1.00
  - price_position_52w: 0.67
  - liquidity_amount: 1.00
### MU: STRONG (score=0.74)
  - roe: 1.00
  - pe_ttm: 0.94
  - dividend_yield: 0.00
  - price_position_52w: 0.75
  - liquidity_amount: 1.00
### UAL: STRONG (score=0.94)
  - roe: 1.00
  - pe_ttm: 1.00
  - dividend_yield: 1.00
  - price_position_52w: 0.68
  - liquidity_amount: 1.00
### FLEX: STRONG (score=0.93)
  - roe: 1.00
  - pe_ttm: 0.97
  - dividend_yield: 1.00
  - price_position_52w: 0.70
  - liquidity_amount: 1.00

## Risk Checklist (UZI-Skill)
### DAL: WATCH (red=0, yellow=2)
  - price_extended_vs_52w: [YELLOW] latest/52w_high=99.3%
  - intraday_gap: [GREEN] intraday_pct_chg=4.19%
  - liquidity: [GREEN] amount=261,371,743
  - valuation: [GREEN] pe_ttm=3.05
  - quality_gap: [YELLOW] roe=-140.00%
  - price_manipulation: [GREEN] 5d_accel=-0.0515
  - news_red_flags: [GREEN] narrative_status=missing
  - supply_chain_risk: [GREEN] business_status=missing
  - short_interest: [GREEN] provider_field_unavailable
  - dilution_risk: [GREEN] provider_field_unavailable
  - debt_covenant: [GREEN] provider_field_unavailable
  - earnings_quality: [GREEN] provider_field_unavailable
  - insider_selling: [GREEN] provider_field_unavailable
  - regulatory_risk: [GREEN] provider_field_unavailable
  - concentration_risk: [GREEN] provider_field_unavailable
### CAT: WATCH (red=0, yellow=1)
  - price_extended_vs_52w: [YELLOW] latest/52w_high=99.6%
  - intraday_gap: [GREEN] intraday_pct_chg=5.32%
  - liquidity: [GREEN] amount=1,255,774,608
  - valuation: [GREEN] pe_ttm=25.85
  - quality_gap: [GREEN] roe=1275.00%
  - price_manipulation: [GREEN] 5d_accel=-0.0427
  - news_red_flags: [GREEN] narrative_status=missing
  - supply_chain_risk: [GREEN] business_status=missing
  - short_interest: [GREEN] provider_field_unavailable
  - dilution_risk: [GREEN] provider_field_unavailable
  - debt_covenant: [GREEN] provider_field_unavailable
  - earnings_quality: [GREEN] provider_field_unavailable
  - insider_selling: [GREEN] provider_field_unavailable
  - regulatory_risk: [GREEN] provider_field_unavailable
  - concentration_risk: [GREEN] provider_field_unavailable
### MU: WATCH (red=0, yellow=2)
  - price_extended_vs_52w: [GREEN] latest/52w_high=94.0%
  - intraday_gap: [YELLOW] intraday_pct_chg=12.47%
  - liquidity: [GREEN] amount=45,453,214,464
  - valuation: [GREEN] pe_ttm=13.22
  - quality_gap: [GREEN] roe=6103.00%
  - price_manipulation: [YELLOW] 5d_accel=-0.1432
  - news_red_flags: [GREEN] narrative_status=missing
  - supply_chain_risk: [GREEN] business_status=missing
  - short_interest: [GREEN] provider_field_unavailable
  - dilution_risk: [GREEN] provider_field_unavailable
  - debt_covenant: [GREEN] provider_field_unavailable
  - earnings_quality: [GREEN] provider_field_unavailable
  - insider_selling: [GREEN] provider_field_unavailable
  - regulatory_risk: [GREEN] provider_field_unavailable
  - concentration_risk: [GREEN] provider_field_unavailable
### UAL: WATCH (red=0, yellow=2)
  - price_extended_vs_52w: [YELLOW] latest/52w_high=98.8%
  - intraday_gap: [GREEN] intraday_pct_chg=4.75%
  - liquidity: [GREEN] amount=403,190,416
  - valuation: [GREEN] pe_ttm=2.80
  - quality_gap: [GREEN] roe=449.00%
  - price_manipulation: [YELLOW] 5d_accel=-0.1309
  - news_red_flags: [GREEN] narrative_status=missing
  - supply_chain_risk: [GREEN] business_status=missing
  - short_interest: [GREEN] provider_field_unavailable
  - dilution_risk: [GREEN] provider_field_unavailable
  - debt_covenant: [GREEN] provider_field_unavailable
  - earnings_quality: [GREEN] provider_field_unavailable
  - insider_selling: [GREEN] provider_field_unavailable
  - regulatory_risk: [GREEN] provider_field_unavailable
  - concentration_risk: [GREEN] provider_field_unavailable
### FLEX: WATCH (red=0, yellow=1)
  - price_extended_vs_52w: [YELLOW] latest/52w_high=97.5%
  - intraday_gap: [GREEN] intraday_pct_chg=7.97%
  - liquidity: [GREEN] amount=474,710,128
  - valuation: [GREEN] pe_ttm=11.59
  - quality_gap: [GREEN] roe=1735.00%
  - price_manipulation: [GREEN] 5d_accel=-0.0264
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
### DAL: MIXED (pos=1, neg=1)
  - fundamental_analyst: Quality verdict: STRONG (score=0.74)
  - news_analyst: News status: missing, relevance=0.00
  - sentiment_analyst: Business/sentiment status: missing, relevance=0.00
  - technical_analyst: Signals: strong_momentum, outperforming_market, volume_confirmed
  - bull_case: Bull points: 3
  - bear_case: Bear points: 1
  - risk_manager: Risk: WATCH, Quality: STRONG, Rec: PROCEED_WITH_MONITORING
### CAT: MIXED (pos=1, neg=0)
  - fundamental_analyst: Quality verdict: STRONG (score=0.87)
  - news_analyst: News status: missing, relevance=0.00
  - sentiment_analyst: Business/sentiment status: missing, relevance=0.00
  - technical_analyst: Signals: moderate_momentum, outperforming_market, volume_confirmed
  - bull_case: Bull points: 2
  - bear_case: Bear points: 0
  - risk_manager: Risk: WATCH, Quality: STRONG, Rec: PROCEED_WITH_MONITORING
### MU: MIXED (pos=1, neg=2)
  - fundamental_analyst: Quality verdict: STRONG (score=0.74)
  - news_analyst: News status: missing, relevance=0.00
  - sentiment_analyst: Business/sentiment status: missing, relevance=0.00
  - technical_analyst: Signals: strong_momentum, deceleration_warning, outperforming_market
  - bull_case: Bull points: 2
  - bear_case: Bear points: 2
  - risk_manager: Risk: WATCH, Quality: STRONG, Rec: PROCEED_WITH_MONITORING
### UAL: MIXED (pos=1, neg=2)
  - fundamental_analyst: Quality verdict: STRONG (score=0.94)
  - news_analyst: News status: missing, relevance=0.00
  - sentiment_analyst: Business/sentiment status: missing, relevance=0.00
  - technical_analyst: Signals: strong_momentum, deceleration_warning, outperforming_market
  - bull_case: Bull points: 2
  - bear_case: Bear points: 2
  - risk_manager: Risk: WATCH, Quality: STRONG, Rec: PROCEED_WITH_MONITORING
### FLEX: MIXED (pos=1, neg=0)
  - fundamental_analyst: Quality verdict: STRONG (score=0.93)
  - news_analyst: News status: missing, relevance=0.00
  - sentiment_analyst: Business/sentiment status: missing, relevance=0.00
  - technical_analyst: Signals: moderate_momentum, volume_confirmed
  - bull_case: Bull points: 2
  - bear_case: Bear points: 0
  - risk_manager: Risk: WATCH, Quality: STRONG, Rec: PROCEED_WITH_MONITORING

## Supply Chain Map (Serenity Skill)
- DAL: no_supply_chain_data | themes=[]
- CAT: no_supply_chain_data | themes=[]
- MU: no_supply_chain_data | themes=[]
- UAL: no_supply_chain_data | themes=[]
- FLEX: no_supply_chain_data | themes=[]

## Replay Hypothesis (QuantDinger)
- DAL: Entry=no_entry, SL=0.0%, TP=0.0%, Period=N/A, Conf=20%
- CAT: Entry=no_entry, SL=0.0%, TP=0.0%, Period=N/A, Conf=20%
- MU: Entry=no_entry, SL=0.0%, TP=0.0%, Period=N/A, Conf=20%
- UAL: Entry=no_entry, SL=0.0%, TP=0.0%, Period=N/A, Conf=20%
- FLEX: Entry=no_entry, SL=0.0%, TP=0.0%, Period=N/A, Conf=20%

## Risk Management (Cross-Platform Best Practices)
### DAL: ALLOWED
  - stop_loss: $88.01
  - take_profit: $95.92
  - risk_reward: 2.00
  - kelly_fraction: 0.174
  - risk_score: N/A
  - confidence: 1.00
### CAT: ALLOWED
  - stop_loss: $965.52
  - take_profit: $1052.32
  - risk_reward: 2.00
  - kelly_fraction: 0.174
  - risk_score: N/A
  - confidence: 1.00
### MU: ALLOWED
  - stop_loss: $1018.00
  - take_profit: $1109.52
  - risk_reward: 2.00
  - kelly_fraction: 0.174
  - risk_score: N/A
  - confidence: 1.00
### UAL: ALLOWED
  - stop_loss: $126.74
  - take_profit: $138.14
  - risk_reward: 2.00
  - kelly_fraction: 0.174
  - risk_score: N/A
  - confidence: 1.00
### FLEX: ALLOWED
  - stop_loss: $146.33
  - take_profit: $159.49
  - risk_reward: 2.00
  - kelly_fraction: 0.174
  - risk_score: N/A
  - confidence: 1.00

## Forward Tracking
|symbol|rank|horizon|due_date|status|
|---|---|---|---|---|
|DAL|1|1d|2026-06-25|pending|
|DAL|1|3d|2026-06-29|pending|
|DAL|1|5d|2026-07-01|pending|
|DAL|1|10d|2026-07-08|pending|
|CAT|2|1d|2026-06-25|pending|
|CAT|2|3d|2026-06-29|pending|
|CAT|2|5d|2026-07-01|pending|
|CAT|2|10d|2026-07-08|pending|
|MU|3|1d|2026-06-25|pending|
|MU|3|3d|2026-06-29|pending|
|MU|3|5d|2026-07-01|pending|
|MU|3|10d|2026-07-08|pending|
|UAL|4|1d|2026-06-25|pending|
|UAL|4|3d|2026-06-29|pending|
|UAL|4|5d|2026-07-01|pending|
|UAL|4|10d|2026-07-08|pending|
|FLEX|5|1d|2026-06-25|pending|
|FLEX|5|3d|2026-06-29|pending|
|FLEX|5|5d|2026-07-01|pending|
|FLEX|5|10d|2026-07-08|pending|

## Market Snapshot Top 10
- momentum_exhaustion_guard_threshold: -0.22
- momentum_exhaustion_guard_adjustment: -0.04
|rank|symbol|raw_market_score|market_score|rule|prior_20d|accel_5d|volume_confirm|closing_strength|vwmomentum|
|---|---|---|---|---|---|---|---|---|---|
|1|DAL|1.2710121920243835|1.1424859997819437||0.1418314649200152|-0.05150190033016666|0.33714642612018797|0.6271261446661225|0.1757160162558001|
|2|CAT|1.2226273851768803|1.1315821881448007||0.09454625502173797|-0.04273020780662584|0.5508930604249582|0.5677711652094215|0.12071207650406364|
|3|MU|1.2484360751192645|1.131567104275804||0.17036879939277583|-0.1431831729967572|0.2124761613626318|0.5640278466217514|0.1789270481988837|
|4|ABBV|1.2340783017754469|1.127185961203762||0.10214902402402393|-0.04632127196756697|0.4642137829638413|0.570320963767023|0.1358195022891611|
|5|UAL|1.3358824032865457|1.1010935224355447||0.23243957703927487|-0.13092915597776122|0.23766928642345198|0.5567783225669728|0.2619198740247348|
|6|FLEX|1.1306218005386401|1.0990413988795704||0.052220050265288975|-0.026425454199135112|2.835263003129067|0.6102788156836338|0.11841142974652578|
|7|URI|1.2838210653071127|1.0983219962550288||0.12545175092427208|-0.11244953679299763|0.14951355816505862|0.5168829921758534|0.12572101992318557|
|8|IP|1.3129299627020303|1.0906422634145503||0.19837296620775957|-0.13889855403625195|0.4095544102003168|0.35444998010801826|0.2279169065146106|
|9|MTD|1.1823110174991733|1.0878032880919064||0.09247918425903245|-0.047661930873024394|0.2707025085045791|0.5928975071273563|0.10721496727936361|
|10|INCY|1.166858159789025|1.0838266958554441||0.11699279093717818|-0.02967449519782983|0.08832493794670149|0.653973993651606|0.12583203857176575|

## Final Classification
- CANDIDATE_FOR_PAPER_REVIEW
