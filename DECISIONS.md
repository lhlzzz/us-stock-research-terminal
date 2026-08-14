# DECISIONS

## 2026-07-25 market ownership split (crypto → xiaobi)

- `xiaomei` **只管美股**；虚拟币 / 加密主责迁至独立智能体 **`xiaobi`**。
- 不再在 xiaomei 内扩展 crypto pipeline、交易所数据主链路或加密出票。
- 若美股研究需要风险偏好/流动性背景，可引用公开宏观叙述，但 **不得** 把 crypto 当作 xiaomei 业务产出。
- 启动加密工作请用：`xiaobi`。

## 2026-06-09 xiaomei research-only boundary

- `xiaomei` 是 **美股** research-only workspace（历史文档曾写「美股 + 加密」；自 2026-07-25 起加密归 `xiaobi`）。
- 美股行情源已迁移为 EastMoney US realtime/delayed quote + kline provider；禁止回退 legacy market-data source。
- `last30days` 只作为 public-source narrative / social research source，不作为行情源。
- 禁止接 broker feed / order / ledger / paper-trade / live-trade。
- 禁止输出 `BUY` / `SELL` / `ORDER`；研究输出只能是 classification / evidence / replay result。

## 2026-06-09 replay validation decisions

- 6 票 mega-cap universe（AAPL / MSFT / NVDA / META / AMZN / TSLA）只作为 smoke / toy universe，不代表真实出票能力。
- `XIAOMEI_HISTORICAL_REPLAY_BASELINE_V0`、`XIAOMEI_US_STOCK_REPLAY_FEATURE_VALIDATION_V0`、`XIAOMEI_US_STOCK_REPLAY_ROLLING_WINDOW_V0`、`XIAOMEI_US_STOCK_REPLAY_SOCIAL_FEATURE_VALIDATION_V0` 均已完成。
- 纯行情 replay 和 social overlay 都没有通过 rolling stability gate，最终分类保持 `REJECTED_FOR_INSTABILITY`。
- social feature 可以解释公开叙事，但不能升格为交易或执行信号。

## 2026-06-09 universe expansion decision

- 用户指出当前收益低且样本只有 6 个；该判断成立。
- 下一步转向 `XIAOMEI_US_STOCK_UNIVERSE_EXPANSION_REPLAY_V0`。
- 第一阶段 universe 扩到 Nasdaq 100 / S&P 500 级别，后续再视 EastMoney US 数据质量与 rate-limit 扩展更广 US listed universe。
- 正确出票验证方式：每个交易日只用当日以前可见数据打分，选 top1 / topK，再用 future forward return 验证。
- 禁止 lookahead / 事后挑最大赢家。
- 最低过滤方向：price floor、liquidity / median dollar volume、完整日线、current-listed universe 的 survivorship-bias disclaimer。
- 下一步仍是 research-only，不接 broker / order / ledger / live-trade。

## 2026-06-09 universe expansion replay result

- current-listed Nasdaq 100 / S&P 500 union replay is only meaningful after switching from full-universe intersection to per-date available-sample selection.
- after that switch, `prior_20d_momentum_only` became the stable best method across top1 / top3 / top5.
- `XIAOMEI_US_STOCK_UNIVERSE_EXPANSION_REPLAY_V0` is now a `CANDIDATE_FOR_PAPER_REVIEW`, not an execution path.
- keep the boundary at research-only; no broker / order / ledger / live-trade and no BUY / SELL output.

## 2026-06-11 workspace cleanup decision

- `_v0.py` files were promoted to canonical current implementations and renamed without compatibility wrappers:
  - `historical_replay_baseline.py`
  - `us_profit_ticket_pipeline.py`
- Runtime cache and duplicate undated raw smoke artifacts were removed.
- Research artifacts were preserved unless explicitly duplicated, because they are business evidence.
- `xiaomei` remains research-only: no broker / order / ledger / paper-trade / live-trade.

## 2026-06-18 scoring reweighting decision

