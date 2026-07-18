# XIAOMEI US Profit Ticket Pipeline V0

RESEARCH_ONLY
NOT_TRADING_ADVICE
NO_BROKER
NO_ORDER
NO_LEDGER
NO_LIVE_TRADE

- output_date: 2026-06-19-final
- as_of_date: 2026-06-18
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
- artifact_summary: /root/hermes/company-ai-system/workspaces/xiaomei/research/profit-ticket-pipeline/summary-2026-06-19-final.md
- artifact_metrics: /root/hermes/company-ai-system/workspaces/xiaomei/research/profit-ticket-pipeline/metrics-2026-06-19-final.json
- artifact_candidates: /root/hermes/company-ai-system/workspaces/xiaomei/research/profit-ticket-pipeline/candidates-2026-06-19-final.csv
- artifact_forward_tracking: /root/hermes/company-ai-system/workspaces/xiaomei/research/profit-ticket-pipeline/forward-tracking-2026-06-19-final.csv

## Backtest Feedback Applied
- feedback_win_rate: 64%
- symbol_penalties: ADBE, ALNY, CPB, KIM

## Market Regime: ACTIVE
- breadth: 55.8% (stocks with positive 20d return)
- momentum: +1.07% (median 20d return)
- volatility: 0.0145 (median daily |return|)
- advance_ratio: 51.8% (1d advancers)
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
- equal_weight_20d_benchmark: 0.023692998517547907
- median_20d_momentum: 0.013570734601290435
- median_5d_acceleration: -0.0193883073059104
- median_volume_confirmation: -0.024029867263304694
- median_relative_strength: -0.010122263916257472
- top_market_score_p90: 0.7029513618677042

## Paper Review Candidates
|rank|symbol|company|latest|intraday|source_gap|market_score|catalyst_score|ticket_score|narrative|business|gate_status|
|---|---|---|---|---|---|---|---|---|---|---|---|
|1|SW|Smurfit WestRock plc|44.151|0.016835559649930998|0.00020380089318849937|0.7872568093385214|0.525|1.3622568093385214|found_relevant|found_relevant|CANDIDATE_FOR_PAPER_REVIEW|
  - ticket_card: research_only=true allow_trade=false auto_order=false no_broker_api=true
  - kline_source: Yahoo Finance historical kline
  - quote_source: EastMoney US realtime/delayed quote + kline | status=ok | prev_close=43.42 | cross_check_basis=latest_price | gap=0.00020380089318849937 | mismatch=false
  - catalyst: Assessing Smurfit Westrock (SW) Valuation After Recent Mixed Share Performance; Smurfit WestRock PLC (SW): Best Stock to Buy According to George Soros
|2|GE|GE航空航天|357.78|0.002100663809763814|0.0013676529675870075|0.786284046692607|0.525|1.361284046692607|found_relevant|found_relevant|CANDIDATE_FOR_PAPER_REVIEW|
  - ticket_card: research_only=true allow_trade=false auto_order=false no_broker_api=true
  - kline_source: Yahoo Finance historical kline
  - quote_source: EastMoney US realtime/delayed quote + kline | status=ok | prev_close=357.03 | cross_check_basis=latest_price | gap=0.0013676529675870075 | mismatch=false
  - catalyst: The Overlooked Signal In GE Stock's Shipping Delays; Is GE Stock's Large Backlog Enough To Out-Fly a Slowdown?
|3|STX|希捷科技|1063.24|-0.0026546099224252773|0.0005156429841043364|0.8318093385214009|0.425|1.306809338521401|found_relevant|found_relevant|CANDIDATE_FOR_PAPER_REVIEW|
  - ticket_card: research_only=true allow_trade=false auto_order=false no_broker_api=true
  - kline_source: Yahoo Finance historical kline
  - quote_source: EastMoney US realtime/delayed quote + kline | status=ok | prev_close=1066.07 | cross_check_basis=prev_close | gap=0.0005156429841043364 | mismatch=false
  - catalyst: Why JPMorgan Remains Bullish on Seagate Technology Holdings plc (STX); AI's Data Explosion Creates a Multi-Year Growth Runway for Seagate
