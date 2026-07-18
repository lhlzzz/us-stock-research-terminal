# XIAOMEI US Profit Ticket Pipeline V0

RESEARCH_ONLY
NOT_TRADING_ADVICE
NO_BROKER
NO_ORDER
NO_LEDGER
NO_LIVE_TRADE

- output_date: 2026-06-23-fixed
- as_of_date: 2026-06-22
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
- universe_source: explicit
- source_mode: live
- data_mode: historical_kline
- universe_key: explicit
- universe_total_symbols: 15
- universe_included_symbols: 15
- period_used: 1y
- classification: CANDIDATE_FOR_PAPER_REVIEW
- candidate_pool_size: 10
- top_k: 5
- paper_review_count: 5
- market_watchlist_count: 0
- zero_paper_review_is_valid_output: False
- artifact_summary: /root/hermes/company-ai-system/workspaces/xiaomei/research/profit-ticket-pipeline/summary-2026-06-23-fixed.md
- artifact_metrics: /root/hermes/company-ai-system/workspaces/xiaomei/research/profit-ticket-pipeline/metrics-2026-06-23-fixed.json
- artifact_candidates: /root/hermes/company-ai-system/workspaces/xiaomei/research/profit-ticket-pipeline/candidates-2026-06-23-fixed.csv
- artifact_forward_tracking: /root/hermes/company-ai-system/workspaces/xiaomei/research/profit-ticket-pipeline/forward-tracking-2026-06-23-fixed.csv
- artifact_runtime_context: /root/hermes/company-ai-system/workspaces/xiaomei/research/profit-ticket-pipeline/runtime-decision-context-2026-06-23-fixed.json
- artifact_runtime_ledger: /root/hermes/company-ai-system/workspaces/xiaomei/research/profit-ticket-pipeline/runtime-decision-ledger.jsonl

## Backtest Feedback Applied
- feedback_win_rate: 64%
- symbol_penalties: ADBE, ALNY, CPB, KIM

## Market Regime: ACTIVE
- breadth: 53.3% (stocks with positive 20d return)
- momentum: +15.53% (median 20d return)
- volatility: 0.0204 (median daily |return|)
- advance_ratio: 33.3% (1d advancers)
- description: Moderate accel gate, balanced risk
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
- equal_weight_20d_benchmark: 0.08399182484520118
- median_20d_momentum: 0.15526703252576635
- median_5d_acceleration: -0.06667280410706256
- median_volume_confirmation: 0.26918556693789
- median_relative_strength: 0.07127520768056517
- top_market_score_p90: 0.7772584805669445

## Paper Review Candidates
|rank|symbol|company|latest|intraday|source_gap|market_score|catalyst_score|ticket_score|narrative|business|gate_status|
|---|---|---|---|---|---|---|---|---|---|---|---|
|1|MRNA|Moderna Inc|59.345|-0.07215447154471544|0.0|0.7665641613406367|0.525|1.3115641613406366|found_relevant|found_relevant|CANDIDATE_FOR_PAPER_REVIEW|
  - ticket_card: research_only=true allow_trade=false auto_order=false no_broker_api=true
  - lifecycle_stage: paper_review_candidate
  - kline_source: EastMoney US historical kline
  - quote_source: EastMoney US realtime/delayed quote + kline | status=ok | prev_close=63.96 | cross_check_basis=latest_price | gap=0.0 | mismatch=false
  - eastmoney_tabs: detail=https://quote.eastmoney.com/us/MRNA.html | news=https://quote.eastmoney.com/us/MRNA.html#news | company=https://quote.eastmoney.com/us/MRNA.html#company
  - catalyst: Moderna Stock’s 6-Day Rally Ends in a Dive. Why It’s One of the S&P 500’s Biggest Losers Today.; Moderna just got a signal investors can’t ignore
