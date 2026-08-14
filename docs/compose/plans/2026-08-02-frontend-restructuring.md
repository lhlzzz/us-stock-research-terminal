# Xiaomei 前端重构实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use compose:subagent (recommended) or compose:execute to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 重构 xiaomei 前端为3个中文模块（模拟交易、AI出票、出票记录），增加状元/探花/榜眼排名、获利机会判定、详细评分分析和数据来源标注。

**Architecture:** 单文件SPA架构，使用hash路由实现页面切换。所有文本中文化，保持现有粉紫色主题。API层复用现有端点，仅需增强explain端点。

**Tech Stack:** HTML/CSS/JavaScript（无框架依赖）、FastAPI（后端API）

## Global Constraints

- 所有界面文本必须使用中文
- 保持现有粉紫色主题（--primary: #FF8FB8; --purple: #C8A7FF）
- 分类标签：状元🥇/探花🥈/榜眼🥉/候选/观察
- 风险判定：获利机会高/中/低
- 数据来源需标注：数据提供方、发布时间、获取时间
- 单文件SPA架构，所有代码在 `public/index.html` 中

---

### Task 1: 设置Hash路由系统

**Covers:** S2, S7

**Files:**
- Modify: `public/index.html`

**Interfaces:**
- Produces: `navigateTo(page)` 函数、`getCurrentPage()` 函数、路由状态管理

- [ ] **Step 1: 添加路由状态变量和导航函数**

在 `<script>` 标签开头添加：

```javascript
// 路由状态
let currentPage = 'simulation';
let currentSubPage = 'overview';

// 页面配置
const pages = {
  simulation: { name: '模拟交易', icon: '💼' },
  aiPicks: { name: 'AI出票', icon: '🎫', subPages: {
    overview: { name: '出票概览', icon: '📋' },
    signals: { name: 'AI信号', icon: '📡' }
  }},
  records: { name: '出票记录', icon: '📊' }
};

// 导航函数
function navigateTo(page, subPage = null) {
  currentPage = page;
  if (subPage) currentSubPage = subPage;
  window.location.hash = subPage ? `${page}/${subPage}` : page;
  renderPage();
}

// 解析hash
function parseHash() {
  const hash = window.location.hash.slice(1) || 'simulation';
  const parts = hash.split('/');
  currentPage = parts[0] || 'simulation';
  currentSubPage = parts[1] || (currentPage === 'aiPicks' ? 'overview' : null);
}

// 监听hash变化
window.addEventListener('hashchange', parseHash);
```

- [ ] **Step 2: 添加renderPage占位函数**

```javascript
// 页面渲染主函数（后续Task实现具体渲染）
function renderPage() {
  const main = document.querySelector('.main');
  // 根据currentPage和currentSubPage渲染对应内容
  // 将在后续Task中实现
}
```

- [ ] **Step 3: 验证路由系统**

刷新页面，检查：
1. 浏览器地址栏显示 `#simulation`
2. 控制台无错误
3. `navigateTo('aiPicks', 'overview')` 正确更新hash

---

### Task 2: 重构导航栏为3个中文模块

**Covers:** S2, S7

**Files:**
- Modify: `public/index.html`

**Interfaces:**
- Consumes: `navigateTo()` 函数、`pages` 配置
- Produces: 动态导航栏渲染

- [ ] **Step 1: 替换现有导航栏HTML**

找到 `<nav>` 标签（约130-135行），替换为：

```html
<nav>
  <button class="nav-item active" onclick="navigateTo('simulation')">
    <span class="icon">💼</span>模拟交易
  </button>
  <div class="nav-group">
    <button class="nav-item" onclick="navigateTo('aiPicks', 'overview')">
      <span class="icon">🎫</span>AI出票
    </button>
    <div class="sub-nav" id="aiPicks-sub">
      <button class="nav-item sub" onclick="navigateTo('aiPicks', 'overview')">
        <span class="icon">📋</span>出票概览
      </button>
      <button class="nav-item sub" onclick="navigateTo('aiPicks', 'signals')">
        <span class="icon">📡</span>AI信号
      </button>
    </div>
  </div>
  <button class="nav-item" onclick="navigateTo('records')">
    <span class="icon">📊</span>出票记录
  </button>
</nav>
```

- [ ] **Step 2: 添加子导航样式**

在CSS部分添加：

