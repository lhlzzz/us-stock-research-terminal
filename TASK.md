# TASK

当前任务：
- `XIAOMEI_LAST30DAYS_FIX_AND_SCORING_V2`：已修复 last30days 超时瓶颈（build_supply_chain_map 改为本地逻辑 + _run_last30days 加 SKIP 检查 + timeout 20s），pipeline 不再需要 --skip-last30days。
- `XIAOMEI_BLENDED_SCORING_V1`：参考 xiaogu blended scoring，实现 `0.6×base + 0.4×structured`，structured 含 6 维度（volume_price_alignment / closing_consistency / momentum_health / dollar_volume_quality / trend_stability / fund_flow_momentum）。新增 EastMoney f178 资金流向信号。
- `XIAOMEI_EASTMONEY_ONLY_V2`：已移除 Yahoo/yfinance，改为 akshare（东财底层）作为 kline 源 + EastMoney realtime quote。

状态：
- `py_compile` 通过全部修改文件。
- 完整 pipeline（不跳过 last30days）成功出票，3 票 universe ~60s 完成。
- 2026-06-23-v2：MRNA + GE 进入 PAPER_REVIEW，STX/TER/SW/IP 进入 WATCHLIST。
- 2026-06-24-final：MRNA + GE 进入 PAPER_REVIEW（paper_review_count=2），STX/TER/SW 进入 WATCHLIST。
- 2026-06-24-v4（改进后）：MRNA(0.955) + GE(0.525) 进入 PAPER_REVIEW，STX(0.483)/TER(0.455)/SW(0.303) 因 accel 硬拒留在 WATCHLIST。
- 数据源：akshare kline + EastMoney realtime quote + EastMoney fund flow (f178)。
- last30days 零候选问题已修复：添加 Google News RSS fallback。
- backfill_forward_tracking.py 已切换到 akshare 作为 kline 源，不再依赖不可用的 eastmoney_us kline。
- scoring v3 改进：accel 权重 -0.15→-0.10，confirmation 权重 0.08→0.12，accel 惩罚降低，momentum_health 阈值收紧。

2026-06-23 出票结果：
- PAPER_REVIEW：MRNA(1.177) narrative+business=found_relevant，GE(0.856) narrative+business=found_relevant
- WATCHLIST：STX(0.898) accel硬拒，TER(0.660) accel硬拒，SW(0.470) accel硬拒，IP(0.309) accel硬拒+blowoff
- 注意：MRNA 今日 -7.22%，但 evidence gate 找到相关催化剂

历史收益验证：
- 06-18 3d：100% 胜率，+6.09%
- 06-19 3d：75% 胜率，+2.58%
- 06-21 1d：67% 胜率，-0.06%
- 06-23 1d：100% 胜率（PAPER_REVIEW票），+2.28% 平均收益（MRNA +4.21%，GE +0.35%）
- 06-24-final 3d/5d/10d：due_date 分别为 2026-06-25、2026-06-29、2026-07-06，尚未到期，将在到期后回填验证。