|2|STX|希捷科技|1094.04|0.022247554264036573|0.0|0.7938589656240109|0.425|1.268858965624011|found_relevant|found_relevant|REVERSAL_OVERRIDE|
  - ticket_card: research_only=true allow_trade=false auto_order=false no_broker_api=true
  - lifecycle_stage: paper_review_candidate
  - kline_source: EastMoney US historical kline
  - quote_source: EastMoney US realtime/delayed quote + kline | status=ok | prev_close=1070.23 | cross_check_basis=latest_price | gap=0.0 | mismatch=false
  - eastmoney_tabs: detail=https://quote.eastmoney.com/us/STX.html | news=https://quote.eastmoney.com/us/STX.html#news | company=https://quote.eastmoney.com/us/STX.html#company
  - catalyst: Buy, Hold, or Sell: Wall Street Fears Tech Compression, but This AI Storage Monster Has a Hidden Weapon; The Billionaire Who Called the 2008 Bubble Just Dumped Google to Buy These 5 AI Hardware Stocks
|3|GE|GE航空航天|355.12|-0.007046191701151949|0.0|0.6806551494550439|0.525|1.225655149455044|found_relevant|found_relevant|CANDIDATE_FOR_PAPER_REVIEW|
  - ticket_card: research_only=true allow_trade=false auto_order=false no_broker_api=true
  - lifecycle_stage: paper_review_candidate
  - kline_source: EastMoney US historical kline
  - quote_source: EastMoney US realtime/delayed quote + kline | status=ok | prev_close=357.64 | cross_check_basis=latest_price | gap=0.0 | mismatch=false
  - eastmoney_tabs: detail=https://quote.eastmoney.com/us/GE.html | news=https://quote.eastmoney.com/us/GE.html#news | company=https://quote.eastmoney.com/us/GE.html#company
  - catalyst: GE Vernova Stock Raised The Bar, Now It Has To Prove It; Is GE Stock's Large Backlog Enough To Out-Fly a Slowdown?
|4|TECH|Bio-Techne Corp|55.61|-0.0402140144977563|0.0|0.5910060559261221|0.525|1.166006055926122|found_relevant|found_relevant|CANDIDATE_FOR_PAPER_REVIEW|
  - ticket_card: research_only=true allow_trade=false auto_order=false no_broker_api=true
  - lifecycle_stage: paper_review_candidate
  - kline_source: EastMoney US historical kline
  - quote_source: EastMoney US realtime/delayed quote + kline | status=ok | prev_close=57.94 | cross_check_basis=latest_price | gap=0.0 | mismatch=false
  - eastmoney_tabs: detail=https://quote.eastmoney.com/us/TECH.html | news=https://quote.eastmoney.com/us/TECH.html#news | company=https://quote.eastmoney.com/us/TECH.html#company
  - catalyst: Bio-Techne (TECH) Stock Valuation After New Refeyn Bispecific Antibody Analysis Collaboration; 3 Reasons TECH is Risky and 1 Stock to Buy Instead
|5|TER|泰瑞达|457.0|0.043569601753745024|0.0|0.7843880267178163|0.1875|1.0218880267178163|found_relevant|found_unrelated|REVERSAL_OVERRIDE|
  - ticket_card: research_only=true allow_trade=false auto_order=false no_broker_api=true
  - lifecycle_stage: paper_review_candidate
  - kline_source: EastMoney US historical kline
  - quote_source: EastMoney US realtime/delayed quote + kline | status=ok | prev_close=437.92 | cross_check_basis=latest_price | gap=0.0 | mismatch=false
  - eastmoney_tabs: detail=https://quote.eastmoney.com/us/TER.html | news=https://quote.eastmoney.com/us/TER.html#news | company=https://quote.eastmoney.com/us/TER.html#company
  - catalyst: Stocks To Watch Echo AI Theme. GE Vernova Among Five Stocks Near Buy Points.

## Market Watchlist Needs Evidence
- none

## Catalyst Summary
- candidates_with_narrative_relevant: 5
- candidates_with_business_relevant: 4
- top_shared_titles: [["Moderna Stock’s 6-Day Rally Ends in a Dive. Why It’s One of the S&P 500’s Biggest Losers Today.", 1], ["Moderna just got a signal investors can’t ignore", 1], ["Buy, Hold, or Sell: Wall Street Fears Tech Compression, but This AI Storage Monster Has a Hidden Weapon", 1], ["The Billionaire Who Called the 2008 Bubble Just Dumped Google to Buy These 5 AI Hardware Stocks", 1], ["GE Vernova Stock Raised The Bar, Now It Has To Prove It", 1]]

