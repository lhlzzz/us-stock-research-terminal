# XIAOMEI US Profit Ticket Pipeline V0

RESEARCH_ONLY
NOT_TRADING_ADVICE
NO_BROKER
NO_ORDER
NO_LEDGER
NO_LIVE_TRADE

- output_date: 2026-06-18-final
- as_of_date: 2026-06-17
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
- candidate_pool_size: 10
- top_k: 5
- paper_review_count: 5
- market_watchlist_count: 0
- zero_paper_review_is_valid_output: False
- artifact_summary: /root/hermes/company-ai-system/workspaces/xiaomei/research/profit-ticket-pipeline/summary-2026-06-18-final.md
- artifact_metrics: /root/hermes/company-ai-system/workspaces/xiaomei/research/profit-ticket-pipeline/metrics-2026-06-18-final.json
- artifact_candidates: /root/hermes/company-ai-system/workspaces/xiaomei/research/profit-ticket-pipeline/candidates-2026-06-18-final.csv
- artifact_forward_tracking: /root/hermes/company-ai-system/workspaces/xiaomei/research/profit-ticket-pipeline/forward-tracking-2026-06-18-final.csv

## Backtest Feedback Applied
- feedback_win_rate: 64%
- symbol_penalties: ADBE, ALNY, CPB, KIM

## Market Regime: ACTIVE
- breadth: 63.6% (stocks with positive 20d return)
- momentum: +2.72% (median 20d return)
- volatility: 0.0143 (median daily |return|)
- advance_ratio: 32.5% (1d advancers)
- description: Relative strength + volume-weighted momentum dominant, acceleration reversed
- scoring_weights: {'prior_20d_momentum': 0.15, 'five_day_acceleration': -0.15, 'relative_strength_vs_equal_weight': 0.4, 'volume_weighted_momentum': 0.3, 'closing_strength_5d': 0.0, 'volume_confirmation_ratio': 0.0}
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
- default_stop_loss: 2.0%

## Methodology References
- UZI-Skill: risk checklist and multi-dimensional review
- TradingAgents: role-based research synthesis
- Serenity Skill: theme and supply-chain catalyst mapping
- Buffett Skills: quality, margin-of-safety, bear-case framing
- QuantDinger: replay discipline and data-health guardrails
- Factor Analysis (300-day IC): scoring weight optimization based on historical information coefficient

## Price-Volume Summary
- equal_weight_20d_benchmark: 0.045139611619764736
- median_20d_momentum: 0.028355200032632366
- median_5d_acceleration: -0.018658709668376794
- median_volume_confirmation: -0.07258532902761677
- median_relative_strength: -0.01678441158713237
- top_market_score_p90: 0.70536186770428

## Paper Review Candidates
|rank|symbol|company|latest|intraday|source_gap|market_score|catalyst_score|ticket_score|narrative|business|gate_status|
|---|---|---|---|---|---|---|---|---|---|---|---|
|1|IP|IP|None|None|None|0.7993190661478599|0.525|1.3243190661478599|found_relevant|found_relevant|CANDIDATE_FOR_PAPER_REVIEW|
  - ticket_card: research_only=true allow_trade=false auto_order=false no_broker_api=true
  - kline_source: Yahoo Finance historical kline
  - quote_source: EastMoney US realtime/delayed quote + kline | status=unavailable | prev_close=None | cross_check_basis=unavailable | gap=None | mismatch=false
  - catalyst: 3 Mid-Cap Stocks We’re Skeptical Of; International Paper Expands Corrugated Reach With Delmarva Deal And New Build
|2|GE|GE|None|None|None|0.7962062256809338|0.525|1.3212062256809338|found_relevant|found_relevant|CANDIDATE_FOR_PAPER_REVIEW|
  - ticket_card: research_only=true allow_trade=false auto_order=false no_broker_api=true
  - kline_source: Yahoo Finance historical kline
  - quote_source: EastMoney US realtime/delayed quote + kline | status=unavailable | prev_close=None | cross_check_basis=unavailable | gap=None | mismatch=false
  - catalyst: SpaceX is sucking the oxygen out of the new space trade; Can GE Aerospace Boost Margin Performance Amid Cost Pressures?
