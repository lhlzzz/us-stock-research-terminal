# Obsidian / Second-Brain Reconciliation

Second brain is used only to confirm evolution and current version. It does not replace returns.

## Source facts

- Current 主力行为 owner in code: `capital_behavior_v2`
- Production ranking owner: `observable_footprint_v1` FROZEN
- Pipeline: Capital Brain runs beside ranking and must not change it.

## Database facts

- `capital_behavior_dataset` has 23 research samples from historical bootstrap, NOT a profitability panel.
- `tickets` / `forward_tracking` are LEGACY_ONLY for this report.
- As-of replay uses `daily_klines` only.

## Second-brain notes

- `2026-08-27 美股知识资产` — `obsidian/project/美股/inbox/2026-08-27-知识资产.md`
- `2026-08-21 美股知识资产` — `obsidian/project/美股/inbox/2026-08-21-知识资产.md`
- `2026-08-18 美股知识资产` — `obsidian/project/美股/inbox/2026-08-18-知识资产.md`
- `2026-08-15 美股知识资产` — `obsidian/project/美股/inbox/2026-08-15-知识资产.md`
- `2026-08-03 美股知识资产` — `obsidian/project/美股/inbox/2026-08-03-知识资产.md`
- `2026-07-30 美股知识资产` — `obsidian/project/美股/inbox/2026-07-30-知识资产.md`
- `2026-07-29 美股知识资产` — `obsidian/project/美股/inbox/2026-07-29-知识资产.md`
- `2026-07-28 美股知识资产` — `obsidian/project/美股/inbox/2026-07-28-知识资产.md`
- `2026-07-27 美股知识资产` — `obsidian/project/美股/inbox/2026-07-27-知识资产.md`
- `2026-07-25 美股知识资产` — `obsidian/project/美股/inbox/2026-07-25-知识资产.md`
- `2026-07-24 美股知识资产` — `obsidian/project/美股/inbox/2026-07-24-知识资产.md`
- `2026-07-22 美股知识资产` — `obsidian/project/美股/inbox/2026-07-22-知识资产.md`
- `2026-07-21 美股知识资产` — `obsidian/project/美股/inbox/2026-07-21-知识资产.md`
- `2026-07-17 美股知识资产` — `obsidian/project/美股/inbox/2026-07-17-知识资产.md`
- `2026-07-16 美股知识资产` — `obsidian/project/美股/inbox/2026-07-16-知识资产.md`
- `2026-07-15 美股知识资产` — `obsidian/project/美股/inbox/2026-07-15-知识资产.md`
- `2026-07-14 美股知识资产` — `obsidian/project/美股/inbox/2026-07-14-知识资产.md`
- `2026-07-13 美股知识资产` — `obsidian/project/美股/inbox/2026-07-13-知识资产.md`
- `2026-07-11 美股知识资产` — `obsidian/project/美股/inbox/2026-07-11-知识资产.md`
- `2026-07-10 美股知识资产` — `obsidian/project/美股/inbox/2026-07-10-知识资产.md`
- `2026-07-09 美股知识资产` — `obsidian/project/美股/inbox/2026-07-09-知识资产.md`
- `2026-07-08 美股知识资产` — `obsidian/project/美股/inbox/2026-07-08-知识资产.md`
- `2026-07-07 美股知识资产` — `obsidian/project/美股/inbox/2026-07-07-知识资产.md`
- `2026-07-06 美股知识资产` — `obsidian/project/美股/inbox/2026-07-06-知识资产.md`
- `2026-07-03 美股知识资产` — `obsidian/project/美股/inbox/2026-07-03-知识资产.md`
- `2026-07-02 美股知识资产` — `obsidian/project/美股/inbox/2026-07-02-知识资产.md`
- `2026-07-01 美股知识资产` — `obsidian/project/美股/inbox/2026-07-01-知识资产.md`
- `2026-06-30 美股知识资产` — `obsidian/project/美股/inbox/2026-06-30-知识资产.md`
- `2026-06-27 美股知识资产` — `obsidian/project/美股/inbox/2026-06-27-知识资产.md`

## Reconciliation

| Claim | Source | Database | Second brain |
| --- | --- | --- | --- |
| Latest 主力行为 version is capital_behavior_v2 | PASS | PASS (model_version column / scoring.MODEL_VERSION) | no newer version recorded |
| Production ranking is still observable_footprint_v1 | PASS | PASS (research.boundary) | knowledge assets still export ticket_score picks |
| Capital score is not proven institutional flow | PASS | PASS | PASS |
| Old tickets prove new strategy profit | FORBIDDEN | isolated | isolated |
