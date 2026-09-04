# REPLAY_AUDIT — Xiaomei 2.2

Replay is **LIVE**. Replay uses published/effective/available ≤ as_of.
`retrieved_at > as_of` is allowed and is not a leak. Replay cannot
write production ranking, Alpha, BUY/SELL, broker, or live orders.

## Temporal fixtures

- 10-Q filed 2026-08-10 is invisible at as_of 2026-08-05 and visible at 2026-08-11.
- 10-Q + 10-Q/A for the same period: as_of after amendment selects the
  amendment and records `supersedes`; original is retained.
- XBRL concept/period conflicts keep all evidence; selected fact is latest
  valid filing as_of. Silent overwrite is false.

## Estimate revision history

History:

- 2026-07-01 = 4.20
- 2026-07-10 = 4.35
- 2026-07-25 = 4.50

as_of 2026-07-15 sees 4.20 and 4.35 only. 30/60/90D windows are DERIVED
and point back to raw observations.

## Universe survivorship

`Universe(as_of)` uses membership `effective_from`/`effective_to`.
A name removed after 2024 remains in 2024 replay. Current S&P/Nasdaq
membership is **not** written into historical snapshots. Live historical
universe source = **DATA_GAP**.

## Snapshot hash

`ResearchSnapshot` includes as_of, universe, market, fundamentals,
earnings, revisions, industry, risk, evidence, research_version,
code_commit, and `content_hash`. Same payload → same hash. Mutation
changes the hash. Research run identity is
`symbol|as_of|research_version|snapshot_hash` and is reused, not
duplicated.

Real hashes as_of 2026-09-03:

- NVDA `c61ad477f8cfafdd52ad84d000a098277e4857541bcafc6d629f2dfe8e101209`
- AAPL `fc00d195a9a5c2e5299afd8882bdd248529945a6cf2c91c1bc272fa95b4a5e53`
- MSFT `65acf16f41c95a39f123b0f87140fb8489daed6cec44ef8ea43c484b2d955399`

## Outcomes

T+1 / T+3 / T+5 / T+10 are independent records. A single total outcome
is forbidden. Research-only runs without OHLCV mark horizons incomplete
instead of inventing returns.

## Determinism

`scripts/xiaomei_22_audit.py` snapshot hash equality = PASS.
Unit tests cover as-of filters, amendments, conflicts, revision windows,
and run idempotency.
