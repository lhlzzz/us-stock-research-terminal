# 优化建议报告

**日期:** 2026-07-01
**基于:** 性能分析报告 + 记分板数据 + 出票数据

---

## 1. 出票策略优化

### 1.1 分类优化

**当前状态:**
- MARKET_WATCHLIST_NEEDS_EVIDENCE: 21张, 平均得分 0.69
- CANDIDATE_FOR_PAPER_REVIEW: 10张, 平均得分 1.31

**优化建议:**

| 优化项 | 当前 | 建议 | 预期效果 |
|--------|------|------|----------|
| CANDIDATE_FOR_PAPER_REVIEW 阈值 | ticket_score > 1.0 | 提高到 ticket_score > 1.2 | 提高优质票据识别率 |
| MARKET_WATCHLIST 筛选 | 所有非 CANDIDATE | 增加 market_score > 0.8 的硬门槛 | 减少低质量追踪 |
| 出票数量 | 5张/天 | 调整为 3-8张，根据市场状态动态调整 | 避免强行出票 |

**具体实施:**
```python
# 当前分类逻辑 (us_profit_ticket_pipeline.py)
if ticket_score >= 1.0:
    category = "CANDIDATE_FOR_PAPER_REVIEW"
else:
    category = "MARKET_WATCHLIST_NEEDS_EVIDENCE"

# 建议调整
if ticket_score >= 1.2 and market_score >= 0.8:
    category = "CANDIDATE_FOR_PAPER_REVIEW"
elif ticket_score >= 0.7 and market_score >= 0.6:
    category = "MARKET_WATCHLIST_NEEDS_EVIDENCE"
else:
    category = "WATCHLIST_LOW_PRIORITY"  # 新增：低优先级，减少追踪资源
```

### 1.2 评分优化

**当前权重 (DEFAULT_WEIGHTS):**
- relative_strength_vs_equal_weight: 0.45 (最高)
- volume_weighted_momentum: 0.30
- prior_20d_momentum: 0.10
- five_day_acceleration: -0.10
- closing_strength_5d: 0.0
- volume_confirmation_ratio: 0.0

**优化建议:**

| 因子 | 当前权重 | 建议权重 | 调整理由 |
|------|----------|----------|----------|
| relative_strength_vs_equal_weight | 0.45 | 0.40 | 略降，避免过度集中 |
| volume_weighted_momentum | 0.30 | 0.35 | 提升，成交量确认更重要 |
| prior_20d_momentum | 0.10 | 0.15 | 提升，20日动量有预测力 |
| five_day_acceleration | -0.10 | -0.05 | 减弱负权重，避免过度惩罚 |
| closing_strength_5d | 0.0 | 0.10 | 新增权重，收盘强度是有效信号 |
| volume_confirmation_ratio | 0.0 | 0.05 | 新增权重，成交量确认辅助 |

**实施路径:**
1. 等待 `weight_optimizer.py` 积累足够数据（30+ completed tracking）
2. 运行 IC 分析获取因子有效性
3. 根据 IC 分数自动调整权重
4. 每周五自动运行优化

---

## 2. 风险控制优化

### 2.1 止损策略

**当前状态:**
- 固定止损: -2.4% (基于凯利公式)
- 止盈: +7.0%

**优化建议:**

| 策略 | 当前 | 建议 | 预期效果 |
|------|------|------|----------|
| 动态止损 | 固定 -2.4% | 根据波动率调整: ATR×2 | 适应不同股票波动特性 |
| 移动止盈 | 固定 +7.0% | 盈利后启用 trailing stop: 回撤 30% | 让利润奔跑 |
| 时间止损 | 无 | 3天未达预期收益 50% 则平仓 | 提高资金效率 |

