# Xiaomei Research OS Architecture

```
                     XIAOMEI RESEARCH OS
                              │
          ┌───────────────────┼───────────────────┐
          ↓                   ↓                   ↓
   FUNDAMENTAL BRAIN    INDUSTRY BRAIN       MARKET BRAIN
          │                   │                   │
      Buffett              Serenity          Capital Behavior
          └───────────────────┼───────────────────┘
                              ↓
                    STATISTICAL / LEARNING
                              ↓
                  Historical Ticket Learning
                              ↓
                    T+1 / T+3 / T+5 / T+10
                              ↓
                     Research Decision
                              ↓
                         PAPER TICKET
                         (existing owner)
```

Owners (not rebuilt):

- production ranking: `scripts/us_profit_ticket_pipeline.py` sort `(ticket_score, market_score, volume_confirmation_ratio)`
- tickets / forward tracking: `scripts/db/pipeline_bridge.py` + `backfill_forward_tracking.py`
- historical replay: `scripts/capital/historical_bootstrap.py`
- Obsidian: `scripts/obsidian/sync_obsidian.py` + `knowledge_asset_export.py`
- database: `scripts/db/`
- research context: `scripts/research/` attached as research/shadow/replay/learning only

PostgreSQL is the fact layer. Obsidian is the knowledge layer. Skills never bypass ranking.
