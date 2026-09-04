# Historical OHLCV Backfill - 2026-09-03

- daily_klines mutated = `False`
- replayable = `23`
- data_gap = `0`
- unavailable = `0`

## Source Inventory

- daily_klines max_bar_date = `2026-07-31`
- provider_cache max_window_end = `2026-08-28`
- covers 2026-08-15..2026-08-27 via provider_cache = `True`

## OHLCV Funnel

- Valid lineage: `23` (100.0%) drop=MISSING_LINEAGE
- Source available: `23` (100.0%) drop=OHLCV_UNAVAILABLE
- Sufficient history: `23` (100.0%) drop=INSUFFICIENT_HISTORY
- As-of valid: `23` (100.0%) drop=DATA_GAP
- Replayable: `23` (100.0%) drop=SOURCE_INVALID/OHLCV_UNAVAILABLE/DATA_GAP

## Versioned Tickets

- ticket `506` NBIS 2026-08-15 run=143 source=provider_cache last_bar=2026-08-14 status=REPLAYABLE reason=None
- ticket `507` NTAP 2026-08-15 run=143 source=provider_cache last_bar=2026-08-14 status=REPLAYABLE reason=None
- ticket `508` LITE 2026-08-15 run=143 source=provider_cache last_bar=2026-08-14 status=REPLAYABLE reason=None
- ticket `509` ADI 2026-08-18 run=144 source=provider_cache last_bar=2026-08-18 status=REPLAYABLE reason=None
- ticket `510` FOX 2026-08-18 run=144 source=provider_cache last_bar=2026-08-18 status=REPLAYABLE reason=None
- ticket `511` BIIB 2026-08-18 run=144 source=provider_cache last_bar=2026-08-18 status=REPLAYABLE reason=None
- ticket `512` WTW 2026-08-21 run=145 source=provider_cache last_bar=2026-08-21 status=REPLAYABLE reason=None
- ticket `513` SOLV 2026-08-21 run=145 source=provider_cache last_bar=2026-08-21 status=REPLAYABLE reason=None
- ticket `514` RVTY 2026-08-21 run=145 source=provider_cache last_bar=2026-08-21 status=REPLAYABLE reason=None
- ticket `515` TGT 2026-08-27 run=146 source=provider_cache last_bar=2026-08-27 status=REPLAYABLE reason=None
- ticket `516` TRGP 2026-08-27 run=146 source=provider_cache last_bar=2026-08-27 status=REPLAYABLE reason=None
- ticket `517` MSTR 2026-08-27 run=146 source=provider_cache last_bar=2026-08-27 status=REPLAYABLE reason=None
