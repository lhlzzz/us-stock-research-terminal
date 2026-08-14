#!/usr/bin/env python3
"""Live paper trading monitor - supports both LONG and SHORT positions."""

import json
import sys
from datetime import datetime, date
from pathlib import Path

RESEARCH_DIR = Path(__file__).resolve().parent.parent / "research"
TRADES_FILE = RESEARCH_DIR / "dual-paper-trades.json"
SCRIPTS_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPTS_DIR))
from data_provider import DataProvider

_PROVIDER: DataProvider | None = None


def load_trades():
    if TRADES_FILE.exists():
        return json.loads(TRADES_FILE.read_text())
    return None


def get_current_prices(symbols):
    global _PROVIDER
    if _PROVIDER is None:
        _PROVIDER = DataProvider()

    prices = {}
    wanted = {sym.upper() for sym in symbols if sym}
    try:
        quotes = _PROVIDER.fetch_batch_quotes()
        for sym in wanted:
            quote = quotes.get(sym)
            if quote and quote.get('latest_price'):
                current = float(quote['latest_price'])
                prices[sym] = {
                    'current': current,
                    'open': float(quote.get('open') or current),
                    'high': float(quote.get('high') or current),
                    'low': float(quote.get('low') or current),
                }
    except Exception:
        pass

    for sym in wanted - set(prices):
        try:
            quote, _source, _meta = _PROVIDER.fetch_realtime_quote(sym)
            if quote and quote.get('latest_price'):
                current = float(quote['latest_price'])
                prices[sym] = {
                    'current': current,
                    'open': float(quote.get('open') or current),
                    'high': float(quote.get('high') or current),
                    'low': float(quote.get('low') or current),
                }
        except Exception as e:
            print(f"Error fetching {sym}: {e}")
    return prices


def check_positions(trades, prices):
    results = []
    total_pnl = 0
    long_pnl = 0
    short_pnl = 0

    for pos in trades['positions']:
        sym = pos['symbol']
        if sym not in prices:
            continue

        entry = pos['entry_price']
        current = prices[sym]['current']
        direction = pos.get('direction', 'long').lower()

        if direction == 'short':
            # Short: profit when price goes down
            pnl_pct = (entry - current) / entry * 100
            pnl_dollar = pos['cost'] - (pos['shares'] * current)
            sl = pos.get('stop_loss_price', entry * 1.05)
            tp = pos.get('take_profit_price', entry * 0.90)
            status = 'HOLD'
            if current >= sl:
                status = 'STOP_LOSS'
            elif current <= tp:
                status = 'TAKE_PROFIT'
            short_pnl += pnl_dollar
        else:
            # Long: profit when price goes up
            pnl_pct = (current - entry) / entry * 100
            pnl_dollar = pos['shares'] * (current - entry)
            sl = pos.get('stop_loss_price', entry * 0.95)
            tp = pos.get('take_profit_price', entry * 1.10)
            status = 'HOLD'
            if current <= sl:
                status = 'STOP_LOSS'
            elif current >= tp:
                status = 'TAKE_PROFIT'
            long_pnl += pnl_dollar

        total_pnl += pnl_dollar
        results.append({
            'symbol': sym,
            'direction': direction,
            'entry': entry,
            'current': current,
            'pnl_pct': pnl_pct,
            'pnl_dollar': pnl_dollar,
            'status': status,
            'high': prices[sym]['high'],
            'low': prices[sym]['low'],
        })

    return results, total_pnl, long_pnl, short_pnl


def main():
    trades = load_trades()
    if not trades:
        print("No trades found")
        return

    symbols = [p['symbol'] for p in trades['positions']]
    prices = get_current_prices(symbols)
    results, total_pnl, long_pnl, short_pnl = check_positions(trades, prices)

    print(f"\n{'='*60}")
    print(f"Dual Direction Paper Trading Monitor - {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print(f"{'='*60}")

    # Long positions
    print(f"\n📈 LONG POSITIONS:")
    for r in results:
        if r['direction'] == 'long':
            emoji = '✅' if r['pnl_dollar'] >= 0 else '❌'
            print(f"  {emoji} {r['symbol']}: ${r['entry']:.2f} → ${r['current']:.2f} | P&L: ${r['pnl_dollar']:+.2f} ({r['pnl_pct']:+.2f}%) | {r['status']}")

    # Short positions
    print(f"\n📉 SHORT POSITIONS:")
    for r in results:
        if r['direction'] == 'short':
            emoji = '✅' if r['pnl_dollar'] >= 0 else '❌'
            print(f"  {emoji} {r['symbol']}: ${r['entry']:.2f} → ${r['current']:.2f} | P&L: ${r['pnl_dollar']:+.2f} ({r['pnl_pct']:+.2f}%) | {r['status']}")

    initial = trades['initial_capital']
    equity = initial + total_pnl

    print(f"\n💰 PORTFOLIO SUMMARY:")
    print(f"  Initial Capital: ${initial:,.2f}")
    print(f"  Current Equity: ${equity:,.2f}")
    print(f"  Total P&L: ${total_pnl:+.2f} ({(equity/initial - 1)*100:+.2f}%)")
    print(f"  Long P&L: ${long_pnl:+.2f}")
    print(f"  Short P&L: ${short_pnl:+.2f}")
    print(f"  Net Exposure: ${trades.get('long_exposure', 600) - trades.get('short_exposure', 250):.2f}")

    # Save updated record
    trades['monitor_results'] = results
    trades['total_pnl'] = total_pnl
    trades['long_pnl'] = long_pnl
    trades['short_pnl'] = short_pnl
    trades['current_equity'] = equity
    trades['last_check'] = datetime.now().isoformat()
    TRADES_FILE.write_text(json.dumps(trades, indent=2, default=str))

    # Also update DB
    try:
        sys.path.insert(0, str(Path(__file__).resolve().parent))
        from db.engine import SessionLocal
        from sqlalchemy import text

        with SessionLocal() as session:
            for r in results:
                session.execute(text("""
                    UPDATE paper_trades SET
                        current_price = :current,
                        unrealized_pnl = :pnl,
                        last_check = NOW()
                    WHERE trade_date = :trade_date AND symbol = :symbol AND status = 'open'
                """), {
                    'current': r['current'],
                    'pnl': r['pnl_dollar'],
                    'trade_date': trades['date'],
                    'symbol': r['symbol'],
                })
            session.commit()
    except Exception as e:
        print(f"DB update error: {e}")


if __name__ == "__main__":
    main()
