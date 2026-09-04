# Historical Capital Bootstrap - 2026-09-03

- Baseline: `41e9430`
- Status: `RESEARCH_ONLY`
- Validation: `UNVALIDATED_NO_FIXED_CHAIN`
- Production: `NO_PRODUCTION_WEIGHT_CHANGE`
- Historical replay is not model validation.

## Database Reality

- tickets = `458`
- forward_tracking = `1161`
- T+1 = `295`
- T+3 = `292`
- T+5 = `276`
- T+10 = `286`
- all = `276`
- T+10 confirmed tickets = `286`
- T+10 date range = `2026-06-25` .. `2026-08-15`

## Join Reality

- unique = `295`
- ambiguous = `79`
- orphan_ticket = `84`
- orphan_tracking = `0`
- unique_research_run_id = `12`

## Replay Reality

- replay candidates = `23`
- replay success = `23`
- replay failed = `0`
- ohlcv replayable = `23`
- ohlcv unavailable = `0`
- ohlcv invalid = `0`
- ohlcv data_gap = `0`

## Dataset Reality

- VALID = `5`
- INSUFFICIENT_FORWARD_DATA = `18`
- MISSING_LINEAGE = `435`
- SOURCE_INVALID = `0`
- VERSION_INVALID = `0`
- DATA_GAP = `0`

## Funnel

- Historical Tickets: `458` (100.0%) drop=None
- Unique Forward Tracking Join: `295` (64.4105%) drop=ambiguous/orphan
- Valid Lineage: `23` (5.0218%) drop=MISSING_LINEAGE
- Historical OHLCV Replayable: `23` (5.0218%) drop=SOURCE_INVALID/OHLCV_UNAVAILABLE/DATA_GAP
- Capital V2 Replay Success: `23` (5.0218%) drop=REPLAY_ERROR
- Complete T+1/T+3/T+5/T+10: `5` (1.0917%) drop=INSUFFICIENT_FORWARD_DATA
- VALID Dataset: `5` (1.0917%) drop=eligibility gates

## Empirical Reality

- status = `NOT_READY`
- sample_count = `5`
- min_samples = `30`

## Lineage Block

- unversioned_tickets = `446`
- unique_join_unversioned = `283`
- complete_four_horizon_tickets = `276`
- recovered_lineage = `11`
- Recovered lineage is audit-only. tickets.research_run_id is never guessed or overwritten.

## Production

- `RESEARCH_ONLY`
- `UNVALIDATED_NO_FIXED_CHAIN`
- `NO_PRODUCTION_WEIGHT_CHANGE`
