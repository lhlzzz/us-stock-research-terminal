# Universe Expansion

Status: **PARTIAL**

CORE_UNIVERSE remains production default: nasdaq100_sp500_union (`choose_universe` in `us_profit_ticket_pipeline.py`). This task does not replace it.

Research-only universes in `research_universes()`:

| Universe | When used | Sources |
| --- | --- | --- |
| CORE_UNIVERSE | default research | Nasdaq100 + S&P500 |
| INDUSTRY_DISCOVERY_UNIVERSE | industry-level change | Russell 2000, industry sets, ETF constituents, Serenity |
| CHOKEPOINT_UNIVERSE | Serenity finds a key node | suppliers, customers, chokepoint companies |

Live `universe` table count: **3095** (Russell 3000 cache). That is a listing universe, not automatic CORE expansion and not a second ranking pool.

does_not_replace_production_universe: true.
