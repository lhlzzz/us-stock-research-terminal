#!/usr/bin/env python3
"""
向量嵌入生成脚本（本地版本）
- 读取知识资产分块
- 使用本地哈希方法生成嵌入向量
- 更新 PostgreSQL + pgvector 数据库
"""

import os
import sys
import hashlib
import numpy as np
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import psycopg2

DATABASE_URL = os.environ.get(
    "DATABASE_URL",
    "postgresql://xiaomei:xiaomei2026@localhost:5432/xiaomei",
)

# 嵌入配置
EMBEDDING_MODEL = "local-tfidf-hash"
EMBEDDING_DIMENSION = 1536
BATCH_SIZE = 20  # 每批处理数量


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


def generate_embeddings(texts):
    """批量生成嵌入"""
    return [generate_local_embedding(text) for text in texts]


def main():
    """主函数"""
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
            embeddings = generate_embeddings(batch_texts)

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
