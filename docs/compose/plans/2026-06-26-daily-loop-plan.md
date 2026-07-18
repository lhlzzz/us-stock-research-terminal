# xiaomei Daily Loop 实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use compose:subagent (recommended) or compose:execute to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 实现 xiaomei 每日自动出票的完整闭环，确保数据可复现、流程可追踪。

**Architecture:** 单一入口脚本 `daily_loop.py` 编排所有步骤，每步写入 DB，失败可恢复。

**Tech Stack:** Python, PostgreSQL, SQLAlchemy, EastMoney API, akshare

## Global Constraints

- 所有 DB 操作使用 `scripts/db/` 模块
- 写入用 `get_db()` 上下文管理器
- 查询用 `query_rows()`
- 数据源：东财 push2 API + akshare
- 禁止 A 股逻辑、broker、order、live-trade

---

### Task 1: Daily Loop 主脚本

**Covers:** [S1]

**Files:**
- Create: `scripts/daily_loop.py`

**Interfaces:**
- Produces: `run_daily_loop(output_date: str) -> dict`

- [ ] **Step 1: 创建 daily_loop.py 骨架**

```python
#!/usr/bin/env python3
"""Daily Loop: 每日自动出票全流程编排。"""
import sys
from pathlib import Path
from datetime import date

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scripts.db.engine import get_db, query_rows


def run_daily_loop(output_date: str = None) -> dict:
    """执行每日完整流程。"""
    if not output_date:
        output_date = date.today().isoformat()

    results = {"output_date": output_date, "steps": {}}

    # Step 1: Market Scan
    results["steps"]["market_scan"] = step_market_scan(output_date)

    # Step 2: Factor Snapshot
    results["steps"]["factor_snapshot"] = step_factor_snapshot(output_date)

    # Step 3: Scoring + Ticket
    results["steps"]["scoring"] = step_scoring(output_date)

    # Step 4: Backfill
    results["steps"]["backfill"] = step_backfill()

    # Step 5: Scoreboard
    results["steps"]["scoreboard"] = step_scoreboard()

    # Step 6: Signal Effectiveness
    results["steps"]["signal_analysis"] = step_signal_analysis()

    return results


def step_market_scan(output_date: str) -> dict:
    """扫描东财实时行情 + 资金流。"""
    from scripts.eastmoney_us_cdp import fetch_realtime_quote, fetch_fund_flow
    from scripts.db.crud import upsert_realtime_quote, upsert_fund_flow
    from datetime import datetime

    with get_db() as db:
        rows = query_rows("SELECT symbol FROM universe")
        symbols = [r["symbol"] for r in rows]

        quotes_ok = 0
        flow_ok = 0
        for sym in symbols[:50]:
            try:
                q = fetch_realtime_quote(sym)
                if q and q.get("latest_price"):
                    upsert_realtime_quote(db, sym, datetime.utcnow(),
                        latest_price=q["latest_price"],
                        prev_close=q.get("prev_close"),
                        open=q.get("open"), high=q.get("high"), low=q.get("low"),
                        volume=int(q.get("volume", 0)), amount=q.get("amount"),
                        pct_chg=q.get("pct_chg"),
                        pe_ttm=q.get("pe_ttm"), roe=q.get("roe"))
                    quotes_ok += 1
            except Exception:
                pass

            try:
                ff = fetch_fund_flow(sym)
                if ff:
                    upsert_fund_flow(db, sym, date.fromisoformat(output_date),
                        net_inflow_5d=ff.get("net_inflow_5d"),
                        score=ff.get("score"))
                    flow_ok += 1
            except Exception:
                pass

    return {"quotes": quotes_ok, "fund_flow": flow_ok}


def step_factor_snapshot(output_date: str) -> dict:
    """从 daily_klines 计算因子快照。"""
    from scripts.db.crud import upsert_factor_snapshot
    from datetime import date as date_type

    with get_db() as db:
        rows = query_rows("""
            SELECT DISTINCT f.symbol, f.output_date
            FROM forward_tracking f
            WHERE f.check_status = 'completed'
            AND f.output_date = :d
        """, {"d": output_date})

        total = 0
        for symbol, trade_date in rows:
            try:
                klines = query_rows("""
                    SELECT close, volume FROM daily_klines
                    WHERE symbol = :s AND trade_date <= :d
                    ORDER BY trade_date DESC LIMIT 20
                """, {"s": symbol, "d": trade_date})

                if len(klines) < 5:
                    continue

                closes = [float(k["close"]) for k in klines if k["close"]]
                volumes = [int(k["volume"]) for k in klines if k["volume"]]
                if not closes or not volumes:
                    continue

                current = closes[0]
                prior_5d = closes[4] if len(closes) > 4 else current
                prior_20d = closes[19] if len(closes) > 19 else closes[-1]

                upsert_factor_snapshot(db, trade_date, symbol,
                    prior_5d_momentum=(current / prior_5d - 1) if prior_5d else 0,
                    prior_20d_momentum=(current / prior_20d - 1) if prior_20d else 0,
                    five_day_acceleration=((current / prior_5d - 1) - (current / prior_20d - 1)) if prior_5d and prior_20d else 0,
                )
                total += 1
            except Exception:
                continue

    return {"factor_snapshots": total}


def step_scoring(output_date: str) -> dict:
    """运行 pipeline 出票。"""
    import subprocess
    import json

    result = subprocess.run(
        ["python3", "scripts/us_profit_ticket_pipeline.py",
         "--output-date", output_date,
         "--save-db", "--skip-last30days"],
        capture_output=True, text=True, timeout=600,
        cwd="/workspace/hermes-workspaces/xiaomei"
    )

    if result.returncode == 0:
        try:
            output = json.loads(result.stdout.strip().split("\n")[-1])
            return {
                "status": "success",
                "candidates": output.get("top_candidates", []),
                "classification": output.get("final_classification"),
            }
        except (json.JSONDecodeError, KeyError):
            return {"status": "parse_error"}
    return {"status": "failed", "error": result.stderr[:200]}


def step_backfill() -> dict:
    """回填到期收益。"""
    import subprocess

    result = subprocess.run(
        ["python3", "scripts/backfill_forward_tracking.py", "--db"],
        capture_output=True, text=True, timeout=300,
        cwd="/workspace/hermes-workspaces/xiaomei"
    )
    return {"status": "ok" if result.returncode == 0 else "failed"}


def step_scoreboard() -> dict:
    """更新记分板。"""
    import subprocess

    result = subprocess.run(
        ["python3", "scripts/lifecycle_scoreboard.py", "--db"],
        capture_output=True, text=True, timeout=120,
        cwd="/workspace/hermes-workspaces/xiaomei"
    )
    return {"status": "ok" if result.returncode == 0 else "failed"}


def step_signal_analysis() -> dict:
    """运行信号有效性分析。"""
    import subprocess

    result = subprocess.run(
        ["python3", "scripts/signal_effectiveness.py"],
        capture_output=True, text=True, timeout=120,
        cwd="/workspace/hermes-workspaces/xiaomei"
    )
    return {"status": "ok" if result.returncode == 0 else "failed"}


if __name__ == "__main__":
    import json
    result = run_daily_loop()
    print(json.dumps(result, indent=2, ensure_ascii=False))
```

