#!/usr/bin/env python3
"""
向量搜索脚本
- 接收查询文本
- 生成查询向量
- 搜索最相关的知识资产
"""

import os
import sys
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import psycopg2

DB_CONFIG = {
    "dbname": "xiaomei",
    "user": "postgres",
    "password": "postgres",
    "host": "localhost"
}


def get_db_conn():
    return psycopg2.connect(**DB_CONFIG)


def get_openai_client():
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        return None
    from openai import OpenAI
    return OpenAI(api_key=api_key)


def search_knowledge(query, top_k=5, source_type=None):
    """搜索知识资产"""
    client = get_openai_client()
    if not client:
        print("[ERROR] 未设置 OPENAI_API_KEY")
        return []
    
    # 生成查询向量
    response = client.embeddings.create(
        model="text-embedding-ada-002",
        input=query
    )
    query_embedding = response.data[0].embedding
    
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