|4|TER|泰瑞达|431.93|0.057200900724495796|0.00020841900442913897|0.807101167315175|0.425|1.282101167315175|found_relevant|found_relevant|CANDIDATE_FOR_PAPER_REVIEW|
  - ticket_card: research_only=true allow_trade=false auto_order=false no_broker_api=true
  - kline_source: Yahoo Finance historical kline
  - quote_source: EastMoney US realtime/delayed quote + kline | status=ok | prev_close=408.56 | cross_check_basis=latest_price | gap=0.00020841900442913897 | mismatch=false
  - catalyst: Micron is on an absolute TEAR this morning. How do you find these stocks before they blow up?; NBIS Stock Rally Rolls On After Record High: Retail Sees 'Shorts Drowning In Losses' As Nasdaq-100 Inclusion Nears
|5|IP|国际纸业|36.96|0.02212389380530988|0.0013546505769328476|0.8028210116731517|0.425|1.2778210116731517|found_relevant|found_relevant|CANDIDATE_FOR_PAPER_REVIEW|
  - ticket_card: research_only=true allow_trade=false auto_order=false no_broker_api=true
  - kline_source: Yahoo Finance historical kline
  - quote_source: EastMoney US realtime/delayed quote + kline | status=ok | prev_close=36.16 | cross_check_basis=latest_price | gap=0.0013546505769328476 | mismatch=false
  - catalyst: 3 Mid-Cap Stocks We’re Skeptical Of; International Paper Expands Corrugated Reach With Delmarva Deal And New Build

## Market Watchlist Needs Evidence
- none

## Catalyst Summary
- candidates_with_narrative_relevant: 5
- candidates_with_business_relevant: 5
- top_shared_titles: [["Assessing Smurfit Westrock (SW) Valuation After Recent Mixed Share Performance", 1], ["Smurfit WestRock PLC (SW): Best Stock to Buy According to George Soros", 1], ["The Overlooked Signal In GE Stock's Shipping Delays", 1], ["Is GE Stock's Large Backlog Enough To Out-Fly a Slowdown?", 1], ["Why JPMorgan Remains Bullish on Seagate Technology Holdings plc (STX)", 1]]

## Evidence Gaps
### 1. SW
- company: Smurfit WestRock plc (eastmoney_us)
- narrative query: SW smurfit westrock stock catalyst earnings news
- business query: SW smurfit westrock orders demand backlog guidance revenue customer contract
- narrative ranked candidates: 10 | status: found_relevant | returncode: 0
- business ranked candidates: 10 | status: found_relevant | returncode: 0
- evidence gap reason: paper_review_gate_passed
### 2. GE
- company: GE航空航天 (eastmoney_us)
- narrative query: GE ge stock catalyst earnings news
- business query: GE ge orders demand backlog guidance revenue customer contract
- narrative ranked candidates: 10 | status: found_relevant | returncode: 0
- business ranked candidates: 10 | status: found_relevant | returncode: 0
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
### 5. IP
- company: 国际纸业 (eastmoney_us)
- narrative query: IP 国际纸业 stock catalyst earnings news
- business query: IP 国际纸业 orders demand backlog guidance revenue customer contract
- narrative ranked candidates: 10 | status: found_relevant | returncode: 0
- business ranked candidates: 10 | status: found_relevant | returncode: 0
- evidence gap reason: paper_review_gate_passed

## Quality Check (Buffett Skills)
### SW: STRONG (score=0.77)
  - roe: 1.00
  - pe_ttm: 1.00
  - dividend_yield: 0.00
  - price_position_52w: 0.86
  - liquidity_amount: 1.00
### GE: STRONG (score=0.90)
  - roe: 1.00
  - pe_ttm: 0.79
  - dividend_yield: 1.00
  - price_position_52w: 0.69
  - liquidity_amount: 1.00
### STX: STRONG (score=0.75)
  - roe: 1.00
  - pe_ttm: 0.00
  - dividend_yield: 1.00
  - price_position_52w: 0.76
  - liquidity_amount: 1.00
