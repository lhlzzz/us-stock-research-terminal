#!/usr/bin/env python3
"""Realtime paper trading runner for xiaomei.

Continuously monitors positions, executes orders, manages SL/TP.
Designed to run in tmux during market hours.

Usage:
    python3 scripts/realtime_runner.py                    # run once (for cron)
    python3 scripts/realtime_runner.py --loop             # continuous loop
    python3 scripts/realtime_runner.py --tick 30          # 30s tick interval
    python3 scripts/realtime_runner.py --close-positions  # close all positions
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path

from sqlalchemy import text

SCRIPTS_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPTS_DIR))
from db.engine import SessionLocal
from data_provider import DataProvider
from trading_engine import TradingEngine, OrderSide, OrderType

ROOT = SCRIPTS_DIR.parent
TRADES_FILE = ROOT / "research" / "dual-paper-trades.json"
ENGINE_STATE = ROOT / "research" / "engine-state.json"
TRADE_LOG = ROOT / "research" / "trade-log.jsonl"

BJT = timezone(timedelta(hours=8))
ET = timezone(timedelta(hours=-4))
_DATA_PROVIDER: DataProvider | None = None


def _now_bjt() -> datetime:
    return datetime.now(BJT)


def _now_et() -> datetime:
    return datetime.now(ET)


def _is_market_open() -> bool:
    et = _now_et()
    if et.weekday() >= 5:
        return False
    market_open = et.replace(hour=9, minute=30, second=0, microsecond=0)
    market_close = et.replace(hour=16, minute=0, second=0, microsecond=0)
    return market_open <= et <= market_close


def _fetch_prices(symbols: list[str]) -> dict[str, float]:
    """Fetch current prices through the project-owned data provider."""
    global _DATA_PROVIDER
    prices: dict[str, float] = {}
    wanted = {s.upper() for s in symbols if s}
    if not wanted:
        return prices
    if _DATA_PROVIDER is None:
        _DATA_PROVIDER = DataProvider()

    try:
        batch_quotes = _DATA_PROVIDER.fetch_batch_quotes()
        for sym in wanted:
            quote = batch_quotes.get(sym)
            if quote and quote.get("latest_price"):
                prices[sym] = float(quote["latest_price"])
    except Exception:
        pass

    for sym in wanted - set(prices):
        try:
            quote, _source, _meta = _DATA_PROVIDER.fetch_realtime_quote(sym)
            if quote and quote.get("latest_price"):
                prices[sym] = float(quote["latest_price"])
        except Exception:
            pass
    return prices


def _get_today_tickets() -> list[dict]:
    """Get today's tickets from DB (latest date)."""
    with SessionLocal() as session:
        result = session.execute(text("""
            SELECT symbol, ticket_score, market_score, catalyst_score,
                   classification, risk_verdict, output_date
            FROM tickets
            WHERE output_date = (SELECT MAX(output_date) FROM tickets)
            ORDER BY ticket_score DESC
        """))
        cols = result.keys()
        return [dict(zip(cols, row)) for row in result.fetchall()]


def _log_trade(entry: dict):
    TRADE_LOG.parent.mkdir(parents=True, exist_ok=True)
    with open(TRADE_LOG, "a") as f:
        f.write(json.dumps(entry, default=str) + "\n")


def migrate_from_json(engine: TradingEngine):
    """Migrate existing dual-paper-trades.json positions into the engine."""
    if not TRADES_FILE.exists():
        return

    data = json.loads(TRADES_FILE.read_text())
    if not data.get("positions"):
        return

    # Only migrate if engine has no positions yet
    if engine.positions:
        return

    print("[MIGRATE] Importing positions from dual-paper-trades.json...")
    for pos in data["positions"]:
        sym = pos["symbol"]
        direction = pos.get("direction", "LONG").upper()
        entry_price = pos["entry_price"]
        shares = pos["shares"]
        cost = pos["cost"]

        if direction == "SHORT":
            from trading_engine import Position, PositionSide
            engine.positions[sym] = Position(
                symbol=sym,
                side=PositionSide.SHORT,
                quantity=shares,
                avg_price=entry_price,
                cost_basis=cost,
                current_price=entry_price,
                stop_loss_price=pos.get("stop_loss_price", 0),
                take_profit_price=pos.get("take_profit_price", 0),
                opened_at=datetime.now(BJT).isoformat(),
            )
        else:
            from trading_engine import Position, PositionSide
            engine.positions[sym] = Position(
                symbol=sym,
                side=PositionSide.LONG,
                quantity=shares,
                avg_price=entry_price,
                cost_basis=cost,
                current_price=entry_price,
                stop_loss_price=pos.get("stop_loss_price", 0),
                take_profit_price=pos.get("take_profit_price", 0),
                opened_at=datetime.now(BJT).isoformat(),
            )

    engine.cash = data.get("cash", 0)
    engine._save_state()
    print(f"[MIGRATE] Done: {len(engine.positions)} positions, cash=${engine.cash:.2f}")


