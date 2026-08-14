# RESEARCH Index (2026-06-11)

## 研究边界

- Market data: EastMoney US realtime/delayed quote + kline provider（`scripts/eastmoney_us.py`，当前唯一美股行情源）。
- Social/research source: `last30days`，仅 public-source，用于 narrative/context 验证，不作行情价格源。
- Crypto：主责已迁至 `xiaobi`（2026-07-25）。xiaomei 只管美股；不再扩展加密主链路。
- 禁止输出交易意图词：`BUY` / `SELL` / `ORDER`。
- 允许产物包括 replay、forward tracking、pipeline summary / metrics / csv。

## 当前有效结论

- `historical_replay_baseline.py` 的 6 票 mega-cap universe 已确认是 `toy / smoke` 结果，不能视为可复用主线出票。
- `universe-expansion-replay` 已是更高置信候选研究方向，`prior_20d_momentum_only` 在 top1/top3/top5 显著稳定优于原 6 票 smoke 设定。
- `profit-ticket` pipeline 当前输出主类为 `MARKET_WATCHLIST_NEEDS_EVIDENCE`（当前票池无 company-specific evidence 强信号）。
- `last30days` 的 company-specific 查询在当前环境可能返回 0 ranked items，不降 evidence gate，保持 `不降证据门`；行情源不回退 legacy market-data source。

## Manual Evidence Completion Pass（2026-06-12）

范围：只读 public-source evidence completion；不改 generated candidates / metrics / forward-tracking artifact；不接 broker / execution / ledger / live-trade；不输出交易动作。

门槛：company-specific、last 30 days、业务/盈利/订单/指引/风险相关度 `>= 0.6` 才允许进入 paper review 复核；泛行业新闻继续留在 `MARKET_WATCHLIST_NEEDS_EVIDENCE`；出现明确负面风险则保持 watch 或降级。

|symbol|manual relevance|evidence status|manual gate note|
|---|---:|---|---|
|LRCX|0.68|company-specific but partly analyst/news-flow driven|可进入 paper review 复核，但需标记 `WATCH`：AI/WFE 需求与工具 AI 化证据相关；未见明确披露的大额新订单，且 `5d_accel=-0.1466` 接近 momentum exhaustion guard。|
|COO|0.78|company-specific official earnings/guidance|证据相关度达标，但不建议直接抬升：Q2 业绩与 FY2026 指引有效；同时存在 CooperSurgical embryo culture media recall 相关重大诉讼费用 / settlement 风险，先保持 watch 或降级复核。|
|SJM|0.86|company-specific official earnings/outlook|可进入 paper review 复核：FY2026 Q4 / FY2027 outlook、coffee cost relief、Uncrustables / Hostess 主题均为公司级 catalyst；但 FY2027 sales decline outlook 与 pipeline quality=`WEAK` 必须作为 bear-case。|

Sources:
- LRCX：Investing.com / Cantor Fitzgerald（2026-06-10）称 Lam Research price target 上调，理由为 AI-driven WFE、foundry/logic、advanced packaging、HBM、NAND conversion；Reuters via Investing.com（2026-05-21）称 Lam 正在为 chipmaking tools 增加 sensing/AI 能力并推进 Arizona / Fremont 扩张。
- COO：CooperCompanies official Q2 FY2026 release（2026-06-04）披露 revenue `$1.082B`、organic growth `5%`、non-GAAP diluted EPS `1.21`，并更新 FY2026 guidance；同次披露 CooperSurgical 召回相关 product litigation net pre-tax charge `$271.6M`。
- SJM：J.M. Smucker official FY2026 Q4 / FY2027 outlook（2026-06-09）披露 Q4 net sales `$2.27B`、adjusted EPS `$2.77`、FY2027 adjusted EPS `$9.75-$10.25`、free cash flow about `$1.0B`；Reuters（2026-06-09）报道 coffee cost relief / upbeat annual profit 与盘中股价反应。

## Artifact Index

- `research/universe-expansion-replay/`
- `research/profit-ticket-pipeline/`
- `research/profit-ticket-pipeline-opening/`
- historical legacy-source smoke artifact directory（历史证据归档，非当前行情源）
- `research/replay-social-feature-validation/`

## 去噪与维护约束

- 保留 business evidence 与历史实验产物，不做大规模删除，避免丢失研究链路。
- 允许噪音清理范围：
  - `workspaces/xiaomei/scripts/__pycache__/`
  - `workspaces/xiaomei/research/last30days-smoke/nvda-ai-gpu-demand-raw.md`
  - `workspaces/xiaomei/research/replay-social-feature-validation/nvidia-raw-nvda.md`

## 当前运行入口快照

- `historical_replay_baseline.py`
- `us_profit_ticket_pipeline.py`
- 统一命令风格：通过 `--help` 检查参数、以 artifact path 追溯结果。
- 两条 pipeline 路径共享同一 `research-only` 边界与 artifact 约定。

---

## 跨平台 Day Trading / 当天买卖升级研究（2026-06-15）

### 数据来源

- Reddit r/Daytrading（309K 成员，top posts this month）
- Reddit r/algotrading（1.9K weekly contributions）
- YouTube（AI trading bot / day trading strategy 2026 搜索结果）
- Hacker News / Polymarket（补充验证）

### 核心发现

**1. 风险管理 > 策略本身（Reddit r/Daytrading 高票帖共识）**

