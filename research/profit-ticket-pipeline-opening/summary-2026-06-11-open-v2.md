# XIAOMEI US Profit Ticket Pipeline V0

RESEARCH_ONLY
NOT_TRADING_ADVICE
NO_BROKER
NO_ORDER
NO_LEDGER
NO_LIVE_TRADE

- output_date: 2026-06-11-open-v2
- as_of_date: 2026-06-11
- universe_source: nasdaq100_sp500_union
- source_mode: live
- universe_key: union
- universe_total_symbols: 516
- universe_included_symbols: 500
- period_used: 1y
- classification: MARKET_WATCHLIST_NEEDS_EVIDENCE
- candidate_pool_size: 5
- top_k: 5
- paper_review_count: 0
- market_watchlist_count: 5
- zero_paper_review_is_valid_output: True
- artifact_summary: /root/hermes/company-ai-system/workspaces/xiaomei/research/profit-ticket-pipeline-opening/summary-2026-06-11-open-v2.md
- artifact_metrics: /root/hermes/company-ai-system/workspaces/xiaomei/research/profit-ticket-pipeline-opening/metrics-2026-06-11-open-v2.json
- artifact_candidates: /root/hermes/company-ai-system/workspaces/xiaomei/research/profit-ticket-pipeline-opening/candidates-2026-06-11-open-v2.csv
- artifact_forward_tracking: /root/hermes/company-ai-system/workspaces/xiaomei/research/profit-ticket-pipeline-opening/forward-tracking-2026-06-11-open-v2.csv

## Methodology References
- UZI-Skill: risk checklist and multi-dimensional review
- TradingAgents: role-based research synthesis
- Serenity Skill: theme and supply-chain catalyst mapping
- Buffett Skills: quality, margin-of-safety, bear-case framing
- QuantDinger: replay discipline and data-health guardrails

## Price-Volume Summary
- equal_weight_20d_benchmark: 0.02586825733486444
- median_20d_momentum: 0.021701089569438725
- median_5d_acceleration: -0.01831174863994911
- median_volume_confirmation: -0.1350478725891534
- median_relative_strength: -0.004167167765425715
- top_market_score_p90: 0.6924248496993988

## Paper Review Candidates
- none

## Market Watchlist Needs Evidence
|rank|symbol|company|raw_market_score|market_score|rule|ticket_score|narrative|business|gate_status|
|---|---|---|---|---|---|---|---|---|---|
|1|SJM|The J.M. Smucker Company|0.8625250501002004|0.8625250501002004||0.8625250501002004|missing|missing|MARKET_WATCHLIST_NEEDS_EVIDENCE|
|2|COO|The Cooper Companies, Inc.|0.7915831663326653|0.7915831663326653||0.8115831663326654|missing|missing|MARKET_WATCHLIST_NEEDS_EVIDENCE|
|3|KIM|Kimco Realty Corporation (HC)|0.8040080160320642|0.8040080160320642||0.8040080160320642|missing|missing|MARKET_WATCHLIST_NEEDS_EVIDENCE|
|4|CAH|Cardinal Health, Inc.|0.790380761523046|0.790380761523046||0.790380761523046|missing|missing|MARKET_WATCHLIST_NEEDS_EVIDENCE|
|5|CPB|CPB|0.7887775551102204|0.7887775551102204||0.7887775551102204|missing|missing|MARKET_WATCHLIST_NEEDS_EVIDENCE|

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
### 2. COO
- company: The Cooper Companies, Inc. (yfinance)
- narrative query: COO cooper companies stock catalyst earnings news
- business query: COO cooper companies orders demand backlog guidance revenue customer contract
- narrative ranked candidates: 0 | status: missing | returncode: 124
- business ranked candidates: 0 | status: missing | returncode: 124
- evidence gap reason: last30days_returned_zero_ranked_candidates
### 3. KIM
- company: Kimco Realty Corporation (HC) (yfinance)
- narrative query: KIM kimco realty corporation hc stock catalyst earnings news
- business query: KIM kimco realty corporation hc orders demand backlog guidance revenue customer contract
- narrative ranked candidates: 0 | status: missing | returncode: 124
- business ranked candidates: 0 | status: missing | returncode: 124
- evidence gap reason: last30days_returned_zero_ranked_candidates
### 4. CAH
- company: Cardinal Health, Inc. (yfinance)
- narrative query: CAH cardinal health stock catalyst earnings news
- business query: CAH cardinal health orders demand backlog guidance revenue customer contract
- narrative ranked candidates: 0 | status: missing | returncode: 124
- business ranked candidates: 0 | status: missing | returncode: 124
- evidence gap reason: last30days_returned_zero_ranked_candidates
### 5. CPB
- company: CPB (symbol)
- narrative query: CPB cpb stock catalyst earnings news
- business query: CPB cpb orders demand backlog guidance revenue customer contract
- narrative ranked candidates: 0 | status: missing | returncode: 124
- business ranked candidates: 0 | status: missing | returncode: 124
- evidence gap reason: last30days_returned_zero_ranked_candidates