### TER: STRONG (score=0.89)
  - roe: 1.00
  - pe_ttm: 0.77
  - dividend_yield: 1.00
  - price_position_52w: 0.69
  - liquidity_amount: 1.00
### IP: STRONG (score=0.78)
  - roe: 1.00
  - pe_ttm: 1.00
  - dividend_yield: 0.00
  - price_position_52w: 0.91
  - liquidity_amount: 1.00

## Risk Checklist (UZI-Skill)
### SW: ELEVATED (red=1, yellow=0)
  - price_extended_vs_52w: [GREEN] latest/52w_high=85.3%
  - intraday_gap: [GREEN] intraday_pct_chg=1.68%
  - liquidity: [GREEN] amount=183,476,058
  - valuation: [GREEN] pe_ttm=1.28
  - quality_gap: [GREEN] roe=36.00%
  - price_manipulation: [RED] 5d_accel=-0.1549
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
  - price_extended_vs_52w: [YELLOW] latest/52w_high=98.1%
  - intraday_gap: [GREEN] intraday_pct_chg=0.21%
  - liquidity: [GREEN] amount=1,093,941,488
  - valuation: [GREEN] pe_ttm=20.67
  - quality_gap: [GREEN] roe=1037.00%
  - price_manipulation: [YELLOW] 5d_accel=-0.1169
  - news_red_flags: [GREEN] narrative_status=found_relevant
  - supply_chain_risk: [GREEN] business_status=found_relevant
  - short_interest: [GREEN] provider_field_unavailable
  - dilution_risk: [GREEN] provider_field_unavailable
  - debt_covenant: [GREEN] provider_field_unavailable
  - earnings_quality: [GREEN] provider_field_unavailable
  - insider_selling: [GREEN] provider_field_unavailable
  - regulatory_risk: [GREEN] provider_field_unavailable
  - concentration_risk: [GREEN] provider_field_unavailable
### STX: ELEVATED (red=1, yellow=1)
  - price_extended_vs_52w: [GREEN] latest/52w_high=92.9%
  - intraday_gap: [GREEN] intraday_pct_chg=-0.27%
  - liquidity: [GREEN] amount=5,100,477,184
  - valuation: [YELLOW] pe_ttm=217.73
  - quality_gap: [GREEN] roe=58879.00%
  - price_manipulation: [RED] 5d_accel=-0.1914
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
  - price_extended_vs_52w: [YELLOW] latest/52w_high=98.0%
  - intraday_gap: [GREEN] intraday_pct_chg=5.72%
  - liquidity: [GREEN] amount=1,031,105,408
  - valuation: [GREEN] pe_ttm=21.51
  - quality_gap: [GREEN] roe=1343.00%
  - price_manipulation: [YELLOW] 5d_accel=-0.1223
  - news_red_flags: [GREEN] narrative_status=found_relevant
  - supply_chain_risk: [GREEN] business_status=found_relevant
  - short_interest: [GREEN] provider_field_unavailable
  - dilution_risk: [GREEN] provider_field_unavailable
  - debt_covenant: [GREEN] provider_field_unavailable
  - earnings_quality: [GREEN] provider_field_unavailable
  - insider_selling: [GREEN] provider_field_unavailable
  - regulatory_risk: [GREEN] provider_field_unavailable
  - concentration_risk: [GREEN] provider_field_unavailable
### IP: ELEVATED (red=1, yellow=0)
  - price_extended_vs_52w: [GREEN] latest/52w_high=68.1%
  - intraday_gap: [GREEN] intraday_pct_chg=2.21%
  - liquidity: [GREEN] amount=181,529,818
  - valuation: [GREEN] pe_ttm=1.32
  - quality_gap: [GREEN] roe=40.00%
  - price_manipulation: [RED] 5d_accel=-0.1570
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
### SW: NEUTRAL (pos=3, neg=2)
  - fundamental_analyst: Quality verdict: STRONG (score=0.77)
  - news_analyst: News status: found_relevant, relevance=0.95
  - sentiment_analyst: Business/sentiment status: found_relevant, relevance=0.95
  - technical_analyst: Signals: strong_momentum, deceleration_warning, outperforming_market
  - bull_case: Bull points: 4
  - bear_case: Bear points: 2
  - risk_manager: Risk: ELEVATED, Quality: STRONG, Rec: PROCEED_WITH_CAUTION