def run_once(engine: TradingEngine, verbose: bool = True) -> dict:
    """Single tick: fetch prices, execute orders, check SL/TP, log state."""
    symbols = list(engine.positions.keys())

    # Also check open orders' symbols
    for order in engine.open_orders:
        if order.symbol not in symbols:
            symbols.append(order.symbol)

    prices = _fetch_prices(symbols) if symbols else {}

    # Execute pending orders
    fills = engine.execute_orders(prices)

    # Log fills
    for fill in fills:
        _log_trade({
            "event": "FILL",
            "fill_id": fill.fill_id,
            "symbol": fill.symbol,
            "side": fill.side,
            "quantity": fill.quantity,
            "price": fill.price,
            "commission": fill.commission,
            "reason": fill.reason,
            "timestamp": fill.timestamp,
        })
        emoji = "🟢" if fill.side == "BUY" else "🔴"
        print(f"  {emoji} FILL: {fill.side} {fill.quantity:.2f} {fill.symbol} @ ${fill.price:.2f} "
              f"(fee=${fill.commission+fill.sec_fee+fill.finra_fee:.2f}) [{fill.reason}]")

    # Update positions with current prices
    for sym, pos in engine.positions.items():
        if sym in prices:
            pos.update_price(prices[sym])

    engine._update_equity(prices)
    engine._save_state()  # persist latest prices even when no fills
    state = engine.get_state()

    if verbose:
        equity = state["equity"]
        pnl = state["total_pnl"]
        pnl_pct = state["total_pnl_pct"]
        print(f"\n{'='*60}")
        print(f"  xiaomei 实时模拟盘 — {_now_bjt().strftime('%Y-%m-%d %H:%M')}")
        print(f"{'='*60}")
        print(f"  权益: ${equity:,.2f}  P&L: ${pnl:+.2f} ({pnl_pct:+.2f}%)")
        print(f"  持仓: {state['position_count']}  现金: ${state['cash']:.2f}")
        print(f"  成交: {state['total_fills']}笔  费用: ${state['total_fees']:.2f}")
        print(f"  胜率: {state['win_rate']}%  最大回撤: {state['max_drawdown']:.2f}%")

        if engine.positions:
            print(f"\n  {'标的':<8} {'方向':<6} {'入场':>10} {'现价':>10} {'P&L%':>8} {'止损':>10} {'止盈':>10}")
            print(f"  {'-'*72}")
            for sym, pos in engine.positions.items():
                sl = f"${pos.stop_loss_price:.2f}" if pos.stop_loss_price > 0 else "--"
                tp = f"${pos.take_profit_price:.2f}" if pos.take_profit_price > 0 else "--"
                print(f"  {sym:<8} {pos.side.value:<6} ${pos.avg_price:>8.2f} "
                      f"${pos.current_price:>8.2f} {pos.unrealized_pnl_pct:>+7.2f}% {sl:>10} {tp:>10}")

        if state["halted"]:
            print(f"\n  ⚠️  ENGINE HALTED: {state['halt_reason']}")

    # Push to dashboard after each tick
    try:
        import subprocess
        subprocess.run(
            [sys.executable, str(SCRIPTS_DIR / "push_to_dashboard.py")],
            capture_output=True, timeout=10,
        )
    except Exception:
        pass  # Don't fail the tick if dashboard push fails

    return state


def run_loop(engine: TradingEngine, tick_seconds: int = 60):
    """Continuous loop during market hours."""
    print(f"[RUNNER] Starting realtime loop (tick={tick_seconds}s)")
    print(f"[RUNNER] Market open: {_is_market_open()}")

    # Sync with dual-paper-trades.json on startup
    migrate_from_json(engine)

    while True:
        try:
            if _is_market_open():
                run_once(engine)
            else:
                # After hours - just show final state
                et = _now_et()
                if et.hour >= 16 or et.hour < 9:
                    print(f"[{_now_bjt().strftime('%H:%M')}] 美股已收盘，等待开盘...")
                    # Do one final run to capture close prices
                    run_once(engine)
                    break
                else:
                    print(f"[{_now_bjt().strftime('%H:%M')}] 盘前等待...")

            time.sleep(tick_seconds)

        except KeyboardInterrupt:
            print("\n[RUNNER] Stopped by user")
            break
        except Exception as e:
            print(f"[RUNNER] Error: {e}")
            time.sleep(10)


