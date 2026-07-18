"""K-line fetch tasks."""
from datetime import date, datetime
from scripts.tasks.celery_app import app


@app.task(bind=True, max_retries=3, default_retry_delay=60)
def fetch_daily_klines(self, symbols: list[str] = None):
    """Fetch daily klines for universe symbols and store in PostgreSQL."""
    from scripts.db.engine import SessionLocal
    from scripts.db.crud import upsert_kline
    from scripts.eastmoney_us_cdp import fetch_realtime_quote

    db = SessionLocal()
    try:
        if not symbols:
            from scripts.db.crud import get_all_symbols
            symbols = get_all_symbols(db)

        today = date.today()
        fetched = 0
        for sym in symbols:
            try:
                q = fetch_realtime_quote(sym)
                if q and q.get("latest_price") and q.get("prev_close"):
                    upsert_kline(db, sym, today,
                                 open=q.get("open"),
                                 high=q.get("high"),
                                 low=q.get("low"),
                                 close=q["latest_price"],
                                 adj_close=q["latest_price"],
                                 volume=int(q.get("volume", 0)),
                                 amount=q.get("amount"),
                                 pct_chg=q.get("pct_chg"),
                                 source="eastmoney_cdp")
                    fetched += 1
            except Exception as e:
                print(f"Error fetching {sym}: {e}")
                continue

        db.commit()
        return {"status": "done", "fetched": fetched, "total": len(symbols), "date": str(today)}
    except Exception as exc:
        db.rollback()
        self.retry(exc=exc)
    finally:
        db.close()