- [ ] **Step 2: 验证脚本可运行**

```bash
cd /workspace/hermes-workspaces/xiaomei && python3 scripts/daily_loop.py
```

Expected: 输出 JSON 结果，所有步骤 status=ok

- [ ] **Step 3: Commit**

```bash
git add scripts/daily_loop.py
git commit -m "feat: add daily_loop.py - 每日全流程编排"
```

---

### Task 2: Quant Gate 四级状态

**Covers:** [S3]

**Files:**
- Create: `scripts/quant_gate.py`

**Interfaces:**
- Produces: `run_quant_gate(output_date: str) -> dict` 返回 {status: PASS/SOFT_PASS/WATCH/FAIL, metrics: {...}}

- [ ] **Step 1: 创建 quant_gate.py**

```python
#!/usr/bin/env python3
"""Quant Gate: 量化验证门，四级状态。"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scripts.db.engine import query_rows


def run_quant_gate(output_date: str = None) -> dict:
    """运行量化验证，返回四级状态。"""
    if not output_date:
        from datetime import date
        output_date = date.today().isoformat()

    metrics = compute_metrics()
    status = evaluate_status(metrics)

    return {
        "output_date": output_date,
        "status": status,
        "metrics": metrics,
    }


def compute_metrics() -> dict:
    """计算验证指标。"""
    rows = query_rows("""
        SELECT
            COUNT(*) as total,
            COUNT(CASE WHEN forward_return > 0 THEN 1 END) as wins,
            AVG(forward_return) as avg_return,
            MAX(forward_return) as max_return,
            MIN(forward_return) as min_return
        FROM forward_tracking
        WHERE check_status = 'completed' AND forward_return IS NOT NULL
    """)
    r = rows[0]

    total = r["total"] or 0
    wins = r["wins"] or 0
    avg_ret = float(r["avg_return"] or 0)
    max_ret = float(r["max_return"] or 0)
    min_ret = float(r["min_return"] or 0)

    win_rate = wins / total if total else 0
    profit_factor = abs(max_ret / min_ret) if min_ret and min_ret < 0 else 999

    signal_rows = query_rows("""
        SELECT
            COUNT(*) as total,
            COUNT(CASE WHEN forward_return > 0.03 THEN 1 END) as high_return
        FROM forward_tracking
        WHERE check_status = 'completed' AND forward_return IS NOT NULL
    """)
    sr = signal_rows[0]
    high_return_rate = (sr["high_return"] or 0) / (sr["total"] or 1)

    return {
        "win_rate": round(win_rate * 100, 2),
        "avg_return": round(avg_ret * 100, 4),
        "profit_factor": round(profit_factor, 2),
        "max_return": round(max_ret * 100, 4),
        "min_return": round(min_ret * 100, 4),
        "high_return_rate": round(high_return_rate * 100, 2),
        "total_records": total,
    }


def evaluate_status(metrics: dict) -> str:
    """根据指标判断四级状态。"""
    wr = metrics["win_rate"]
    ar = metrics["avg_return"]
    pf = metrics["profit_factor"]
    hr = metrics["high_return_rate"]

    if wr >= 55 and ar > 0 and pf > 1.5 and hr > 30:
        return "PASS"
    elif wr >= 50 and ar > -1 and pf > 1.0:
        return "SOFT_PASS"
    elif wr >= 45 and ar > -2:
        return "WATCH"
    else:
        return "FAIL"


if __name__ == "__main__":
    import json
    result = run_quant_gate()
    print(json.dumps(result, indent=2, ensure_ascii=False))
```

