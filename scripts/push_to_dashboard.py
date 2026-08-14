#!/usr/bin/env python3
"""Push realtime simulation state to Financial OS dashboard."""
import json
import sys
from pathlib import Path
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
ENGINE_STATE = ROOT / "research" / "engine-state.json"
TRADE_LOG = ROOT / "research" / "trade-log.jsonl"
DASHBOARD_API = "http://localhost:3000/api/simulation/xiaomei"


def load_engine_state() -> dict:
    if not ENGINE_STATE.exists():
        return {}
    return json.loads(ENGINE_STATE.read_text())


def load_recent_orders(limit: int = 20) -> list[dict]:
    if not TRADE_LOG.exists():
        return []
    orders = []
    for line in TRADE_LOG.read_text().strip().split("\n"):
        if not line.strip():
            continue
        try:
            entry = json.loads(line)
            orders.append(entry)
        except json.JSONDecodeError:
            continue
    return orders[-limit:]


def build_payload(state: dict, orders: list[dict]) -> dict:
    positions = []
    for sym, pos in state.get("positions", {}).items():
        positions.append({
            "symbol": sym,
            "side": pos.get("side", "LONG").lower(),
            "qty": pos.get("quantity", 0),
            "shares": pos.get("quantity", 0),
            "avg_price": pos.get("avg_price", 0),
            "avg_cost": pos.get("avg_price", 0),
            "mark": pos.get("current_price", 0),
            "current_price": pos.get("current_price", 0),
            "market_value": pos.get("quantity", 0) * pos.get("current_price", 0),
            "unrealized_pnl": pos.get("unrealized_pnl", 0),
            "u_pnl": pos.get("unrealized_pnl", 0),
            "unrealized_pnl_pct": pos.get("unrealized_pnl_pct", 0),
            "stop_loss": pos.get("stop_loss_price", 0),
            "take_profit": pos.get("take_profit_price", 0),
        })

    recent_orders = []
    for order in orders:
        recent_orders.append({
            "time": order.get("timestamp", ""),
            "ts": order.get("timestamp", ""),
            "symbol": order.get("symbol", ""),
            "action": order.get("side", ""),
            "price": order.get("price", 0),
            "qty": order.get("quantity", 0),
            "status": "filled",
            "pnl": order.get("pnl", 0),
            "reason": order.get("reason", ""),
        })

    return {
        "starting_cash": 1000,
        "cash": state.get("cash", 0),
        "equity": state.get("equity", 0),
        "total_return": state.get("total_pnl_pct", 0) / 100,
        "total_pnl": state.get("total_pnl", 0),
        "positions": positions,
        "recent_orders": recent_orders,
        "win_rate": state.get("win_rate", 0),
        "max_drawdown": state.get("max_drawdown", 0),
        "total_fills": state.get("total_fills", 0),
        "total_fees": state.get("total_fees", 0),
    }


def push_to_dashboard(payload: dict) -> bool:
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        DASHBOARD_API,
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=5) as resp:
            result = json.loads(resp.read())
            return result.get("ok", False)
    except Exception as e:
        print(f"Error pushing to dashboard: {e}", file=sys.stderr)
        return False


def main():
    state = load_engine_state()
    if not state:
        print("No engine state found")
        return

    orders = load_recent_orders()
    payload = build_payload(state, orders)

    ok = push_to_dashboard(payload)
    if ok:
        print(f"Pushed to dashboard: equity=${payload['equity']:.2f}, "
              f"pnl={payload['total_return']*100:+.2f}%, "
              f"positions={len(payload['positions'])}")
    else:
        print("Failed to push to dashboard")
        sys.exit(1)


if __name__ == "__main__":
    main()
