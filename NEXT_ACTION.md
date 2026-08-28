# NEXT_ACTION

**已完成（2026-08-28，Capital Behavior V2 研究并行升级）：**
- 完成 V2 gap audit，并将 Capital Brain 升级为公开 OHLCV 的确定性行为推演链：卖方活动/实际与预期伤害/吸收效率与持续性/失败、方向性价格响应效率、control asymmetry/collapse、动态 state transition、state aging、竞争 intent/path 概率、capital strength/quality、distribution/trap 风险。
- 完成完整 V2 持久化：扩展现有 `capital_daily_snapshot`、`capital_evidence`、`capital_state_history`、`capital_intent`、`capital_path_prediction`、`capital_prediction_outcome` 及 ticket/tracking 字段；迁移对旧表幂等兼容。
- API 已支持 `/api/capital/{symbol}`、`history`、`transitions`、`path`、`scoreboard` 的完整 V2 对象；盘中 paper context 同时读取 daily state/intent/path/quality/distribution/trap。
- 回测增加 state-specific、关键 transition、top 5/10/20% momentum 和 calibration 输出；零 fixed-chain 时保持 `UNVALIDATED_NO_FIXED_CHAIN`，不修改权重。
- 新增 9 个 V2 专项测试文件；最终验证：`77 passed`、compileall、shell syntax、diff check、幂等 migration、API contract、outcome persistence transaction、lifecycle、scheduler dry-run、intraday paper outside-session smoke 均通过。
- `actual_intent_proxy` 已配套持久化 `actual_intent_semantic=POST_HOC_INFERRED_PROXY`，明确它是事后公开数据推断代理，不是机构事实；事务 smoke 已验证后回滚，未污染业务数据。
- 生产保护继续固定为 `RESEARCH_ONLY`、`KEEP_OBSERVABLE_FOOTPRINT_RANKING_UNCHANGED`、`NO_PRODUCTION_WEIGHT_CHANGE`；Capital 模型仍无生产资格。

**下一步（样本积累后）：**
- 继续生成独立版本化 V2 ticket/tracking/outcome 链，待 fixed-chain gate 满足后执行 train/validate/walk-forward/out-of-sample/A/B；在此之前不得解释 accuracy、calibration 或经济结果为模型能力。

**已验证（2026-08-28，Capital Behavior Engine 研究并行）：**
- 新增 `capital_behavior_v1`：仅使用公开 OHLCV/实时行情，严格区分 `OBSERVED`、`DERIVED`、`INFERRED`、`PREDICTED`；不声明机构、主力或隐藏参与者身份。
- 新的 Capital Brain 以并行元数据接入 `observable_footprint_v1` 日研究、票据、T+1/T+3/T+5 跟踪、生命周期、盘中纸面策略、API 与失败复盘；旧的候选排序仍为 `(ticket_score, market_score, volume_confirmation_ratio)`，未被 Capital 分数改变。
- PostgreSQL 已应用幂等迁移：`capital_daily_snapshot`、`capital_evidence`、`capital_state_history`、`capital_intent`、`capital_path_prediction`、`capital_prediction_outcome`，并扩展票据和 tracking 资本字段。
- 验证：`pytest -q tests` 为 **66 passed**；`python3 -m compileall -q scripts`、`python3 scripts/daily_scheduler.py --dry-run`、shell syntax 与 Capital API route contract 均通过。
- 资本 A/B、feature optimizer、walk-forward 均返回 `UNVALIDATED_NO_FIXED_CHAIN`，没有独立版本化完成样本；生产动作固定为 `KEEP_OBSERVABLE_FOOTPRINT_RANKING_UNCHANGED` / `NO_PRODUCTION_WEIGHT_CHANGE`。Capital Model **不具备 production-ready 状态**。