def close_all_positions(engine: TradingEngine, reason: str = "MANUAL_CLOSE"):
    """Close all open positions at market price."""
    symbols = list(engine.positions.keys())
    if not symbols:
        print("No positions to close.")
        return

    prices = _fetch_prices(symbols)
    print(f"Closing {len(symbols)} positions...")

    for sym, pos in list(engine.positions.items()):
        price = prices.get(sym, 0)
        if price <= 0:
            print(f"  SKIP {sym}: no price data")
            continue

        from trading_engine import Order
        order = Order(
            order_id=f"ORD-close-{sym}",
            symbol=sym,
            side=OrderSide.SELL if pos.side.value == "LONG" else OrderSide.BUY,
            order_type=OrderType.MARKET,
            quantity=pos.quantity,
            reason=reason,
        )
        fill = engine._try_fill(order, price)
        if fill:
            print(f"  ✅ Closed {sym}: ${fill.price:.2f} P&L=${pos.unrealized_pnl:+.2f}")
            _log_trade({
                "event": "CLOSE",
                "symbol": sym,
                "exit_price": fill.price,
                "pnl": pos.unrealized_pnl,
                "reason": reason,
                "timestamp": fill.timestamp,
            })

    engine._update_equity(prices)
    engine._save_state()
    state = engine.get_state()
    print(f"\nFinal equity: ${state['equity']:.2f}  P&L: ${state['total_pnl']:+.2f} ({state['total_pnl_pct']:+.2f}%)")


def main():
    parser = argparse.ArgumentParser(description="xiaomei realtime paper trading runner")
    parser.add_argument("--loop", action="store_true", help="Run continuous loop")
    parser.add_argument("--tick", type=int, default=60, help="Tick interval in seconds (default: 60)")
    parser.add_argument("--close-positions", action="store_true", help="Close all positions")
    parser.add_argument("--capital", type=float, default=1000.0, help="Initial capital")
    parser.add_argument("--open-orders", action="store_true", help="Submit orders for today's tickets")
    parser.add_argument("--sync-json", action="store_true", help="Migrate from dual-paper-trades.json")
    parser.add_argument("--mode", choices=["paper", "live"], default="paper",
                        help="paper=validate many positions, live=concentrated top picks")
    args = parser.parse_args()

    engine = TradingEngine(initial_capital=args.capital, mode=args.mode)

    if args.sync_json:
        migrate_from_json(engine)
        return

    if args.close_positions:
        close_all_positions(engine)
        return

    if args.open_orders:
        migrate_from_json(engine)
        tickets = _get_today_tickets()
        existing = set(engine.positions.keys())
        submitted = 0
        for t in tickets:
            sym = t["symbol"]
            if sym in existing:
                continue
            if t["classification"] not in ("CANDIDATE_FOR_PAPER_REVIEW",):
                continue
            # Calculate position size
            equity = engine.cash + sum(p.cost_basis for p in engine.positions.values())
            size = equity * 0.18  # ~18% per position
            if size > engine.cash:
                size = engine.cash * 0.9
            # Get current price
            prices = _fetch_prices([sym])
            price = prices.get(sym, 0)
            if price <= 0:
                continue
            qty = int(size / price)
            if qty < 1:
                continue
            order = engine.submit_order(
                symbol=sym,
                side="BUY",
                quantity=qty,
                reason=f"ticket_score={t['ticket_score']:.3f}",
                ticket_date=str(t.get("output_date", "")),
                ticket_score=t["ticket_score"],
            )
            print(f"  Submitted: {order.side.value} {qty} {sym} @ ~${price:.2f} [{order.status.value}]")
            submitted += 1

            # Set SL/TP after submit (will be applied on fill)
            sl = round(price * 0.95, 2)
            tp = round(price * 1.20, 2)
            if sym in engine.positions:
                engine.set_sl_tp(sym, sl, tp)

        print(f"Submitted {submitted} orders. Run --loop to execute.")
        return

    if args.loop:
        run_loop(engine, args.tick)
    else:
        migrate_from_json(engine)
        run_once(engine)


if __name__ == "__main__":
    main()