## Lifecycle Snapshot
- paper_review_candidates: 5
- market_watchlist_candidates: 0
- blocked_by_risk_candidates: 0
- best_watch_candidate: AAPL
- best_watch_reason: classification=MARKET_WATCHLIST_NEEDS_EVIDENCE; risk=CLEAN; evidence=LOW_CONFIRMATION_BLOCK

## Evidence Gaps
### 1. MRNA
- company: Moderna Inc (eastmoney_us)
- narrative query: MRNA moderna stock catalyst earnings news
- business query: MRNA moderna orders demand backlog guidance revenue customer contract
- narrative ranked candidates: 10 | status: found_relevant | returncode: 124
- business ranked candidates: 10 | status: found_relevant | returncode: 124
- evidence gap reason: paper_review_gate_passed
### 2. STX
- company: 希捷科技 (eastmoney_us)
- narrative query: STX 希捷科技 stock catalyst earnings news
- business query: STX 希捷科技 orders demand backlog guidance revenue customer contract
- narrative ranked candidates: 10 | status: found_relevant | returncode: 124
- business ranked candidates: 10 | status: found_relevant | returncode: 124
- evidence gap reason: paper_review_gate_passed
### 3. GE
- company: GE航空航天 (eastmoney_us)
- narrative query: GE ge stock catalyst earnings news
- business query: GE ge orders demand backlog guidance revenue customer contract
- narrative ranked candidates: 10 | status: found_relevant | returncode: 124
- business ranked candidates: 10 | status: found_relevant | returncode: 124
- evidence gap reason: paper_review_gate_passed
### 4. TECH
- company: Bio-Techne Corp (eastmoney_us)
- narrative query: TECH bio techne stock catalyst earnings news
- business query: TECH bio techne orders demand backlog guidance revenue customer contract
- narrative ranked candidates: 10 | status: found_relevant | returncode: 124
- business ranked candidates: 10 | status: found_relevant | returncode: 124
- evidence gap reason: paper_review_gate_passed
### 5. TER
- company: 泰瑞达 (eastmoney_us)
- narrative query: TER 泰瑞达 stock catalyst earnings news
- business query: TER 泰瑞达 orders demand backlog guidance revenue customer contract
- narrative ranked candidates: 10 | status: found_relevant | returncode: 124
- business ranked candidates: 10 | status: found_unrelated | returncode: 124
- evidence gap reason: paper_review_gate_passed

## Quality Check (Buffett Skills)
### MRNA: MODERATE (score=0.57)
  - roe: 0.00
  - pe_ttm: 1.00
  - dividend_yield: 0.00
  - price_position_52w: 0.83
  - liquidity_amount: 1.00
### STX: STRONG (score=0.75)
  - roe: 1.00
  - pe_ttm: 0.00
  - dividend_yield: 1.00
  - price_position_52w: 0.73
  - liquidity_amount: 1.00
### GE: MODERATE (score=0.70)
  - roe: 1.00
  - pe_ttm: 0.79
  - dividend_yield: 0.00
  - price_position_52w: 0.70
  - liquidity_amount: 1.00
### TECH: STRONG (score=0.79)
  - roe: 1.00
  - pe_ttm: 1.00
  - dividend_yield: 0.00
  - price_position_52w: 0.97
  - liquidity_amount: 1.00
### TER: STRONG (score=0.88)
  - roe: 1.00
  - pe_ttm: 0.74
  - dividend_yield: 1.00
  - price_position_52w: 0.67
  - liquidity_amount: 1.00

