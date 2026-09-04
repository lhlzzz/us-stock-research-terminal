# SEC Coverage

Status: **DATA_GAP**

Layer: `scripts/research/fundamentals.py` → `sec_filing`.

Supported types: 10-K, 10-Q, 8-K, DEF 14A, 13D, 13G, Form 3, Form 4, Form 5.

Recorded metadata: source_url, filing_type, filing_date, period_end, effective_date, retrieved_at, company, ticker.

Evidence level: LEVEL_1 when a complete filing record is present; otherwise DATA_GAP / LEVEL_6 inference is forbidden as a substitute fact.

Live ingested SEC rows: **0**. Xiaomei currently has no EDGAR harvest. Schema and lineage rule (`effective_date <= as_of_date` else BLOCK) are in place; replay will refuse future filings.

This is the largest company-data hole. Buffett skill exists; statement completeness does not.
