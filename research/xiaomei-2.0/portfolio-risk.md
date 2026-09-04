# Portfolio Risk

Status: **PARTIAL**

Layers:

- existing Obsidian `portfolio_context` (market_alpha_adjustment always 0)
- `supply_chain_portfolio` relations: same_value_chain, same_theme, supplier_relationship, customer_relationship, substitute_relationship
- `portfolio_risk_graph`: Portfolio → Company → Industry → Theme → Supply Chain → Common Risk

Questions answered without touching alpha_score:

- where is current exposure?
- which layer is missing?
- is there a better chokepoint?
- are several names the same risk (example: AI capex)?

Obsidian knowledge_assets: **207**. Holdings such as NVDA/AMD/TSM/AVGO/ANET/MRVL can be mapped only when notes and graph edges exist. Missing graph edges stay DATA_GAP, not inferred from ticker co-occurrence.

portfolio_context never enters alpha_score.