## Risk Checklist (UZI-Skill)
### MRNA: WATCH (red=0, yellow=1)
  - price_extended_vs_52w: [GREEN] latest/52w_high=87.6%
  - intraday_gap: [GREEN] intraday_pct_chg=-7.22%
  - liquidity: [GREEN] amount=499,932,048
  - valuation: [GREEN] pe_ttm=3.18
  - quality_gap: [YELLOW] roe=-1673.00%
  - price_manipulation: [GREEN] 5d_accel=-0.0667
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
  - price_extended_vs_52w: [YELLOW] latest/52w_high=95.5%
  - intraday_gap: [GREEN] intraday_pct_chg=2.22%
  - liquidity: [GREEN] amount=7,527,336,192
  - valuation: [YELLOW] pe_ttm=224.03
  - quality_gap: [GREEN] roe=58879.00%
  - price_manipulation: [RED] 5d_accel=-0.1748
  - news_red_flags: [GREEN] narrative_status=found_relevant
  - supply_chain_risk: [GREEN] business_status=found_relevant
  - short_interest: [GREEN] provider_field_unavailable
  - dilution_risk: [GREEN] provider_field_unavailable
  - debt_covenant: [GREEN] provider_field_unavailable
  - earnings_quality: [GREEN] provider_field_unavailable
  - insider_selling: [GREEN] provider_field_unavailable
  - regulatory_risk: [GREEN] provider_field_unavailable
  - concentration_risk: [GREEN] provider_field_unavailable
### GE: WATCH (red=0, yellow=2)
  - price_extended_vs_52w: [YELLOW] latest/52w_high=97.4%
  - intraday_gap: [GREEN] intraday_pct_chg=-0.70%
  - liquidity: [GREEN] amount=1,934,930,704
  - valuation: [GREEN] pe_ttm=20.52
  - quality_gap: [GREEN] roe=1037.00%
  - price_manipulation: [YELLOW] 5d_accel=-0.1177
  - news_red_flags: [GREEN] narrative_status=found_relevant
  - supply_chain_risk: [GREEN] business_status=found_relevant
  - short_interest: [GREEN] provider_field_unavailable
  - dilution_risk: [GREEN] provider_field_unavailable
  - debt_covenant: [GREEN] provider_field_unavailable
  - earnings_quality: [GREEN] provider_field_unavailable
  - insider_selling: [GREEN] provider_field_unavailable
  - regulatory_risk: [GREEN] provider_field_unavailable
  - concentration_risk: [GREEN] provider_field_unavailable
### TECH: WATCH (red=0, yellow=1)
  - price_extended_vs_52w: [GREEN] latest/52w_high=77.2%
  - intraday_gap: [GREEN] intraday_pct_chg=-4.02%
  - liquidity: [GREEN] amount=114,007,433
  - valuation: [GREEN] pe_ttm=4.18
  - quality_gap: [GREEN] roe=636.00%
  - price_manipulation: [YELLOW] 5d_accel=-0.1441
  - news_red_flags: [GREEN] narrative_status=found_relevant
  - supply_chain_risk: [GREEN] business_status=found_relevant
  - short_interest: [GREEN] provider_field_unavailable
  - dilution_risk: [GREEN] provider_field_unavailable
  - debt_covenant: [GREEN] provider_field_unavailable
  - earnings_quality: [GREEN] provider_field_unavailable
  - insider_selling: [GREEN] provider_field_unavailable
  - regulatory_risk: [GREEN] provider_field_unavailable
  - concentration_risk: [GREEN] provider_field_unavailable
### TER: ELEVATED (red=1, yellow=2)
  - price_extended_vs_52w: [YELLOW] latest/52w_high=99.5%
  - intraday_gap: [GREEN] intraday_pct_chg=4.36%
  - liquidity: [GREEN] amount=1,957,491,728
  - valuation: [GREEN] pe_ttm=22.76
  - quality_gap: [GREEN] roe=1343.00%
  - price_manipulation: [RED] 5d_accel=-0.1596
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
### MRNA: BULLISH_CONSENSUS (pos=3, neg=0)
  - fundamental_analyst: Quality verdict: MODERATE (score=0.57)
  - news_analyst: News status: found_relevant, relevance=0.95
  - sentiment_analyst: Business/sentiment status: found_relevant, relevance=0.95
  - technical_analyst: Signals: strong_momentum, outperforming_market, volume_confirmed
  - bull_case: Bull points: 4
  - bear_case: Bear points: 0
  - risk_manager: Risk: WATCH, Quality: MODERATE, Rec: PROCEED_WITH_MONITORING
