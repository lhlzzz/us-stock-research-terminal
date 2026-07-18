# xiaomei 全生命周期闭环系统设计

> **For agentic workers:** REQUIRED SUB-SKILL: Use compose:subagent to implement this plan task-by-task.

**Goal:** 将 xiaomei 从"美股选股脚本"升级为"美股量化研究平台"，实现可复现、可迭代、可持续优化的完整生命周期闭环。

**Architecture:** 四层 Loop 架构（Daily → Research → Reflection → Meta），所有状态持久化到 PostgreSQL，所有改动经过 Quant Gate 验证。

**Tech Stack:** PostgreSQL, FastAPI, Celery, APScheduler, Parquet, EastMoney API, akshare

---

## [S1] Daily Loop（每日闭环）

每日自动执行的完整流程：

```
Market Data（东财实时行情 + 资金流）
    ↓
Factor Snapshot（技术指标 + 结构化信号）
    ↓
Scoring（评分 + 排序）
    ↓
Quant Gate（量化验证）
    ↓
Ticket（出票 → DB）
    ↓
Forward Tracking（前瞻跟踪）
    ↓
Backfill（到期收益回填）
    ↓
Lifecycle Scoreboard（记分板更新）
    ↓
Signal Effectiveness（信号有效性分析）
```

所有步骤都有数据库记录，任意一天可完整复现。

## [S2] Research Loop（研究闭环）

拆分为三个子循环：

### Factor Research
- 哪些因子贡献最大？（RSI、资金流、动量、成交量等）
- 因子重要性排序
- 新因子发现与评估

### Scoring Research
- 权重自动优化
- 信号有效性分析
- Scoring 公式迭代

### Strategy Research
- 哪些 Gate 应该增加？
- 哪些 Rule 应该删除？
- 策略整体表现评估

## [S3] Quant Gate（量化验证门）

四级验证状态：

| 状态 | 含义 | 出票决策 |
|---|---|---|
| PASS | 全部指标达标 | 可以出票 |
| SOFT PASS | 风险略高 | 人工确认后出票 |
| WATCH | 边界情况 | 继续观察，不出票 |
| FAIL | 指标不达标 | 禁止出票 |

验证指标：
- 胜率 > 50%
- 平均收益 > 0%
- 盈亏比 > 1.5
- 最大回撤 < 20%
- 信号有效性 > 20% high return rate

## [S4] Reflection Loop（反思闭环）

每轮完成后执行：

```
Failure Classification（失败分类）
    ↓
Root Cause（根因分析）
    ↓
Improvement Proposal（改进提案）
    ↓
Implementation Candidate（实施候选）
```

示例：
```
出票失败 → 为什么？→ 资金流假突破 → 是否增加 Volume Gate？→ 生成候选
```

## [S5] Meta Loop（元循环）

检查整个系统是否退化：

每日统计：
- 出票数量
- 平均收益
- 胜率
- 平均 Alpha
- Gate 通过率
- 因子覆盖率
- 缺失数据率
- Pipeline 成功率

退化检测：过去 30 天胜率下降 > 10% → 自动生成 Research Task

## [S6] 实施优先级

### Phase 1（最高优先）
Daily Loop 稳定运行：Market Scan → Factor → Ticket → Tracking → Backfill

### Phase 2
Quant Gate 完善：Walk-forward 验证 + Gate 分级 + 研究记录

### Phase 3
Research Loop：因子分析 + 权重优化 + 策略迭代

### Phase 4
自动化：Scheduler + Worker + 监控 + 告警 + Dashboard
