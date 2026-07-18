# XIAOMEI US Profit Ticket Pipeline V0

RESEARCH_ONLY
NOT_TRADING_ADVICE
NO_BROKER
NO_ORDER
NO_LEDGER
NO_LIVE_TRADE

- output_date: 2026-06-18-evidence
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
- universe_total_symbols: 5
- universe_included_symbols: 5
- period_used: 1y
- classification: CANDIDATE_FOR_PAPER_REVIEW
- candidate_pool_size: 5
- top_k: 5
- paper_review_count: 5
- market_watchlist_count: 0
- zero_paper_review_is_valid_output: False
- artifact_summary: /root/hermes/company-ai-system/workspaces/xiaomei/research/profit-ticket-pipeline/summary-2026-06-18-evidence.md
- artifact_metrics: /root/hermes/company-ai-system/workspaces/xiaomei/research/profit-ticket-pipeline/metrics-2026-06-18-evidence.json
- artifact_candidates: /root/hermes/company-ai-system/workspaces/xiaomei/research/profit-ticket-pipeline/candidates-2026-06-18-evidence.csv
- artifact_forward_tracking: /root/hermes/company-ai-system/workspaces/xiaomei/research/profit-ticket-pipeline/forward-tracking-2026-06-18-evidence.csv

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
- Factor Analysis (300-day IC): scoring weight optimization based on historical information coefficient

## Price-Volume Summary
- equal_weight_20d_benchmark: 0.4506337421732435
- median_20d_momentum: 0.486834432967691
- median_5d_acceleration: -0.15058030219826457
- median_volume_confirmation: 0.33211050766502126
- median_relative_strength: 0.03620069079444754
- top_market_score_p90: 0.642

## Paper Review Candidates
|rank|symbol|company|latest|intraday|source_gap|market_score|catalyst_score|ticket_score|narrative|business|gate_status|
|---|---|---|---|---|---|---|---|---|---|---|---|
|1|AMAT|应用材料|611.6|0.07632472766309428|0.00037621225223594124|0.51|0.425|0.9850000000000001|found_relevant|found_relevant|CANDIDATE_FOR_PAPER_REVIEW|
  - ticket_card: research_only=true allow_trade=false auto_order=false no_broker_api=true
  - kline_source: Yahoo Finance historical kline
  - quote_source: EastMoney US realtime/delayed quote + kline | status=ok | prev_close=568.23 | cross_check_basis=latest_price | gap=0.00037621225223594124 | mismatch=false
  - catalyst: Applied Materials shares jump on launch of integrated AR smart glasses system; Applied Materials (AMAT) Climbed Amid Broad-Based Growth Drivers
|2|WDC|西部数据|739.46|0.08571680272508364|0.0006360164167797944|0.73|0.1875|0.9375|found_relevant|found_unrelated|CANDIDATE_FOR_PAPER_REVIEW|
  - ticket_card: research_only=true allow_trade=false auto_order=false no_broker_api=true
  - kline_source: Yahoo Finance historical kline
  - quote_source: EastMoney US realtime/delayed quote + kline | status=ok | prev_close=681.08 | cross_check_basis=latest_price | gap=0.0006360164167797944 | mismatch=false
  - catalyst: Western Digital (WDC) is a Great Momentum Stock: Should You Buy?
|3|STX|希捷科技|1090.37|0.05723621696045922|4.4781243158098505e-09|0.33999999999999997|0.425|0.815|found_relevant|found_relevant|CANDIDATE_FOR_PAPER_REVIEW|
  - ticket_card: research_only=true allow_trade=false auto_order=false no_broker_api=true
  - kline_source: Yahoo Finance historical kline
  - quote_source: EastMoney US realtime/delayed quote + kline | status=ok | prev_close=1031.34 | cross_check_basis=latest_price | gap=4.4781243158098505e-09 | mismatch=false
  - catalyst: Seagate (STX) Stock Rallies As US Iran Ceasefire Lifts Memory Sector Mood; Can Seagate's Mozaic HAMR Platform Strengthen Its Competitive Edge?
