# HANDOFF

完成：
- 300天因子分析 + scoring 重配完成。
- Scoring v3 改进：accel 权重 -0.15→-0.10，confirmation ×0.08→×0.12，accel 惩罚降低，momentum_health 阈值收紧。
- 回测验证：胜率 56.9%，avg +1.75%，PF=1.92（旧公式：47.5%，-0.08%，0.96）
- backfill_forward_tracking.py 切换到 akshare 作为 kline 源，不再依赖不可用的 eastmoney_us kline。
- last30days 零候选修复：添加 Google News RSS fallback。
- 2026-06-24-v4 出票：MRNA(0.955) + GE(0.525) PAPER_REVIEW，STX/TER/SW 因 accel 硬拒。
- 06-23 1d 收益已验证：PAPER_REVIEW 票（MRNA+GE）平均 +2.18%，胜率 100%。

下一步：
- 跟踪 06-24-v4 3d/5d/10d 收益（due_date 2026-06-25、2026-06-29、2026-07-06）。
- 探索更多 structured 信号（news_quality、sector_propagation）。
- 优化 fund flow 信号（扩展到 10/20 天趋势）。


风险：
- 未接 broker / order / ledger / live-trade；严格 research-only。
- 300天回测基于历史数据，live 表现可能有差异。
- Yahoo/yfinance historical kline 仍依赖外部网络。
