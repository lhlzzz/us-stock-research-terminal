# Attribution

Status: **VALIDATION_GAP**

Performance split (not only ticket PnL):

- company_contribution
- industry_contribution
- capital_contribution
- market_contribution
- catalyst_contribution

Alpha split:

- alpha_from_company
- alpha_from_industry
- alpha_from_capital
- alpha_from_market
- alpha_from_event

Purpose: know which Brain actually created value. Schema exists in `scripts/research/thesis.py` → `attribution`. Independent future outcomes remain T+1/3/5/10 from `independent_price_outcomes`.

Cannot compute live attribution until VALID lineage samples ≥ 30 with complete horizons. Current VALID capital dataset = 5; research samples VALID = 0.
