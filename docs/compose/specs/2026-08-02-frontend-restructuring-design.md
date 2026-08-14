# Xiaomei 前端重构设计规格

## [S1] 问题陈述

当前 xiaomei 前端存在以下问题：
1. 导航结构不清晰：4个英文导航项（Dashboard, Positions, Tickets, Journal）无实际路由功能
2. 分类标签使用英文（CANDIDATE_FOR_PAPER_REVIEW, MARKET_WATCHLIST_NEEDS_EVIDENCE）
3. 风险判定使用英文（CLEAN, WATCH, ELEVATED）
4. 评分详情缺失：仅显示综合分、市场分、催化分，无详细分解
5. 缺少"唯一标的"推荐功能（类似A股的状元机制）
6. 中英文混杂，无统一中文界面

## [S2] 解决方案概述

重构前端为3个核心模块，全中文界面，增加详细评分分析：

### 新导航结构
1. **模拟交易**（原组合总览）- 纸面交易组合概览
2. **AI出票** - AI信号分析与出票   - 出票概览（子页面）   - AI信号（子页面，独立模块）
3. **出票记录** - 历史出票记录与个股详情

### 核心改动
- 分类标签：候选 → 状元/探花/榜眼（Top 3排名）
- 风险判定：CLEAN → 获利机会高，WATCH → 获利机会中，ELEVATED → 获利机会低
- 评分评解：详细市场评分、催化因素、技术信号分解
- 数据来源标注：明确标注数据来源（Pipeline、yfinance、东财等）

## [S3] 模块详细设计

### 3.1 模拟交易模块

**功能**：
- 纸面交易组合概览（总权益、持仓数、现金、胜率）
- 当前持仓列表（标的、方向、入场价、现价、变动、盈亏、止损、止盈）
- 点击持仓展开交易理由（市场信号、催化剂、情绪/分类、风险评估）
- 前瞻跟踪（1d/3d/5d/10d收益）

**数据来源**：
- 持仓数据：`/api/positions` → `research/engine-state.json`
- 交易理由：`trade_journal` 表
- 前瞻跟踪：`forward_tracking` 表

### 3.2 AI出票模块

#### 3.2.1 出票概览（子页面）
**功能**：
- 今日出票列表（标的、综合分、市场分、催化分、分类、风险）
- **唯一标的推荐**：从今日出票中选出最高获利机会的标的
- 分类标签改为：
  - 第1名 → 状元 🥇
  - 第2名 → 探花 🥈
  - 第3名 → 榜眼 🥉
  - 其他 → 候选

**数据来源**：
- 出票数据：`/picks?limit=20`
- 排名逻辑：按 `ticket_score` 降序排列

#### 3.2.2 AI信号（子页面，独立模块）
**功能**：
- 展示原始AI信号数据（信号键、信号值、交易日期）
- 信号有效性分析（胜率、平均收益、IC评分）
- 因子权重展示（当前权重配置）

**数据来源**：
- 信号数据：`/signals`
- 信号有效性：`/signals/effectiveness`
- 因子权重：`scoring_config` 表

### 3.3 出票记录模块

**功能**：
- 历史出票记录列表（支持日期筛选）
- 个股详情页面（点击标的展开）

#### 个股详情组件：
1. **基本信息**
   - 标的代码、名称
   - 出票日期、分类（状元/探花/榜眼/候选）
   - 风险判定（获利机会高/中/低）

2. **评分评解**（详细分解）
   - 综合评分（ticket_score）
   - 市场评分（market_score）- 含技术信号分解
   - 催化剂评分（catalyst_score）- 含叙事/业务证据
   - 机构资金流评分（institutional_flow_score）
   - 社交情绪评分（social_sentiment_score）
   - 突破评分（breakout_score）
   - 风险惩罚（risk_penalty）
   - 确认评分（confirmation_score）

3. **技术信号**
   - 20日动量、5日加速、相对强度
   - 成交量确认、RSI(14)
   - 突破评分、反转质量

4. **催化剂分析**
   - 叙事证据状态与理由
   - 业务证据状态与理由
   - 催化剂摘要

5. **风险评估**
   - 风险判定：获利机会高/中/低
   - 风险摘要（risk_summary）
   - 质量判定（quality_verdict）
   - 质量摘要（quality_summary）

6. **前瞻跟踪**
   - 1d/3d/5d/10d 收益
   - 盈亏分析

