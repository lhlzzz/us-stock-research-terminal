---
name: serenity
description: US-equity industry / value-chain / chokepoint research. Evidence only. Never a pick generator.
---

# Serenity — Industry Brain

Research knowledge, not a ticket printer. Xiaomei production ranking remains
`observable_footprint_v1`.

Provenance: Xiaogu `.agents/skills/serenity-skill/`. Adapted for US listings.
A-share source paths (互动易, 龙虎榜) are not used.

## Contract

Owner: `scripts/research/brains.py` → `build_serenity_context`.

Produces:

- `industry_context`
- `chokepoint_candidates`
- `critical_dependencies`
- `company_implications`
- `confidence`
- `evidence_refs`

`produces_pick: false`

## Layers

`end_market → system → platform → equipment → component → subcomponent → material → software → service → infrastructure`

## Questions the analysis must answer

- What is actually scarce in this industry?
- Who controls the bottleneck?
- Why is it hard to replace?
- What is the substitution cost?
- Do certification / know-how / supply chain / capacity form a barrier?
- Is the bottleneck being repriced?

Missing evidence stays UNKNOWN. This skill never ranks production tickets.
