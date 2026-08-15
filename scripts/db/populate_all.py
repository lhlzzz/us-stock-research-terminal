#!/usr/bin/env python3
"""Populate all empty database tables from existing pipeline data and EastMoney API."""
import sys
from pathlib import Path
from datetime import date, datetime

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from scripts.db.engine import SessionLocal
from scripts.db.models import (
    Universe, RealtimeQuote, FundFlow,
    LifecycleScoreboard, CeleryTask,
)
from scripts.db.crud import upsert_universe, upsert_realtime_quote, upsert_fund_flow
from scripts.data_provider import get_provider
from scripts.eastmoney_us_cdp import fetch_fund_flow
from sqlalchemy import text


def populate_universe(db):
    """Populate universe from Nasdaq-100 + S&P 500 union."""
    symbols = [
        ("AAPL", "Apple", "Technology"), ("MSFT", "Microsoft", "Technology"),
        ("GOOGL", "Alphabet", "Communication"), ("AMZN", "Amazon", "Consumer Cyclical"),
        ("NVDA", "NVIDIA", "Technology"), ("META", "Meta Platforms", "Communication"),
        ("TSLA", "Tesla", "Consumer Cyclical"), ("AVGO", "Broadcom", "Technology"),
        ("COST", "Costco", "Consumer Defensive"), ("NFLX", "Netflix", "Communication"),
        ("AMD", "AMD", "Technology"), ("ADBE", "Adobe", "Technology"),
        ("CRM", "Salesforce", "Technology"), ("CSCO", "Cisco", "Technology"),
        ("INTC", "Intel", "Technology"), ("TXN", "Texas Instruments", "Technology"),
        ("QCOM", "Qualcomm", "Technology"), ("INTU", "Intuit", "Technology"),
        ("AMAT", "Applied Materials", "Technology"), ("NOW", "ServiceNow", "Technology"),
        ("BKNG", "Booking Holdings", "Consumer Cyclical"), ("ISRG", "Intuitive Surgical", "Healthcare"),
        ("AMGN", "Amgen", "Healthcare"), ("GILD", "Gilead Sciences", "Healthcare"),
        ("REGN", "Regeneron", "Healthcare"), ("PFE", "Pfizer", "Healthcare"),
        ("MRNA", "Moderna", "Healthcare"), ("LLY", "Eli Lilly", "Healthcare"),
        ("ABT", "Abbott Labs", "Healthcare"), ("MDT", "Medtronic", "Healthcare"),
        ("JNJ", "Johnson & Johnson", "Healthcare"), ("UNH", "UnitedHealth", "Healthcare"),
        ("ABBV", "AbbVie", "Healthcare"), ("TMO", "Thermo Fisher", "Healthcare"),
        ("CAT", "Caterpillar", "Industrials"), ("DE", "Deere & Co", "Industrials"),
        ("HON", "Honeywell", "Industrials"), ("UPS", "UPS", "Industrials"),
        ("BA", "Boeing", "Industrials"), ("GE", "GE Aerospace", "Industrials"),
        ("RTX", "RTX Corp", "Industrials"), ("LMT", "Lockheed Martin", "Industrials"),
        ("GD", "General Dynamics", "Industrials"), ("NOC", "Northrop Grumman", "Industrials"),
        ("WM", "Waste Management", "Industrials"), ("ETN", "Eaton", "Industrials"),
        ("EMR", "Emerson Electric", "Industrials"), ("ITW", "Illinois Tool Works", "Industrials"),
        ("FDX", "FedEx", "Industrials"), ("CSX", "CSX Corp", "Industrials"),
        ("JPM", "JPMorgan Chase", "Financial"), ("BAC", "Bank of America", "Financial"),
        ("WFC", "Wells Fargo", "Financial"), ("GS", "Goldman Sachs", "Financial"),
        ("MS", "Morgan Stanley", "Financial"), ("BLK", "BlackRock", "Financial"),
        ("SCHW", "Charles Schwab", "Financial"), ("C", "Citigroup", "Financial"),
        ("AXP", "American Express", "Financial"), ("V", "Visa", "Financial"),
        ("MA", "Mastercard", "Financial"), ("SPGI", "S&P Global", "Financial"),
        ("MCO", "Moody's", "Financial"), ("PGR", "Progressive", "Financial"),
        ("TRV", "Travelers", "Financial"), ("CB", "Chubb", "Financial"),
        ("AON", "Aon", "Financial"), ("MMC", "Marsh McLennan", "Financial"),
        ("TGT", "Target", "Consumer Defensive"), ("WMT", "Walmart", "Consumer Defensive"),
        ("PG", "Procter & Gamble", "Consumer Defensive"), ("KO", "Coca-Cola", "Consumer Defensive"),
        ("PEP", "PepsiCo", "Consumer Defensive"), ("PM", "Philip Morris", "Consumer Defensive"),
        ("MO", "Altria", "Consumer Defensive"), ("CL", "Colgate-Palmolive", "Consumer Defensive"),
        ("KMB", "Kimberly-Clark", "Consumer Defensive"), ("GIS", "General Mills", "Consumer Defensive"),
        ("SJM", "Smucker", "Consumer Defensive"), ("HSY", "Hershey", "Consumer Defensive"),
        ("MCD", "McDonald's", "Consumer Cyclical"), ("SBUX", "Starbucks", "Consumer Cyclical"),
        ("TJX", "TJX Companies", "Consumer Cyclical"), ("ROST", "Ross Stores", "Consumer Cyclical"),
        ("LOW", "Lowe's", "Consumer Cyclical"), ("HD", "Home Depot", "Consumer Cyclical"),
        ("NKE", "Nike", "Consumer Cyclical"), ("LULU", "Lululemon", "Consumer Cyclical"),
        ("CMG", "Chipotle", "Consumer Cyclical"), ("ORLY", "O'Reilly Auto", "Consumer Cyclical"),
        ("MAR", "Marriott", "Consumer Cyclical"), ("HLT", "Hilton", "Consumer Cyclical"),
        ("DAL", "Delta Air Lines", "Consumer Cyclical"), ("UAL", "United Airlines", "Consumer Cyclical"),
        ("LUV", "Southwest Airlines", "Consumer Cyclical"), ("ABNB", "Airbnb", "Consumer Cyclical"),
        ("EXPE", "Expedia", "Consumer Cyclical"), ("PYPL", "PayPal", "Financial"),
        ("SQ", "Block Inc", "Financial"), ("COIN", "Coinbase", "Financial"),
        ("UBER", "Uber", "Industrials"), ("LYFT", "Lyft", "Industrials"),
        ("NEE", "NextEra Energy", "Utilities"), ("DUK", "Duke Energy", "Utilities"),
        ("SO", "Southern Company", "Utilities"), ("D", "Dominion Energy", "Utilities"),
        ("AEP", "American Electric Power", "Utilities"), ("EXC", "Exelon", "Utilities"),
        ("XEL", "Xcel Energy", "Utilities"), ("WEC", "WEC Energy", "Utilities"),
        ("ED", "Consolidated Edison", "Utilities"), ("AWK", "American Water Works", "Utilities"),
        ("AMT", "American Tower", "Real Estate"), ("PLD", "Prologis", "Real Estate"),
        ("CCI", "Crown Castle", "Real Estate"), ("EQIX", "Equinix", "Real Estate"),
        ("SPG", "Simon Property", "Real Estate"), ("PSA", "Public Storage", "Real Estate"),
        ("O", "Realty Income", "Real Estate"), ("WELL", "Welltower", "Real Estate"),
        ("DLR", "Digital Realty", "Real Estate"), ("AVB", "AvalonBay", "Real Estate"),
        ("LIN", "Linde", "Materials"), ("APD", "Air Products", "Materials"),
        ("SHW", "Sherwin-Williams", "Materials"), ("FCX", "Freeport-McMoRan", "Materials"),
        ("NEM", "Newmont", "Materials"), ("NUE", "Nucor", "Materials"),
        ("DOW", "Dow Inc", "Materials"), ("DD", "DuPont", "Materials"),
        ("EIX", "Edison International", "Utilities"), ("PEG", "Public Service Enterprise", "Utilities"),
        ("STX", "Seagate Technology", "Technology"), ("TER", "Teradyne", "Technology"),
        ("SWK", "Stanley Black & Decker", "Industrials"), ("SW", "Smurfit WestRock", "Materials"),
        ("TECH", "Bio-Techne", "Healthcare"), ("FLEX", "Flex Ltd", "Technology"),
        ("LRCX", "Lam Research", "Technology"), ("URI", "United Rentals", "Industrials"),
        ("MU", "Micron Technology", "Technology"), ("MRVL", "Marvell Technology", "Technology"),
        ("PANW", "Palo Alto Networks", "Technology"), ("FTNT", "Fortinet", "Technology"),
        ("SNPS", "Synopsys", "Technology"), ("CDNS", "Cadence Design", "Technology"),
        ("KLAC", "KLA Corp", "Technology"), ("ON", "ON Semiconductor", "Technology"),
        ("ALGN", "Align Technology", "Healthcare"), ("IDXX", "IDEXX Laboratories", "Healthcare"),
        ("DXCM", "DexCom", "Healthcare"), ("VRSK", "Verisk Analytics", "Industrials"),
        ("ANSS", "ANSYS", "Technology"), ("CPRT", "Copart", "Industrials"),
        ("WBD", "Warner Bros Discovery", "Communication"), ("DIS", "Disney", "Communication"),
        ("CMCSA", "Comcast", "Communication"), ("CHTR", "Charter Communications", "Communication"),
        ("TMUS", "T-Mobile", "Communication"), ("VZ", "Verizon", "Communication"),
        ("T", "AT&T", "Communication"), ("EA", "Electronic Arts", "Communication"),
        ("TTWO", "Take-Two Interactive", "Communication"), ("ROKU", "Roku", "Communication"),
    ]
    added = 0
    for sym, name, sector in symbols:
        upsert_universe(db, sym, name, sector)
        added += 1
    print(f"  Universe: {added} symbols added")


