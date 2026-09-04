# Fundamentals Coverage

Status: **DATA_GAP**

Abstraction: `scripts/research/fundamentals.py` → `company_fundamentals`.

Required fields (28): revenue, revenue_growth, gross_profit, gross_margin, operating_income, operating_margin, net_income, free_cash_flow, operating_cash_flow, capex, roic, roe, roa, cash, debt, net_debt, interest_expense, interest_coverage, share_count, diluted_share_count, stock_based_compensation, share_dilution, buyback_amount, dividend, segment_revenue, segment_margin, geographic_revenue, customer_concentration, backlog, bookings, remaining_performance_obligation, guidance.

Live quote provider (`realtime_quotes`) currently exposes: pe_ttm, roe, dividend_yield plus price/volume. Missing almost all statement fields.

| Source | Coverage |
| --- | --- |
| realtime_quotes | pe_ttm, roe, dividend_yield |
| SEC filing layer | schema only, no ingested 10-K/10-Q rows |
| Buffett context | DERIVED quality from observed roe/pe/dividend; moat/management/allocation stay UNKNOWN |

SBC / dilution: `sbc_dilution()` computes net shareholder capital return = gross buyback − SBC − issuance. BUYBACK_QUALITY_WARNING fires when a buyback is announced and share count does not decline.

Management: `management_allocation()` separates management_says vs management_delivered; guidance_hit_rate / guidance_revision_rate / capital_allocation_consistency are UNKNOWN until filing history exists.

Do not invent statement numbers. Missing fields stay UNKNOWN.
