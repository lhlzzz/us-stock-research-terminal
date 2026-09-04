# Research Engine Inventory — Xiaomei 2.1.1

Canonical owner: `scripts/research/`.

Production ranking owner remains `observable_footprint_v1` with sort
`(ticket_score, market_score, volume_confirmation_ratio)`. Research engines
do not produce picks, orders, or weight changes.

| Module | Owner | Callers | Production pipeline | Compatibility only | May delete |
| --- | --- | --- | --- | --- | --- |
| `scripts/research/` | Research OS | `research_panel.py` adapter, tests, company reports | No. Research / shadow / replay / learning only | No | No |
| `scripts/research/decision.py` | Research OS conclusion | `build_company_research` | No | No | No |
| `scripts/research/brains.py` | Buffett / Serenity / UZI / TradingAgents adapters | Research OS, compatibility adapter | No | No | No |
| `scripts/research/contracts.py` | Four-brain scores + coverage | Research OS | No | No | No |
| `scripts/research/evidence.py` | Claim / provenance | Research OS | No | No | No |
| `scripts/research/fundamentals.py` | Company / SEC / earnings layers | Research OS, tests | No. SEC/earnings stay DATA_GAP | No | No |
| `scripts/research/industry.py` | Industry graph + UniverseSnapshot | Research OS, tests | No. Graph ingest DATA_GAP | No | No |
| `scripts/research/market_context.py` | Market setup context | Research OS | No | No | No |
| `scripts/research/thesis.py` | Structured thesis | Research OS | No | No | No |
| `scripts/research/learning.py` | Research samples / census | Research OS | No | No | No |
| `scripts/research/outcomes.py` | Independent T+1/3/5/10 | Research OS, tests | No | No | No |
| `scripts/research/memory.py` | Obsidian / portfolio context | Research OS, tests | No. Alpha adjustment is 0 | No | No |
| `scripts/research/regime.py` | Research regime labels | Research OS | No | No | No |
| `scripts/research/validate.py` | Research validation gates | Research OS | No | No | No |
| `scripts/research/metric_semantics.py` | ResearchMetricRegistry | Adapter + brains | No | No | No |
| `scripts/research/temporal.py` | published/effective/retrieved/as_of | Research OS, pipeline quote check | No | No | No |
| `scripts/research/providers.py` | Provider contract / DATA_GAP | Fundamentals | No | No | No |
| `scripts/research_panel.py` | Compatibility adapter | `us_profit_ticket_pipeline.build_candidate_record`, tests | Yes, as legacy dict shape only | Yes | No — pipeline still needs `quality_check` / `risk_checklist` / `research_panel` / `replay_hypothesis` keys |
| `build_quality_check` | Adapter → `REGISTRY` + Buffett context | Adapter, tests | Display / research metadata | Yes | No |
| `build_risk_checklist` | Adapter → UNKNOWN / NEED_MORE_EVIDENCE | Adapter, tests | Display / research metadata | Yes | No |
| `build_supply_chain_map` | Adapter → Serenity context | Adapter | Display | Yes | No |
| `run_research_panel` | Adapter → DETERMINISTIC_PANEL_RULE | Adapter | Display | Yes | No |
| `_build_fundamental_analyst` / `_build_bull_case` / `_build_bear_case` | Removed from engine | None | No | n/a | Already gone; names live only as adapter fields |
| `build_replay_hypothesis` | Adapter → UNCALIBRATED_HYPOTHESIS | Adapter, tests | Display | Yes | No |
| TradingAgents | Methodology reference + `build_tradingagents_adapter` | Skill text, methodology_references | No | Yes | Do not vendor or execute |
| UZI | Methodology reference + `build_uzi_adapter` | Adapter risk | No | Yes | Do not vendor |
| QuantDinger | Methodology reference for replay discipline | Skill text, methodology_references | No | Yes | Do not vendor |
| Serenity | `build_serenity_context` | Research OS | No | No | No |
| Buffett | `build_buffett_context` | Research OS | No | No | No |
| `observable_footprint_v1` | Production ranking | `us_profit_ticket_pipeline` | Yes | No | No |

## Dual-engine status

Legacy `research_panel.py` no longer scores ROE/PE/liquidity with raw unit
ratios and no longer maps missing risk to GREEN. It calls Research OS and
returns the historical dict so existing artifacts and tests keep working.

`us_profit_ticket_pipeline.py` still imports `run_full_research_panel` on
purpose. That import is the adapter, not a second engine.

## Not research engines

| Module | Role |
| --- | --- |
| `scripts/market_calendar.py` | USMarketCalendar owner |
| `scripts/data_provider.py` | Canonical market-data transport |
| `scripts/us_profit_ticket_pipeline.py` | Production ranking + paper-review gate |
| `scripts/capital/` | Capital Behavior V2/V3 research parallel; formulas unchanged |