## Quality Check (Buffett Skills)
### SJM: UNAVAILABLE (score=0.00)
### COO: MODERATE (score=0.67)
  - roe: 0.10
  - profit_margin: 0.22
  - gross_margin: 1.00
  - debt_to_equity: 0.83
  - free_cash_flow: 1.00
  - payout_ratio: 1.00
  - current_ratio: 0.51
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
### CPB: WEAK (score=0.42)
  - roe: 0.51
  - profit_margin: 0.24
  - gross_margin: 0.49
  - debt_to_equity: 0.09
  - free_cash_flow: 1.00
  - payout_ratio: 0.24
  - current_ratio: 0.35

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
### COO: CLEAN (red=0, yellow=0)
  - short_interest: [GREEN] short_interest=3.0%
  - dilution_risk: [GREEN] shares_outstanding=195,030,630
  - debt_covenant: [GREEN] debt_to_equity=0.33
  - price_manipulation: [GREEN] 5d_accel=-0.0458
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
  - price_manipulation: [GREEN] 5d_accel=-0.0438
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
  - price_manipulation: [YELLOW] 5d_accel=-0.0906
  - news_red_flags: [GREEN] narrative_status=missing
  - supply_chain_risk: [GREEN] business_status=missing
  - regulatory_risk: [GREEN] not_assessed_automatically
  - concentration_risk: [GREEN] not_assessed_automatically
  - earnings_quality: [GREEN] yfinance_limited
  - insider_selling: [GREEN] not_assessed_automatically
### CPB: ELEVATED (red=1, yellow=1)
  - short_interest: [RED] short_interest=31.6%
  - dilution_risk: [GREEN] shares_outstanding=298,206,243
  - debt_covenant: [YELLOW] debt_to_equity=1.82
  - price_manipulation: [GREEN] 5d_accel=-0.0632
  - news_red_flags: [GREEN] narrative_status=missing
  - supply_chain_risk: [GREEN] business_status=missing
  - regulatory_risk: [GREEN] not_assessed_automatically
  - concentration_risk: [GREEN] not_assessed_automatically
  - earnings_quality: [GREEN] yfinance_limited
  - insider_selling: [GREEN] not_assessed_automatically

## Research Panel (TradingAgents)
### SJM: MIXED (pos=0, neg=1)
  - fundamental_analyst: Quality verdict: UNAVAILABLE (score=0.00)
  - news_analyst: News status: missing, relevance=0.00
  - sentiment_analyst: Business/sentiment status: missing, relevance=0.00
  - technical_analyst: Signals: strong_momentum, outperforming_market, volume_confirmed
  - bull_case: Bull points: 2
  - bear_case: Bear points: 1
  - risk_manager: Risk: WATCH, Quality: UNAVAILABLE, Rec: PROCEED_WITH_MONITORING
### COO: MIXED (pos=1, neg=0)
  - fundamental_analyst: Quality verdict: MODERATE (score=0.67)
  - news_analyst: News status: missing, relevance=0.00
  - sentiment_analyst: Business/sentiment status: missing, relevance=0.00
  - technical_analyst: Signals: strong_momentum, outperforming_market, volume_confirmed
  - bull_case: Bull points: 3
  - bear_case: Bear points: 0
  - risk_manager: Risk: CLEAN, Quality: MODERATE, Rec: PROCEED
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
### CPB: MIXED (pos=0, neg=1)
  - fundamental_analyst: Quality verdict: WEAK (score=0.42)
  - news_analyst: News status: missing, relevance=0.00
  - sentiment_analyst: Business/sentiment status: missing, relevance=0.00
  - technical_analyst: Signals: strong_momentum, outperforming_market, volume_confirmed
  - bull_case: Bull points: 2
  - bear_case: Bear points: 1
  - risk_manager: Risk: ELEVATED, Quality: WEAK, Rec: PROCEED_WITH_CAUTION