```css
.nav-group { position: relative; }
.sub-nav {
  display: none;
  padding-left: 20px;
  background: rgba(255,214,231,0.2);
  border-radius: 0 0 12px 12px;
}
.nav-group:hover .sub-nav,
.nav-group.active .sub-nav { display: block; }
.nav-item.sub {
  padding: 8px 12px;
  font-size: 13px;
  color: var(--text-2);
}
.nav-item.sub:hover { background: rgba(255,214,231,0.4); }
.nav-item.sub.active { background: rgba(255,214,231,0.6); color: var(--primary-dark); }
```

- [ ] **Step 3: 添加导航高亮逻辑**

在 `renderPage()` 函数中添加：

```javascript
function updateNavigation() {
  // 移除所有active状态
  document.querySelectorAll('.nav-item').forEach(el => el.classList.remove('active'));
  document.querySelectorAll('.nav-group').forEach(el => el.classList.remove('active'));

  // 设置当前页面高亮
  if (currentPage === 'simulation') {
    document.querySelector('[onclick*="simulation"]').classList.add('active');
  } else if (currentPage === 'aiPicks') {
    document.querySelector('.nav-group').classList.add('active');
    document.querySelector(`[onclick*="${currentSubPage}"]`).classList.add('active');
  } else if (currentPage === 'records') {
    document.querySelector('[onclick*="records"]').classList.add('active');
  }
}
```

- [ ] **Step 4: 验证导航**

刷新页面，检查：
1. 导航栏显示3个中文模块
2. 鼠标悬停AI出票显示子菜单
3. 点击导航正确更新hash和高亮

---

### Task 3: 实现模拟交易模块

**Covers:** S3.1, S7

**Files:**
- Modify: `public/index.html`

**Interfaces:**
- Consumes: `/api/positions` 端点、`navigateTo()` 函数
- Produces: 模拟交易页面渲染函数

- [ ] **Step 1: 创建模拟交易页面渲染函数**

```javascript
function renderSimulationPage() {
  const main = document.querySelector('.main');
  main.innerHTML = `
    <header class="header">
      <div>
        <h1>🌙 Xiaomei 美股投资终端</h1>
        <p id="date-line">模拟交易 · 交易理由追踪 · 多因子分析</p>
      </div>
      <div style="display:flex;align-items:center;gap:12px">
        <span id="market-status" style="padding:6px 14px;border-radius:999px;font-size:12px;font-weight:600;background:#D4F5E9;color:#2D7A52">● 运行中</span>
        <button onclick="refresh()" style="padding:8px 16px;border:1px solid var(--border);border-radius:10px;background:var(--bg-card);cursor:pointer;font-weight:600">刷新</button>
      </div>
    </header>

    <!-- Stat Grid -->
    <section class="stat-grid">
      <div class="stat-card">
        <div class="label">💰 总权益</div>
        <div class="value" id="equity">$1,000.00</div>
        <div class="change" id="pnl-pct">--</div>
      </div>
      <div class="stat-card">
        <div class="label">📈 持仓数</div>
        <div class="value" id="pos-count">0</div>
        <div class="change">活跃持仓</div>
      </div>
      <div class="stat-card">
        <div class="label">💵 现金</div>
        <div class="value" id="cash">$1,000.00</div>
        <div class="change">可用资金</div>
      </div>
      <div class="stat-card">
        <div class="label">🎯 胜率</div>
        <div class="value" id="win-rate">--</div>
        <div class="change">历史统计</div>
      </div>
    </section>

    <!-- Positions -->
    <section class="card" style="margin-bottom:24px">
      <div class="card-head">
        <h2>💼 模拟持仓 — 点击查看交易理由</h2>
        <span class="sub" id="last-update">--</span>
      </div>
      <div class="card-body" style="padding:0">
        <table>
          <thead><tr>
            <th>标的</th><th>方向</th><th>入场价</th><th>现价</th><th>变动</th><th>盈亏</th><th>止损</th><th>止盈</th>
          </tr></thead>
          <tbody id="positions"><tr><td colspan="8" class="empty">加载中...</td></tr></tbody>
        </table>
      </div>
    </section>

    <footer class="foot">
      <span>🌸 Financial OS · Xiaomei 美股 AI 投资终端</span>
      <span>数据来源：Pipeline出票 + yfinance行情 · 纸面模拟</span>
    </footer>
  `;

  // 加载数据
  loadPositions();
}
```

- [ ] **Step 2: 更新renderPage函数**

```javascript
function renderPage() {
  updateNavigation();

  switch(currentPage) {
    case 'simulation':
      renderSimulationPage();
      break;
    case 'aiPicks':
      renderAiPicksPage();
      break;
    case 'records':
      renderRecordsPage();
      break;
  }
}
```

- [ ] **Step 3: 验证模拟交易页面**

