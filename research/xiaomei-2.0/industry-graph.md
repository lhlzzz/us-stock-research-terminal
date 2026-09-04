# Industry Graph

Status: **PARTIAL** (persistence contract READY; populated graph DATA_GAP)

Owner: `scripts/research/industry.py`. Serenity still produces industry context; this layer persists it.

Entities: industry, system, platform, equipment, module, component, material, software, service, infrastructure, company.

Relations: supplies, depends_on, competes_with, enables, replaces, bottlenecks, certified_by, capacity_constrained.

Memory rule: existing graph + new evidence = updated Industry View. `update_industry_memory` never re-zeros.

Obsidian remains the narrative memory; PostgreSQL/research graph is the structured copy. Next Serenity run on the same industry must load the previous graph first.

Live persisted industry entities: **0** until a Serenity run supplies evidenced layers.