### STX: BEARISH_CONSENSUS (pos=3, neg=3)
  - fundamental_analyst: Quality verdict: STRONG (score=0.75)
  - news_analyst: News status: found_relevant, relevance=0.75
  - sentiment_analyst: Business/sentiment status: found_relevant, relevance=0.75
  - technical_analyst: Signals: strong_momentum, deceleration_warning, outperforming_market, volume_confirmed
  - bull_case: Bull points: 5
  - bear_case: Bear points: 3
  - risk_manager: Risk: ELEVATED, Quality: STRONG, Rec: PROCEED_WITH_CAUTION
### GE: NEUTRAL (pos=3, neg=2)
  - fundamental_analyst: Quality verdict: MODERATE (score=0.70)
  - news_analyst: News status: found_relevant, relevance=0.95
  - sentiment_analyst: Business/sentiment status: found_relevant, relevance=0.95
  - technical_analyst: Signals: strong_momentum, deceleration_warning, outperforming_market, volume_confirmed
  - bull_case: Bull points: 5
  - bear_case: Bear points: 2
  - risk_manager: Risk: WATCH, Quality: MODERATE, Rec: PROCEED_WITH_MONITORING
### TECH: BULLISH_CONSENSUS (pos=3, neg=1)
  - fundamental_analyst: Quality verdict: STRONG (score=0.79)
  - news_analyst: News status: found_relevant, relevance=0.95
  - sentiment_analyst: Business/sentiment status: found_relevant, relevance=0.95
  - technical_analyst: Signals: strong_momentum, deceleration_warning, outperforming_market
  - bull_case: Bull points: 4
  - bear_case: Bear points: 1
  - risk_manager: Risk: WATCH, Quality: STRONG, Rec: PROCEED_WITH_MONITORING
### TER: BEARISH_CONSENSUS (pos=2, neg=3)
  - fundamental_analyst: Quality verdict: STRONG (score=0.88)
  - news_analyst: News status: found_relevant, relevance=0.75
  - sentiment_analyst: Business/sentiment status: found_unrelated, relevance=0.00
  - technical_analyst: Signals: strong_momentum, deceleration_warning, outperforming_market, volume_confirmed
  - bull_case: Bull points: 4
  - bear_case: Bear points: 3
  - risk_manager: Risk: ELEVATED, Quality: STRONG, Rec: PROCEED_WITH_CAUTION

## Supply Chain Map (Serenity Skill)
- MRNA: no_supply_chain_data | themes=[]
- STX: no_supply_chain_data | themes=[]
- GE: no_supply_chain_data | themes=[]
- TECH: 6 themes identified | themes=['pharma', 'biotech', 'FDA', 'technology', 'cloud', 'AI']
- TER: no_supply_chain_data | themes=[]

## Replay Hypothesis (QuantDinger)
- MRNA: Entry=momentum_continuation, SL=-5.0%, TP=8.0%, Period=5d_10d, Conf=70%
- STX: Entry=avoid_deceleration, SL=0.0%, TP=0.0%, Period=N/A, Conf=10%
- GE: Entry=pullback_entry, SL=-3.0%, TP=5.0%, Period=3d_5d, Conf=50%
- TECH: Entry=momentum_continuation, SL=-5.0%, TP=8.0%, Period=5d_10d, Conf=70%
- TER: Entry=avoid_deceleration, SL=0.0%, TP=0.0%, Period=N/A, Conf=10%

## Risk Management (Cross-Platform Best Practices)
### MRNA: ALLOWED
  - stop_loss: $57.62
  - take_profit: $62.80
  - risk_reward: 2.00
  - kelly_fraction: 0.174
  - risk_score: N/A
  - confidence: 1.00
### STX: ALLOWED
  - stop_loss: $1062.21
  - take_profit: $1157.70
  - risk_reward: 2.00
  - kelly_fraction: 0.174
  - risk_score: N/A
  - confidence: 1.00
