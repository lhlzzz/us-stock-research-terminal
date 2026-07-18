# xiaomei-us-stock-research

## Purpose
美股 research-only skill，用于提升 daily profitability research quality、profit-ticket discovery 和 paper-review tracking。

## Non-goals
- 不下单
- 不接 broker
- 不接 uSMART / 盈立证券 API
- 不接交易所 API / wallet
- 不写 ledger
- 不新增 paper/live execution
- 不输出 BUY/SELL/ORDER
- 不处理 A股
- 不替代 EastMoney market provider / last30days；不回退 legacy market-data source

## Canonical entry

- Scripts:
  - `workspaces/xiaomei/scripts/historical_replay_baseline.py`
  - `workspaces/xiaomei/scripts/us_profit_ticket_pipeline.py`
- Canonical probe command:
  - `/root/hermes/company-ai-system/tools/external/bin/quant-python workspaces/xiaomei/scripts/us_profit_ticket_pipeline.py --help`

## Data Sources
- Market data: EastMoney US realtime/delayed quote + kline provider
- Social/public research: last30days
- Crypto: risk appetite proxy only
- External frameworks: methodology reference only

## Methodology Inputs
- TradingAgents: multi-role research panel
- Serenity: theme/supply-chain/catalyst mapping
- Buffett Skills: quality/safety-margin/bear-case check
- UZI-Skill: risk/trap checklist and multi-dimensional review
- QuantDinger: replay/data-health/liquidity-guard methodology

## Research Flow
1. Clarify ticker/theme/date
2. Pull market context from EastMoney US provider
3. Pull social/public context from last30days if available
4. Build catalyst map
5. Build supply-chain/theme map (Serenity Skill)
6. Run research panel (TradingAgents):
   - fundamental analyst (EastMoney detail fields + explicit provider data gaps)
   - news analyst (last30days narrative)
   - sentiment analyst (last30days business)
   - technical analyst (momentum/RS/volume)
   - bull case
   - bear case
   - risk manager
7. Buffett-style quality check (EastMoney available fields; unavailable financial statement fields remain explicit data gaps)
8. UZI-style trap/risk checklist (short interest, dilution, debt, price patterns, news flags)
9. QuantDinger-style replay hypothesis (entry/exit/SL/TP/holding period)
10. Build forward tracking sheet (1d / 3d / 5d / 10d)
11. Final research-only classification

## Profit-Ticket Pipeline
1. Build current-listed Nasdaq100/S&P500 union snapshot.
2. Score market evidence using IC-optimized formula:
   - `score = 0.40×relative_strength + 0.30×volume_weighted_momentum - 0.15×five_day_acceleration + 0.15×prior_20d_momentum`
   - Relative strength (IC=+0.043): individual 20d return minus equal-weight benchmark
   - Volume-weighted momentum (IC=+0.028): 20d momentum × volume trend
   - Five-day acceleration (IC=-0.025, reversed): 5d momentum minus 20d momentum
   - Prior 20d momentum (IC=+0.024): past 20-day return
3. Pull separate narrative and business queries from last30days.
4. Run company-aware relevance matching against title/snippet content.
5. Relevance statuses must be one of `found_relevant`, `found_unrelated`, or `missing`.
6. Only relevant evidence can add bonus / qualify a candidate for `CANDIDATE_FOR_PAPER_REVIEW`.
7. Market-leg pass but no relevant evidence should stay in `MARKET_WATCHLIST_NEEDS_EVIDENCE`; it is research-only and not a paper-review ticket or trade signal.
8. Emit top 5 paper-review candidates, a market watchlist for research validation, a forward tracking sheet, and explicit rejection reasons for unrelated/missing evidence.

### Backtest Validation (300-day)
- Win rate: 56.9%
- Avg return: +1.75%
- Profit factor: 1.92
- 1d/3d/5d: +0.61% / +1.53% / +3.14%

## Output Classes
- RESEARCH_ONLY
- NEED_MORE_EVIDENCE
- MARKET_WATCHLIST_NEEDS_EVIDENCE
- NEED_REPLAY
- BLOCKED_BY_RISK
- CANDIDATE_FOR_PAPER_REVIEW

## Required Output Template
- ticker/theme
- date/as-of
- market context
- social evidence
- catalyst map
- supply-chain/theme map
- top 5 candidate tickets
- bull case
- bear case
- quality check
- risk/trap checklist
- replay hypothesis
- forward tracking dates
- data gaps
- final classification