刷新页面，检查：
1. 页面显示模拟交易内容
2. 持仓数据正确加载
3. 点击持仓展开交易理由

---

### Task 4: 实现出票概览页面（状元/探花/榜眼）

**Covers:** S3.2.1, S4, S7

**Files:**
- Modify: `public/index.html`

**Interfaces:**
- Consumes: `/picks?limit=20` 端点
- Produces: 出票概览页面渲染函数、状元/探花/榜眼映射函数

- [ ] **Step 1: 创建分类标签映射函数**

```javascript
// 分类标签映射
function getClassificationLabel(classification, rank) {
  if (rank === 1) return { label: '状元 🥇', class: 'rank-gold' };
  if (rank === 2) return { label: '探花 🥈', class: 'rank-silver' };
  if (rank === 3) return { label: '榜眼 🥉', class: 'rank-bronze' };
  if (classification.includes('PAPER')) return { label: '候选', class: 'class-paper' };
  return { label: '观察', class: 'class-watch' };
}

// 风险判定映射
function getRiskLabel(riskVerdict) {
  const map = {
    'CLEAN': { label: '获利机会高', class: 'risk-high' },
    'WATCH': { label: '获利机会中', class: 'risk-med' },
    'ELEVATED': { label: '获利机会低', class: 'risk-low' }
  };
  return map[riskVerdict] || { label: riskVerdict || '--', class: '' };
}
```

- [ ] **Step 2: 添加排名相关CSS样式**

```css
/* 排名样式 */
.rank-gold { background: linear-gradient(135deg, #FFD700, #FFA500); color: #8B4513; }
.rank-silver { background: linear-gradient(135deg, #C0C0C0, #A8A8A8); color: #333; }
.rank-bronze { background: linear-gradient(135deg, #CD7F32, #B87333); color: #fff; }
.rank-badge {
  display: inline-flex; align-items: center; gap: 4px;
  padding: 4px 12px; border-radius: 999px; font-size: 12px; font-weight: 600;
}

/* 今日状元推荐区域 */
.top-pick {
  background: linear-gradient(135deg, var(--primary-light), var(--purple-light));
  border: 2px solid var(--primary);
  border-radius: 16px;
  padding: 20px;
  margin-bottom: 24px;
}
.top-pick-header {
  display: flex; align-items: center; gap: 12px;
  margin-bottom: 16px; font-size: 18px; font-weight: 700;
}
.top-pick-details {
  display: grid; grid-template-columns: repeat(4, 1fr); gap: 12px;
}
.top-pick-stat {
  text-align: center; padding: 12px;
  background: var(--bg-card); border-radius: 12px;
}
.top-pick-stat .label { font-size: 11px; color: var(--text-3); }
.top-pick-stat .value { font-size: 20px; font-weight: 700; margin-top: 4px; }
```

- [ ] **Step 3: 创建出票概览页面渲染函数**

```javascript
function renderAiPicksOverview() {
  return `
    <section class="card" style="margin-bottom:24px">
      <div class="card-head">
        <h2>🎫 今日AI出票</h2>
        <span class="sub" id="ticket-date">--</span>
      </div>
      <div class="card-body">
        <div id="top-pick-container"></div>
        <div class="table-wrap">
          <table>
            <thead><tr>
              <th>排名</th><th>标的</th><th>综合分</th><th>市场分</th><th>催化分</th><th>分类</th><th>风险</th>
            </tr></thead>
            <tbody id="tickets-table"><tr><td colspan="7" class="empty">加载中...</td></tr></tbody>
          </table>
        </div>
      </div>
    </section>
  `;
}
```

- [ ] **Step 4: 实现出票数据加载和渲染**