|3|TER|泰瑞达|423.79|0.035275436667888016|0.004276181044152727|0.8042801556420233|0.425|1.2792801556420232|found_relevant|found_relevant|CANDIDATE_FOR_PAPER_REVIEW|
  - ticket_card: research_only=true allow_trade=false auto_order=false no_broker_api=true
  - kline_source: Yahoo Finance historical kline
  - quote_source: EastMoney US realtime/delayed quote + kline | status=ok | prev_close=409.35 | cross_check_basis=latest_price | gap=0.004276181044152727 | mismatch=false
  - catalyst: Teradyne (TER) to Showcase Physical AI Robotics at Automate 2026; Teradyne (TER) Joins The Nasdaq 100 As It Lands A $139.9 Million Air Force Deal
|4|STX|希捷科技|1086.22|0.053212325712180375|0.004134827637919836|0.8314202334630352|0.425|1.2764202334630352|found_relevant|found_relevant|CANDIDATE_FOR_PAPER_REVIEW|
  - ticket_card: research_only=true allow_trade=false auto_order=false no_broker_api=true
  - kline_source: Yahoo Finance historical kline
  - quote_source: EastMoney US realtime/delayed quote + kline | status=ok | prev_close=1031.34 | cross_check_basis=latest_price | gap=0.004134827637919836 | mismatch=false
  - catalyst: Seagate (STX) Stock Rallies As US Iran Ceasefire Lifts Memory Sector Mood; Can Seagate's Mozaic HAMR Platform Strengthen Its Competitive Edge?
|5|WDC|西部数据|737.46|0.08278029012744459|0.002913664897046031|0.8310311284046692|0.425|1.2760311284046693|found_relevant|found_relevant|CANDIDATE_FOR_PAPER_REVIEW|
  - ticket_card: research_only=true allow_trade=false auto_order=false no_broker_api=true
  - kline_source: Yahoo Finance historical kline
  - quote_source: EastMoney US realtime/delayed quote + kline | status=ok | prev_close=681.08 | cross_check_basis=latest_price | gap=0.002913664897046031 | mismatch=false
  - catalyst: Western Digital (WDC) is a Great Momentum Stock: Should You Buy?; Western Digital Earnings Nearly Double on AI, Cloud Demand

## Market Watchlist Needs Evidence
- none

## Catalyst Summary
- candidates_with_narrative_relevant: 5
- candidates_with_business_relevant: 5
- top_shared_titles: [["3 Mid-Cap Stocks We’re Skeptical Of", 1], ["International Paper Expands Corrugated Reach With Delmarva Deal And New Build", 1], ["SpaceX is sucking the oxygen out of the new space trade", 1], ["Can GE Aerospace Boost Margin Performance Amid Cost Pressures?", 1], ["Teradyne (TER) to Showcase Physical AI Robotics at Automate 2026", 1]]

## Evidence Gaps
### 1. IP
- company: IP (symbol)
- narrative query: IP ip stock catalyst earnings news
- business query: IP ip orders demand backlog guidance revenue customer contract
- narrative ranked candidates: 10 | status: found_relevant | returncode: 0
- business ranked candidates: 10 | status: found_relevant | returncode: 0
- evidence gap reason: paper_review_gate_passed
### 2. GE
- company: GE (symbol)
- narrative query: GE ge stock catalyst earnings news
- business query: GE ge orders demand backlog guidance revenue customer contract
- narrative ranked candidates: 10 | status: found_relevant | returncode: 0
- business ranked candidates: 10 | status: found_relevant | returncode: 0
- evidence gap reason: paper_review_gate_passed
### 3. TER
- company: 泰瑞达 (eastmoney_us)
- narrative query: TER 泰瑞达 stock catalyst earnings news
- business query: TER 泰瑞达 orders demand backlog guidance revenue customer contract
- narrative ranked candidates: 10 | status: found_relevant | returncode: 0
- business ranked candidates: 10 | status: found_relevant | returncode: 0
- evidence gap reason: paper_review_gate_passed
### 4. STX
- company: 希捷科技 (eastmoney_us)
- narrative query: STX 希捷科技 stock catalyst earnings news
- business query: STX 希捷科技 orders demand backlog guidance revenue customer contract
- narrative ranked candidates: 10 | status: found_relevant | returncode: 0
- business ranked candidates: 10 | status: found_relevant | returncode: 0
- evidence gap reason: paper_review_gate_passed
### 5. WDC
- company: 西部数据 (eastmoney_us)
- narrative query: WDC 西部数据 stock catalyst earnings news
- business query: WDC 西部数据 orders demand backlog guidance revenue customer contract
- narrative ranked candidates: 10 | status: found_relevant | returncode: 0
- business ranked candidates: 10 | status: found_relevant | returncode: 0
- evidence gap reason: paper_review_gate_passed