|4|TER|泰瑞达|424.67|0.0374251862709174|3.161921946492896e-08|0.19000000000000003|0.425|0.635|found_relevant|found_relevant|CANDIDATE_FOR_PAPER_REVIEW|
  - ticket_card: research_only=true allow_trade=false auto_order=false no_broker_api=true
  - kline_source: Yahoo Finance historical kline
  - quote_source: EastMoney US realtime/delayed quote + kline | status=ok | prev_close=409.35 | cross_check_basis=latest_price | gap=3.161921946492896e-08 | mismatch=false
  - catalyst: Micron is on an absolute TEAR this morning. How do you find these stocks before they blow up?; Teradyne (TER) Joins The Nasdaq 100 As It Lands A $139.9 Million Air Force Deal
|5|UAL|联合航空|117.545|-0.008142772761792316|1.5577478640338427e-08|0.030000000000000013|0.1875|0.2675|found_relevant|found_unrelated|CANDIDATE_FOR_PAPER_REVIEW|
  - ticket_card: research_only=true allow_trade=false auto_order=false no_broker_api=true
  - kline_source: Yahoo Finance historical kline
  - quote_source: EastMoney US realtime/delayed quote + kline | status=ok | prev_close=118.51 | cross_check_basis=latest_price | gap=1.5577478640338427e-08 | mismatch=false
  - catalyst: United Airlines (UAL) CEO Says Asset Purchases Remain Possible as Fuel Costs Pressure Weaker Rivals

## Market Watchlist Needs Evidence
- none

## Catalyst Summary
- candidates_with_narrative_relevant: 5
- candidates_with_business_relevant: 3
- top_shared_titles: [["Applied Materials shares jump on launch of integrated AR smart glasses system", 1], ["Applied Materials (AMAT) Climbed Amid Broad-Based Growth Drivers", 1], ["Western Digital (WDC) is a Great Momentum Stock: Should You Buy?", 1], ["Seagate (STX) Stock Rallies As US Iran Ceasefire Lifts Memory Sector Mood", 1], ["Can Seagate's Mozaic HAMR Platform Strengthen Its Competitive Edge?", 1]]

## Evidence Gaps
### 1. AMAT
- company: 应用材料 (eastmoney_us)
- narrative query: AMAT 应用材料 stock catalyst earnings news
- business query: AMAT 应用材料 orders demand backlog guidance revenue customer contract
- narrative ranked candidates: 10 | status: found_relevant | returncode: 0
- business ranked candidates: 10 | status: found_relevant | returncode: 0
- evidence gap reason: paper_review_gate_passed
### 2. WDC
- company: 西部数据 (eastmoney_us)
- narrative query: WDC 西部数据 stock catalyst earnings news
- business query: WDC 西部数据 orders demand backlog guidance revenue customer contract
- narrative ranked candidates: 10 | status: found_relevant | returncode: 0
- business ranked candidates: 6 | status: found_unrelated | returncode: 0
- evidence gap reason: paper_review_gate_passed
### 3. STX
- company: 希捷科技 (eastmoney_us)
- narrative query: STX 希捷科技 stock catalyst earnings news
- business query: STX 希捷科技 orders demand backlog guidance revenue customer contract
- narrative ranked candidates: 10 | status: found_relevant | returncode: 0
- business ranked candidates: 10 | status: found_relevant | returncode: 0
- evidence gap reason: paper_review_gate_passed
### 4. TER
- company: 泰瑞达 (eastmoney_us)
- narrative query: TER 泰瑞达 stock catalyst earnings news
- business query: TER 泰瑞达 orders demand backlog guidance revenue customer contract
- narrative ranked candidates: 1 | status: found_relevant | returncode: 0
- business ranked candidates: 10 | status: found_relevant | returncode: 0
- evidence gap reason: paper_review_gate_passed
### 5. UAL
- company: 联合航空 (eastmoney_us)
- narrative query: UAL 联合航空 stock catalyst earnings news
- business query: UAL 联合航空 orders demand backlog guidance revenue customer contract
- narrative ranked candidates: 10 | status: found_relevant | returncode: 0
- business ranked candidates: 10 | status: found_unrelated | returncode: 0
- evidence gap reason: paper_review_gate_passed

## Quality Check (Buffett Skills)
### AMAT: STRONG (score=0.90)
  - roe: 1.00
  - pe_ttm: 0.79
  - dividend_yield: 1.00
  - price_position_52w: 0.69
  - liquidity_amount: 1.00