```javascript
async function loadTickets() {
  try {
    const resp = await fetch(`${API_PREFIX}/picks?limit=20`, {cache:'no-store'});
    if (!resp.ok) return;
    const tickets = await resp.json();

    if (!tickets.length) {
      document.getElementById('tickets-table').innerHTML =
        '<tr><td colspan="7" class="empty">暂无出票</td></tr>';
      return;
    }

    // 按ticket_score排序，分配排名
    const sorted = tickets.sort((a, b) => (b.ticket_score||0) - (a.ticket_score||0));
    sorted.forEach((t, i) => t.rank = i + 1);

    // 渲染今日状元
    const topPick = sorted[0];
    document.getElementById('top-pick-container').innerHTML = `
      <div class="top-pick">
        <div class="top-pick-header">
          <span>🏆</span>
          <span>今日状元：${esc(topPick.symbol)}</span>
          <span class="rank-badge rank-gold">状元 🥇</span>
        </div>
        <div class="top-pick-details">
          <div class="top-pick-stat">
            <div class="label">综合评分</div>
            <div class="value">${(topPick.ticket_score||0).toFixed(3)}</div>
          </div>
          <div class="top-pick-stat">
            <div class="label">市场评分</div>
            <div class="value">${(topPick.market_score||0).toFixed(3)}</div>
          </div>
          <div class="top-pick-stat">
            <div class="label">催化剂评分</div>
            <div class="value">${(topPick.catalyst_score||0).toFixed(3)}</div>
          </div>
          <div class="top-pick-stat">
            <div class="label">风险判定</div>
            <div class="value">${getRiskLabel(topPick.risk_verdict).label}</div>
          </div>
        </div>
      </div>
    `;

    // 渲染出票列表
    document.getElementById('ticket-date').textContent = sorted[0]?.output_date || '--';
    document.getElementById('tickets-table').innerHTML = sorted.map(t => {
      const cls = getClassificationLabel(t.classification, t.rank);
      const risk = getRiskLabel(t.risk_verdict);
      const ms = Number(t.market_score||0);
      const cs = Number(t.catalyst_score||0);
      return `<tr>
        <td><span class="rank-badge ${cls.class}">${cls.label}</span></td>
        <td><span class="ticker">${esc(t.symbol)}</span></td>
        <td>${(t.ticket_score||0).toFixed(3)}</td>
        <td class="${ms>=0.8?'up':''}">${ms.toFixed(3)}</td>
        <td class="${cs>=0.1?'up':''}">${cs.toFixed(3)}</td>
        <td><span class="rank-badge ${cls.class}">${cls.label}</span></td>
        <td><span class="risk-badge ${risk.class}">${risk.label}</span></td>
      </tr>`;
    }).join('');
  } catch(e) {
    console.error('Failed to load tickets:', e);
  }
}
```

- [ ] **Step 5: 验证出票概览页面**

点击AI出票 → 出票概览，检查：
1. 今日状元推荐区域显示
2. 出票列表显示状元/探花/榜眼标签
3. 风险判定显示为中文

---

### Task 5: 实现AI信号页面

**Covers:** S3.2.2, S7

**Files:**
- Modify: `public/index.html`

**Interfaces:**
- Consumes: `/signals`、`/signals/effectiveness` 端点
- Produces: AI信号页面渲染函数

- [ ] **Step 1: 创建AI信号页面渲染函数**

```javascript
function renderAiSignalsPage() {
  return `
    <section class="card" style="margin-bottom:24px">
      <div class="card-head">
        <h2>📡 AI信号分析</h2>
        <span class="sub">原始信号数据与有效性分析</span>
      </div>
      <div class="card-body">
        <div class="signal-tabs">
          <button class="tab-btn active" onclick="showSignalTab('raw')">原始信号</button>
          <button class="tab-btn" onclick="showSignalTab('effectiveness')">信号有效性</button>
        </div>
        <div id="signal-content">
          <div class="empty">加载中...</div>
        </div>
      </div>
    </section>
  `;
}
```

- [ ] **Step 2: 添加信号页面CSS**

```css
.signal-tabs {
  display: flex; gap: 8px; margin-bottom: 16px;
  border-bottom: 1px solid var(--border); padding-bottom: 8px;
}
.tab-btn {
  padding: 8px 16px; border: none; background: transparent;
  cursor: pointer; font-size: 13px; color: var(--text-2);
  border-radius: 8px; transition: all 0.15s;
}
.tab-btn:hover { background: rgba(255,214,231,0.4); }
.tab-btn.active { background: var(--primary-light); color: var(--primary-dark); font-weight: 600; }
.signal-table { width: 100%; }
.signal-table th { font-size: 11px; }
.signal-table td { font-size: 12px; }
```

- [ ] **Step 3: 实现信号数据加载**

