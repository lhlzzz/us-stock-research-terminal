# Obsidian 知识资产同步配置

## 当前配置（WSL 直接挂载）

已配置为直接访问 Windows 路径，无需 Git 同步：
- `Project` → `/mnt/d/obisidian/Obsidian/Project` (美股研究)
- `神临` → `/mnt/d/obisidian/Obsidian/神临` (全项目)

## 使用命令

### 同步知识资产
```bash
# 同步 Obsidian 文件到数据库（实时读取 Windows 文件）
python3 scripts/obsidian/sync_obsidian.py
```

### 生成向量嵌入（需要 OpenAI API Key）
```bash
# 设置 API Key
export OPENAI_API_KEY="sk-your-api-key"

# 生成嵌入
python3 scripts/obsidian/generate_embeddings.py
```

### 搜索知识资产
```bash
# 搜索相关知识
python3 scripts/obsidian/search_knowledge.py "美股量化策略"

# 指定返回数量
python3 scripts/obsidian/search_knowledge.py "动量因子" --top 10

# 按类型筛选
python3 scripts/obsidian/search_knowledge.py "回测" --type us_stock
```

## 数据库查询

```sql
-- 查看知识资产统计
SELECT source_type, COUNT(*) as count 
FROM knowledge_assets 
GROUP BY source_type;

-- 查看向量嵌入统计
SELECT 
    ka.source_type,
    COUNT(DISTINCT ka.id) as assets,
    COUNT(ke.id) as chunks,
    COUNT(ke.embedding) as embeddings
FROM knowledge_assets ka
LEFT JOIN knowledge_embeddings ke ON ka.id = ke.asset_id
GROUP BY ka.source_type;
```

## 定时同步（可选）

```bash
# 每小时同步一次
0 * * * * cd /workspace/hermes-workspaces/xiaomei && python3 scripts/obsidian/sync_obsidian.py >> /var/log/obsidian_sync.log 2>&1
```
