# Chokepoint Database

Status: **DATA_GAP**

Schema: `chokepoint_record`.

Fields: industry, layer, company, product, dependency, substitutability, switching_cost, qualification_time, capacity, market_share, customer_dependency, evidence, confidence.

Statuses: EMERGING, CONFIRMED, STRESSED, RELAXING, BROKEN.

Query: `research chokepoint <name>` via `scripts/research/query.py` and GET `/research/chokepoint/{name}`.

Live confirmed chokepoints: **0**. Serenity bottleneck claims remain INFERRED until LEVEL_1/2 evidence is attached.