```javascript
async function loadSignals() {
  try {
    const resp = await fetch(`${API_PREFIX}/signals?limit=50`, {cache:'no-store'});
    if (!resp.ok) return;
    const signals = await resp.json();

    const content = document.getElementById('signal-content');
    if (!signals.length) {
      content.innerHTML = '<div class="empty">暂无信号数据</div>';
      return;
    }

    content.innerHTML = `
      <table class="signal-table">
        <thead><tr>
          <th>交易日期</th><th>标的</th><th>信号键</th><th>信号值</th>
        </tr></thead>
        <tbody>
          ${signals.map(s => `
            <tr>
              <td>${s.trade_date}</td>
              <td><span class="ticker">${esc(s.symbol)}</span></td>
              <td>${esc(s.signal_key)}</td>
              <td>${(s.signal_value||0).toFixed(4)}</td>
            </tr>
          `).join('')}
        </tbody>
      </table>
    `;
  } catch(e) {
    console.error('Failed to load signals:', e);
  }
}

async function loadSignalEffectiveness() {
  try {
    const resp = await fetch(`${API_PREFIX}/signals/effectiveness`, {cache:'no-store'});
    if (!resp.ok) return;
    const data = await resp.json();

    const content = document.getElementById('signal-content');
    if (!data.length) {
      content.innerHTML = '<div class="empty">暂无有效性数据</div>';
      return;
    }

    content.innerHTML = `
      <table class="signal-table">
        <thead><tr>
          <th>分析日期</th><th>信号键</th><th>样本数</th><th>胜率</th><th>平均收益</th><th>IC评分</th><th>P值</th>
        </tr></thead>
        <tbody>
          ${data.map(d => `
            <tr>
              <td>${d.analysis_date}</td>
              <td>${esc(d.signal_key)}</td>
              <td>${d.present_count}</td>
              <td class="${d.win_rate>=50?'up':'down'}">${(d.win_rate||0).toFixed(1)}%</td>
              <td class="${d.avg_return>=0?'up':'down'}">${(d.avg_return||0).toFixed(2)}%</td>
              <td>${(d.ic_score||0).toFixed(4)}</td>
              <td>${(d.p_value||0).toFixed(4)}</td>
            </tr>
          `).join('')}
        </tbody>
      </table>
    `;
  } catch(e) {
    console.error('Failed to load signal effectiveness:', e);
  }
}

function showSignalTab(tab) {
  document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
  event.target.classList.add('active');

  if (tab === 'raw') {
    loadSignals();
  } else {
    loadSignalEffectiveness();
  }
}
```

- [ ] **Step 4: 验证AI信号页面**

点击AI出票 → AI信号，检查：
1. 原始信号数据正确显示
2. 切换到信号有效性标签页
3. 数据表格格式正确

---

### Task 6: 实现出票记录页面（含个股详情）

**Covers:** S3.3, S5, S6, S7

**Files:**
- Modify: `public/index.html`

**Interfaces:**
- Consumes: `/picks`、`/explain/{date}/{symbol}` 端点
- Produces: 出票记录页面渲染函数、个股详情组件

- [ ] **Step 1: 创建出票记录页面渲染函数**

```javascript
function renderRecordsPage() {
  return `
    <header class="header">
      <div>
        <h1>📊 出票记录</h1>
        <p>历史出票记录与个股详细分析</p>
      </div>
      <div style="display:flex;align-items:center;gap:12px">
        <input type="date" id="date-filter" style="padding:8px 12px;border:1px solid var(--border);border-radius:8px">
        <button onclick="loadRecords()" style="padding:8px 16px;border:1px solid var(--border);border-radius:10px;background:var(--bg-card);cursor:pointer;font-weight:600">筛选</button>
      </div>
    </header>

    <section class="card">
      <div class="card-head">
        <h2>历史出票</h2>
        <span class="sub" id="records-count">--</span>
      </div>
      <div class="card-body" style="padding:0">
        <table>
          <thead><tr>
            <th>日期</th><th>标的</th><th>综合分</th><th>分类</th><th>风险</th><th>操作</th>
          </tr></thead>
          <tbody id="records-table"><tr><td colspan="6" class="empty">加载中...</td></tr></tbody>
        </table>
      </div>
    </section>

    <div id="stock-detail-modal" class="modal" style="display:none">
      <div class="modal-content">
        <button class="modal-close" onclick="closeDetailModal()">×</button>
        <div id="stock-detail-body"></div>
      </div>
    </div>
  `;
}
```

- [ ] **Step 2: 添加模态框和详情样式**