### GE: NEUTRAL (pos=3, neg=2)
  - fundamental_analyst: Quality verdict: STRONG (score=0.90)
  - news_analyst: News status: found_relevant, relevance=0.95
  - sentiment_analyst: Business/sentiment status: found_relevant, relevance=0.95
  - technical_analyst: Signals: strong_momentum, deceleration_warning, outperforming_market
  - bull_case: Bull points: 4
  - bear_case: Bear points: 2
  - risk_manager: Risk: WATCH, Quality: STRONG, Rec: PROCEED_WITH_MONITORING
### STX: NEUTRAL (pos=3, neg=2)
  - fundamental_analyst: Quality verdict: STRONG (score=0.75)
  - news_analyst: News status: found_relevant, relevance=0.75
  - sentiment_analyst: Business/sentiment status: found_relevant, relevance=0.75
  - technical_analyst: Signals: strong_momentum, deceleration_warning, outperforming_market, volume_confirmed
  - bull_case: Bull points: 5
  - bear_case: Bear points: 2
  - risk_manager: Risk: ELEVATED, Quality: STRONG, Rec: PROCEED_WITH_CAUTION
### TER: NEUTRAL (pos=3, neg=2)
  - fundamental_analyst: Quality verdict: STRONG (score=0.89)
  - news_analyst: News status: found_relevant, relevance=0.75
  - sentiment_analyst: Business/sentiment status: found_relevant, relevance=0.75
  - technical_analyst: Signals: strong_momentum, deceleration_warning, outperforming_market
  - bull_case: Bull points: 4
  - bear_case: Bear points: 2
  - risk_manager: Risk: WATCH, Quality: STRONG, Rec: PROCEED_WITH_MONITORING
### IP: NEUTRAL (pos=3, neg=2)
  - fundamental_analyst: Quality verdict: STRONG (score=0.78)
  - news_analyst: News status: found_relevant, relevance=0.75
  - sentiment_analyst: Business/sentiment status: found_relevant, relevance=0.75
  - technical_analyst: Signals: strong_momentum, deceleration_warning, outperforming_market
  - bull_case: Bull points: 4
  - bear_case: Bear points: 2
  - risk_manager: Risk: ELEVATED, Quality: STRONG, Rec: PROCEED_WITH_CAUTION

## Supply Chain Map (Serenity Skill)
- SW: no_supply_chain_data | themes=[]
- GE: no_supply_chain_data | themes=[]
- STX: no_supply_chain_data | themes=[]
- TER: no_supply_chain_data | themes=[]
- IP: no_supply_chain_data | themes=[]

## Replay Hypothesis (QuantDinger)
- SW: Entry=avoid_deceleration, SL=-3.0%, TP=5.0%, Period=3d_5d, Conf=20%
- GE: Entry=pullback_entry, SL=-3.0%, TP=5.0%, Period=3d_5d, Conf=50%
- STX: Entry=avoid_deceleration, SL=-3.0%, TP=5.0%, Period=3d_5d, Conf=20%
- TER: Entry=pullback_entry, SL=-3.0%, TP=5.0%, Period=3d_5d, Conf=50%
- IP: Entry=avoid_deceleration, SL=-3.0%, TP=5.0%, Period=3d_5d, Conf=20%

## Risk Management (Cross-Platform Best Practices)
### SW: ALLOWED
  - stop_loss: $42.88
  - take_profit: $46.73
  - risk_reward: 2.00
  - kelly_fraction: 0.174
  - risk_score: N/A
  - confidence: 1.00
### GE: ALLOWED
  - stop_loss: $347.85
  - take_profit: $379.12
  - risk_reward: 2.00
  - kelly_fraction: 0.174
  - risk_score: N/A
  - confidence: 1.00
