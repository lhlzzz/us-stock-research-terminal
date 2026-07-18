import psycopg2

conn = psycopg2.connect(
    host="localhost",
    port=5432,
    database="xiaomei",
    user="xiaomei",
    password="xiaomei2026"
)

cur = conn.cursor()
cur.execute("""
    SELECT symbol, horizon_days, forward_return, loss_reason
    FROM forward_tracking 
    WHERE check_status = 'completed'
""")

results = cur.fetchall()
wins = 0
losses = 0
total_return = 0

for row in results:
    symbol, horizon, return_val, reason = row
    if return_val and return_val > 0:
        wins += 1
    elif return_val and return_val < 0:
        losses += 1
    if return_val:
        total_return += return_val

print(f"总记录数: {len(results)}")
print(f"盈利记录: {wins}")
print(f"亏损记录: {losses}")
print(f"总收益率: {total_return:.2%}")
print(f"胜率: {wins/len(results):.2%}" if results else "无数据")

cur.close()
conn.close()
