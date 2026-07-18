# NEXT_ACTION

**当前待办：**
1. **生成向量嵌入**：设置 OPENAI_API_KEY 后运行 `python3 scripts/obsidian/generate_embeddings.py`
2. **每日自动循环**：`daily_scheduler.py` 已集成全循环，可通过 cron 每日自动运行
3. **候选因子扩展**：已将 reversal_quality, rsi_14, momentum_quality, breakout_score, market_score, catalyst_score 加入权重优化
4. **Universe 扩展完成**：从 164 扩展到 3095 只（Russell 3000）

**已完成（2026-07-17）：**
- **pgvector 安装**：v0.8.0 已编译安装，数据库支持向量搜索
- **知识资产表创建**：knowledge_assets + knowledge_embeddings（1536维，HNSW索引）
- **Obsidian 同步脚本**：
  - `sync_obsidian.py` - Git 拉取 + Markdown 解析
  - `generate_embeddings.py` - OpenAI 向量生成
  - `search_knowledge.py` - 向量相似度搜索

**已完成（2026-07-16）：**
- **07-16 出票（新权重）**：DE, WFC, BIIB, ASML, HCA（CANDIDATE_FOR_PAPER_REVIEW）
- **分类逻辑优化**：降低催化剂门槛，当使用 --skip-last30days 时，市场分数 >= 0.4即可通过
- **回填完成**：30 行 pending 数据已回填
- **记分板**：233 张已完成票，52.79% 胜率，-0.089% 平均收益
- **因子分析**：盈利 vs 亏损因子差异显著
  - volume_confirmation: 盈利 0.3574 vs 亏损 0.1937（p=0.0029）
  - reversal_quality: 盈利 0.0116 vs 亏损 0.0060（p=0.0056）
  - five_day_acceleration: 盈利 0.0033 vs 亏损 -0.0251（p=0.0312）
- **权重优化**：基于 442 条回填数据，扩展因子集
  - 新增因子：reversal_quality, rsi_14, momentum_quality, breakout_score, market_score, catalyst_score
  - five_day_acceleration: IC=+0.1937（最强正向因子）
  - market_score: IC=-0.1746（负向因子）
  - relative_strength: IC=-0.1605（负向因子）
  - volume_weighted_momentum: IC=-0.1532（负向因子）
  - momentum_quality: IC=-0.1524（负向因子）
  - catalyst_score: IC=+0.098（正向因子）
- **链路升级**：权重已更新（7 个显著因子）
- **Universe 扩展**：从 164 扩展到 3095 只（Russell 3000）

**已完成（2026-07-15）：**
- **07-15 出票（分周期权重）**：MRNA, TTWO, FFIV, TECH, HOOD
- **回填完成**：30 行 pending 数据已回填
- **记分板**：88 张已完成票，70.45% 胜率，+2.53% 平均收益

**已完成（2026-07-14）：**
- **07-14 出票（分周期权重）**：MRNA, TTWO, FFIV, TECH, HOOD
- **分周期权重优化** — 基于 194 条回填数据
  - 1d: relative_strength 主导（IC=-0.708）
  - 10d: closing_strength_5d 主导（IC=-0.419）
  - 动态持仓：1d→3d（避免 48% 胜率），10d 保持（71% 胜率）
- **权重重大更新** — 基于 382 条回填数据
  - five_day_acceleration: +0.3066（最强正向因子，IC=+0.2138）
  - relative_strength_vs_equal_weight: -0.2479
  - volume_weighted_momentum: -0.2473
  - prior_20d_momentum: -0.1982
  - volume_confirmation: 不再显著（IC=+0.0436，p=0.3955）
- **07-13 出票（新权重）**：CRM, CCI, CASY, ADBE, MSFT
- **回填完成**：73 行 pending 数据已回填
- **记分板**：83 张已完成票，71.08% 胜率，+2.65% 平均收益

**已完成（2026-07-10）：**
- **全循环系统（Full Cycle）**
  - `full_cycle.py`：出票→回填→因子回测→权重优化→记分板→退化检测→链路升级
  - `candidate_factors.py`：10 个候选因子（RSI, MACD, BB, ATR, Stochastic, Williams %R, OBV, MFI, VWAP）
  - `backfill_kline_factors.py`：回填 43 个股票的历史 kline + 候选因子
  - `daily_loop.py`：重写为全循环编排器
  - `daily_scheduler.py`：集成全循环

- **因子回测关键发现**（257 条记录，43 symbols * 10 dates）
  - **volume_confirmation**: IC = +0.2375 (p<0.05) — 唯一显著正向因子
  - **momentum_quality**: IC = -0.1283 (p<0.05) — 弱负向
  - 之前的反向动量效应在更大样本中消失了
  - 新权重：volume_confirmation_ratio = 0.2375（主导）

- **07-11 出票（新权重）**：META, NVDA, AMAT, STX, KDP

**已完成（2026-07-09）：**
- 动态持仓周期（Dynamic Horizon Allocation）
- Pipeline 出票：ABNB, HBAN, MNST, NTRS, PFG

**配置项：**
- AKSHARE_KLINE_CONCURRENCY=5
- AKSHARE_KLINE_BATCH_SIZE=50
- EASTMONEY_COOLDOWN_SECONDS=1800
- MAX_RETRY_COUNT=2

**循环命令：**
```bash
# 完整日循环（跳过出票）
PYTHONPATH=scripts python3 scripts/daily_loop.py --skip-pipeline

# 完整日循环（含出票）
PYTHONPATH=scripts python3 scripts/daily_loop.py

# 完整循环编排器
PYTHONPATH=scripts python3 scripts/full_cycle.py

# 单独出票
python3 scripts/us_profit_ticket_pipeline.py --save-db --skip-last30days

# 单独记分板
python3 scripts/lifecycle_scoreboard.py --db
```