- [ ] **Step 2: 验证**

```bash
cd /workspace/hermes-workspaces/xiaomei && python3 scripts/quant_gate.py
```

Expected: 输出包含 status 和 metrics

- [ ] **Step 3: Commit**

```bash
git add scripts/quant_gate.py
git commit -m "feat: add quant_gate.py - 四级量化验证门"
```

---

### Task 3: Meta Loop 退化检测

**Covers:** [S5]

**Files:**
- Create: `scripts/meta_loop.py`

**Interfaces:**
- Produces: `run_meta_loop() -> dict` 返回退化检测结果

- [ ] **Step 1: 创建 meta_loop.py**

```python
#!/usr/bin/env python3
"""Meta Loop: 检查系统是否退化。"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scripts.db.engine import query_rows


def run_meta_loop() -> dict:
    """检查系统退化情况。"""
    recent = compute_recent_metrics(days=30)
    historical = compute_historical_metrics()

    degradation = detect_degradation(recent, historical)

    return {
        "recent_30d": recent,
        "historical": historical,
        "degradation": degradation,
        "action_needed": len(degradation) > 0,
    }


def compute_recent_metrics(days: int = 30) -> dict:
    """计算最近 N 天的指标。"""
    rows = query_rows(f"""
        SELECT
            COUNT(*) as total,
            COUNT(CASE WHEN forward_return > 0 THEN 1 END) as wins,
            AVG(forward_return) as avg_return
        FROM forward_tracking
        WHERE check_status = 'completed'
        AND forward_return IS NOT NULL
        AND completed_at >= NOW() - INTERVAL '{days} days'
    """)
    r = rows[0]
    total = r["total"] or 0
    wins = r["wins"] or 0
    return {
        "win_rate": round(wins / total * 100, 2) if total else 0,
        "avg_return": round(float(r["avg_return"] or 0) * 100, 4),
        "total": total,
    }


def compute_historical_metrics() -> dict:
    """计算全量指标。"""
    rows = query_rows("""
        SELECT
            COUNT(*) as total,
            COUNT(CASE WHEN forward_return > 0 THEN 1 END) as wins,
            AVG(forward_return) as avg_return
        FROM forward_tracking
        WHERE check_status = 'completed' AND forward_return IS NOT NULL
    """)
    r = rows[0]
    total = r["total"] or 0
    wins = r["wins"] or 0
    return {
        "win_rate": round(wins / total * 100, 2) if total else 0,
        "avg_return": round(float(r["avg_return"] or 0) * 100, 4),
        "total": total,
    }


def detect_degradation(recent: dict, historical: dict) -> list:
    """检测退化。"""
    issues = []

    if historical["win_rate"] > 0:
        wr_drop = historical["win_rate"] - recent["win_rate"]
        if wr_drop > 10:
            issues.append({
                "type": "win_rate_degradation",
                "message": f"胜率下降 {wr_drop:.1f}%（历史 {historical['win_rate']}% → 近期 {recent['win_rate']}%）",
                "severity": "HIGH",
            })

    if recent["avg_return"] < -1 and historical["avg_return"] > 0:
        issues.append({
            "type": "return_degradation",
            "message": f"平均收益转负（近期 {recent['avg_return']}%）",
            "severity": "HIGH",
        })

    if recent["total"] < 10:
        issues.append({
            "type": "insufficient_data",
            "message": f"近期数据不足（仅 {recent['total']} 条）",
            "severity": "MEDIUM",
        })

    return issues


if __name__ == "__main__":
    import json
    result = run_meta_loop()
    print(json.dumps(result, indent=2, ensure_ascii=False))
```

