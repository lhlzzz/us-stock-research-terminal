# Failure Library

Status: **DATA_GAP**

Schema: failure_case, failure_reason, brain_at_entry, what_changed, early_warning, missed_signal.

Classes: FALSE_BREAKOUT, CATALYST_FAILURE, DISTRIBUTION, EARNINGS_MISS, GUIDANCE_CUT, LIQUIDITY_TRAP, SHORT_PRESSURE, VALUATION_TRAP, THESIS_BREAK, REGIME_MISMATCH.

Query: `research similar failures <class>` answers “有没有以前犯过类似错误？”

Similarity dimensions (not text-only embedding): company, industry, setup, capital, thesis, failure. `pick_case_embeddings` remains the text index; research similarity is a structured overlay.

Live classified failure cases: **0**. Negative T+5 analogues from Capital retrieval can be listed but are not auto-classified into the library.
