# RULES

- US ticker，不是 A 股六位代码。
- 美股历史 kline 来源：akshare（底层调用东财数据接口）；东财 push2delay kline 对美股返回 0 行，不可用。
- 美股实时行情来源：EastMoney US realtime/delayed quote（`scripts/eastmoney_us.py`）。
- EastMoney provider 负责 realtime OHLCV / Close / detail；akshare 负责 historical daily kline；当前 `Adj Close` 仅镜像 `Close`。
- `last30days` 只做 Reddit / HN / Polymarket / GitHub / YouTube 等社交 / 公开资料研究。
- `last30days` 不提供正式行情价格，也不作为行情源。
- 不默认接其他行情源；禁止回退到 legacy market-data source。
- **只管美股**；虚拟币 / 加密归 `xiaobi`，不在本 workspace 扩展 crypto 主链路。
- close-to-close replay。
- 每个 replay_date 只选 Top 1。
- no broker / no order / no ledger / no paper-trade / no live-trade。
- 不接 broker feed / paid market data。
- 不接交易所 API / 钱包 / order endpoint。
- 不复用 A 股东财、龙虎榜、涨停、一手、6000 元逻辑。

## Scoring Formula (2026-06-24 v3 blended)

参考 xiaogu blended scoring 模式，当前评分为混合架构：

```
base_score = 0.45 × RS + 0.30 × VWM - 0.10 × accel + 0.10 × mom

structured_score = mean(volume_price_alignment, closing_consistency, momentum_health,
                        dollar_volume_quality, trend_stability, fund_flow_momentum)

blended = 0.6 × base_score + 0.4 × structured_score

score = blended + confirmation × 0.12 - risk_penalty
```

**Base 因子（IC 验证）：**
- `RS` (relative_strength_vs_equal_weight)：IC=+0.043，最强因子
- `VWM` (volume_weighted_momentum)：IC=+0.028，量价复合
- `accel` (five_day_acceleration)：IC=-0.025，反转使用（权重从 -0.15 降至 -0.10）
- `mom` (prior_20d_momentum)：IC=+0.024

**Structured 因子（xiaogu 模式）：**
- `volume_price_alignment`：量价趋势一致性
- `closing_consistency`：收盘强度一致性
- `momentum_health`：加速度健康度（阈值收紧：> -0.03 满分，-0.03~-0.10 六折，-0.10~-0.18 二折）
- `dollar_volume_quality`：成交额质量（机构参与度）
- `trend_stability`：趋势稳定性
- `fund_flow_momentum`：东财 f178 主力资金流向（近 5 日净流入）

**风险惩罚与硬拒规则（regime 动态化 + 反转覆盖）：**
- 减速硬拒：accel ≤ regime阈值 且无反转信号 → `MOMENTUM_EXHAUSTION_HARD_BLOCK`
  - risk_on: -0.22, active: -0.22, balanced: -0.18, risk_off: -0.12
- 反转覆盖：accel ≤ 阈值 但日内涨 > 0.5% → `REVERSAL_OVERRIDE`（允许出票）
- 日内暴跌惩罚：日内跌 > 3% → risk_penalty +0.25；跌 > 1% → +0.10
- accel 极端惩罚：accel < 阈值×1.5 → risk_penalty +0.12
- 放量滞涨：volume > regime阈值 且 closing < regime阈值 且 accel < regime阈值 且日内不涨 → `BLOWOFF_RISK_HARD_BLOCK`
- 低确认：confirmation_score < 0.4 且日内不涨 → `LOW_CONFIRMATION_BLOCK`

**历史收益验证（截至 2026-06-23）：**
- 06-18 出票 3d：胜率 100%，均收益 +6.09%
- 06-19 出票 3d：胜率 75%，均收益 +2.58%
- 06-21 出票 1d：胜率 67%，均收益 -0.06%

## xiaomei-us-stock-research output guardrails

- 允许的输出类：`RESEARCH_ONLY`、`NEED_MORE_EVIDENCE`、`NEED_REPLAY`、`BLOCKED_BY_RISK`、`CANDIDATE_FOR_PAPER_REVIEW`
- 禁止的输出标签：`BUY`、`SELL`、`ORDER`
- 研究 skill 只做方法论整合，不引入 broker / execution / ledger。
