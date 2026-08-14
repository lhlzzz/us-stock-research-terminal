#!/usr/bin/env python3
"""
Obsidian 知识资产同步脚本
- 从 Git 仓库拉取 Obsidian 知识资产
- 解析 Markdown 文件
- 生成向量嵌入并存入 PostgreSQL
"""

import os
import sys
import hashlib
import json
import subprocess
from pathlib import Path
from datetime import datetime
from urllib.parse import urlparse

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import psycopg2

# 配置 - 直接挂载 Windows 路径
OBSIDIAN_REPOS = {
    "project": {
        "url": None,  # 直接挂载，无需 Git
        "local_path": "/mnt/d/obisidian/Obsidian/Project",
        "type": "us_stock",
        "include_dirs": ["美股", "xiaomei-trades"],
    },
    "shenlin": {
        "url": None,  # 直接挂载，无需 Git
        "local_path": "/mnt/d/obisidian/Obsidian/神临",
        "type": "all_projects",
        "include_name_contains": ["xiaomei", "美股"],
    }
}

DATABASE_URL = os.environ.get(
    "DATABASE_URL", "postgresql://xiaomei:xiaomei2026@localhost:5432/xiaomei"
)


def get_db_conn():
    """获取数据库连接"""
    parsed = urlparse(DATABASE_URL)
    return psycopg2.connect(
        dbname=parsed.path.lstrip("/"),
        user=parsed.username,
        password=parsed.password,
        host=parsed.hostname or "localhost",
        port=parsed.port or 5432,
    )


def clone_or_pull(repo_config):
    """克隆或更新 Git 仓库（直接挂载模式跳过）"""
    local_path = Path(repo_config["local_path"])
    url = repo_config["url"]

    # 直接挂载模式
    if not url:
        if local_path.exists():
            print(f"  [MOUNT] 直接挂载 Windows 路径")
            return True
        else:
            print(f"  [ERROR] 路径不存在: {local_path}")
            return False

    if local_path.exists():
        # Pull 更新
        print(f"  Pulling updates...")
        result = subprocess.run(
            ["git", "pull"],
            cwd=str(local_path),
            capture_output=True,
            text=True
        )
        if result.returncode != 0:
            print(f"  [ERROR] Git pull failed: {result.stderr}")
            return False
    else:
        # Clone 新仓库
        print(f"  Cloning repository...")
        local_path.parent.mkdir(parents=True, exist_ok=True)
        result = subprocess.run(
            ["git", "clone", url, str(local_path)],
            capture_output=True,
            text=True
        )
        if result.returncode != 0:
            print(f"  [ERROR] Git clone failed: {result.stderr}")
            return False

    return True


def scan_markdown_files(base_path, include_dirs=None, include_name_contains=None):
    """扫描所有 Markdown 文件"""
    md_files = []
    base = Path(base_path)

    if not base.exists():
        return md_files

    for md_file in base.rglob("*.md"):
        # 跳过 .obsidian 配置目录
        if ".obsidian" in str(md_file):
            continue
        rel = md_file.relative_to(base)
        rel_parts = rel.parts
        rel_text = str(rel).lower()
        if include_dirs and (not rel_parts or rel_parts[0] not in include_dirs):
            continue
        if include_name_contains:
            needles = [item.lower() for item in include_name_contains]
            if not any(item in rel_text for item in needles):
                continue
        md_files.append(md_file)

    return md_files


def compute_content_hash(content):
    """计算内容 hash"""
    return hashlib.sha256(content.encode('utf-8')).hexdigest()


def extract_title(content, filepath):
    """从内容或文件名提取标题"""
    lines = content.strip().split('\n')
    for line in lines[:5]:
        if line.startswith('# '):
            return line[2:].strip()
    return filepath.stem


def extract_metadata(content, filepath):
    """提取元数据（YAML frontmatter）"""
    metadata = {
        "file_path": str(filepath),
        "file_name": filepath.name,
        "directory": str(filepath.parent.name)
    }

    # 解析 YAML frontmatter
    if content.startswith('---'):
        try:
            end_idx = content.index('---', 3)
            frontmatter = content[3:end_idx].strip()
            for line in frontmatter.split('\n'):
                if ':' in line:
                    key, value = line.split(':', 1)
                    metadata[key.strip()] = value.strip()
        except ValueError:
            pass

    return metadata