def populate_realtime_quotes(db):
    """Fetch and store current realtime quotes."""
    rows = db.execute(text("SELECT symbol FROM universe")).fetchall()
    symbols = [r[0] for r in rows]

    now = datetime.utcnow()
    total = 0
    provider = get_provider()
    for sym in symbols[:30]:
        try:
            q, _source, _metadata = provider.fetch_realtime_quote(sym)
            if q and q.get("latest_price"):
                upsert_realtime_quote(db, sym, now,
                    latest_price=q.get("latest_price"),
                    prev_close=q.get("prev_close"),
                    open=q.get("open"), high=q.get("high"), low=q.get("low"),
                    volume=int(q.get("volume", 0)), amount=q.get("amount"),
                    pct_chg=q.get("pct_chg"),
                    pe_ttm=q.get("pe_ttm"), roe=q.get("roe"),
                    dividend_yield=q.get("dividend_yield"),
                    week52_high=q.get("week52_high"), week52_low=q.get("week52_low"))
                total += 1
        except Exception:
            pass
    print(f"  Realtime quotes: {total} rows")


def populate_fund_flow(db):
    """Fetch and store fund flow data."""
    rows = db.execute(text("SELECT symbol FROM universe")).fetchall()
    symbols = [r[0] for r in rows]

    total = 0
    for sym in symbols[:20]:
        try:
            ff = fetch_fund_flow(sym)
            if ff:
                upsert_fund_flow(db, sym, date.today(),
                    net_inflow_5d=ff.get("net_inflow_5d"),
                    score=ff.get("score"))
                total += 1
        except Exception:
            pass
    print(f"  Fund flow: {total} rows")


