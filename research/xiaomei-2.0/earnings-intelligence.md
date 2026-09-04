# Earnings Intelligence

Status: **DATA_GAP**

Layer: `scripts/research/fundamentals.py` → `earnings_intelligence` + `estimate_revision_direction`.

Fields: earnings_calendar, earnings_history, earnings_surprise, revenue_surprise, guidance_change, estimate_revision, margin_change, call_transcript_context.

Independent evidence: `estimate_revision_direction` from EPS estimate history (UP / DOWN / FLAT / UNKNOWN). Consecutive ↑ or ↓ is DERIVED, not inferred from price.

Forbidden mapping: price_up ≠ fundamental_improvement. A rising price with DOWN revisions stays not-fundamental-improvement.

Earnings regimes (`scripts/research/regime.py`): PRE_EARNINGS, EARNINGS_DAY, POST_EARNINGS, POST_GUIDANCE. Setup is EVENT_SETUP vs NORMAL_SETUP. Checks: gap risk, volatility expansion, volume expansion, drift, reversal, estimate revision.

Live earnings calendar / surprise / transcript rows: **0**.
