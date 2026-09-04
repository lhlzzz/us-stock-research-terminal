---
name: buffett
description: US-equity company-quality research framework. Structured evidence only. Never a pick generator.
---

# Buffett — Fundamental Brain

Research knowledge, not a ticket printer. Xiaomei production ranking remains
`observable_footprint_v1` in `scripts/us_profit_ticket_pipeline.py`.

Provenance: Xiaogu `uzi/deep-analysis/personas/buffett.yaml` (philosophy and
metrics). There is no `.claude/skills/buffett/` reference pack in Xiaogu; this
skill is the structured US conversion, not a prompt copy.

## Contract

Owner: `scripts/research/brains.py` → `build_buffett_context`.

Output fields:

- `buffett_quality` (DERIVED from observed public fields, else UNKNOWN)
- `buffett_moat` (UNKNOWN unless filings evidence is supplied)
- `buffett_management` (UNKNOWN unless evidence is supplied)
- `buffett_financial_quality`
- `buffett_capital_allocation`
- `buffett_valuation`
- `buffett_risk`
- `buffett_industry_fit`

Every claim is one of `OBSERVED | DERIVED | INFERRED | UNKNOWN`.
UNKNOWN is never guessed into a fact.

## What this skill does

Answer: is this a good business at a sensible price, given public evidence?

Use only as-of public fields (quotes, filings already present). Missing
statements stay UNKNOWN.

## What this skill does not do

- Does not emit BUY / SELL / ORDER / PAPER_PICK
- Does not change `ticket_score` / `market_score` / ranking
- Does not treat personal holdings as quality evidence
