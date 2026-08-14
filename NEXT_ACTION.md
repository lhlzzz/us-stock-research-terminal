# NEXT_ACTION

**当前待办：**
1. **来源缺口保留**：16 条历史 tracking、2 条开放纸面记录和 4 条日志记录没有对应 ticket，统一标记 `UNRESOLVED_NO_TICKET`，不要伪造出票或选择理由
2. **策略质量修正**：1d/3d/5d 完成收益仍为负（分别约 -0.92%/-0.57%/-1.23%），10d 约 +3.04%；不要把纸面结果当实盘能力

**已验证（2026-08-14）：**
- 系统边界为美股研究 + 纸面模拟，`paperOnly=true`，没有券商执行链，不能称为已进入实盘
- 修复出票→tracking 的 `ticket_id` 链路：1125/1141 条 tracking 已关联，16 条明确标记未解析
- 新增 `research_trade_trace` 唯一复盘投影和 `/api/trade-traces`，贯通出票、周期收益、纸面记录、交易日志和归因；无 ticket 的记录统一显式标记未解析
- 881 条历史完成记录已补齐 outcome 分类；回填后 1138 completed，3 pending
- Financial OS overview/journal 接入真实复盘链；3000 已重启到最新生产构建
- 知识库：366 条向量均已生成，pgvector 搜索通过
- 验证：`pytest` 25 passed，Financial OS `tsc --noEmit` 和 `next build` 通过，Plan Enforcer 严格审计和目标覆盖均通过

**已完成（2026-08-02）：**
- **前端模块真实数据接通**：模拟交易、AI 出票、AI 信号、出票记录均读取 PostgreSQL 真实记录
- **Obsidian ⇄ 数据库同步验证**：同步 66 个 xiaomei/美股相关 Markdown，knowledge_assets 增至 197 条，trade_journal 已关联 14 条 Obsidian 笔记
- **模拟交易真实行情源收口**：realtime_runner、dual_direction_signals、live_paper_monitor 统一改用 DataProvider，不再绕过项目行情层
- **验证**：API smoke 通过；实时纸面模拟 tick 成功；`python3 -m pytest tests` 25 passed
- **前端全量数据对齐**：Financial OS 仪表盘去除所有硬编码模拟数据，改为读取 API 真实数据
  - Dashboard 统计卡: 总资产/收益/回撤/胜率全部来自 engine-state.json
  - 华尔街晨报 → 系统概览: 显示真实出票、持仓、收益
  - AI信号: 改为显示最新出票信号（来自 tickets 表）
  - 模拟交易中心: 显示真实持仓和订单记录
  - 组合页面: 显示真实持仓明细和盈亏
  - 风险中心: 显示真实回撤和持仓风险
  - 策略实验室: 显示真实 scoring_config 参数
  - 投资日志: 显示真实 trade_journal 记录
- **API 端点扩展**: 新增 scoringConfig(20项)、signalEffectiveness(7条)、forwardTrackingStats(4个周期)
- **lifecycle_scoreboard 刷新**: 更新为最新数据(881 completed, 49.83% win rate, -0.65% avg return)
- **Standalone HTML 增强**: 新增系统概览区域，显示因子权重和收益跟踪统计

**已完成（2026-07-27）：**
- **完整生命周期闭环系统运行成功**：出票→回填→因子回测→权重优化→记分板→退化检测
- **07-27 出票**：AAPL, IR（CANDIDATE_FOR_PAPER_REVIEW）；MSFT, WFC（MARKET_WATCHLIST_NEEDS_EVIDENCE）
- **forward_tracking**：16 条记录已创建（pending，等待到期回填）
- **因子回测**（562 条记录）：
  - catalyst_score: IC=+0.1899（最强正向因子）
  - five_day_acceleration: IC=+0.1615（正向因子）
  - breakout_score: IC=+0.1311（正向因子）
  - prior_5d_momentum: IC=+0.1203（正向因子）
  - reversal_quality: IC=+0.1163（正向因子）
- **权重优化**：5 个显著因子，新权重已应用
  - catalyst_score: 0.3171
  - five_day_acceleration: 0.2697
  - breakout_score: 0.2189
  - reversal_quality: 0.1942