### STX: ALLOWED
  - stop_loss: $1035.59
  - take_profit: $1128.68
  - risk_reward: 2.00
  - kelly_fraction: 0.174
  - risk_score: N/A
  - confidence: 1.00
### TER: ALLOWED
  - stop_loss: $419.28
  - take_profit: $456.97
  - risk_reward: 2.00
  - kelly_fraction: 0.174
  - risk_score: N/A
  - confidence: 1.00
### IP: ALLOWED
  - stop_loss: $35.84
  - take_profit: $39.06
  - risk_reward: 2.00
  - kelly_fraction: 0.174
  - risk_score: N/A
  - confidence: 1.00

## Forward Tracking
|symbol|rank|horizon|due_date|status|
|---|---|---|---|---|
|SW|1|1d|2026-06-19|pending|
|SW|1|3d|2026-06-23|pending|
|SW|1|5d|2026-06-25|pending|
|SW|1|10d|2026-07-02|pending|
|GE|2|1d|2026-06-19|pending|
|GE|2|3d|2026-06-23|pending|
|GE|2|5d|2026-06-25|pending|
|GE|2|10d|2026-07-02|pending|
|STX|3|1d|2026-06-19|pending|
|STX|3|3d|2026-06-23|pending|
|STX|3|5d|2026-06-25|pending|
|STX|3|10d|2026-07-02|pending|
|TER|4|1d|2026-06-19|pending|
|TER|4|3d|2026-06-23|pending|
|TER|4|5d|2026-06-25|pending|
|TER|4|10d|2026-07-02|pending|
|IP|5|1d|2026-06-19|pending|
|IP|5|3d|2026-06-23|pending|
|IP|5|5d|2026-06-25|pending|
|IP|5|10d|2026-07-02|pending|

## Market Snapshot Top 10
- momentum_exhaustion_guard_threshold: -0.2
- momentum_exhaustion_guard_adjustment: -0.05
|rank|symbol|raw_market_score|market_score|rule|prior_20d|accel_5d|volume_confirm|closing_strength|vwmomentum|
|---|---|---|---|---|---|---|---|---|---|
|1|STX|0.8318093385214009|0.8318093385214009||0.4201339218925213|-0.19143648024483295|0.7203123819311859|0.45765532733982434|0.5631128656112171|
|2|TER|0.807101167315175|0.807101167315175||0.25458297858343504|-0.1223333633537711|0.1067997173399442|0.4405763454298176|0.24771609946872755|
|3|IP|0.8028210116731517|0.8028210116731517||0.2131026954159987|-0.1570226083863293|0.2786883443012851|0.3508223228256257|0.23604101188639687|
|4|UAL|0.7974708171206225|0.7974708171206225||0.20597840372232268|-0.15624926382560989|0.0808833085763414|0.2538850827425661|0.20322088496016266|
|5|LUV|0.7973735408560311|0.7973735408560311||0.2115648248399975|-0.13028240443573424|0.17245424299054646|0.3291942480734782|0.2317983084195841|
|6|WDC|0.8409533073929962|0.7909533073929962|momentum_exhaustion_guard|0.6365608277187431|-0.21578954691215513|1.109306953567219|0.4928439312582739|0.92525684121863|
|7|SW|0.7872568093385214|0.7872568093385214||0.18933473140494383|-0.1549004079570293|0.18864357747188398|0.304630409734685|0.19122469692295785|
|8|GE|0.786284046692607|0.786284046692607||0.19355689438287293|-0.11689510059937569|0.0668652642547598|0.48869420525080676|0.18947722580283372|
|9|SWK|0.781420233463035|0.781420233463035||0.1693420326391597|-0.12579574530383564|0.30485169729821493|0.30592397142323574|0.1927152594699568|
|10|HOOD|0.8311284046692606|0.7811284046692606|momentum_exhaustion_guard|0.4023230579208592|-0.2504202714423991|0.36820064363754224|0.4238200147892677|0.4786100097325055|

## Final Classification
- CANDIDATE_FOR_PAPER_REVIEW
