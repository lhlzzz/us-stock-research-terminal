# xiaomei MIMO.md

## 全局规范

遵循 `/root/.mimo/CLAUDE.md` MiMo 工程操作系统。

## 项目信息

美股量化研究系统，全量对齐 xiaogu 架构。

## 时间线约束（核心）

```
A股:  09:30 开盘 ──────────── 15:00 收盘（北京时间）
美股:                          21:30 开盘 ──────────── 04:00(+1) 收盘（北京时间）
      |---白天---|---空窗---|---夜间美股交易---|--凌晨--|
      06:00    09:30    15:00    21:30    04:00    06:00
```

**关键约束**：
- 美股收盘 = 北京时间 **凌晨 04:00**（夏令时）
- **出票必须在 04:00 之后**，否则数据不完整
- **回填收益也必须在 04:00 之后**
- A股和美股的 scheduler 必须分开

## 文件结构

```
xiaomei/
├── scripts/
│   ├── db/                          # 数据库模块
│   │   └── migrate_v2_alignment.sql # v2 对齐迁移（6张新表）
│   ├── obsidian/                    # Obsidian 知识资产同步
│   │   ├── sync_obsidian.py         # 同步脚本
│   │   ├── generate_embeddings.py   # 向量生成
│   │   └── search_knowledge.py      # 向量搜索
│   ├── us_profit_ticket_pipeline.py # 主 pipeline
│   ├── backfill_forward_tracking.py # 回填
│   ├── lifecycle_scoreboard.py      # 记分板
│   ├── signal_effectiveness.py      # 信号分析
│   ├── weight_optimizer.py          # 因子权重优化
│   ├── neural_vector_store.py       # 神经向量存储（sentence-transformers）
│   ├── knowledge_asset_export.py    # 知识资产导出（Obsidian 第二大脑）
│   ├── daily_pipeline.sh            # 日闭环脚本（8步）
│   ├── xiaomei_scheduler.py         # 时区感知调度器
│   ├── xiaomei_api.py               # FastAPI 服务（12端点）
│   ├── xiaomei_self_evolve.py       # 有界自进化
│   └── xiaomei_evidence_card.py     # 证据卡生成器
├── data/
│   ├── scoring_weights.json         # IC 优化权重
│   └── provider-cache/              # 数据源缓存
├── research/                        # 输出产物
│   ├── knowledge-assets/            # 知识资产 JSON
│   └── profit-ticket-pipeline/      # Pipeline 输出
├── docker-compose.yml               # PostgreSQL + Redis
└── .env                             # 环境变量
```

## 数据库（20 张表 + pgvector）

### 核心表（14张）
universe, daily_klines, realtime_quotes, fund_flow, tickets, forward_tracking, runtime_decisions, market_snapshots, lifecycle_scoreboard, research_runs, factor_snapshots, daily_candidates, scoring_config, scan_sessions

### 知识资产表（4张，pgvector 向量搜索）
- `knowledge_assets` - 文档元数据（路径、标题、内容、hash）
- `knowledge_embeddings` - 向量嵌入（1536维，HNSW 索引，tfidf）
- `pick_case_embeddings` - 案例向量（384维，HNSW 索引，sentence-transformers）

### 信号分析表（2张）
- `signal_effectiveness` - 每日信号分析快照
- `signals` - 逐股原始信号快照

### pgvector 配置
- 版本: 0.8.0
- 索引: HNSW (vector_cosine_ops)
- 嵌入模型: sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2 (384维)
- Fallback: local-tfidf-hash (1536维)

## 数据源

- 东财 push2delay API：批量实时行情（3475只美股，~9s，xiaogu v2 模式）
- yfinance：K 线历史数据（主源，最新到 T-1）+ 财务数据（180字段免费）
- akshare：K 线 fallback

## 命令

```bash
# 日闭环（完整8步）
bash scripts/daily_pipeline.sh

# 出票
python3 scripts/us_profit_ticket_pipeline.py --save-db --skip-last30days --top-k 3

# 回填
python3 scripts/backfill_forward_tracking.py --db

# 记分板
python3 scripts/lifecycle_scoreboard.py --db

# 因子权重优化
python3 scripts/weight_optimizer.py

# 信号分析
python3 scripts/signal_effectiveness.py

# 知识资产导出
python3 scripts/knowledge_asset_export.py --date 2026-07-24

# 神经向量搜索
python3 -c "from neural_vector_store import search_similar_cases; ..."

# 证据卡
python3 scripts/xiaomei_evidence_card.py --date 2026-07-24 --symbol IR --format markdown

# 自进化检查
python3 scripts/xiaomei_self_evolve.py --check-gate

# 调度器（守护进程）
python3 scripts/xiaomei_scheduler.py --daemon

# API 服务
访问 `http://localhost:3000/dashboard/xiaomei`（统一 Web 网关）

# 健康检查
python3 scripts/xiaomei_scheduler.py --health
```

## API 端点

| 端点 | 方法 | 说明 |
|------|------|------|
| `/health` | GET | 健康检查 |
| `/picks` | GET | 列出 tickets/picks |
| `/picks/{date}/summary` | GET | 每日 pick 摘要 |
| `/picks/{date}/detail` | GET | 完整 pick 详情 |
| `/returns` | GET | 收益记录 |
| `/signals` | GET | 原始信号值 |
| `/signals/effectiveness` | GET | 信号有效性分析 |
| `/stats/overview` | GET | 系统统计概览 |
| `/stats/performance` | GET | 月度绩效分解 |
| `/daily-candidates/{date}` | GET | 每日候选分析 |
| `/explain/{date}/{symbol}` | GET | 解释候选 |

## 调度器时间表

| 任务 | 时间（北京时间） | 说明 |
|------|-----------------|------|
| Daily Pipeline | 05:00 | 美股收盘后，完整8步闭环 |
| Morning Health | 09:00 | 开盘前健康检查 |
| Signal Effectiveness | 20:00 | 信号有效性分析 |

## 禁止

- 不碰 A 股逻辑
- 不碰 xiaogu 任何内容
- 不新增 broker / execution / live-trade
- 不输出 BUY/SELL

## 当前状态

- 本机 PostgreSQL 14（端口 5432）+ Redis 6 运行中
- **pgvector 0.8.0** 已安装，支持向量搜索
- **20 张表**（14 核心 + 4 向量 + 2 信号）
- **神经向量**: sentence-transformers 384维，HNSW cosine 索引
- **知识资产**: Obsidian 第二大脑（主动写入）
- **自进化**: 有界参数调整（7个可调 knob）
- **API**: 统一由 Financial OS 的 `http://localhost:3000/api/*` 提供
- **调度器**: 时区感知（A股/美股分离）
- **评分系统**: 双重过滤（门槛 0.55 + top-k=3）
- **Universe**: 3095 只（Russell 3000）