**已验证（2026-08-18，盘中纸面模拟继续）：**
- `scripts/realtime_runner.py` 已在纽约常规交易时段运行两轮：手动 `run_id=1`（北京时间 21:47）和 scheduler 自动 `run_id=2`（北京时间 21:55）；两轮均使用已完成的研究运行 `144` 作为上下文。
- `intraday_paper_v1` 每轮对 15 个候选写入多头与短模型审计决策；可用行情未达到多头入场门槛，短模型因没有可验证借券来源而拒绝。当前纸面持仓、订单、成交均为 `0`，没有 broker 或外部订单调用。
- 现有 scheduler 已注册 `Intraday Paper Strategy`，北京时区每 5 分钟触发，runner 自行执行纽约时段、节假日和行情新鲜度门控；PostgreSQL、Redis、scheduler 健康检查通过。
- 验证：`pytest -q tests` 为 **50 passed**，`python3 -m compileall -q scripts`、`bash -n scripts/start_services.sh scripts/daily_pipeline.sh` 和 API 盘中概览 smoke 通过。

**当前待办：**
1. **策略质量验证**：`observable_footprint_v1` 当前没有已版本化的完成 1d 样本，权重优化、信号分析和自进化均会返回 `UNVALIDATED_NO_FIXED_CHAIN` / `NOT_READY` 并保留现有权重；必须积累独立样本后再判断 1d/3d/5d/10d 结果，不能把已有纸面收益当作实盘能力或策略证明。
2. **历史版本边界**：446 张历史票缺少可唯一推导的 `research_run_id`，其新闻、资金代理和情绪快照均保持历史缺失；不得补造。
3. **数据源运行边界**：Yahoo Chart API 在 2026-08-15 的真实 smoke 返回 403，EastMoney 历史 K 线 API 失败；CloakBrowser 可正常加载东财详情页，但日 K 仅以图表图片呈现、没有可验证的结构化 OHLCV 行。`DataProvider` 记录 Scrapy 与浏览器来源证据后回退到 Akshare。仅在来源、时间戳和 fallback 链均已保存时使用行情。

**已验证（2026-08-15，生命周期闭环加固）：**
- scheduler 现在自行维护并校验 daemon PID 身份；`start_services.sh` 用 `setsid --fork` 启动后必须通过独立 liveness 检查，`--health` 同时检查 PostgreSQL、Redis、日链、磁盘与 daemon。真实进程在独立检查中存活，Financial OS overview smoke 通过
- 所有可执行 Python/Shell 脚本不再嵌入 PostgreSQL 密码或 `PGPASSWORD`；统一从环境或仓库 `.env` 读取 `DATABASE_URL`
- 未来 pipeline 保存改为 `running` research run + 单事务派生记录；全部 flush 成功后才标记 `done` 和 `finished_at`，任一异常会 rollback 派生数据并把 run 标记为 `failed`
- 权重优化、信号分析和自进化只读取 `observable_footprint_v1`、`VERSIONED`、已完成的研究运行；排除 446 张无版本历史票和 `RECONSTRUCTED_FROM_DATABASE` 运行。样本/收益/下行/因子覆盖 gate 不满足时只记录决策，不改写现有权重
- 验证：`python3 -m pytest -q tests` 为 44 passed；`python3 -m compileall -q scripts`、`bash -n scripts/start_services.sh scripts/daily_pipeline.sh`、真实 optimizer/signal/self-evolve gate、scheduler health、PostgreSQL 版本样本查询和 Financial OS overview smoke 均通过