- **退化检测**：近30天胜率 43.44%，平均收益 -1.00%，无需调整
- **记分板**：554 张已完成票，49.82% 胜率，-0.69% 平均收益

**已完成（2026-07-22）：**
- **实时数据出票成功**：获取新开盘数据，生成10张票
- **07-22 出票（实时数据）**：AVGO, AMD, NBIS, NFLX, NVDA, WFC, IR, GS, UNH, EME（CANDIDATE_FOR_PAPER_REVIEW）
- **完整生命周期闭环系统运行成功**：出票→回填→因子回测→权重优化→记分板→退化检测→链路升级
- **07-22 出票（新权重）**：WFC, IR, GS, UNH, EME（CANDIDATE_FOR_PAPER_REVIEW）
- **回填完成**：26 行 pending 数据已回填
- **记分板**：323 张已完成票，50.46% 胜率，-0.14% 平均收益
- **因子回测**（560 条记录）：
  - five_day_acceleration: IC=+0.2055（最强正向因子）
  - market_score: IC=-0.1530（最强负向因子）
  - relative_strength: IC=-0.1459（负向因子）
  - reversal_quality: IC=+0.1401（正向因子）
  - volume_weighted_momentum: IC=-0.1372（负向因子）
  - momentum_quality: IC=-0.1240（负向因子）
  - prior_20d_momentum: IC=-0.1126（负向因子）
  - catalyst_score: IC=+0.0966（正向因子，新增显著）
- **权重优化**：8 个显著因子，新权重已应用
- **退化检测**：系统性能在正常范围内，无需调整
- **Obsidian 同步完成**：5 个新文件同步（美股Project 64个，神临17个）
- **向量嵌入更新**：25 个新分块已生成嵌入（总计148个）
- **想法池更新**：新增2026-07-22每日想法和想法池

**已完成（2026-07-21）：**
- **完整生命周期闭环系统运行成功**：出票→回填→因子回测→权重优化→记分板→退化检测→链路升级
- **07-21 出票（新权重）**：AKAM, ISRG, GOOG, MSFT, GOOGL（CANDIDATE_FOR_PAPER_REVIEW）
- **回填完成**：40 行 pending 数据已回填
- **记分板**：448 张已完成票，34.38% 胜率，-0.24% 平均收益
- **因子回测**（534 条记录）：
  - five_day_acceleration: IC=+0.2126（最强正向因子）
  - market_score: IC=-0.1739（最强负向因子）
  - reversal_quality: IC=+0.1495（正向因子）
  - relative_strength: IC=-0.1471（负向因子）
  - volume_weighted_momentum: IC=-0.1417（负向因子）
  - momentum_quality: IC=-0.1342（负向因子）
  - prior_20d_momentum: IC=-0.1142（负向因子）
- **权重优化**：7 个显著因子，新权重已应用
- **退化检测**：系统性能在正常范围内，无需调整
- **数据库修复**：修正端口配置（5433→5432）
- **向量嵌入生成完成**：123 个分块已生成本地嵌入（使用 local-tfidf-hash 方法）
- **向量搜索功能验证**：搜索"美股投资策略"返回相关结果

**已完成（2026-07-21）：**
- **完整生命周期闭环系统运行成功**：出票→回填→因子回测→权重优化→记分板→退化检测→链路升级
- **07-21 出票（新权重）**：AKAM, ISRG, GOOG, MSFT, GOOGL（CANDIDATE_FOR_PAPER_REVIEW）
- **回填完成**：40 行 pending 数据已回填
- **记分板**：448 张已完成票，34.38% 胜率，-0.24% 平均收益
- **因子回测**（534 条记录）：
  - five_day_acceleration: IC=+0.2126（最强正向因子）
  - market_score: IC=-0.1739（最强负向因子）
  - reversal_quality: IC=+0.1495（正向因子）
  - relative_strength: IC=-0.1471（负向因子）
  - volume_weighted_momentum: IC=-0.1417（负向因子）
  - momentum_quality: IC=-0.1342（负向因子）
  - prior_20d_momentum: IC=-0.1142（负向因子）
- **权重优化**：7 个显著因子，新权重已应用
- **退化检测**：系统性能在正常范围内，无需调整
- **数据库修复**：修正端口配置（5433→5432）

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