### GE: ALLOWED
  - stop_loss: $344.79
  - take_profit: $375.78
  - risk_reward: 2.00
  - kelly_fraction: 0.174
  - risk_score: N/A
  - confidence: 1.00
### TECH: ALLOWED
  - stop_loss: $53.99
  - take_profit: $58.85
  - risk_reward: 2.00
  - kelly_fraction: 0.174
  - risk_score: N/A
  - confidence: 1.00
### TER: ALLOWED
  - stop_loss: $443.70
  - take_profit: $483.59
  - risk_reward: 2.00
  - kelly_fraction: 0.174
  - risk_score: N/A
  - confidence: 1.00

## Forward Tracking
|symbol|rank|horizon|due_date|status|
|---|---|---|---|---|
|MRNA|1|1d|2026-06-23|pending|
|MRNA|1|3d|2026-06-25|pending|
|MRNA|1|5d|2026-06-29|pending|
|MRNA|1|10d|2026-07-06|pending|
|STX|2|1d|2026-06-23|pending|
|STX|2|3d|2026-06-25|pending|
|STX|2|5d|2026-06-29|pending|
|STX|2|10d|2026-07-06|pending|
|GE|3|1d|2026-06-23|pending|
|GE|3|3d|2026-06-25|pending|
|GE|3|5d|2026-06-29|pending|
|GE|3|10d|2026-07-06|pending|
|TECH|4|1d|2026-06-23|pending|
|TECH|4|3d|2026-06-25|pending|
|TECH|4|5d|2026-06-29|pending|
|TECH|4|10d|2026-07-06|pending|
|TER|5|1d|2026-06-23|pending|
|TER|5|3d|2026-06-25|pending|
|TER|5|5d|2026-06-29|pending|
|TER|5|10d|2026-07-06|pending|

## Market Snapshot Top 10
- momentum_exhaustion_guard_threshold: -0.2
- momentum_exhaustion_guard_adjustment: -0.05
|rank|symbol|raw_market_score|market_score|rule|prior_20d|accel_5d|volume_confirm|closing_strength|vwmomentum|
|---|---|---|---|---|---|---|---|---|---|
|1|STX|1.1124868710825004|0.7938589656240109||0.3499000567578905|-0.17482702015366303|1.264873755801918|0.38945666948432767|0.5592894722350429|
|2|TER|1.08216206092183|0.7843880267178163||0.29300588501584435|-0.15957334533330458|0.9933267896002531|0.48998234847077526|0.45027025829646344|
|3|MRNA|0.7097003745318352|0.7665641613406367||0.2557130765975455|-0.06667280410706256|1.6932672054489761|0.6390387983896992|0.4587835076394849|
|4|SW|0.9726666666666668|0.6999440602033451||0.20270270270270263|-0.15491876918469716|0.26918556693789|0.32792943118351087|0.2317070871891023|
|5|GE|0.5852720079129572|0.6806551494550439||0.17682926829268308|-0.11771802463029113|0.3271229120157162|0.32807946154237755|0.20533124001121714|
|6|TECH|0.4848387096774193|0.5910060559261221||0.17394975723031458|-0.14413494241549984|0.05605570699605322|0.46911453786172475|0.16196854920423354|
|7|SWK|0.5077777777777779|0.524578393969871||0.15526703252576635|-0.12309769504669443|0.5239622653480294|0.20155036668139809|0.20313271439817504|
|8|IP|0.7172881355932207|0.49729205053198333||0.18856222311719684|-0.16809196032328244|0.4917318273836522|0.1602923986407651|0.22686250292518584|
|9|AAPL|0.4010836277974087|0.4795632800837837||-0.026164792288271843|0.046361955067786176|0.0359875879311371|0.46381263481340984|-0.02568478063189355|
|10|TSLA|0.42233415233415245|0.3759463735162601||-0.030633002273543153|0.027237583628266004|-0.008107382499199622|0.4852777670031963|-0.03057112889002993|

## Final Classification
- CANDIDATE_FOR_PAPER_REVIEW