def chunk_text(text, chunk_size=1000, overlap=200):
    """文本分块"""
    chunks = []
    start = 0
    text_len = len(text)

    while start < text_len:
        end = start + chunk_size

        # 尝试在句子边界分割
        if end < text_len:
            # 找最近的句号、换行或空格
            for sep in ['\n\n', '\n', '。', '.', '！', '!', '？', '?']:
                last_sep = text[start:end].rfind(sep)
                if last_sep > chunk_size * 0.5:
                    end = start + last_sep + len(sep)
                    break

        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)

        start = end - overlap
        if start >= text_len:
            break

    return chunks


def sync_to_database(repo_name, repo_config):
    """同步知识资产到数据库"""
    local_path = Path(repo_config["local_path"])
    asset_type = repo_config["type"]

    if not local_path.exists():
        print(f"  [SKIP] 目录不存在: {local_path}")
        return 0

    md_files = scan_markdown_files(
        local_path,
        include_dirs=repo_config.get("include_dirs"),
        include_name_contains=repo_config.get("include_name_contains"),
    )
    print(f"  找到 {len(md_files)} 个 Markdown 文件")

    conn = get_db_conn()
    cur = conn.cursor()

    synced_count = 0

    for md_file in md_files:
        try:
            content = md_file.read_text(encoding='utf-8')
            content_hash = compute_content_hash(content)
            relative_path = str(md_file.relative_to(local_path))
            source_path = f"obsidian/{repo_name}/{relative_path}"

            # 检查是否已存在且未变化
            cur.execute(
                "SELECT id, content_hash FROM knowledge_assets WHERE source_path = %s",
                (source_path,)
            )
            existing = cur.fetchone()

            if existing and existing[1] == content_hash:
                continue  # 内容未变化，跳过

            title = extract_title(content, md_file)
            metadata = extract_metadata(content, md_file)
            metadata["repo"] = repo_name

            if existing:
                # 更新现有记录
                cur.execute("""
                    UPDATE knowledge_assets
                    SET title = %s, content = %s, metadata = %s,
                        content_hash = %s, updated_at = NOW()
                    WHERE id = %s
                """, (title, content, json.dumps(metadata), content_hash, existing[0]))
                asset_id = existing[0]

                # 删除旧的嵌入
                cur.execute("DELETE FROM knowledge_embeddings WHERE asset_id = %s", (asset_id,))
            else:
                # 插入新记录
                cur.execute("""
                    INSERT INTO knowledge_assets (source_path, source_type, title, content, metadata, content_hash)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    RETURNING id
                """, (source_path, asset_type, title, content, json.dumps(metadata), content_hash))
                asset_id = cur.fetchone()[0]

            # 生成文本分块（嵌入需要 API key，这里只存储分块）
            chunks = chunk_text(content)
            for i, chunk in enumerate(chunks):
                cur.execute("""
                    INSERT INTO knowledge_embeddings (asset_id, chunk_index, chunk_text)
                    VALUES (%s, %s, %s)
                """, (asset_id, i, chunk))

            synced_count += 1

        except Exception as e:
            print(f"  [ERROR] 处理文件失败 {md_file}: {e}")

    conn.commit()
    cur.close()
    conn.close()

    return synced_count


def main():
    """主函数"""
    print("=" * 60)
    print("Obsidian 知识资产同步")
    print("=" * 60)
    print(f"时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()

    total_synced = 0

    for repo_name, repo_config in OBSIDIAN_REPOS.items():
        print(f"[{repo_name}]")
        print(f"  类型: {repo_config['type']}")
        print(f"  路径: {repo_config['local_path']}")

        # 同步 Git 仓库
        if clone_or_pull(repo_config):
            # 同步到数据库
            count = sync_to_database(repo_name, repo_config)
            print(f"  同步: {count} 个文件")
            total_synced += count

        print()

    print("=" * 60)
    print(f"总计同步: {total_synced} 个文件")
    print("=" * 60)


if __name__ == "__main__":
    main()