## Quality Check (Buffett Skills)
### IP: POOR (score=0.00)
### GE: POOR (score=0.00)
### TER: STRONG (score=0.90)
  - roe: 1.00
  - pe_ttm: 0.78
  - dividend_yield: 1.00
  - price_position_52w: 0.72
  - liquidity_amount: 1.00
### STX: MODERATE (score=0.54)
  - roe: 1.00
  - pe_ttm: 0.00
  - dividend_yield: 0.00
  - price_position_52w: 0.68
  - liquidity_amount: 1.00
### WDC: MODERATE (score=0.67)
  - roe: 1.00
  - pe_ttm: 0.67
  - dividend_yield: 0.00
  - price_position_52w: 0.67
  - liquidity_amount: 1.00

## Risk Checklist (UZI-Skill)
### IP: WATCH (red=0, yellow=1)
  - price_extended_vs_52w: [GREEN] provider_field_unavailable
  - intraday_gap: [GREEN] provider_field_unavailable
  - liquidity: [GREEN] provider_field_unavailable
  - valuation: [GREEN] provider_field_unavailable
  - quality_gap: [GREEN] provider_field_unavailable
  - price_manipulation: [YELLOW] 5d_accel=-0.1159
  - news_red_flags: [GREEN] narrative_status=found_relevant
  - supply_chain_risk: [GREEN] business_status=found_relevant
  - short_interest: [GREEN] provider_field_unavailable
  - dilution_risk: [GREEN] provider_field_unavailable
  - debt_covenant: [GREEN] provider_field_unavailable
  - earnings_quality: [GREEN] provider_field_unavailable
  - insider_selling: [GREEN] provider_field_unavailable
  - regulatory_risk: [GREEN] provider_field_unavailable
  - concentration_risk: [GREEN] provider_field_unavailable
### GE: WATCH (red=0, yellow=1)
  - price_extended_vs_52w: [GREEN] provider_field_unavailable
  - intraday_gap: [GREEN] provider_field_unavailable
  - liquidity: [GREEN] provider_field_unavailable
  - valuation: [GREEN] provider_field_unavailable
  - quality_gap: [GREEN] provider_field_unavailable
  - price_manipulation: [YELLOW] 5d_accel=-0.1331
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
  - price_extended_vs_52w: [YELLOW] latest/52w_high=96.2%
  - intraday_gap: [GREEN] intraday_pct_chg=3.53%
  - liquidity: [GREEN] amount=748,805,024
  - valuation: [GREEN] pe_ttm=21.10
  - quality_gap: [GREEN] roe=1343.00%
  - price_manipulation: [YELLOW] 5d_accel=-0.0998
  - news_red_flags: [GREEN] narrative_status=found_relevant
  - supply_chain_risk: [GREEN] business_status=found_relevant
  - short_interest: [GREEN] provider_field_unavailable
  - dilution_risk: [GREEN] provider_field_unavailable
  - debt_covenant: [GREEN] provider_field_unavailable
  - earnings_quality: [GREEN] provider_field_unavailable
  - insider_selling: [GREEN] provider_field_unavailable
  - regulatory_risk: [GREEN] provider_field_unavailable
  - concentration_risk: [GREEN] provider_field_unavailable
