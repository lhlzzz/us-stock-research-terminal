# XIAOMEI US Profit Ticket Pipeline V0

RESEARCH_ONLY
NOT_TRADING_ADVICE
NO_BROKER
NO_ORDER
NO_LEDGER
NO_LIVE_TRADE

- output_date: 2026-06-11-open
- as_of_date: 2026-06-11
- universe_source: nasdaq100_sp500_union
- source_mode: live
- universe_key: union
- universe_total_symbols: 516
- universe_included_symbols: 514
- period_used: 1y
- classification: MARKET_WATCHLIST_NEEDS_EVIDENCE
- candidate_pool_size: 3
- top_k: 3
- paper_review_count: 0
- market_watchlist_count: 3
- zero_paper_review_is_valid_output: True
- artifact_summary: /root/hermes/company-ai-system/workspaces/xiaomei/research/profit-ticket-pipeline-opening/summary-2026-06-11-open.md
- artifact_metrics: /root/hermes/company-ai-system/workspaces/xiaomei/research/profit-ticket-pipeline-opening/metrics-2026-06-11-open.json
- artifact_candidates: /root/hermes/company-ai-system/workspaces/xiaomei/research/profit-ticket-pipeline-opening/candidates-2026-06-11-open.csv
- artifact_forward_tracking: /root/hermes/company-ai-system/workspaces/xiaomei/research/profit-ticket-pipeline-opening/forward-tracking-2026-06-11-open.csv

## Methodology References
- UZI-Skill: risk checklist and multi-dimensional review
- TradingAgents: role-based research synthesis
- Serenity Skill: theme and supply-chain catalyst mapping
- Buffett Skills: quality, margin-of-safety, bear-case framing
- QuantDinger: replay discipline and data-health guardrails

## Price-Volume Summary
- equal_weight_20d_benchmark: 0.02631432597779658
- median_20d_momentum: 0.021387767812082403
- median_5d_acceleration: -0.01850712429085566
- median_volume_confirmation: -0.15332050309929046
- median_relative_strength: -0.004926558165714176
- top_market_score_p90: 0.688327485380117

## Paper Review Candidates
- none

## Market Watchlist Needs Evidence
|rank|symbol|company|raw_market_score|market_score|rule|ticket_score|narrative|business|gate_status|
|---|---|---|---|---|---|---|---|---|---|
|1|SJM|The J.M. Smucker Company|0.8658869395711501|0.8658869395711501||0.8658869395711501|missing|missing|MARKET_WATCHLIST_NEEDS_EVIDENCE|
|2|COO|The Cooper Companies, Inc.|0.8070175438596492|0.8070175438596492||0.8070175438596492|found_unrelated|found_unrelated|MARKET_WATCHLIST_NEEDS_EVIDENCE|
|3|KIM|Kimco Realty Corporation (HC)|0.8023391812865497|0.8023391812865497||0.8023391812865497|missing|found_unrelated|MARKET_WATCHLIST_NEEDS_EVIDENCE|

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
- narrative ranked candidates: 6 | status: found_unrelated | returncode: 0
- business ranked candidates: 12 | status: found_unrelated | returncode: 0
- evidence gap reason: found_unrelated_public_items;relevant_narrative_missing;relevant_business_missing
### 3. KIM
- company: Kimco Realty Corporation (HC) (yfinance)
- narrative query: KIM kimco realty corporation hc stock catalyst earnings news
- business query: KIM kimco realty corporation hc orders demand backlog guidance revenue customer contract
- narrative ranked candidates: 0 | status: missing | returncode: 124
- business ranked candidates: 7 | status: found_unrelated | returncode: 0
- evidence gap reason: found_unrelated_public_items;relevant_narrative_missing;relevant_business_missing

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

## Market Snapshot Top 10
- momentum_exhaustion_guard_threshold: -0.15
- momentum_exhaustion_guard_adjustment: -0.08
|rank|symbol|raw_market_score|market_score|rule|prior_20d|accel_5d|volume_confirm|rs_vs_equal_weight|
|---|---|---|---|---|---|---|---|---|
|1|SJM|0.8658869395711501|0.8658869395711501||0.1668605829418428|-0.01566299362522816|0.6087862375108806|0.1405462569640462|
|2|COO|0.8070175438596492|0.8070175438596492||0.12998142876862828|-0.04646004127676351|0.7431908188684881|0.1036671027908317|
|3|KIM|0.8023391812865497|0.8023391812865497||0.1270223430623687|-0.04365394128399691|0.6840924325276796|0.10070801708457212|
|4|BXP|0.7875243664717348|0.7875243664717348||0.13767124495646743|-0.06692179679654409|0.24015186900781926|0.11135691897867085|
|5|CAH|0.7867446393762183|0.7867446393762183||0.17043252094511296|-0.08928797111379239|0.10974304844756633|0.14411819496731637|
|6|CPB|0.7812865497076024|0.7812865497076024||0.120393061899976|-0.062388419475195134|0.45908126360931045|0.09407873592217943|
|7|ASML|0.7723196881091616|0.7723196881091616||0.14447578140153094|-0.11454071210955652|0.44600967581485307|0.11816145542373437|
|8|LRCX|0.7695906432748538|0.7695906432748538||0.16111564348147467|-0.14140753489183933|0.2567918866576202|0.13480131750367808|
|9|BAX|0.7590643274853801|0.7590643274853801||0.1600479830081678|-0.12283871690169312|0.07011439696326516|0.1337336570303712|
|10|LLY|0.7536062378167642|0.7536062378167642||0.1281014556339264|-0.11154553350933205|0.14642507950241557|0.10178712965612981|

## Final Classification
- MARKET_WATCHLIST_NEEDS_EVIDENCE
