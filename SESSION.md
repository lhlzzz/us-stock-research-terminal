# SESSION

本轮结论：
- 300天因子分析完成：发现 closing_strength_5d 和 five_day_acceleration 是反向因子（负IC），relative_strength_vs_equal_weight 是最强因子（IC=+0.043）。
- 新 scoring 公式：`score = 0.40×RS + 0.30×VWM - 0.15×accel + 0.15×mom`，基于300天回测验证。
- 回测结果：胜率 56.9%（+9.4%），平均收益 +1.75%（+1.83%），盈亏比 1.92（+0.96）。
- 已同步更新 market_regime.py、us_profit_ticket_pipeline.py、SKILL.md、RULES.md 等文档。
- 研究边界保持：只做美股 + crypto research，不接 A 股、不接交易、broker、order、ledger、live-trade，不输出 BUY/SELL。
- 2026-06-19 完成历史票审查后再优化：`score = 0.45×RS + 0.30×VWM - 0.15×accel + 0.10×mom`；`five_day_acceleration <= -0.18` 时降级为 `MARKET_WATCHLIST_NEEDS_EVIDENCE`；`xiaogu` 升级只读学习结论为"强证据先做 observation / ranking-assist，不轻易做 official hard gate"。
- 2026-06-24 实时数据出票：修复 last30days 零候选问题（添加 Google News RSS fallback），06-24-final 出票 MRNA + GE 进入 PAPER_REVIEW，STX/TER/SW 进入 WATCHLIST。验证 2026-06-23 出票 1d 收益：PAPER_REVIEW 票（MRNA+GE）平均 +2.28%，胜率 100%。06-24-final 3d/5d/10d due_date 分别为 2026-06-25、2026-06-29、2026-07-06，将在到期后回填验证。
- 2026-06-25 优化：kline获取并行化(9x加速)，fund flow并行化，evidence gate放宽(市场评分≥1.0可绕过evidence)，symbol惩罚扩展(STX/TER/SW/SWK)。06-25-v2出票UAL/BKNG/TGT/AXON/DAL全部PAPER_REVIEW。
- 06-24-v4 1d回填：MRNA +2.79%, GE +0.38%, TER -8.07%, STX -5.14%, SW -2.27%。PAPER_REVIEW胜率51.4% vs WATCHLIST 21.7%。
- 06-24-v4 3d回填：MRNA +1.81%, GE +3.03%, TER -6.52%, STX -9.21%, SW +2.58%。PAPER_REVIEW 100%胜率 +2.42% avg。
- backfill脚本修复：包含anchor_date本身，解决3d/5d/10d回填遗漏问题。
- structured signals扩展：添加news_quality(证据源多样性+relevance)和sector_propagation(sector evidence density)。
- lifecycle scoreboard更新：PAPER_REVIEW 62.3% win rate -0.10% avg，WATCHLIST 34.8% win rate -3.31% avg。
- Pipeline v6：UAL/BKNG/TGT/AXON/DAL，news_quality_score + sector_propagation_bonus已集成到CSV输出。
- 2026-06-25 技术指标升级（只读学习xiaogu tradingagent_a + Qlib模式）：
  - 新增RSI(14)：从日收益率计算14日RSI，RSI>75时增加0.06 overbought penalty。
  - 新增momentum_quality：价格+量能对齐度，价涨量增=1.0，单边=0.5，否则0.0。
  - 新增breakout_score：强动量(>5%)+放量(>20%)时评分，防止假突破。
  - 新增reversal_quality：RSI<35+放量时评分，捕获超卖反弹机会。
  - confirmation_score重构：从单一因子改为多因子，momentum_quality 0.10 + breakout_score 0.05 + reversal_quality 0.05。
  - 06-25-final出票：DAL/CAT/MU/UAL/FLEX全部PAPER_REVIEW，score 1.14-1.19。