**具体实施:**
```python
# 动态止损计算
def calculate_dynamic_stop_loss(atr_14d: float, current_price: float) -> float:
    """基于14日ATR计算动态止损"""
    stop_loss_pct = min(atr_14d * 2 / current_price, 0.05)  # 上限5%
    return current_price * (1 - stop_loss_pct)

# 移动止盈
def calculate_trailing_stop(entry_price: float, current_price: float, peak_price: float) -> float:
    """盈利后启用移动止盈"""
    if current_price > entry_price * 1.03:  # 盈利3%后启用
        drawdown = (peak_price - current_price) / peak_price
        if drawdown > 0.03:  # 回撤3%触发
            return True  # 触发止盈
    return False
```

### 2.2 仓位管理

**当前状态:**
- 凯利比例: 17.4% (统一)
- 无分散化检查

**优化建议:**

| 策略 | 当前 | 建议 | 预期效果 |
|------|------|------|----------|
| 基于评分的仓位 | 固定凯利% | ticket_score × 凯利% | 优质票获得更大仓位 |
| 行业分散 | 无限制 | 单行业最多 30% | 避免行业集中风险 |
| 相关性控制 | 无 | 相关系数 > 0.7 的票只保留 1 只 | 避免重复暴露 |
| 最大持仓 | 无上限 | 同时最多 10 只追踪 | 控制管理复杂度 |

**具体实施:**
```python
# 基于评分的仓位调整
def calculate_position_size(ticket_score: float, kelly_pct: float) -> float:
    """根据票据得分调整仓位"""
    score_multiplier = min(ticket_score / 1.0, 2.0)  # 上限2倍
    return kelly_pct * score_multiplier

# 行业分散化检查
MAX_SECTOR_EXPOSURE = 0.30  # 单行业最大30%
MAX_CORRELATION = 0.70  # 最大相关系数
MAX_POSITIONS = 10  # 最大持仓数
```

---

## 3. 时间周期优化

### 3.1 持仓周期

**当前表现:**

| 周期 | 数量 | 胜率 | 平均收益 |
|------|------|------|----------|
| 1天 | 14 | 85.7% | 2.65% |
| 3天 | 5 | 100% | 5.99% |
| 5天 | 14 | 0% | 0% (未完成) |
| 10天 | 14 | 0% | 0% (未完成) |

**优化建议:**

| 优化项 | 当前 | 建议 | 预期效果 |
|--------|------|------|----------|
| 默认跟踪周期 | 1天 | 3天 | 更高收益，更少交易成本 |
| 1天周期使用 | 主要 | 辅助，仅用于快速获利 | 减少频繁交易 |
| 3天周期使用 | 辅助 | 主要，作为标准持仓周期 | 利用100%胜率 |
| 5天+周期 | 测试中 | 保留，用于高质量票 | 捕捉更大趋势 |

**具体实施:**
```python
# 持仓周期分配策略
HORIZON_ALLOCATION = {
    "1d": 0.20,   # 20% 资金用于1天快速交易
    "3d": 0.50,   # 50% 资金用于3天标准持仓
    "5d": 0.20,   # 20% 资金用于5天中期持仓
    "10d": 0.10,  # 10% 资金用于10天长期持仓
}

# 根据票据质量调整周期
def assign_horizon(ticket_score: float) -> str:
    """根据票据得分分配跟踪周期"""
    if ticket_score >= 1.5:
        return "5d"  # 高质量票给更长周期
    elif ticket_score >= 1.0:
        return "3d"  # 标准周期
    else:
        return "1d"  # 低质量票给短周期
```

---

## 4. 股票选择优化

### 4.1 行业轮动

**当前表现:**

| 行业代表 | 平均收益 | 表现评价 |
|----------|----------|----------|
| 科技 (AXON, AMD, PANW) | 6.4% | 优异 |
| 消费 (EXPE, DLTR) | 5.0% | 良好 |
| 保险 (ALL, PGR) | 3.0% | 稳健 |
| 大科技 (NVDA, TSLA, GOOGL) | 1.5% | 一般 |
| 互联网 (META, AMZN) | -0.5% | 较差 |