- [Warm_Sock7188](https://www.reddit.com/r/Daytrading/comments/1tr7bl7/) 的 589 票帖子（16 days ago）：全职日内期货交易员，胜率仅 49%，但通过严格风控实现持续盈利。
  - 关键数据：5 micros 起手，$250 止损，$500 盈利后开始 trailing，最大持仓 20 micros。
  - 核心观点："Most traders focus on strategies not risk management. Most traders focus on indicators not emotions. Most traders focus on winning not losing."
  - 推荐书：《The Best Loser Wins》、Mark Douglas 的分布思维。
- [cofca5h](https://www.reddit.com/r/Daytrading/comments/1tr7bl7/comment/oon0yg5/) 评论："learn to lose well" 被严重低估。position sizing 和 risk 才是真正的 leak。
- [Suitable_Acadia_190](https://www.reddit.com/r/Daytrading/comments/1tr7bl7/comment/oooz359/)：49% win rate + full time + futures = "The math is doing something most traders never let it do."
- [Haunting_Soup_2696](https://www.reddit.com/r/Daytrading/comments/1tr7bl7/comment/oow7syq/)："If your defense is A/A-, your offense can be B-/C+ and you will make enormous amounts of money."

**2. AI 交易系统正在成为主流工具（YouTube 热门视频）**

- [Humbled Trader](https://www.youtube.com/watch?v=IqvnryFzZD4) - "I Built an AI Trading System With Claude + TradingView"（224K views, 8 days ago）
  - 完整工作流：Claude Code 连接 TradingView → Premarket Gap Scanner → Strategy Scanner → Pine Script 回测 → Telegram Alerts → Interactive Brokers API 自动化
  - 11 章节覆盖：AI chart copilot、TradingView Remix AI、IB API automation
- [Neeraj joshi](https://www.youtube.com/watch?v=XdQToWl-UHA) - "How to Trade Using AI TRADING BOT Without Coding Using Codex & MetaTrader 5"（83K views, 5 days ago）
  - 零代码 AI 交易 bot 方案
- [Fx Prashant Bajpai](https://www.youtube.com/watch?v=B2AcrtulKu4) - "I Turned Claude AI Into a 24/7 Trader"（3.1K views, 1 day ago）
  - TradingView + AI Strategy 实战
- [Bryan Soler](https://www.youtube.com/watch?v=ETb8I7x4qXA) - "How to Build a Claude AI Agent for Day Trading Crypto"（7.2K views, 2 days ago）
  - Claude AI agent 做加密货币日内交易

**3. 算法交易社区的实战验证（Reddit r/algotrading）**

- [Enough-Ad-5600](https://www.reddit.com/r/algotrading/comments/1tv8m1z/) - "It's finally working!"（376 票, 189 comments, 12 days ago）- 算法策略终于跑通
- [jtm_ind](https://www.reddit.com/r/algotrading/comments/1tpi8o3/) - "First day testing out my breadth algo"（252 票, 93 comments, 18 days ago）- 市场宽度算法首次实测

### 对 xiaomei 的升级启示

**Gap 1: 缺少实时风控模块**

xiaomei 当前只有 scoring + evidence gate + forward tracking，没有：
- 实时止损/止盈逻辑
- 仓位 sizing 系统
- trailing stop 机制
- 每日最大亏损限制
- 连续亏损后的冷却期

**Gap 2: 缺少 intraday 数据粒度**

当前 pipeline 用 historical kline（日线级别），但 day trading 需要：
- 1min / 5min / 15min 级别行情
- 盘前/盘后数据（premarket gap scanner）
- 成交量分布（volume profile）
- Level 2 order book 深度

**Gap 3: 缺少自动化执行层**

YouTube 上 224K views 的视频展示了完整链路：
Claude AI → TradingView Signal → Telegram Alert → IB API Execution
xiaomei 当前停在 "MARKET_WATCHLIST_NEEDS_EVIDENCE"，没有 alert → execution 的链路。

**Gap 4: 缺少回测验证的日内粒度**

当前 forward tracking 是 1d/3d/5d/10d，但 day trading 需要：
- 单日内的 entry/exit time stamp
- 持仓时间分布（holding period distribution）
- 滑点/手续费模拟
- 最大回撤（max drawdown）统计

**Gap 5: 缺少情绪/叙事的实时性**

last30days 是 30 天窗口，但 day trading 需要：
- 盘前催化剂扫描（earnings, FDA, macro events）
- 实时社交媒体情绪（X/Twitter 脉冲）
- 新闻情绪分数（sentiment score）作为 alpha factor

### 升级优先级建议

| 优先级 | 升级项 | 理由 |
|--------|--------|------|
| P0 | 风控模块（止损/止盈/仓位/冷却期） | Reddit 共识：风控是盈利的第一要素，49% 胜率也能盈利 |
| P1 | Intraday 数据接入（1min/5min kline） | Day trading 的基本粒度需求 |
| P1 | 盘前催化剂扫描（earnings calendar + news pulse） | YouTube 最热门方案的核心组件 |
| P2 | Alert → 通知链路（Telegram/Discord webhook） | 从 watchlist 到 execution 的桥梁 |
| P2 | 日内回测框架（entry/exit timestamp + 滑点模拟） | 验证策略真实收益 |
| P3 | 实时情绪因子（X/Twitter API + news sentiment） | 增强 evidence gate 的时效性 |
| P3 | Broker API 接入（paper → live 渐进） | 最终执行层，需 Claude gate 审批 |

