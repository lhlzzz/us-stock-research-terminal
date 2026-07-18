# XIAOMEI US Profit Ticket Pipeline V0

RESEARCH_ONLY
NOT_TRADING_ADVICE
NO_BROKER
NO_ORDER
NO_LEDGER
NO_LIVE_TRADE

- output_date: 2026-06-11-research-test
- as_of_date: 2026-06-11
- universe_source: nasdaq100_sp500_union
- source_mode: live
- universe_key: union
- universe_total_symbols: 516
- universe_included_symbols: 492
- period_used: 1y
- classification: MARKET_WATCHLIST_NEEDS_EVIDENCE
- candidate_pool_size: 3
- top_k: 3
- paper_review_count: 0
- market_watchlist_count: 3
- zero_paper_review_is_valid_output: True
- artifact_summary: /root/hermes/company-ai-system/workspaces/xiaomei/research/profit-ticket-pipeline-opening/summary-2026-06-11-research-test.md
- artifact_metrics: /root/hermes/company-ai-system/workspaces/xiaomei/research/profit-ticket-pipeline-opening/metrics-2026-06-11-research-test.json
- artifact_candidates: /root/hermes/company-ai-system/workspaces/xiaomei/research/profit-ticket-pipeline-opening/candidates-2026-06-11-research-test.csv
- artifact_forward_tracking: /root/hermes/company-ai-system/workspaces/xiaomei/research/profit-ticket-pipeline-opening/forward-tracking-2026-06-11-research-test.csv

## Methodology References
- UZI-Skill: risk checklist and multi-dimensional review
- TradingAgents: role-based research synthesis
- Serenity Skill: theme and supply-chain catalyst mapping
- Buffett Skills: quality, margin-of-safety, bear-case framing
- QuantDinger: replay discipline and data-health guardrails

## Price-Volume Summary
- equal_weight_20d_benchmark: 0.025638026000613868
- median_20d_momentum: 0.021294718632937304
- median_5d_acceleration: -0.01845001191254214
- median_volume_confirmation: -0.13993729631880503
- median_relative_strength: -0.004343307367676564
- top_market_score_p90: 0.6892057026476578

## Paper Review Candidates
- none

## Market Watchlist Needs Evidence
|rank|symbol|company|raw_market_score|market_score|rule|ticket_score|narrative|business|gate_status|
|---|---|---|---|---|---|---|---|---|---|
|1|SJM|The J.M. Smucker Company|0.8623217922606925|0.8623217922606925||0.8623217922606925|missing|missing|MARKET_WATCHLIST_NEEDS_EVIDENCE|
|2|KIM|KIM|0.8085539714867618|0.8085539714867618||0.8085539714867618|missing|missing|MARKET_WATCHLIST_NEEDS_EVIDENCE|
|3|CAH|Cardinal Health, Inc.|0.7947046843177189|0.7947046843177189||0.7947046843177189|missing|missing|MARKET_WATCHLIST_NEEDS_EVIDENCE|

## Catalyst Summary
- candidates_with_narrative_relevant: 0
- candidates_with_business_relevant: 0
- top_shared_titles: []

## Evidence Gaps
### 1. SJM
- company: The J.M. Smucker Company (yfinance)
- narrative query: SJM j m smucker stock catalyst earnings news
- business query: SJM j m smucker orders demand backlog guidance revenue customer contract
- narrative ranked candidates: 0 | status: missing | returncode: 124
- business ranked candidates: 0 | status: missing | returncode: 124
- evidence gap reason: last30days_returned_zero_ranked_candidates
### 2. KIM
- company: KIM (symbol)
- narrative query: KIM kim stock catalyst earnings news
- business query: KIM kim orders demand backlog guidance revenue customer contract
- narrative ranked candidates: 0 | status: missing | returncode: 124
- business ranked candidates: 0 | status: missing | returncode: 124
- evidence gap reason: last30days_returned_zero_ranked_candidates
### 3. CAH
- company: Cardinal Health, Inc. (yfinance)
- narrative query: CAH cardinal health stock catalyst earnings news
- business query: CAH cardinal health orders demand backlog guidance revenue customer contract
- narrative ranked candidates: 0 | status: missing | returncode: 124
- business ranked candidates: 0 | status: missing | returncode: 124
- evidence gap reason: last30days_returned_zero_ranked_candidates