```css
/* 模态框 */
.modal {
  position: fixed; top: 0; left: 0; width: 100%; height: 100%;
  background: rgba(0,0,0,0.5); z-index: 100;
  display: flex; align-items: center; justify-content: center;
}
.modal-content {
  background: var(--bg-card); border-radius: 16px; padding: 24px;
  max-width: 800px; width: 90%; max-height: 80vh; overflow-y: auto;
  position: relative;
}
.modal-close {
  position: absolute; top: 12px; right: 12px;
  width: 32px; height: 32px; border: none; background: var(--border);
  border-radius: 50%; cursor: pointer; font-size: 18px;
  display: flex; align-items: center; justify-content: center;
}

/* 详情组件 */
.detail-section {
  margin-bottom: 20px; padding: 16px;
  border: 1px solid var(--border); border-radius: 12px;
}
.detail-section h3 {
  font-size: 14px; font-weight: 600; margin-bottom: 12px;
  color: var(--primary-dark); border-bottom: 1px solid var(--border);
  padding-bottom: 8px;
}
.detail-grid {
  display: grid; grid-template-columns: repeat(2, 1fr); gap: 12px;
}
.detail-item {
  padding: 8px 12px; background: var(--primary-light); border-radius: 8px;
}
.detail-item .label { font-size: 11px; color: var(--text-3); }
.detail-item .value { font-size: 14px; font-weight: 600; margin-top: 4px; }

/* 数据来源 */
.source-card {
  background: #f8f9fa; border: 1px solid #e9ecef; border-radius: 8px;
  padding: 12px; margin-top: 12px; font-size: 11px;
}
.source-item {
  display: flex; justify-content: space-between; padding: 4px 0;
  border-bottom: 1px solid #eee;
}
.source-item:last-child { border-bottom: none; }
.source-label { color: var(--text-3); }
.source-value { font-weight: 500; }
```

- [ ] **Step 3: 实现出票记录加载**

```javascript
async function loadRecords() {
  const dateFilter = document.getElementById('date-filter').value;
  let url = `${API_PREFIX}/picks?limit=50`;
  if (dateFilter) url += `&date_from=${dateFilter}&date_to=${dateFilter}`;

  try {
    const resp = await fetch(url, {cache:'no-store'});
    if (!resp.ok) return;
    const records = await resp.json();

    document.getElementById('records-count').textContent = `共 ${records.length} 条记录`;

    // 按日期分组，分配排名
    const grouped = {};
    records.forEach(r => {
      if (!grouped[r.output_date]) grouped[r.output_date] = [];
      grouped[r.output_date].push(r);
    });

    // 排序并分配排名
    Object.values(grouped).forEach(group => {
      group.sort((a, b) => (b.ticket_score||0) - (a.ticket_score||0));
      group.forEach((r, i) => r.rank = i + 1);
    });

    document.getElementById('records-table').innerHTML = records.map(r => {
      const cls = getClassificationLabel(r.classification, r.rank);
      const risk = getRiskLabel(r.risk_verdict);
      return `<tr>
        <td>${r.output_date}</td>
        <td><span class="ticker">${esc(r.symbol)}</span></td>
        <td>${(r.ticket_score||0).toFixed(3)}</td>
        <td><span class="rank-badge ${cls.class}">${cls.label}</span></td>
        <td><span class="risk-badge ${risk.class}">${risk.label}</span></td>
        <td><button class="detail-btn" onclick="showStockDetail('${r.output_date}','${r.symbol}')">查看详情</button></td>
      </tr>`;
    }).join('');
  } catch(e) {
    console.error('Failed to load records:', e);
  }
}
```

- [ ] **Step 4: 实现个股详情模态框**