def populate_lifecycle_scoreboard(db):
    """Compute and store lifecycle scoreboard from forward_tracking data."""
    import json
    result = db.execute(text("""
        SELECT COUNT(*) as total,
               COUNT(CASE WHEN forward_return > 0 THEN 1 END) as wins,
               AVG(forward_return) as avg_return,
               PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY forward_return) as median_return
        FROM forward_tracking WHERE check_status = 'completed'
    """)).fetchone()

    overall = {
        "completed_rows": result[0] if result else 0,
        "win_rate": round((result[1] / result[0] * 100), 2) if result and result[0] else 0,
        "avg_forward_return": round(float(result[2]) * 100, 6) if result and result[2] else 0,
        "median_forward_return": round(float(result[3]) * 100, 6) if result and result[3] else 0,
    }

    horizon_rows = db.execute(text("""
        SELECT horizon_days, COUNT(*) as total,
               COUNT(CASE WHEN forward_return > 0 THEN 1 END) as wins,
               AVG(forward_return) as avg_return
        FROM forward_tracking WHERE check_status = 'completed'
        GROUP BY horizon_days ORDER BY horizon_days
    """)).fetchall()

    by_horizon = {}
    for row in horizon_rows:
        by_horizon[f"{row[0]}d"] = {
            "count": row[1],
            "win_rate": round((row[2] / row[1] * 100), 2) if row[1] else 0,
            "avg_return": round(float(row[3]) * 100, 4) if row[3] else 0,
        }

    from scripts.db.models import LifecycleScoreboard
    obj = LifecycleScoreboard(
        overall=overall,
        by_horizon=by_horizon,
    )
    db.add(obj)
    db.commit()
    print(f"  Lifecycle scoreboard: overall={overall['win_rate']}% win rate")


def main():
    db = SessionLocal()
    try:
        print("=== Populating empty DB tables ===")
        print("\n1. Universe:")
        populate_universe(db)

        print("\n2. Realtime quotes:")
        populate_realtime_quotes(db)

        print("\n3. Fund flow:")
        populate_fund_flow(db)

        print("\n4. Daily klines (EastMoney push2):")
        print("\n5. Lifecycle scoreboard:")
        populate_lifecycle_scoreboard(db)

        print("\n=== Final counts ===")
        for t in ['universe','realtime_quotes','fund_flow','lifecycle_scoreboard']:
            c = db.execute(text(f"SELECT COUNT(*) FROM {t}")).scalar()
            print(f"  {t}: {c}")
    finally:
        db.close()


if __name__ == "__main__":
    main()
