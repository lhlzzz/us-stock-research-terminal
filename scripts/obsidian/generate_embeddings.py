#!/usr/bin/env python3
"""
向量嵌入生成脚本
- 读取知识资产分块
- 调用 OpenAI API 生成嵌入
- 更新数据库
"""

import os
import sys
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import psycopg2
from psycopg2.extras import execute_values

# 配置
DB_CONFIG = {
    "dbname": "xiaomei",
    "user": "postgres",
    "password": "postgres",
    "host": "localhost"
}

# OpenAI 配置（需要设置环境变量 OPENAI_API_KEY）
EMBEDDING_MODEL = "text-embedding-ada-002"
EMBEDDING_DIMENSION = 1536
BATCH_SIZE = 20  # 每批处理数量


def get_db_conn():
    return psycopg2.connect(**DB_CONFIG)


def get_openai_client():
    """获取 OpenAI 客户端"""
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        print("[ERROR] 未设置 OPENAI_API_KEY 环境变量")
        print("  export OPENAI_API_KEY='your-api-key'")
        return None
    
    from openai import OpenAI
    return OpenAI(api_key=api_key)


def generate_embeddings(client, texts):
    """批量生成嵌入"""
    response = client.embeddings.create(
        model=EMBEDDING_MODEL,
        input=texts
    )
    return [item.embedding for item in response.data]


def main():
    """主函数"""
    client = get_openai_client()
    if not client:
        sys.exit(1)
    
    conn = get_db_conn()
    cur = conn.cursor()
    
    # 获取未生成嵌入的分块
    cur.execute("""
        SELECT ke.id, ke.chunk_text
        FROM knowledge_embeddings ke
        WHERE ke.embedding IS NULL
        ORDER BY ke.id
        LIMIT 1000
    """)
    
    chunks = cur.fetchall()
    print(f"待处理分块: {len(chunks)}")
    
    if not chunks:
        print("没有需要处理的分块")
        return
    
    # 批量处理
    processed = 0
    for i in range(0, len(chunks), BATCH_SIZE):
        batch = chunks[i:i + BATCH_SIZE]
        batch_ids = [c[0] for c in batch]
        batch_texts = [c[1] for c in batch]
        
        try:
            embeddings = generate_embeddings(client, batch_texts)
            
            # 更新数据库
            for chunk_id, embedding in zip(batch_ids, embeddings):
                cur.execute("""
                    UPDATE knowledge_embeddings 
                    SET embedding = %s, model = %s
                    WHERE id = %s
                """, (str(embedding), EMBEDDING_MODEL, chunk_id))
            
            conn.commit()
            processed += len(batch)
            print(f"  已处理: {processed}/{len(chunks)}")
            
        except Exception as e:
            print(f"  [ERROR] 批处理失败: {e}")
            conn.rollback()
    
    cur.close()
    conn.close()
    
    print(f"\n完成: {processed} 个分块已生成嵌入")


if __name__ == "__main__":
    main()