```javascript
async function showStockDetail(tradeDate, symbol) {
  try {
    const resp = await fetch(`${API_PREFIX}/explain/${tradeDate}/${symbol}`, {cache:'no-store'});
    if (!resp.ok) throw new Error('Failed to fetch');
    const data = await resp.json();

    const ticket = data.ticket || {};
    const candidate = data.candidate || {};
    const returns = data.returns || [];

    // 解析因子快照
    let factors = {};
    try { factors = JSON.parse(candidate.factor_snapshot || '{}'); } catch(e) {}

    const risk = getRiskLabel(ticket.risk_verdict);

    document.getElementById('stock-detail-body').innerHTML = `
      <h2 style="margin-bottom:20px">${esc(symbol)} 详细分析</h2>

      <!-- 基本信息 -->
      <div class="detail-section">
        <h3>📋 基本信息</h3>
        <div class="detail-grid">
          <div class="detail-item">
            <div class="label">标的代码</div>
            <div class="value">${esc(symbol)}</div>
          </div>
          <div class="detail-item">
            <div class="label">出票日期</div>
            <div class="value">${tradeDate}</div>
          </div>
          <div class="detail-item">
            <div class="label">分类</div>
            <div class="value">${ticket.classification || '--'}</div>
          </div>
          <div class="detail-item">
            <div class="label">风险判定</div>
            <div class="value">${risk.label}</div>
          </div>
        </div>
      </div>

      <!-- 评分评解 -->
      <div class="detail-section">
        <h3>📊 评分评解</h3>
        <div class="detail-grid">
          <div class="detail-item">
            <div class="label">综合评分</div>
            <div class="value">${(ticket.ticket_score||0).toFixed(4)}</div>
          </div>
          <div class="detail-item">
            <div class="label">市场评分</div>
            <div class="value">${(ticket.market_score||0).toFixed(4)}</div>
          </div>
          <div class="detail-item">
            <div class="label">催化剂评分</div>
            <div class="value">${(ticket.catalyst_score||0).toFixed(4)}</div>
          </div>
          <div class="detail-item">
            <div class="label">机构资金流</div>
            <div class="value">${(ticket.institutional_flow_score||0).toFixed(4)}</div>
          </div>
          <div class="detail-item">
            <div class="label">社交情绪</div>
            <div class="value">${(ticket.social_sentiment_score||0).toFixed(4)}</div>
          </div>
          <div class="detail-item">
            <div class="label">突破评分</div>
            <div class="value">${(ticket.breakout_score||0).toFixed(4)}</div>
          </div>
          <div class="detail-item">
            <div class="label">风险惩罚</div>
            <div class="value">${(ticket.risk_penalty||0).toFixed(4)}</div>
          </div>
          <div class="detail-item">
            <div class="label">确认评分</div>
            <div class="value">${(ticket.confirmation_score||0).toFixed(4)}</div>
          </div>
        </div>
      </div>

      <!-- 技术信号 -->
      <div class="detail-section">
        <h3>📈 技术信号</h3>
        <div class="detail-grid">
          <div class="detail-item">
            <div class="label">20日动量</div>
            <div class="value">${(factors.prior_20d_momentum||0).toFixed(4)}</div>
          </div>
          <div class="detail-item">
            <div class="label">5日加速</div>
            <div class="value">${(factors.five_day_acceleration||0).toFixed(4)}</div>
          </div>
          <div class="detail-item">
            <div class="label">相对强度</div>
            <div class="value">${(factors.relative_strength||0).toFixed(4)}</div>
          </div>
          <div class="detail-item">
            <div class="label">成交量确认</div>
            <div class="value">${(factors.volume_confirmation||0).toFixed(4)}</div>
          </div>
          <div class="detail-item">
            <div class="label">RSI(14)</div>
            <div class="value">${(factors.rsi_14||0).toFixed(2)}</div>
          </div>
          <div class="detail-item">
            <div class="label">突破评分</div>
            <div class="value">${(factors.breakout_score||0).toFixed(4)}</div>
          </div>
        </div>
      </div>

      <!-- 催化剂分析 -->
      <div class="detail-section">
        <h3>🔥 催化剂分析</h3>
        <div class="detail-grid">
          <div class="detail-item">
            <div class="label">叙事证据</div>
            <div class="value">${candidate.selection_reason || '--'}</div>
          </div>
          <div class="detail-item">
            <div class="label">业务证据</div>
            <div class="value">${candidate.candidate_entry_reason || '--'}</div>
          </div>
        </div>
      </div>

      <!-- 风险评估 -->
      <div class="detail-section">
        <h3>⚠️ 风险评估</h3>
        <div class="detail-grid">
          <div class="detail-item">
            <div class="label">风险判定</div>
            <div class="value">${risk.label}</div>
          </div>
          <div class="detail-item">
            <div class="label">风险摘要</div>
            <div class="value">${ticket.risk_summary || '--'}</div>
          </div>
          <div class="detail-item">
            <div class="label">质量判定</div>
            <div class="value">${ticket.quality_verdict || '--'}</div>
          </div>
          <div class="detail-item">
            <div class="label">质量摘要</div>
            <div class="value">${ticket.quality_summary || '--'}</div>
          </div>
        </div>
      </div>

      <!-- 前瞻跟踪 -->
      <div class="detail-section">
        <h3>🔮 前瞻跟踪</h3>
        <table class="signal-table">
          <thead><tr><th>周期</th><th>收益</th><th>状态</th></tr></thead>
          <tbody>
            ${returns.map(r => `
              <tr>
                <td>${r.horizon_days}天</td>
                <td class="${r.forward_return>=0?'up':'down'}">${(r.forward_return||0).toFixed(2)}%</td>
                <td>${r.check_status}</td>
              </tr>
            `).join('') || '<tr><td colspan="3">暂无跟踪数据</td></tr>'}
          </tbody>
        </table>
      </div>

      <!-- 数据来源 -->
      <div class="detail-section">
        <h3>📚 数据来源</h3>
        <div class="source-card">
          <div class="source-item">
            <span class="source-label">出票数据</span>
            <span class="source-value">profit-ticket-pipeline · ${tradeDate}</span>
          </div>
          <div class="source-item">
            <span class="source-label">生成者</span>
            <span class="source-value">xiaomei AI Pipeline</span>
          </div>
          <div class="source-item">
            <span class="source-label">因子数据</span>
            <span class="source-value">factor_snapshots · ${factors.created_at || '--'}</span>
          </div>
          <div class="source-item">
            <span class="source-label">因子生成者</span>
            <span class="source-value">weight_optimizer.py</span>
          </div>
          <div class="source-item">
            <span class="source-label">交易理由</span>
            <span class="source-value">trade_journal · AI推理</span>
          </div>
        </div>
      </div>
    `;

    document.getElementById('stock-detail-modal').style.display = 'flex';
  } catch(e) {
    console.error('Failed to load stock detail:', e);
    alert('加载详情失败');
  }
}

function closeDetailModal() {
  document.getElementById('stock-detail-modal').style.display = 'none';
}
```