### WDC: MODERATE (score=0.67)
  - roe: 1.00
  - pe_ttm: 0.67
  - dividend_yield: 0.00
  - price_position_52w: 0.67
  - liquidity_amount: 1.00
### STX: STRONG (score=0.73)
  - roe: 1.00
  - pe_ttm: 0.00
  - dividend_yield: 1.00
  - price_position_52w: 0.67
  - liquidity_amount: 1.00
### TER: MODERATE (score=0.70)
  - roe: 1.00
  - pe_ttm: 0.78
  - dividend_yield: 0.00
  - price_position_52w: 0.72
  - liquidity_amount: 1.00
### UAL: STRONG (score=0.75)
  - roe: 1.00
  - pe_ttm: 1.00
  - dividend_yield: 0.00
  - price_position_52w: 0.74
  - liquidity_amount: 1.00

## Risk Checklist (UZI-Skill)
### AMAT: ELEVATED (red=1, yellow=1)
  - price_extended_vs_52w: [YELLOW] latest/52w_high=98.1%
  - intraday_gap: [GREEN] intraday_pct_chg=7.63%
  - liquidity: [GREEN] amount=4,087,629,904
  - valuation: [GREEN] pe_ttm=20.31
  - quality_gap: [GREEN] roe=2180.00%
  - price_manipulation: [RED] 5d_accel=-0.2742
  - news_red_flags: [GREEN] narrative_status=found_relevant
  - supply_chain_risk: [GREEN] business_status=found_relevant
  - short_interest: [GREEN] provider_field_unavailable
  - dilution_risk: [GREEN] provider_field_unavailable
  - debt_covenant: [GREEN] provider_field_unavailable
  - earnings_quality: [GREEN] provider_field_unavailable
  - insider_selling: [GREEN] provider_field_unavailable
  - regulatory_risk: [GREEN] provider_field_unavailable
  - concentration_risk: [GREEN] provider_field_unavailable
### WDC: ELEVATED (red=0, yellow=4)
  - price_extended_vs_52w: [YELLOW] latest/52w_high=99.8%
  - intraday_gap: [YELLOW] intraday_pct_chg=8.57%
  - liquidity: [GREEN] amount=6,373,201,408
  - valuation: [GREEN] pe_ttm=26.33
  - quality_gap: [GREEN] roe=8185.00%
  - price_manipulation: [YELLOW] 5d_accel=-0.1139
  - news_red_flags: [GREEN] narrative_status=found_relevant
  - supply_chain_risk: [YELLOW] business_status=found_unrelated
  - short_interest: [GREEN] provider_field_unavailable
  - dilution_risk: [GREEN] provider_field_unavailable
  - debt_covenant: [GREEN] provider_field_unavailable
  - earnings_quality: [GREEN] provider_field_unavailable
  - insider_selling: [GREEN] provider_field_unavailable
  - regulatory_risk: [GREEN] provider_field_unavailable
  - concentration_risk: [GREEN] provider_field_unavailable
### STX: ELEVATED (red=1, yellow=2)
  - price_extended_vs_52w: [YELLOW] latest/52w_high=99.4%
  - intraday_gap: [GREEN] intraday_pct_chg=5.72%
  - liquidity: [GREEN] amount=2,727,234,400
  - valuation: [YELLOW] pe_ttm=223.28
  - quality_gap: [GREEN] roe=58879.00%
  - price_manipulation: [RED] 5d_accel=-0.1506
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
  - price_extended_vs_52w: [YELLOW] latest/52w_high=96.4%
  - intraday_gap: [GREEN] intraday_pct_chg=3.74%
  - liquidity: [GREEN] amount=729,709,968
  - valuation: [GREEN] pe_ttm=21.15
  - quality_gap: [GREEN] roe=1343.00%
  - price_manipulation: [YELLOW] 5d_accel=-0.0996
  - news_red_flags: [GREEN] narrative_status=found_relevant
  - supply_chain_risk: [GREEN] business_status=found_relevant
  - short_interest: [GREEN] provider_field_unavailable
  - dilution_risk: [GREEN] provider_field_unavailable
  - debt_covenant: [GREEN] provider_field_unavailable
  - earnings_quality: [GREEN] provider_field_unavailable
  - insider_selling: [GREEN] provider_field_unavailable
  - regulatory_risk: [GREEN] provider_field_unavailable
  - concentration_risk: [GREEN] provider_field_unavailable