### STX: ELEVATED (red=1, yellow=2)
  - price_extended_vs_52w: [YELLOW] latest/52w_high=99.0%
  - intraday_gap: [GREEN] intraday_pct_chg=5.32%
  - liquidity: [GREEN] amount=2,783,439,360
  - valuation: [YELLOW] pe_ttm=222.43
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
### WDC: ELEVATED (red=0, yellow=3)
  - price_extended_vs_52w: [YELLOW] latest/52w_high=99.4%
  - intraday_gap: [YELLOW] intraday_pct_chg=8.28%
  - liquidity: [GREEN] amount=6,467,906,816
  - valuation: [GREEN] pe_ttm=26.26
  - quality_gap: [GREEN] roe=8185.00%
  - price_manipulation: [YELLOW] 5d_accel=-0.1140
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
### IP: NEUTRAL (pos=2, neg=2)
  - fundamental_analyst: Quality verdict: POOR (score=0.00)
  - news_analyst: News status: found_relevant, relevance=0.95
  - sentiment_analyst: Business/sentiment status: found_relevant, relevance=0.95
  - technical_analyst: Signals: strong_momentum, deceleration_warning, outperforming_market, volume_confirmed
  - bull_case: Bull points: 4
  - bear_case: Bear points: 2
  - risk_manager: Risk: WATCH, Quality: POOR, Rec: PROCEED_WITH_MONITORING
### GE: NEUTRAL (pos=2, neg=2)
  - fundamental_analyst: Quality verdict: POOR (score=0.00)
  - news_analyst: News status: found_relevant, relevance=0.95
  - sentiment_analyst: Business/sentiment status: found_relevant, relevance=0.95
  - technical_analyst: Signals: strong_momentum, deceleration_warning, outperforming_market
  - bull_case: Bull points: 3
  - bear_case: Bear points: 2
  - risk_manager: Risk: WATCH, Quality: POOR, Rec: PROCEED_WITH_MONITORING
### TER: BULLISH_CONSENSUS (pos=3, neg=1)
  - fundamental_analyst: Quality verdict: STRONG (score=0.90)
  - news_analyst: News status: found_relevant, relevance=0.75
  - sentiment_analyst: Business/sentiment status: found_relevant, relevance=0.75
  - technical_analyst: Signals: strong_momentum, outperforming_market
  - bull_case: Bull points: 4
  - bear_case: Bear points: 1
  - risk_manager: Risk: WATCH, Quality: STRONG, Rec: PROCEED_WITH_MONITORING
### STX: BEARISH_CONSENSUS (pos=3, neg=3)
  - fundamental_analyst: Quality verdict: MODERATE (score=0.54)
  - news_analyst: News status: found_relevant, relevance=0.75
  - sentiment_analyst: Business/sentiment status: found_relevant, relevance=0.75
  - technical_analyst: Signals: strong_momentum, deceleration_warning, outperforming_market, volume_confirmed
  - bull_case: Bull points: 4
  - bear_case: Bear points: 3
  - risk_manager: Risk: ELEVATED, Quality: MODERATE, Rec: PROCEED_WITH_CAUTION
### WDC: NEUTRAL (pos=3, neg=2)
  - fundamental_analyst: Quality verdict: MODERATE (score=0.67)
  - news_analyst: News status: found_relevant, relevance=0.75
  - sentiment_analyst: Business/sentiment status: found_relevant, relevance=0.75
  - technical_analyst: Signals: strong_momentum, deceleration_warning, outperforming_market, volume_confirmed
  - bull_case: Bull points: 5
  - bear_case: Bear points: 2
  - risk_manager: Risk: ELEVATED, Quality: MODERATE, Rec: PROCEED_WITH_CAUTION

## Supply Chain Map (Serenity Skill)
- IP: no_supply_chain_data | themes=[]
- GE: no_supply_chain_data | themes=[]
- TER: no_supply_chain_data | themes=[]
- STX: no_supply_chain_data | themes=[]
- WDC: no_supply_chain_data | themes=[]

## Replay Hypothesis (QuantDinger)
- IP: Entry=no_entry, SL=0.0%, TP=0.0%, Period=N/A, Conf=20%
- GE: Entry=no_entry, SL=0.0%, TP=0.0%, Period=N/A, Conf=20%
- TER: Entry=momentum_continuation, SL=-5.0%, TP=8.0%, Period=5d_10d, Conf=70%
- STX: Entry=avoid_deceleration, SL=0.0%, TP=0.0%, Period=N/A, Conf=10%
- WDC: Entry=pullback_entry, SL=-3.0%, TP=5.0%, Period=3d_5d, Conf=50%

## Risk Management (Cross-Platform Best Practices)
### IP: ALLOWED
  - stop_loss: $35.74
  - take_profit: $38.95
  - risk_reward: 2.00
  - kelly_fraction: 0.174
  - risk_score: N/A
  - confidence: 1.00