7. **数据来源标注**
   - Pipeline 出票数据
   - yfinance 实时行情
   - 东财历史K线
   - 因子快照（factor_snapshots）

**数据来源**：
- 出票记录：`/picks`
- 个股详情：`/explain/{date}/{symbol}`
- 前瞻跟踪：`/returns`
- 因子快照：`factor_snapshots` 表

## [S4] 分类标签映射

| 原始值 | 中文显示 | 样式 |
|--------|----------|------|
| 票数排名第1 | 状元 🥇 | 金色背景 |
| 票数排名第2 | 探花 🥈 | 银色背景 |
| 票数排名第3 | 榜眼 🥉 | 铜色背景 |
| CANDIDATE_FOR_PAPER_REVIEW（其他） | 候选 | 绿色背景 |
| MARKET_WATCHLIST_NEEDS_EVIDENCE | 观察 | 紫色背景 |

## [S5] 风险判定映射

| 原始值 | 中文显示 | 样式 |
|--------|----------|------|
| CLEAN | 获利机会高 | 绿色 |
| WATCH | 获利机会中 | 黄色 |
| ELEVATED | 获利机会低 | 红色 |

## [S6] 数据来源标注

在个股详情页中，每个数据组件需标注详细来源信息：

### 来源信息结构
```
{
  "source": "数据提供方名称",
  "source_url": "数据来源链接（如有）",
  "published_at": "数据发布时间",
  "author": "数据发布者/生成者",
  "fetched_at": "数据获取时间"
}
```

### 各组件来源标注

1. **出票数据**（Pipeline生成）
   - 来源：`profit-ticket-pipeline`
   - 发布时间：`tickets.output_date`
   - 生成者：`xiaomei AI Pipeline`
   - 获取时间：`tickets.created_at`

2. **实时行情**（价格数据）
   - 来源：`yfinance`
   - 发布时间：实时获取
   - 数据提供方：`Yahoo Finance`
   - 获取时间：API调用时间

3. **历史K线**（技术指标计算）
   - 来源：`东财 + akshare`
   - 发布时间：`daily_klines.trade_date`
   - 数据提供方：`东方财富`
   - 获取时间：`daily_klines.fetched_at`

4. **因子数据**（因子权重、IC评分）
   - 来源：`factor_snapshots` 表
   - 发布时间：`factor_snapshots.trade_date`
   - 生成者：`weight_optimizer.py`
   - 获取时间：`factor_snapshots.created_at`

5. **交易理由**（AI生成）
   - 来源：`trade_journal` 表
   - 发布时间：`trade_journal.trade_date`
   - 生成者：`trade_journal.py`（AI推理）
   - 获取时间：记录创建时间

6. **信号有效性**（统计分析）
   - 来源：`signal_effectiveness` 表
   - 发布时间：`signal_effectiveness.analysis_date`
   - 生成者：`signal_effectiveness.py`
   - 获取时间：分析运行时间

### 界面展示方式
- 在个股详情页底部添加"数据来源"卡片
- 每个数据组件旁显示来源图标（悬停显示详情）
- 来源信息包含：数据提供方、发布时间、获取时间

## [S7] 技术实现方案

### 前端文件选择
- **主文件**：`/workspace/hermes-workspaces/xiaomei/public/index.html`（FastAPI服务）
- **原因**：FastAPI是主API服务，`public/index.html` 是主要前端入口

### 实现方式
- 保持单文件SPA架构（无框架依赖）
- 使用JavaScript实现页面路由（hash路由）
- 所有CSS内联，保持现有粉紫色主题
- 所有文本使用中文

### API调用
- 现有API端点已足够支持所有功能
- 新增：`/explain/{date}/{symbol}` 用于个股详情
- 新增：`/signals/effectiveness` 用于信号分析

## [S8] 验收标准

1. 导航栏显示3个中文模块：模拟交易、AI出票、出票记录
2. AI出票下有2个子页面：出票概览、AI信号
3. 出票概览显示今日出票，分类标签为状元/探花/榜眼/候选
4. 出票概览有"今日状元"推荐区域
5. 出票记录支持日期筛选，点击标的展开详情
6. 个股详情包含7个组件：基本信息、评分评解、技术信号、催化剂分析、风险评估、前瞻跟踪、数据来源
7. 风险判定显示为中文：获利机会高/中/低
8. 所有数据来源有明确标注
9. 界面全中文，无英文混杂
