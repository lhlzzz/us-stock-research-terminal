# LEARNING_AUDIT — Xiaomei 2.2

Failure memory and learning patterns are research diagnosis only.
They do not change production ranking weights.

## Failure taxonomy

TEMPORAL_LEAK, MISSING_EVIDENCE, WRONG_SOURCE, WRONG_UNIT, WRONG_AS_OF,
FALSE_POSITIVE, FALSE_NEGATIVE, THESIS_BREAK, CATALYST_MISREAD,
EARNINGS_MISREAD, REVISION_MISREAD, INDUSTRY_MISREAD,
RISK_UNDERESTIMATED, UNIVERSE_SURVIVORSHIP_ERROR, DATA_PROVIDER_FAILURE.

## Persistent store

SQLite tables `failure_memory` and `research_learning_patterns` are
insert-only. Retrieval is by symbol / type / layer / as_of. Previous
failure warning is a prompt, not a production signal.

## Seeded sample (required)

- FailureMemory id `7656eb6c-1444-455d-82fe-334e50a70b43`
  - symbol NVDA
  - as_of 2026-09-03
  - layer earnings
  - type EARNINGS_MISREAD
  - expected: guidance maintained
  - observed: guidance lowered after earnings beat
  - diagnosis: treated EPS beat as confirmation while guidance was cut
- LearningPattern id `62a04570-6a86-4650-80da-512fa9bb9beb`
  - type `eps_beat_guidance_cut`
  - condition: positive EPS surprise + guidance LOWERED
  - outcome: caution, do not merge into one bullish narrative
  - `does_not_modify_ticket_score` = true

NVDA research run attached this failure warning (`count=1`).

## Thesis / contradiction

Each research sample records thesis, supporting evidence, contradicting
evidence, unknowns, risk, expected behavior. Bull-only narrative is
forbidden. Revenue vs guidance conflicts stay CONTRADICTORY.

## Outcomes binding

Horizons T+1/3/5/10 are stored independently on `research_outcomes`.
Learning may read them later. They do not feed `observable_footprint_v1`.
