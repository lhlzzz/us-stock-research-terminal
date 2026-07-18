# STATE

完成：
- **全循环系统（Full Cycle）** — 2026-07-10
  - `full_cycle.py`：出票→回填→因子回测→权重优化→记分板→退化检测→链路升级
  - `candidate_factors.py`：10 个候选因子
  - `backfill_kline_factors.py`：回填 43 个股票历史 kline + 候选因子
  - `daily_loop.py` / `daily_scheduler.py`：全循环集成

- **因子回测**（257 条记录，43 symbols * 10 dates）
  - volume_confirmation: IC = +0.2375 (p<0.05) — 唯一显著正向因子
  - momentum_quality: IC = -0.1283 (p<0.05) — 弱负向
  - 之前反向动量效应在更大样本中消失

- **IC 优化权重** — 2026-07-10
  - volume_confirmation_ratio: 0.2375（主导）
  - five_day_acceleration: 0.0978
  - relative_strength_vs_equal_weight: -0.1225
  - closing_strength_5d: -0.0823
  - volume_weighted_momentum: -0.0439
  - prior_20d_momentum: -0.0018

- **DataProvider 多源架构**
- **DB ticket save error 修复**
- **Scrapy 高性能采集器**

当前位置：
- **07-16 出票（新权重）**：DE, WFC, BIIB, ASML, HCA (Paper Review: 5)
- **07-15 出票（分周期权重）**：MRNA, TTWO, FFIV, TECH, HOOD (Watchlist: 5)
- **07-14 出票（分周期权重）**：MRNA, TTWO, FFIV, TECH, HOOD (Watchlist: 5)
- **07-13 出票（新权重）**：CRM, CCI, CASY, ADBE, MSFT (Watchlist: 5)
- **权重优化** — 2026-07-16（扩展因子集）
  - five_day_acceleration: IC=+0.1937（最强正向因子）
  - market_score: IC=-0.1746（负向因子）
  - relative_strength: IC=-0.1605（负向因子）
  - volume_weighted_momentum: IC=-0.1532（负向因子）
  - momentum_quality: IC=-0.1524（负向因子）
  - prior_20d_momentum: IC=-0.1238（负向因子）
  - catalyst_score: IC=+0.098（正向因子）
  - 新增因子：reversal_quality, rsi_14, momentum_quality, breakout_score, market_score, catalyst_score
- **因子回测**（442 条记录）
  - 7 个显著因子（p<0.05）
  - five_day_acceleration 成为最强预测因子
- **盈利 vs 亏损因子差异**
  - volume_confirmation: 盈利 0.3574 vs 亏损 0.1937（p=0.0029）
  - reversal_quality: 盈利 0.0116 vs 亏损 0.0060（p=0.0056）
  - five_day_acceleration: 盈利 0.0033 vs 亏损 -0.0251（p=0.0312）
- **回填完成**：30 行 pending 数据已回填
- **记分板**：233 张已完成票，52.79% 胜率，-0.089% 平均收益
- DB：本机 PostgreSQL 14（端口 5432）
- Daily klines: 222,584 rows (43 symbols)
- Factor snapshots: 464 rows
- **数据源状态**：东财批量 API 可用（3472 只美股）
- **Universe 扩展**：从 164 扩展到 3095 只（Russell 3000）

文件清单：
- scripts/full_cycle.py — 全循环编排器
- scripts/candidate_factors.py — 候选因子计算
- scripts/backfill_kline_factors.py — kline + 候选因子回填
- scripts/daily_loop.py — 日循环编排器
- scripts/daily_scheduler.py — 调度器
- scripts/us_profit_ticket_pipeline.py — 主 pipeline
- scripts/lifecycle_scoreboard.py — 记分板
- scripts/meta_loop.py — 退化检测
- scripts/weight_optimizer.py — 权重优化（支持分周期）
- scripts/dynamic_horizon.py — 动态持仓周期
- data/scoring_weights.json — IC 优化权重（含分周期权重）
- data/horizon_weights.json — 分周期权重配置

东财 API 状态：
- kline: blocked（push2his 被封，用 akshare/yfinance fallback）
- batch_quote: available（push2delay clist API，一次拉全部美股行情，~9s）