- [ ] **Step 2: 验证**

```bash
cd /workspace/hermes-workspaces/xiaomei && python3 scripts/meta_loop.py
```

Expected: 输出退化检测结果

- [ ] **Step 3: Commit**

```bash
git add scripts/meta_loop.py
git commit -m "feat: add meta_loop.py - 系统退化检测"
```

---

### Task 4: 集成验证

**Covers:** [S1, S3, S5]

- [ ] **Step 1: 运行完整 Daily Loop**

```bash
cd /workspace/hermes-workspaces/xiaomei && python3 scripts/daily_loop.py
```

Expected: 所有步骤 status=ok

- [ ] **Step 2: 运行 Quant Gate**

```bash
cd /workspace/hermes-workspaces/xiaomei && python3 scripts/quant_gate.py
```

Expected: 输出 status 和 metrics

- [ ] **Step 3: 运行 Meta Loop**

```bash
cd /workspace/hermes-workspaces/xiaomei && python3 scripts/meta_loop.py
```

Expected: 输出退化检测结果

- [ ] **Step 4: 验证 DB 数据完整性**

```bash
cd /workspace/hermes-workspaces/xiaomei && python3 -c "
import sys; sys.path.insert(0, '.')
from scripts.db.engine import query_rows
for t in ['tickets','forward_tracking','runtime_decisions','factor_snapshots']:
    r = query_rows(f'SELECT COUNT(*) as cnt FROM {t}')
    print(f'{t}: {r[0][\"cnt\"]}')
"
```

Expected: 所有表有数据

- [ ] **Step 5: Commit**

```bash
git add -A
git commit -m "feat: Phase 1 Daily Loop 完整闭环验证通过"
```