**已验证（2026-08-15，行情、策略与知识资产重构）：**
- `scripts/data_provider.py` 现在是行情 API 的唯一 transport owner：Scrapy 长生命周期 bridge 提供请求去重、超时、重试、域名并发、响应 hash 和 audit；Yahoo Chart API 为有界可选 K 线源，限流/不可用状态不会被掩盖，EastMoney 与 Akshare fallback 会写入 `source_attempts`
- 东财 K 线新增受限 CloakBrowser 页面来源：仅在东财历史 API 失败后尝试，串行且最多 3 次；只接受完整日期、开高低收和成交量行，记录页面 URL、内容 hash、标题、抓取时间、schema 版本和状态。2026-08-15 NVDA 页面加载成功但没有结构化日线，状态为 `empty`，随后由 Akshare 返回截至 2026-08-14 的 10 根日线
- 历史 K 线、出票实时行情、研究面板、回填任务和 K 线任务均已收口到 `DataProvider`；没有新增 broker、execution 或 live-trade 路径
- 出票策略版本为 `observable_footprint_v1`：公开价格成交量足迹、流动性、相对强弱、突破接受度、收盘强度、市场宽度/涨跌家数、独立催化证据和风险惩罚；不再把 EastMoney 字段描述为主力资金/机构流，缺失项不会使用 `0.5` 中性分数
- 公共催化证据缺失时只能产生 `MARKET_WATCHLIST_NEEDS_EVIDENCE`，不能进入 `CANDIDATE_FOR_PAPER_REVIEW`；`social_sentiment` 保持 `UNAVAILABLE_NO_VALIDATED_CORPUS`
- `daily_candidates` 现保存足迹因子贡献、因子覆盖率、市场参与度、来源层、排名公式与版本；非有限数值规范化为 JSON `null`
- 2026-08-15 的知识资产 JSON 已扩展为研究 run/commit/config、来源层、因子与排名快照、全周期 tracking、唯一 `research_trade_trace` 归因和可复用 case text；LITE、NBIS、NTAP 已写入现有 `pick_case_embeddings`，使用结构化 384 维 fallback
- 验证：本地 Scrapy fixture、Yahoo rate-limit fallback 测试、策略门槛测试通过；`python3 -m pytest -q tests` 为 32 passed，`python3 -m compileall -q scripts`、`bash -n scripts/daily_pipeline.sh`、数据库向量查询和真实 NVDA 行情 smoke 通过

**已验证（2026-08-15，研究证据与前端收口）：**
- 新研究运行会写入 Git 提交、评分配置快照、数据截至时间和完整候选池；每张新票通过 `research_run_id` 连接到唯一研究运行
- 2026-08-15 的 NBIS、NTAP、LITE 三张历史票已可唯一重建到 `37693ec16f8ebbffdd29d758fa48ec458023b93b`；每张票均关联 3 个收益周期和 4 条 `research_trade_trace` 复盘记录
- 当前与未来候选分别保存新闻、公开价格成交量/外部资金代理、社会情绪可用性、因子快照和排名依据；资金代理不再称为验证过的机构资金，社会情绪没有验证数据源时明确为不可用
- Financial OS 的 Xiaomei overview 现在直接读取 PostgreSQL：票、候选、因子、回填收益、复盘链、纸面持仓、日志、研究版本和知识资产；`/api/simulation/xiaomei` 返回 410，移除文件态模拟入口
- 前端全部账户缺口使用“未记录/未入库”，不再默认现金、权益、回撤或收益；研究、情报、记忆、系统、策略和风险页面都绑定数据库契约或明确不可用状态
- 多头只保留研究候选和纸面复盘；空头为 `UNAVAILABLE_NO_VALIDATED_SHORT_MODEL`，未加入空头候选、券商、执行或实盘交易路径
- 验证：`python3 -m pytest -q tests` 28 passed，`python3 -m compileall -q scripts`、`bash -n scripts/daily_pipeline.sh`、Financial OS `npm run lint`、`npm run build`、PostgreSQL/API smoke 通过

**已验证（2026-08-14）：**
- 调度器已恢复为单实例运行：05:00 北京时间按前一日美股交易日判断，并改为周二至周六执行，覆盖周五美股收盘后的周六早晨闭环；启动脚本会幂等拉起调度器
- 系统边界为美股研究 + 纸面模拟，`paperOnly=true`，没有券商执行链，不能称为已进入实盘
- 修复出票→tracking 的 `ticket_id` 链路：1125/1141 条 tracking 已关联，16 条明确标记未解析
- 新增 `research_trade_trace` 唯一复盘投影和 `/api/trade-traces`，贯通出票、周期收益、纸面记录、交易日志和归因；无 ticket 的记录统一显式标记未解析
- 已归档并删除 22 条无 ticket 来源的活动记录（16 tracking、2 纸面、4 日志）；三张活动表的 `ticket_id` 已强制非空，活动复盘链无未解析记录
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