## Quality Check (Buffett Skills)
### SJM: WEAK (score=0.34)
  - roe: 0.00
  - profit_margin: 0.00
  - gross_margin: 0.57
  - debt_to_equity: 0.36
  - free_cash_flow: 1.00
  - payout_ratio: 0.14
  - current_ratio: 0.31
### KIM: WEAK (score=0.50)
  - roe: 0.20
  - profit_margin: 1.00
  - gross_margin: 1.00
  - debt_to_equity: 0.61
  - payout_ratio: 0.00
  - current_ratio: 0.19
### CAH: WEAK (score=0.43)
  - profit_margin: 0.02
  - gross_margin: 0.06
  - free_cash_flow: 1.00
  - payout_ratio: 0.69
  - current_ratio: 0.36

## Risk Checklist (UZI-Skill)
### SJM: WATCH (red=0, yellow=1)
  - short_interest: [GREEN] short_interest=5.5%
  - dilution_risk: [GREEN] shares_outstanding=106,648,319
  - debt_covenant: [YELLOW] debt_to_equity=1.29
  - price_manipulation: [GREEN] 5d_accel=-0.0156
  - news_red_flags: [GREEN] narrative_status=missing
  - supply_chain_risk: [GREEN] business_status=missing
  - regulatory_risk: [GREEN] not_assessed_automatically
  - concentration_risk: [GREEN] not_assessed_automatically
  - earnings_quality: [GREEN] yfinance_limited
  - insider_selling: [GREEN] not_assessed_automatically
### KIM: CLEAN (red=0, yellow=0)
  - short_interest: [GREEN] short_interest=5.0%
  - dilution_risk: [GREEN] shares_outstanding=674,389,792
  - debt_covenant: [GREEN] debt_to_equity=0.79
  - price_manipulation: [GREEN] 5d_accel=-0.0439
  - news_red_flags: [GREEN] narrative_status=missing
  - supply_chain_risk: [GREEN] business_status=missing
  - regulatory_risk: [GREEN] not_assessed_automatically
  - concentration_risk: [GREEN] not_assessed_automatically
  - earnings_quality: [GREEN] yfinance_limited
  - insider_selling: [GREEN] not_assessed_automatically
### CAH: WATCH (red=0, yellow=1)
  - short_interest: [GREEN] short_interest=3.9%
  - dilution_risk: [GREEN] shares_outstanding=234,205,855
  - debt_covenant: [GREEN] N/A
  - price_manipulation: [YELLOW] 5d_accel=-0.0908
  - news_red_flags: [GREEN] narrative_status=missing
  - supply_chain_risk: [GREEN] business_status=missing
  - regulatory_risk: [GREEN] not_assessed_automatically
  - concentration_risk: [GREEN] not_assessed_automatically
  - earnings_quality: [GREEN] yfinance_limited
  - insider_selling: [GREEN] not_assessed_automatically

## Research Panel (TradingAgents)
### SJM: MIXED (pos=0, neg=1)
  - fundamental_analyst: Quality verdict: WEAK (score=0.34)
  - news_analyst: News status: missing, relevance=0.00
  - sentiment_analyst: Business/sentiment status: missing, relevance=0.00
  - technical_analyst: Signals: strong_momentum, outperforming_market, volume_confirmed
  - bull_case: Bull points: 2
  - bear_case: Bear points: 1
  - risk_manager: Risk: WATCH, Quality: WEAK, Rec: PROCEED_WITH_MONITORING
### KIM: MIXED (pos=0, neg=0)
  - fundamental_analyst: Quality verdict: WEAK (score=0.50)
  - news_analyst: News status: missing, relevance=0.00
  - sentiment_analyst: Business/sentiment status: missing, relevance=0.00
  - technical_analyst: Signals: strong_momentum, outperforming_market, volume_confirmed
  - bull_case: Bull points: 2
  - bear_case: Bear points: 0
  - risk_manager: Risk: CLEAN, Quality: WEAK, Rec: PROCEED
