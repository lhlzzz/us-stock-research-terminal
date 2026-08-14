# AGENTS.md — xiaomei

## MiMo 操作模型

MiMo 是执行层，负责实现、测试、验证。

## 启动流程（每次 session 必须执行）

```bash
bash scripts/start_services.sh
```

这会启动 PostgreSQL 14（端口 5432）和 Redis 6（端口 6379）。

## 基础设施

- **PostgreSQL**：localhost:**5432**（Windows 宿主 PG 18.4），用户 xiaomei，数据库 xiaomei
- **Redis 6**：localhost:6379
- **默认启动**：`bash scripts/start_services.sh`（检查 5432 连通性，Docker 为备用方案）
- 连接串：`DATABASE_URL=postgresql://xiaomei:***@localhost:5432/xiaomei`

## 规则

0. **写代码前必读** `/karpathy-guidelines` — 4 条原则防止 LLM 常见错误（假设→简化→手术式改动→目标驱动）
1. 先读 `MIMO.md` 了解工程规范
2. 读 `NEXT_ACTION.md` 了解当前任务
3. 读 `STATE.md` 了解系统状态
4. 代码结构、符号、调用链、影响面优先使用 codebase-memory-mcp（`index_repository`、`search_graph`、`trace_path`、`get_code_snippet`、`query_graph`、`search_code`）；未索引时先索引当前 workspace，再按需回退 CodeGraph/GitNexus/grep
5. 改代码前先验证编译通过
6. 改完后运行相关测试
7. 完成后更新 NEXT_ACTION.md

## 禁止

- **不碰虚拟币主责**（加密归 `xiaobi`；本 agent 只管美股）
- 不新增 broker / execution / live-trade
- 不创建不必要的文件
- 不偏离工程手册规范