## Supply Chain Map (Serenity Skill)
- SJM: no_supply_chain_data | themes=[]
- COO: no_supply_chain_data | themes=[]
- KIM: no_supply_chain_data | themes=[]
- CAH: no_supply_chain_data | themes=[]
- CPB: no_supply_chain_data | themes=[]

## Replay Hypothesis (QuantDinger)
- SJM: Entry=no_entry, SL=0.0%, TP=0.0%, Period=N/A, Conf=20%
- COO: Entry=no_entry, SL=0.0%, TP=0.0%, Period=N/A, Conf=20%
- KIM: Entry=no_entry, SL=0.0%, TP=0.0%, Period=N/A, Conf=20%
- CAH: Entry=no_entry, SL=0.0%, TP=0.0%, Period=N/A, Conf=20%
- CPB: Entry=no_entry, SL=0.0%, TP=0.0%, Period=N/A, Conf=20%

## Forward Tracking
|symbol|rank|horizon|due_date|status|
|---|---|---|---|---|
|SJM|1|1d|2026-06-12|pending|
|SJM|1|3d|2026-06-16|pending|
|SJM|1|5d|2026-06-18|pending|
|SJM|1|10d|2026-06-25|pending|
|COO|2|1d|2026-06-12|pending|
|COO|2|3d|2026-06-16|pending|
|COO|2|5d|2026-06-18|pending|
|COO|2|10d|2026-06-25|pending|
|KIM|3|1d|2026-06-12|pending|
|KIM|3|3d|2026-06-16|pending|
|KIM|3|5d|2026-06-18|pending|
|KIM|3|10d|2026-06-25|pending|
|CAH|4|1d|2026-06-12|pending|
|CAH|4|3d|2026-06-16|pending|
|CAH|4|5d|2026-06-18|pending|
|CAH|4|10d|2026-06-25|pending|
|CPB|5|1d|2026-06-12|pending|
|CPB|5|3d|2026-06-16|pending|
|CPB|5|5d|2026-06-18|pending|
|CPB|5|10d|2026-06-25|pending|

## Market Snapshot Top 10
- momentum_exhaustion_guard_threshold: -0.15
- momentum_exhaustion_guard_adjustment: -0.08
|rank|symbol|raw_market_score|market_score|rule|prior_20d|accel_5d|volume_confirm|rs_vs_equal_weight|
|---|---|---|---|---|---|---|---|---|
|1|SJM|0.8625250501002004|0.8625250501002004||0.16376217967297557|-0.015621403163301295|0.6231132614295283|0.13789392233811112|
|2|KIM|0.8040080160320642|0.8040080160320642||0.13030751745348113|-0.04378118881450077|0.8279975369905339|0.10443926011861668|
|3|COO|0.7915831663326653|0.7915831663326653||0.11484785086362126|-0.04583781277262067|0.754761962090474|0.08897959352875681|
|4|CAH|0.790380761523046|0.790380761523046||0.1870673435394854|-0.0905569802473476|0.1481998471513899|0.16119908620462095|
|5|CPB|0.7887775551102204|0.7887775551102204||0.13538079160309224|-0.06322300226537503|0.49442886611368353|0.1095125342682278|
|6|BXP|0.7787575150300601|0.7787575150300601||0.13287674543624384|-0.06663976758638679|0.273862521223075|0.10700848810137939|
|7|LRCX|0.7779559118236473|0.7779559118236473||0.17644870177372574|-0.14327488547628153|0.29453145014989235|0.1505804444388613|
|8|ASML|0.772745490981964|0.772745490981964||0.1479154200083157|-0.11488495587759684|0.5024197973664537|0.12204716267345125|
|9|INCY|0.7723446893787576|0.7723446893787576||0.08682454824480312|-0.025978995181888287|0.5869887609223574|0.06095629090993868|
|10|BAX|0.7651302605210422|0.7651302605210422||0.16727299546860208|-0.12360378116906667|0.09440689182790751|0.14140473813373763|

## Final Classification
- MARKET_WATCHLIST_NEEDS_EVIDENCE