### CAH: MIXED (pos=0, neg=0)
  - fundamental_analyst: Quality verdict: WEAK (score=0.43)
  - news_analyst: News status: missing, relevance=0.00
  - sentiment_analyst: Business/sentiment status: missing, relevance=0.00
  - technical_analyst: Signals: strong_momentum, outperforming_market
  - bull_case: Bull points: 1
  - bear_case: Bear points: 0
  - risk_manager: Risk: WATCH, Quality: WEAK, Rec: PROCEED_WITH_MONITORING

## Supply Chain Map (Serenity Skill)
- SJM: no_supply_chain_data | themes=[]
- KIM: no_supply_chain_data | themes=[]
- CAH: no_supply_chain_data | themes=[]

## Replay Hypothesis (QuantDinger)
- SJM: Entry=no_entry, SL=0.0%, TP=0.0%, Period=N/A, Conf=20%
- KIM: Entry=no_entry, SL=0.0%, TP=0.0%, Period=N/A, Conf=20%
- CAH: Entry=no_entry, SL=0.0%, TP=0.0%, Period=N/A, Conf=20%

## Forward Tracking
|symbol|rank|horizon|due_date|status|
|---|---|---|---|---|
|SJM|1|1d|2026-06-12|pending|
|SJM|1|3d|2026-06-16|pending|
|SJM|1|5d|2026-06-18|pending|
|SJM|1|10d|2026-06-25|pending|
|KIM|2|1d|2026-06-12|pending|
|KIM|2|3d|2026-06-16|pending|
|KIM|2|5d|2026-06-18|pending|
|KIM|2|10d|2026-06-25|pending|
|CAH|3|1d|2026-06-12|pending|
|CAH|3|3d|2026-06-16|pending|
|CAH|3|5d|2026-06-18|pending|
|CAH|3|10d|2026-06-25|pending|

## Market Snapshot Top 10
- momentum_exhaustion_guard_threshold: -0.15
- momentum_exhaustion_guard_adjustment: -0.08
|rank|symbol|raw_market_score|market_score|rule|prior_20d|accel_5d|volume_confirm|rs_vs_equal_weight|
|---|---|---|---|---|---|---|---|---|
|1|SJM|0.8623217922606925|0.8623217922606925||0.16356173749186498|-0.015618712589422268|0.6181130721070909|0.1379237114912511|
|2|KIM|0.8085539714867618|0.8085539714867618||0.1329356068390979|-0.043882984897280375|0.7852875951948792|0.10729758083848402|
|3|CAH|0.7947046843177189|0.7947046843177189||0.189965080424092|-0.09077803788426242|0.14162563630544|0.1643270544234781|
|4|COO|0.7926680244399186|0.7926680244399186||0.11879943326698195|-0.04600028507251408|0.7501816816092999|0.09316140726636808|
|5|BXP|0.7873727087576375|0.7873727087576375||0.13878416979060315|-0.0669872629230106|0.2622283934630001|0.11314614378998929|
|6|CPB|0.7841140529531568|0.7841140529531568||0.12457001473672835|-0.06262101060287084|0.47906116464808113|0.09893198873611449|
|7|LRCX|0.7739307535641549|0.7739307535641549||0.163823427756989|-0.14173730488638636|0.28523244843433426|0.13818540175637511|
|8|ASML|0.7718940936863544|0.7718940936863544||0.13968313337531546|-0.11406105729576832|0.482266670246545|0.1140451073747016|
|9|BAX|0.7682281059063136|0.7682281059063136||0.17045201859038395|-0.12394041131454392|0.08620031427301345|0.14481399258977007|
|10|LLY|0.7572301425661914|0.7572301425661914||0.13464001364195965|-0.1121920595267798|0.1605077957289378|0.10900198764134579|

## Final Classification
- MARKET_WATCHLIST_NEEDS_EVIDENCE