- 300天因子分析发现：closing_strength_5d 和 five_day_acceleration 是反向因子（负IC），relative_strength_vs_equal_weight 是最强因子（IC=+0.043）。
- 新 scoring 公式：`score = 0.40×RS + 0.30×VWM - 0.15×accel + 0.15×mom`
- 回测验证：胜率 56.9%，avg +1.75%，PF=1.92（旧公式：47.5%，-0.08%，0.96）。
- 移除 closing_strength_5d 和 volume_confirmation_ratio 从 scoring weights（IC 太弱或反向）。
- five_day_acceleration 反转使用（负权重），因为减速票反而跑赢。
- 所有 regime（risk_on/active/balanced/risk_off）使用相同权重，差异仅在风控参数。
- 新增脚本：`historical_backtest.py`（300天历史回测）、`factor_analysis.py`（因子IC分析）。
- `xiaomei` remains research-only: no broker / order / ledger / paper-trade / live-trade.

## 2026-06-19 historical ticket audit and guardrail upgrade decision

- 历史票审查结论：近期 58 笔样本胜率 64%、avg +1.26%、PF 2.19；历史大样本 672 笔胜率 56.9%、avg +1.75%、PF 1.92；最大单笔亏损 -28.69% 说明尾部风险仍需更硬约束。
- 上涨因子：`relative_strength_vs_equal_weight` 最强，`volume_weighted_momentum` 第二；高 52w 位置和有效催化剂是加分项。
- 亏损因子：`five_day_acceleration` 极端负值是最核心信号；防御性板块和高波动成长股在当前动量策略中表现差。
- `xiaogu` 只读学习：第三层增强证据先做 observation / ranking-assist / shadow compare，不轻易升格为 official hard gate；必须在不降低 baseline 胜率/收益且样本足够的前提下才可晋级。
- 最终规则升级：`score = 0.45×RS + 0.30×VWM - 0.15×accel + 0.10×mom`；新增 `five_day_acceleration <= -0.18` 时从 `CANDIDATE_FOR_PAPER_REVIEW` 降为 `MARKET_WATCHLIST_NEEDS_EVIDENCE`；同步收紧 regime 默认止损。

## 2026-06-23 EastMoney-only data source and scoring improvement decision

- 移除 Yahoo/yfinance 作为 kline source。东财 push2delay kline 对美股所有 market code（105/106）返回 0 行，确认不可用。
- 唯一 kline 源改为 akshare（底层调用东财数据接口），保留 EastMoney US realtime quote 作为 enrichment。
- 参考 xiaogu 升级模式，新增三项改进：(1) blowoff risk detection（放量滞涨：volume_confirmation > 0.5 且 closing_strength < 0.4 且 accel < -0.10）；(2) confirmation score（RS/VWM/closing_strength/accel 四因子确认分，×0.1 加权）；(3) accel 硬拒阈值从 -0.18 收紧到 -0.12。
- 历史收益验证：06-18 胜率 100%/+3.45%，06-19 胜率 80%/+1.72%，06-21 胜率 40%/-1.18%。近期衰减明显，MRNA -6.50% 和 TECH -3.90% 是最大拖累。
- `xiaomei` remains research-only: no broker / order / ledger / paper-trade / live-trade。

## 2026-06-23 last30days fix and xiaogu scoring integration

- last30days 超时根因：build_supply_chain_map 调用 _run_last30days（120s timeout），串行查询所有源。
- 修复方案：build_supply_chain_map 改为本地 sector 映射逻辑（SECTOR_THEME_MAP），不再调用 last30days；_run_last30days 加 XIAOMEI_SKIP_LAST30DAYS 环境变量检查 + timeout 降至 20s；run_last30days_topic 加文件缓存。
- xiaogu blended scoring 集成：`blended = 0.6×base + 0.4×structured`，structured 6 维度（volume_price_alignment / closing_consistency / momentum_health / dollar_volume_quality / trend_stability / fund_flow_momentum）。
- EastMoney fund flow 信号：通过 f178 字段获取近 5 日主力净流入，转为 0-1 评分。
- 结果：pipeline 不再需要 --skip-last30days，2026-06-23-v2 出票 MRNA + GE 进入 PAPER_REVIEW（paper_review_count=2）。
- `xiaomei` remains research-only: no broker / order / ledger / paper-trade / live-trade。