- [ ] **Step 5: 验证出票记录页面**

点击出票记录，检查：
1. 历史出票记录正确显示
2. 点击"查看详情"打开模态框
3. 个股详情包含7个组件
4. 数据来源显示详细信息

---

### Task 7: 更新页面路由和刷新逻辑

**Covers:** S7

**Files:**
- Modify: `public/index.html`

**Interfaces:**
- Consumes: 所有页面渲染函数
- Produces: 统一的页面路由和刷新逻辑

- [ ] **Step 1: 更新renderPage函数**

```javascript
function renderPage() {
  updateNavigation();

  switch(currentPage) {
    case 'simulation':
      renderSimulationPage();
      break;
    case 'aiPicks':
      renderAiPicksPage();
      break;
    case 'records':
      renderRecordsPage();
      break;
  }
}

function renderAiPicksPage() {
  const main = document.querySelector('.main');
  main.innerHTML = `
    <header class="header">
      <div>
        <h1>🎫 AI出票</h1>
        <p>AI信号分析与出票概览</p>
      </div>
      <div style="display:flex;align-items:center;gap:12px">
        <button onclick="refresh()" style="padding:8px 16px;border:1px solid var(--border);border-radius:10px;background:var(--bg-card);cursor:pointer;font-weight:600">刷新</button>
      </div>
    </header>
    ${currentSubPage === 'signals' ? renderAiSignalsPage() : renderAiPicksOverview()}
  `;

  if (currentSubPage === 'signals') {
    loadSignals();
  } else {
    loadTickets();
  }
}
```

- [ ] **Step 2: 更新refresh函数**

```javascript
async function refresh() {
  switch(currentPage) {
    case 'simulation':
      await loadPositions();
      break;
    case 'aiPicks':
      if (currentSubPage === 'signals') {
        await loadSignals();
      } else {
        await loadTickets();
      }
      break;
    case 'records':
      await loadRecords();
      break;
  }
}
```

- [ ] **Step 3: 更新初始化逻辑**

```javascript
// 初始化
parseHash();
renderPage();
setInterval(refresh, 30000);
```

- [ ] **Step 4: 验证完整功能**

1. 访问 `#simulation` 显示模拟交易
2. 访问 `#aiPicks/overview` 显示出票概览
3. 访问 `#aiPicks/signals` 显示AI信号
4. 访问 `#records` 显示出票记录
5. 所有页面刷新功能正常

---

### Task 8: 最终验证和清理

**Covers:** S8

**Files:**
- Modify: `public/index.html`

**Interfaces:**
- 无

- [ ] **Step 1: 检查所有中文文本**

确保：
1. 导航栏：模拟交易、AI出票、出票记录
2. 页面标题：中文
3. 表格表头：中文
4. 按钮文本：中文
5. 空状态提示：中文

- [ ] **Step 2: 检查分类标签映射**

验证：
1. 祖元🥇、探花🥈、榜眼🥉 正确显示
2. 候选、观察 正确显示
3. 样式（金色、银色、铜色）正确

- [ ] **Step 3: 检查风险判定映射**

验证：
1. 获利机会高（CLEAN）
2. 获利机会中（WATCH）
3. 获利机会低（ELEVATED）

- [ ] **Step 4: 检查数据来源标注**

验证个股详情中：
1. 出票数据来源显示
2. 因子数据来源显示
3. 交易理由来源显示
4. 包含发布时间和生成者

- [ ] **Step 5: 最终提交**

```bash
git add public/index.html
git commit -m "feat: 重构前端为3个中文模块，增加状元/探花/榜眼排名、获利机会判定、详细评分分析和数据来源标注"
```
