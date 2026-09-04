# Brain Contract

Status: **PARTIAL** (schemas READY; live field fill DATA_GAP)

Four independent schemas exist in `scripts/research/contracts.py`. Research quality and short-term alpha are never mixed into one score.

| Schema | Owner | Horizon | Production ranking |
| --- | --- | --- | --- |
| company_quality | Buffett | LONG_TERM | no |
| industry_position | Serenity | MEDIUM_TERM | no |
| capital_behavior | Capital Brain (unchanged formula) | SHORT_TERM | no |
| market_setup | Market | SHORT_TERM | no |
| risk | Risk | EVENT_TERM | no |
| portfolio_context | Obsidian | n/a | never enters alpha_score |
| historical_evidence | tickets / analogues | n/a | no |

Company Quality fields: business_quality, economic_moat, pricing_power, reinvestment_runway, management_quality, capital_allocation, financial_quality, balance_sheet_quality, cashflow_quality, shareholder_dilution, sbc_quality, buyback_quality, valuation_quality. Each emits score / confidence / evidence / data_gaps / as_of_date.

Industry Position fields: industry_attractiveness, industry_growth, supply_chain_position, chokepoint_strength, switching_cost, customer_dependency, supplier_dependency, capacity_constraint, certification_barrier, replacement_difficulty, competitive_intensity.

Capital Behavior keeps existing Capital Brain fields only: capital_behavior_score, capital_state, capital_intent, pressure, absorption, price_control, control_asymmetry, distribution, trap. company_quality / industry_position / statistical_score are stripped and never mixed in.

Market Setup fields: trend, momentum, relative_strength, volume, volatility, breakout, reversal, market_regime, sector_regime.

Independent scores:

- company_quality_score
- industry_position_score
- capital_behavior_score
- market_setup_score
- risk_score
- research_composite ≠ alpha_score
- long_term_quality / industry_edge / capital_edge / short_term_edge retained

Contradiction statuses: CONVERGENCE / DIVERGENCE / UNRESOLVED. Never averaged.

Skill owners: Buffett=Company Research, Serenity=Industry Research, Capital=Market Capital Behavior, Quant=Statistical Validation, Obsidian=Memory, PostgreSQL=Structured Facts. None may create a production pick.

Production boundary unchanged: RESEARCH_ONLY / PAPER_ONLY / NO_BROKER / NO_LIVE_ORDER / KEEP_OBSERVABLE_FOOTPRINT_RANKING_UNCHANGED.