### UAL: ELEVATED (red=1, yellow=1)
  - price_extended_vs_52w: [GREEN] latest/52w_high=94.2%
  - intraday_gap: [GREEN] intraday_pct_chg=-0.81%
  - liquidity: [GREEN] amount=322,883,552
  - valuation: [GREEN] pe_ttm=2.40
  - quality_gap: [GREEN] roe=449.00%
  - price_manipulation: [RED] 5d_accel=-0.1753
  - news_red_flags: [GREEN] narrative_status=found_relevant
  - supply_chain_risk: [YELLOW] business_status=found_unrelated
  - short_interest: [GREEN] provider_field_unavailable
  - dilution_risk: [GREEN] provider_field_unavailable
  - debt_covenant: [GREEN] provider_field_unavailable
  - earnings_quality: [GREEN] provider_field_unavailable
  - insider_selling: [GREEN] provider_field_unavailable
  - regulatory_risk: [GREEN] provider_field_unavailable
  - concentration_risk: [GREEN] provider_field_unavailable

## Research Panel (TradingAgents)
### AMAT: NEUTRAL (pos=3, neg=2)
  - fundamental_analyst: Quality verdict: STRONG (score=0.90)
  - news_analyst: News status: found_relevant, relevance=0.75
  - sentiment_analyst: Business/sentiment status: found_relevant, relevance=0.75
  - technical_analyst: Signals: strong_momentum, deceleration_warning, outperforming_market, volume_confirmed
  - bull_case: Bull points: 5
  - bear_case: Bear points: 2
  - risk_manager: Risk: ELEVATED, Quality: STRONG, Rec: PROCEED_WITH_CAUTION
### WDC: NEUTRAL (pos=2, neg=2)
  - fundamental_analyst: Quality verdict: MODERATE (score=0.67)
  - news_analyst: News status: found_relevant, relevance=0.75
  - sentiment_analyst: Business/sentiment status: found_unrelated, relevance=0.00
  - technical_analyst: Signals: strong_momentum, deceleration_warning, outperforming_market, volume_confirmed
  - bull_case: Bull points: 4
  - bear_case: Bear points: 2
  - risk_manager: Risk: ELEVATED, Quality: MODERATE, Rec: PROCEED_WITH_CAUTION
### STX: BEARISH_CONSENSUS (pos=3, neg=3)
  - fundamental_analyst: Quality verdict: STRONG (score=0.73)
  - news_analyst: News status: found_relevant, relevance=0.75
  - sentiment_analyst: Business/sentiment status: found_relevant, relevance=0.75
  - technical_analyst: Signals: strong_momentum, deceleration_warning, volume_confirmed
  - bull_case: Bull points: 5
  - bear_case: Bear points: 3
  - risk_manager: Risk: ELEVATED, Quality: STRONG, Rec: PROCEED_WITH_CAUTION
### TER: NEUTRAL (pos=3, neg=2)
  - fundamental_analyst: Quality verdict: MODERATE (score=0.70)
  - news_analyst: News status: found_relevant, relevance=0.75
  - sentiment_analyst: Business/sentiment status: found_relevant, relevance=0.75
  - technical_analyst: Signals: strong_momentum, underperforming_market
  - bull_case: Bull points: 4
  - bear_case: Bear points: 2
  - risk_manager: Risk: WATCH, Quality: MODERATE, Rec: PROCEED_WITH_MONITORING
### UAL: BEARISH_CONSENSUS (pos=2, neg=3)
  - fundamental_analyst: Quality verdict: STRONG (score=0.75)
  - news_analyst: News status: found_relevant, relevance=0.75
  - sentiment_analyst: Business/sentiment status: found_unrelated, relevance=0.00
  - technical_analyst: Signals: strong_momentum, deceleration_warning, underperforming_market
  - bull_case: Bull points: 3
  - bear_case: Bear points: 3
  - risk_manager: Risk: ELEVATED, Quality: STRONG, Rec: PROCEED_WITH_CAUTION

## Supply Chain Map (Serenity Skill)
- AMAT: no_supply_chain_data | themes=[]
- WDC: no_supply_chain_data | themes=[]
- STX: no_supply_chain_data | themes=[]
- TER: no_supply_chain_data | themes=[]
- UAL: no_supply_chain_data | themes=[]