### GE: ALLOWED
  - stop_loss: $351.54
  - take_profit: $383.14
  - risk_reward: 2.00
  - kelly_fraction: 0.174
  - risk_score: N/A
  - confidence: 1.00
### TER: ALLOWED
  - stop_loss: $413.23
  - take_profit: $450.38
  - risk_reward: 2.00
  - kelly_fraction: 0.174
  - risk_score: N/A
  - confidence: 1.00
### STX: ALLOWED
  - stop_loss: $1059.00
  - take_profit: $1154.20
  - risk_reward: 2.00
  - kelly_fraction: 0.174
  - risk_score: N/A
  - confidence: 1.00
### WDC: ALLOWED
  - stop_loss: $718.10
  - take_profit: $782.65
  - risk_reward: 2.00
  - kelly_fraction: 0.174
  - risk_score: N/A
  - confidence: 1.00

## Forward Tracking
|symbol|rank|horizon|due_date|status|
|---|---|---|---|---|
|IP|1|1d|2026-06-18|pending|
|IP|1|3d|2026-06-22|pending|
|IP|1|5d|2026-06-24|pending|
|IP|1|10d|2026-07-01|pending|
|GE|2|1d|2026-06-18|pending|
|GE|2|3d|2026-06-22|pending|
|GE|2|5d|2026-06-24|pending|
|GE|2|10d|2026-07-01|pending|
|TER|3|1d|2026-06-18|pending|
|TER|3|3d|2026-06-22|pending|
|TER|3|5d|2026-06-24|pending|
|TER|3|10d|2026-07-01|pending|
|STX|4|1d|2026-06-18|pending|
|STX|4|3d|2026-06-22|pending|
|STX|4|5d|2026-06-24|pending|
|STX|4|10d|2026-07-01|pending|
|WDC|5|1d|2026-06-18|pending|
|WDC|5|3d|2026-06-22|pending|
|WDC|5|5d|2026-06-24|pending|
|WDC|5|10d|2026-07-01|pending|

## Market Snapshot Top 10
- momentum_exhaustion_guard_threshold: -0.2
- momentum_exhaustion_guard_adjustment: -0.05
|rank|symbol|raw_market_score|market_score|rule|prior_20d|accel_5d|volume_confirm|closing_strength|vwmomentum|
|---|---|---|---|---|---|---|---|---|---|
|1|STX|0.8314202334630352|0.8314202334630352||0.48732531094348275|-0.15063001624328431|0.4253063806949213|0.7186194944008422|0.58293988821656|
|2|WDC|0.8310311284046692|0.8310311284046692||0.6230975033688257|-0.11395633386727488|0.7550185873607782|0.7676286749751791|0.8111728929035734|
|3|UAL|0.811284046692607|0.811284046692607||0.31698832057187576|-0.17503459279829614|0.06634940537008838|0.4845040078335196|0.31626774633887983|
|4|TER|0.8042801556420233|0.8042801556420233||0.3242434736106774|-0.0997836507283496|0.13766043549617502|0.5968518977409932|0.33427785368995994|
|5|RL|0.8034046692607004|0.8034046692607004||0.28555618045424747|-0.19035913805619153|0.017574829425903715|0.5040502800274815|0.23146745687083467|
|6|LUV|0.7999999999999999|0.7999999999999999||0.28201310395395884|-0.12541441823836164|0.15026025976745294|0.5638601886713137|0.30322066001048176|
|7|IP|0.7993190661478599|0.7993190661478599||0.2715834496977796|-0.11585343612117027|0.3231096921533243|0.5412321420689203|0.3188570868549075|
|8|CCL|0.7977626459143968|0.7977626459143968||0.29112599838406283|-0.1043233979611291|0.24703934388407855|0.6498412587077494|0.3099382502423874|
|9|GE|0.7962062256809338|0.7962062256809338||0.26917417580448544|-0.13312567707001088|0.010388965259836125|0.7387922559257508|0.25106799363585725|
|10|AMAT|0.8386186770428017|0.7886186770428016|momentum_exhaustion_guard|0.5028489746094336|-0.2739702746885688|0.33043547237028403|0.5339849268079466|0.5817113519903785|

## Final Classification
- CANDIDATE_FOR_PAPER_REVIEW
