#!/usr/bin/env python3
"""Generate both LONG and SHORT signals for paper trading.

LONG: High ticket_score (>0.6) - buy expecting price increase
SHORT: Low momentum stocks with negative trend - short expecting price decrease
"""

import json
import sys
from datetime import date, datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from data_provider import DataProvider

# Stocks with consistently poor performance in backtest
BEARISH_UNIVERSE = [
    "NVDA",   # 1.06% win rate, -4.71% avg return
    "TSLA",   # 18.75% win rate, -4.44% avg return
    "AMD",    # 26.09% win rate, -3.92% avg return
    "HOOD",   # 12.5% win rate, -10.45% avg return
    "MRNA",   # 12.5% win rate, -11.22% avg return
    "NBIS",   # 0% win rate, -13.90% avg return
    "APP",    # 0% win rate, -7.72% avg return
    "STX",    # 0% win rate, -7.26% avg return
]

_PROVIDER: DataProvider | None = None


def _provider() -> DataProvider:
    global _PROVIDER
    if _PROVIDER is None:
        _PROVIDER = DataProvider()
    return _PROVIDER


def _current_price(symbol: str) -> float | None:
    quote, _source, _meta = _provider().fetch_realtime_quote(symbol)
    if quote and quote.get("latest_price"):
        return float(quote["latest_price"])
    return None


def _recent_closes(symbol: str, lookback_days: int = 45) -> list[float]:
    end = date.today()
    beg = end - timedelta(days=lookback_days)
    rows, _source, _meta = _provider().fetch_klines(
        symbol,
        beg.strftime("%Y-%m-%d"),
        end.strftime("%Y-%m-%d"),
    )
    closes = [float(row["close"]) for row in rows if row.get("close")]
    return closes

def get_bearish_signals():
    """Identify stocks with negative momentum for short selling."""
    signals = []
    for sym in BEARISH_UNIVERSE:
        try:
            closes = _recent_closes(sym)
            if len(closes) < 5:
                continue

            current = closes[-1]
            week_ago = closes[-5]
            month_ago = closes[0]

            week_change = (current - week_ago) / week_ago
            month_change = (current - month_ago) / month_ago

            # Bearish if both week and month are negative
            if week_change < -0.03 and month_change < -0.05:
                signals.append({
                    "symbol": sym,
                    "direction": "SHORT",
                    "entry_price": current,
                    "week_change_pct": round(week_change * 100, 2),
                    "month_change_pct": round(month_change * 100, 2),
                    "bearish_score": round(abs(week_change + month_change) * 10, 2),
                    "stop_loss_price": round(current * 1.05, 2),  # +5% stop-loss for short
                    "take_profit_price": round(current * 0.90, 2),  # -10% take-profit for short
                })
        except Exception as e:
            print(f"Error fetching {sym}: {e}")

    # Sort by bearish_score descending
    signals.sort(key=lambda x: x["bearish_score"], reverse=True)
    return signals


def get_bullish_signals():
    """Get today's pipeline signals (already in DB)."""
    from db.engine import SessionLocal
    from sqlalchemy import text

    with SessionLocal() as session:
        result = session.execute(text("""
            SELECT symbol, ticket_score, market_score, catalyst_score, classification
            FROM tickets
            WHERE output_date = CURRENT_DATE AND classification = 'CANDIDATE_FOR_PAPER_REVIEW'
            ORDER BY ticket_score DESC
            LIMIT 3
        """))
        rows = result.fetchall()

    signals = []
    for row in rows:
        sym = row[0]
        try:
            current = _current_price(sym)
            if not current:
                continue
            signals.append({
                "symbol": sym,
                "direction": "LONG",
                "entry_price": current,
                "ticket_score": float(row[1]),
                "market_score": float(row[2]),
                "catalyst_score": float(row[3]),
                "classification": row[4],
                "stop_loss_price": round(current * 0.95, 2),  # -5% stop-loss
                "take_profit_price": round(current * 1.10, 2),  # +10% take-profit
            })
        except Exception as e:
            print(f"Error fetching {sym}: {e}")

    return signals


def main():
    print("="*60)
    print(f"Dual Direction Signal Generator - {date.today().isoformat()}")
    print("="*60)

    print("\n📈 BULLISH SIGNALS (LONG):")
    bullish = get_bullish_signals()
    for s in bullish:
        print(f"  {s['symbol']}: ${s['entry_price']:.2f} | Score: {s.get('ticket_score', 'N/A')} | SL: ${s['stop_loss_price']:.2f} | TP: ${s['take_profit_price']:.2f}")

    print("\n📉 BEARISH SIGNALS (SHORT):")
    bearish = get_bearish_signals()
    for s in bearish:
        print(f"  {s['symbol']}: ${s['entry_price']:.2f} | Week: {s['week_change_pct']:+.2f}% | Month: {s['month_change_pct']:+.2f}% | Bearish: {s['bearish_score']}")

    # Combine
    all_signals = bullish + bearish[:3]  # Top 3 bearish

    output = {
        "date": date.today().isoformat(),
        "generated_at": datetime.now().isoformat(),
        "bullish_count": len(bullish),
        "bearish_count": len(bearish),
        "signals": all_signals,
    }

    output_path = Path("research/dual-direction-signals.json")
    output_path.write_text(json.dumps(output, indent=2))
    print(f"\nSaved: {output_path}")

    return output


if __name__ == "__main__":
    main()