## Replay Hypothesis (QuantDinger)
- AMAT: Entry=avoid_deceleration, SL=-3.0%, TP=5.0%, Period=3d_5d, Conf=20%
- WDC: Entry=pullback_entry, SL=-3.0%, TP=5.0%, Period=3d_5d, Conf=50%
- STX: Entry=avoid_deceleration, SL=0.0%, TP=0.0%, Period=N/A, Conf=10%
- TER: Entry=pullback_entry, SL=-3.0%, TP=5.0%, Period=3d_5d, Conf=50%
- UAL: Entry=avoid_deceleration, SL=0.0%, TP=0.0%, Period=N/A, Conf=10%

## Risk Management (Cross-Platform Best Practices)
### AMAT: ALLOWED
  - stop_loss: $597.14
  - take_profit: $654.06
  - risk_reward: 2.00
  - kelly_fraction: 0.174
  - risk_score: N/A
  - confidence: 1.00
### WDC: ALLOWED
  - stop_loss: $721.79
  - take_profit: $790.59
  - risk_reward: 2.00
  - kelly_fraction: 0.174
  - risk_score: N/A
  - confidence: 1.00
### STX: ALLOWED
  - stop_loss: $1064.99
  - take_profit: $1166.51
  - risk_reward: 2.00
  - kelly_fraction: 0.174
  - risk_score: N/A
  - confidence: 1.00
### TER: ALLOWED
  - stop_loss: $414.79
  - take_profit: $454.32
  - risk_reward: 2.00
  - kelly_fraction: 0.174
  - risk_score: N/A
  - confidence: 1.00
### UAL: ALLOWED
  - stop_loss: $114.81
  - take_profit: $125.75
  - risk_reward: 2.00
  - kelly_fraction: 0.174
  - risk_score: N/A
  - confidence: 1.00

## Forward Tracking
|symbol|rank|horizon|due_date|status|
|---|---|---|---|---|
|AMAT|1|1d|2026-06-18|pending|
|AMAT|1|3d|2026-06-22|pending|
|AMAT|1|5d|2026-06-24|pending|
|AMAT|1|10d|2026-07-01|pending|
|WDC|2|1d|2026-06-18|pending|
|WDC|2|3d|2026-06-22|pending|
|WDC|2|5d|2026-06-24|pending|
|WDC|2|10d|2026-07-01|pending|
|STX|3|1d|2026-06-18|pending|
|STX|3|3d|2026-06-22|pending|
|STX|3|5d|2026-06-24|pending|
|STX|3|10d|2026-07-01|pending|
|TER|4|1d|2026-06-18|pending|
|TER|4|3d|2026-06-22|pending|
|TER|4|5d|2026-06-24|pending|
|TER|4|10d|2026-07-01|pending|
|UAL|5|1d|2026-06-18|pending|
|UAL|5|3d|2026-06-22|pending|
|UAL|5|5d|2026-06-24|pending|
|UAL|5|10d|2026-07-01|pending|

## Market Snapshot Top 10
- momentum_exhaustion_guard_threshold: -0.15
- momentum_exhaustion_guard_adjustment: -0.08
|rank|symbol|raw_market_score|market_score|rule|prior_20d|accel_5d|volume_confirm|closing_strength|vwmomentum|
|---|---|---|---|---|---|---|---|---|---|
|1|WDC|0.73|0.73||0.6217259303842326|-0.11386003686193091|0.7526432311902176|0.7649271345167087|0.8088247038173687|
|2|AMAT|0.65|0.51|momentum_exhaustion_guard|0.5043375901249163|-0.2742416501950722|0.33211050766502126|0.5377050261156824|0.5831676757062001|
|3|STX|0.42|0.33999999999999997|momentum_exhaustion_guard|0.486834432967691|-0.15058030219826457|0.4305730864968502|0.7171824264288429|0.5818344169798321|
|4|TER|0.19000000000000003|0.19000000000000003||0.32131884371864494|-0.09956327565875567|0.13482236661184266|0.5908932605608846|0.33072450837005557|
|5|UAL|0.11000000000000001|0.030000000000000013|momentum_exhaustion_guard|0.3189519136707326|-0.17529556452683126|0.06494907295238872|0.4916466759098073|0.3178808745969312|

## Final Classification
- CANDIDATE_FOR_PAPER_REVIEW