**优化建议:**

| 策略 | 当前 | 建议 | 预期效果 |
|------|------|------|----------|
| 行业偏好 | 无 | 增加科技成长股权重 | 捕捉强势行业 |
| 行业黑名单 | 无 | 暂停 META, AMZN 出票 | 避免弱势行业 |
| 行业轮动 | 无 | 每周评估行业强度 | 动态调整行业配置 |

**具体实施:**
```python
# 行业偏好配置
SECTOR_PREFERENCE = {
    "Technology_Growth": 1.5,    # 科技成长股加分
    "Consumer_Cyclical": 1.2,    # 消费周期股加分
    "Insurance": 1.0,            # 保险股保持
    "Mega_Cap_Tech": 0.8,        # 大科技股减分
    "Internet_Services": 0.5,    # 互联网服务股大幅减分
}

# 行业黑名单
SECTOR_BLACKLIST = ["META", "AMZN"]  # 暂停出票
```

### 4.2 个股选择

**当前表现:**

| 股票 | 平均收益 | 交易次数 | 建议 |
|------|----------|----------|------|
| AXON | +9.26% | 2 | 增加关注 |
| AMD | +7.63% | 2 | 增加关注 |
| EXPE | +5.50% | 2 | 增加关注 |
| DLTR | +4.48% | 2 | 增加关注 |
| META | -0.43% | 2 | 暂停出票 |
| AMZN | -0.51% | 2 | 暂停出票 |

**优化建议:**

| 策略 | 当前 | 建议 | 预期效果 |
|------|------|------|----------|
| 优质股偏好 | 无 | 建立 top performers 列表 | 优先出票给历史表现好的股票 |
| 股票黑名单 | 无 | 暂停历史亏损股票 | 避免重复亏损 |
| 重复出票控制 | 无 | 同一股票 30 天内最多出票 3 次 | 避免过度交易 |

**具体实施:**
```python
# 优质股列表 (基于历史表现)
TOP_PERFORMERS = ["AXON", "AMD", "EXPE", "DLTR"]  # 平均收益 > 4%

# 股票黑名单
STOCK_BLACKLIST = ["META", "AMZN"]  # 历史亏损

# 重复出票控制
MAX_ISSUES_PER_STOCK = 3  # 30天内最多出票3次
```

---

## 5. 实施优先级

### P0: 立即实施 (本周)
1. ✅ 调整分类阈值: ticket_score > 1.2
2. ✅ 暂停 META, AMZN 出票
3. ✅ 增加 3天周期出票比例

### P1: 短期实施 (1-2周)
1. 建立股票偏好列表和黑名单
2. 调整评分权重 (基于 IC 分析)
3. 实施动态止损

### P2: 中期实施 (1个月)
1. 实施仓位分散化检查
2. 建立行业轮动策略
3. 完善移动止盈机制

### P3: 长期实施 (持续)
1. 积累数据优化模型
2. 引入更多分析维度
3. 建立自动化回测框架

---

## 6. 预期效果

| 优化领域 | 当前表现 | 预期提升 |
|----------|----------|----------|
| 整体胜率 | 89.5% | 92-95% |
| 平均收益 | 3.53% | 4.5-5.5% |
| 最大回撤 | -0.51% | < 0.3% |
| 资金利用率 | 中等 | 提升 20-30% |

---

## 7. 风险提示

1. **数据量不足:** 当前仅 31 张票，统计显著性有限，建议积累 100+ 张票后再做重大调整
2. **过拟合风险:** 基于历史数据的优化可能在市场变化时失效
3. **执行风险:** 策略调整需要同步修改多个脚本，需要仔细测试
4. **市场风险:** 策略优化无法消除系统性市场风险

---

**报告生成时间:** 2026-07-01
**数据来源:** xiaomei 数据库 tickets + forward_tracking 表
**下一步:** 等待 Task 5 性能分析确认后，按优先级实施优化建议
