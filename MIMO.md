# xiaomei MIMO.md

## 全局规范

遵循 `/root/.mimo/CLAUDE.md` MiMo 工程操作系统。

## 项目信息

美股量化研究系统。

## 文件结构

```
xiaomei/
├── scripts/
│   ├── db/                  # 数据库模块
│   ├── api/                 # FastAPI 接口
│   ├── tasks/               # Celery 任务
│   ├── parquet/             # Parquet 因子仓
│   ├── obsidian/            # Obsidian 知识资产同步
│   │   ├── sync_obsidian.py        # 同步脚本
│   │   ├── generate_embeddings.py  # 向量生成
│   │   ├── search_knowledge.py     # 向量搜索
│   │   └── README.md               # 配置说明
│   ├── us_profit_ticket_pipeline.py  # 主 pipeline
│   ├── backfill_forward_tracking.py  # 回填
│   ├── lifecycle_scoreboard.py       # 记分板
│   ├── signal_effectiveness.py       # 信号分析
│   ├── eastmoney_us_cdp.py          # 东财数据采集
│   └── market_regime.py             # 市场状态
├── data/
│   ├── factors/             # Parquet 因子数据
│   └── obsidian/            # Obsidian 知识库（Git 同步）
├── research/                # 输出产物
├── docker-compose.yml       # PostgreSQL + Redis
└── .env                     # 环境变量
```

## 数据源

- 东财 push2delay API：批量实时行情（3475只美股，~9s，xiaogu v2 模式）
- yfinance：K 线历史数据（主源，最新到 T-1）+ 财务数据（180字段免费）
- akshare：K 线 fallback

## 数据库（13 张表 + pgvector）

### 核心表（11张）
universe, daily_klines, realtime_quotes, fund_flow, tickets, forward_tracking, runtime_decisions, market_snapshots, lifecycle_scoreboard, research_runs, factor_snapshots

### 知识资产表（2张，pgvector 向量搜索）
- `knowledge_assets` - 文档元数据（路径、标题、内容、hash）
- `knowledge_embeddings` - 向量嵌入（1536维，HNSW 索引）

### pgvector 配置
- 版本: 0.8.0
- 索引: HNSW (vector_cosine_ops)
- 嵌入模型: text-embedding-ada-002

## 工具

- 代码结构、符号、调用链、影响面优先使用 codebase-memory-mcp（`index_repository`、`search_graph`、`trace_path`、`get_code_snippet`、`query_graph`、`search_code`）；未索引时先索引当前 workspace，再按需回退 CodeGraph/GitNexus/grep。

## 命令

```bash
# 出票
python3 scripts/us_profit_ticket_pipeline.py --save-db --skip-last30days

# 回填
python3 scripts/backfill_forward_tracking.py --db

# 记分板
python3 scripts/lifecycle_scoreboard.py --db

# 信号分析
python3 scripts/signal_effectiveness.py

# 数据库迁移
python3 scripts/db/migrate.py

# Obsidian 知识资产同步
python3 scripts/obsidian/sync_obsidian.py

# 生成向量嵌入（需要 OPENAI_API_KEY）
python3 scripts/obsidian/generate_embeddings.py

# 搜索知识资产
python3 scripts/obsidian/search_knowledge.py "查询文本"
```

## 禁止

- 不碰 A 股逻辑
- 不碰 xiaogu 任何内容
- 不新增 broker / execution / live-trade
- 不输出 BUY/SELL

## 当前状态

- 本机 PostgreSQL 14（端口 5432）+ Redis 6 运行中
- **pgvector 0.8.0** 已安装，支持向量搜索
- 13 张表（11 核心 + 2 知识资产向量表）
- **Obsidian 同步**：WSL 直接挂载 Windows 路径（78 + 18 = 96 个文件已同步）
- **07-16 出票（新权重）**：DE, WFC, BIIB, ASML, HCA (Paper Review)
- **07-15 出票（分周期权重）**：MRNA, TTWO, FFIV, TECH, HOOD
- **07-14 出票（分周期权重）**：MRNA, TTWO, FFIV, TECH, HOOD
- **07-13 出票（新权重）**：CRM, CCI, CASY, ADBE, MSFT
- **记分板**：233 张已完成票，52.79% 胜率，-0.089% 平均收益
- **分周期权重**：1d→relative_strength, 10d→closing_strength_5d
- **Universe 扩展**：3095 只（Russell 3000）
- **数据源**：东财批量 API 可用（3472 只美股）
- **分类逻辑**：降低催化剂门槛，市场分数 >= 0.4即可通过
