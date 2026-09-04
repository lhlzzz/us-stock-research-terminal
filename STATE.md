# STATE

## Xiaomei 2.1.1 — 2026-09-04

Completion: **XIAOMEI 2.1.1 HARDENED**.

Research OS canonical owner is `scripts/research/`. Legacy
`research_panel.py` is a compatibility adapter only. Production ranking
owner remains `observable_footprint_v1` with sort
`(ticket_score, market_score, volume_confirmation_ratio)`. Boundary
unchanged: RESEARCH_ONLY / PAPER_ONLY / NO_BROKER / NO_LIVE_ORDER /
NO_PRODUCTION_PICK / NO_PRODUCTION_WEIGHT_CHANGE.

Verified this session:

- `python -m compileall -q .` pass
- `PYTHONPATH=. pytest -q tests` = 218 passed
- NVDA dry-run `--skip-last30days --top-k 1` = RESEARCH_ONLY SUCCESS,
  `as_of_date`/`target_session` = `2026-09-03`,
  classification = MARKET_WATCHLIST_NEEDS_EVIDENCE, paper_review_count = 0

Honest DATA_GAP (do not convert to READY): SEC ingestion, earnings
ingestion, estimate revision, industry graph, chokepoint, true historical
universe snapshots, persistent failure memory.

Next: Xiaomei 2.2 real SEC + earnings + industry-graph ingestion. Do not
add scoring modules.

---

## 全量对齐完成 — 2026-07-24

### 新增模块（对齐 xiaogu 架构）

**Phase 1: 数据库对齐（6张新表）**
- `daily_candidates` - 全量候选池（400+行/天）
- `scoring_config` - 可调参数（20个配置项）
- `signal_effectiveness` - 每日信号分析快照
- `signals` - 逐股原始信号快照
- `scan_sessions` - 扫描器会话元数据
- `pick_case_embeddings` - 神经向量案例（384维，HNSW）

**Phase 2: 神经向量升级**
- `neural_vector_store.py` - sentence-transformers 384维
- 模型: paraphrase-multilingual-MiniLM-L12-v2
- HNSW cosine 索引，支持相似案例检索
- Fallback: structured 64维（确定性哈希）

**Phase 3: 知识资产导出（Obsidian 第二大脑）**
- `knowledge_asset_export.py` - 主动写入 Obsidian
- 输出: Summary JSON + Obsidian 笔记 + pgvector TOP10
- 路径: `/mnt/d/obisidian/Obsidian/Project/美股/inbox/`

**Phase 4: 日闭环脚本 + 时区调度器**
- `daily_pipeline.sh` - 8步单入口链
- `xiaomei_scheduler.py` - 时区感知 APScheduler
- 时间表: 05:00(美股收盘后) / 09:00(开盘前) / 20:00(信号分析)

**Phase 5: API 层**
- `xiaomei_api.py` - 兼容模块；对外访问统一由 `http://localhost:3000` 提供
- 端点: /picks, /returns, /signals, /stats, /explain

**Phase 6: 自进化 + 证据卡**
- `xiaomei_self_evolve.py` - 有界参数调整（7个可调knob）
- `xiaomei_evidence_card.py` - 紧凑决策证据卡

### 时间线约束

```
美股收盘 = 北京时间 04:00（夏令时）
出票必须在 04:00 之后
回填收益也必须在 04:00 之后
```

### 当前状态

- **数据库**: 24张表（14核心 + 4向量 + 2信号 + 4纸面模拟）
- **神经向量**: sentence-transformers 384维，HNSW cosine
- **知识资产**: Obsidian 第二大脑（主动写入）197条
- **自进化**: 有界参数调整（7个可调knob）
- **API**: 统一由 Financial OS 的 `http://localhost:3000/api/workspaces/xiaomei/overview` 提供（18个字段）
- **调度器**: 时区感知（A股/美股分离）
- **评分系统**: 双重过滤（门槛0.55 + top-k=3）
- **Universe**: 3095只（Russell 3000）
- **前端**: Financial OS 仪表盘全量真实数据（无硬编码）+ Standalone HTML

### 07-27 出票

| 代码 | 总分 | 市场分 | 催化分 | 分类 |
|------|------|--------|--------|------|
| AAPL | 0.975 | 0.858 | 0.107 | CANDIDATE_FOR_PAPER_REVIEW |
| IR | 0.904 | 0.852 | 0.032 | CANDIDATE_FOR_PAPER_REVIEW |
| MSFT | 0.803 | 0.730 | 0.053 | MARKET_WATCHLIST_NEEDS_EVIDENCE |
| WFC | 0.790 | 0.700 | 0.069 | MARKET_WATCHLIST_NEEDS_EVIDENCE |

### 因子权重（最新 07-27）

- catalyst_score: IC=+0.1899（最强正向）→ 权重 0.3171
- five_day_acceleration: IC=+0.1615（正向）→ 权重 0.2697
- breakout_score: IC=+0.1311（正向）→ 权重 0.2189
- reversal_quality: IC=+0.1163（正向）→ 权重 0.1942
- prior_5d_momentum: IC=+0.1203（正向）→ 纳入优化

### 记分板统计（08-02）

- 已完成：881 张
- 胜率：49.83%
- 平均收益：-0.65%
- 待回填：251 条（pending）

### 文件清单

```
scripts/
├── neural_vector_store.py       # 神经向量存储
├── knowledge_asset_export.py    # 知识资产导出
├── daily_pipeline.sh            # 日闭环脚本
├── xiaomei_scheduler.py         # 时区感知调度器
├── xiaomei_api.py               # FastAPI 服务
├── xiaomei_self_evolve.py       # 有界自进化
├── xiaomei_evidence_card.py     # 证据卡生成器
├── us_profit_ticket_pipeline.py # 主 pipeline
├── backfill_forward_tracking.py # 回填
├── lifecycle_scoreboard.py      # 记分板
├── signal_effectiveness.py      # 信号分析
├── weight_optimizer.py          # 因子权重优化
└── db/migrate_v2_alignment.sql  # v2 对齐迁移
```

### 东财 API 状态

- kline: blocked（push2his 被封，用 akshare/yfinance fallback）
- batch_quote: available（push2delay clist API，一次拉全部美股行情，~9s）
