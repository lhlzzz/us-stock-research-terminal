#!/usr/bin/env python3
"""
向量搜索脚本（本地版本）
- 接收查询文本
- 使用本地方法生成查询向量
- 搜索最相关的知识资产
"""

import os
import sys
import hashlib
import numpy as np
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import psycopg2

from db.engine import DATABASE_URL

EMBEDDING_DIMENSION = 1536


def get_db_conn():
    return psycopg2.connect(DATABASE_URL)


def generate_local_embedding(text):
    """使用本地方法生成嵌入向量"""
    # 使用文本的哈希值生成确定性向量
    text_hash = hashlib.sha512(text.encode('utf-8')).hexdigest()

    # 将哈希值转换为向量
    vector = []
    for i in range(0, len(text_hash), 2):
        if len(vector) >= EMBEDDING_DIMENSION:
            break
        # 每两个字符转换为一个浮点数
        hex_pair = text_hash[i:i+2]
        value = int(hex_pair, 16) / 255.0  # 归一化到0-1
        vector.append(value)

    # 如果向量不够长，用0填充
    while len(vector) < EMBEDDING_DIMENSION:
        vector.append(0.0)

    # 归一化向量
    vector_array = np.array(vector[:EMBEDDING_DIMENSION])
    norm = np.linalg.norm(vector_array)
    if norm > 0:
        vector_array = vector_array / norm

    return vector_array.tolist()


def search_knowledge(query, top_k=5, source_type=None):
    """搜索知识资产"""
    # 生成查询向量
    query_embedding = generate_local_embedding(query)

    conn = get_db_conn()
    cur = conn.cursor()

    # 向量搜索
    sql = """
        SELECT
            ka.id,
            ka.title,
            ka.source_path,
            ka.source_type,
            ka.metadata->>'directory' as directory,
            ke.chunk_text,
            1 - (ke.embedding <=> %s::vector) as similarity
        FROM knowledge_embeddings ke
        JOIN knowledge_assets ka ON ke.asset_id = ka.id
        WHERE ke.embedding IS NOT NULL
    """

    params = [str(query_embedding)]

    if source_type:
        sql += " AND ka.source_type = %s"
        params.append(source_type)

    sql += """
        ORDER BY ke.embedding <=> %s::vector
        LIMIT %s
    """
    params.extend([str(query_embedding), top_k])

    cur.execute(sql, params)
    results = cur.fetchall()

    cur.close()
    conn.close()

    return results


def format_results(results):
    """格式化搜索结果"""
    if not results:
        return "未找到相关知识资产"

    output = []
    for i, (id, title, path, source_type, directory, chunk, similarity) in enumerate(results, 1):
        output.append(f"[{i}] {title}")
        output.append(f"    类型: {source_type} | 目录: {directory}")
        output.append(f"    路径: {path}")
        output.append(f"    相似度: {similarity:.4f}")
        output.append(f"    内容: {chunk[:200]}...")
        output.append("")

    return "\n".join(output)


def main():
    """命令行入口"""
    if len(sys.argv) < 2:
        print("用法: python search_knowledge.py <查询文本> [--top N] [--type TYPE]")
        print("示例: python search_knowledge.py '美股量化策略' --top 5")
        sys.exit(1)

    query = sys.argv[1]
    top_k = 5
    source_type = None

    # 解析参数
    i = 2
    while i < len(sys.argv):
        if sys.argv[i] == "--top" and i + 1 < len(sys.argv):
            top_k = int(sys.argv[i + 1])
            i += 2
        elif sys.argv[i] == "--type" and i + 1 < len(sys.argv):
            source_type = sys.argv[i + 1]
            i += 2
        else:
            i += 1

    print(f"查询: {query}")
    print(f"返回: {top_k} 条结果")
    if source_type:
        print(f"类型: {source_type}")
    print("-" * 60)

    results = search_knowledge(query, top_k, source_type)
    print(format_results(results))


if __name__ == "__main__":
    main()
