#!/usr/bin/env python3
"""Full realistic paper trading engine for xiaomei.

Simulates order execution with slippage, fees, partial fills.
Manages positions, stop-loss, take-profit automatically.
Designed to be swapped 1:1 with a real broker API later.

Usage:
    from trading_engine import TradingEngine
    engine = TradingEngine()
    engine.submit_order("AAPL", "BUY", 100, limit_price=150.0)
    engine.check_and_execute()  # called on each tick/interval
"""
from __future__ import annotations

import json
import uuid
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone, timedelta
from enum import Enum
from pathlib import Path
from typing import Any

from sqlalchemy import text
import sys
sys.path.insert(0, str(Path(__file__).resolve().parent))
from db.engine import SessionLocal

# ─── Constants ──────────────────────────────────────────────────
BJT = timezone(timedelta(hours=8))

# Fee structure (simulate US broker: IBKR-like)
COMMISSION_PER_SHARE = 0.005  # $0.005 per share (IBKR tiered)
MIN_COMMISSION = 1.0           # $1 minimum per order
SEC_FEE_RATE = 0.0000278       # SEC fee on sells
FINRA_TAF_RATE = 0.000166      # FINRA TAF on sells
SLIPPAGE_BPS = 5               # 5 bps slippage simulation

# Risk limits
# Paper mode: more positions to validate opportunities
# Live mode: concentrated in best pick(s)
MAX_POSITION_PCT_PAPER = 0.20   # 20% per position in paper
MAX_POSITION_PCT_LIVE = 0.50    # 50% per position in live (concentrated)
MAX_TOTAL_EXPOSURE = 1.0        # 100% max (no leverage)
MAX_DRAWDOWN_PCT = 0.15         # 15% max drawdown -> halt
MAX_CONCURRENT_PAPER = 8        # Paper: validate many
MAX_CONCURRENT_LIVE = 3         # Live: only best picks


class OrderSide(str, Enum):
    BUY = "BUY"
    SELL = "SELL"


class OrderType(str, Enum):
    MARKET = "MARKET"
    LIMIT = "LIMIT"
    STOP = "STOP"
    STOP_LIMIT = "STOP_LIMIT"


class OrderStatus(str, Enum):
    PENDING = "PENDING"
    FILLED = "FILLED"
    PARTIALLY_FILLED = "PARTIALLY_FILLED"
    CANCELLED = "CANCELLED"
    REJECTED = "REJECTED"


class PositionSide(str, Enum):
    LONG = "LONG"
    SHORT = "SHORT"


@dataclass
class Order:
    order_id: str
    symbol: str
    side: OrderSide
    order_type: OrderType
    quantity: float
    limit_price: float | None = None
    stop_price: float | None = None
    status: OrderStatus = OrderStatus.PENDING
    filled_quantity: float = 0.0
    filled_price: float = 0.0
    commission: float = 0.0
    sec_fee: float = 0.0
    finra_fee: float = 0.0
    slippage: float = 0.0
    created_at: str = ""
    filled_at: str = ""
    parent_ticket_date: str = ""
    parent_ticket_id: int | None = None
    parent_ticket_score: float = 0.0
    reason: str = ""

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class Position:
    symbol: str
    side: PositionSide
    quantity: float
    avg_price: float
    cost_basis: float
    current_price: float = 0.0
    unrealized_pnl: float = 0.0
    unrealized_pnl_pct: float = 0.0
    stop_loss_price: float = 0.0
    take_profit_price: float = 0.0
    opened_at: str = ""
    last_update: str = ""
    ticket_date: str = ""
    ticket_id: int | None = None
    ticket_score: float = 0.0

    def market_value(self) -> float:
        if self.side == PositionSide.SHORT:
            return self.cost_basis - (self.quantity * (self.current_price - self.avg_price))
        return self.quantity * self.current_price

    def update_price(self, price: float):
        self.current_price = price
        if self.side == PositionSide.SHORT:
            self.unrealized_pnl = (self.avg_price - price) * self.quantity
        else:
            self.unrealized_pnl = (price - self.avg_price) * self.quantity
        self.unrealized_pnl_pct = (self.unrealized_pnl / self.cost_basis * 100) if self.cost_basis > 0 else 0
        self.last_update = datetime.now(BJT).isoformat()

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class Fill:
    fill_id: str
    order_id: str
    symbol: str
    side: str
    quantity: float
    price: float
    commission: float
    sec_fee: float
    finra_fee: float
    slippage: float
    timestamp: str
    reason: str = ""
    ticket_id: int | None = None


class TradingEngine:
    """Full paper trading engine with order management, position tracking,
    risk controls, and DB persistence. Swappable with real broker API."""

    def __init__(
        self,
        initial_capital: float = 1000.0,
        db_persist: bool = True,
        state_file: str | Path | None = None,
        mode: str = "paper",  # "paper" or "live"
    ):
        self.initial_capital = initial_capital
        self.cash = initial_capital
        self.db_persist = db_persist
        self.mode = mode  # paper: validate many; live: concentrated

        self.positions: dict[str, Position] = {}
        self.open_orders: list[Order] = []
        self.fills: list[Fill] = []
        self.closed_trades: list[dict] = []
        self.equity_curve: list[dict] = []
        self.rejected_orders: list[Order] = []

        # Risk state
        self.halted = False
        self.halt_reason = ""
        self.peak_equity = initial_capital
        self.max_drawdown = 0.0

        # State file for JSON persistence
        self.state_file = Path(state_file) if state_file else Path(__file__).resolve().parent.parent / "research" / "engine-state.json"

        self._load_state()

    # ── Order Submission ─────────────────────────────────────────

    def submit_order(
        self,
        symbol: str,
        side: str | OrderSide,
        quantity: float,
        order_type: str | OrderType = "MARKET",
        limit_price: float | None = None,
        stop_price: float | None = None,
        ticket_date: str = "",
        ticket_id: int | None = None,
        ticket_score: float = 0.0,
        reason: str = "",
    ) -> Order:
        """Submit an order. Returns the Order object."""
        if self.halted:
            return self._reject_order(symbol, side, quantity, f"Engine halted: {self.halt_reason}")

        side = OrderSide(side) if isinstance(side, str) else side
        order_type = OrderType(order_type) if isinstance(order_type, str) else order_type

        # Risk checks
        rejection = self._risk_check(symbol, side, quantity, limit_price or 0)
        if rejection:
            return self._reject_order(symbol, side, quantity, rejection)

        order = Order(
            order_id=f"ORD-{uuid.uuid4().hex[:12]}",
            symbol=symbol.upper(),
            side=side,
            order_type=order_type,
            quantity=quantity,
            limit_price=limit_price,
            stop_price=stop_price,
            created_at=datetime.now(BJT).isoformat(),
            parent_ticket_date=ticket_date,
            parent_ticket_id=ticket_id,
            parent_ticket_score=ticket_score,
            reason=reason,
        )
        self.open_orders.append(order)
        self._save_state()
        return order

    def cancel_order(self, order_id: str) -> bool:
        for i, order in enumerate(self.open_orders):
            if order.order_id == order_id:
                order.status = OrderStatus.CANCELLED
                self.open_orders.pop(i)
                self._save_state()
                return True
        return False

    # ── Order Execution ──────────────────────────────────────────

    def execute_orders(self, prices: dict[str, float]) -> list[Fill]:
        """Execute pending orders against current prices.
        Called on each tick/interval with live prices."""
        if self.halted:
            return []

        fills = []
        remaining = []

        for order in self.open_orders:
            price = prices.get(order.symbol, 0)
            if price <= 0:
                remaining.append(order)
                continue

            fill = self._try_fill(order, price)
            if fill:
                fills.append(fill)
            else:
                remaining.append(order)

        self.open_orders = remaining

        # Check stop-loss / take-profit on existing positions
        sl_tp_fills = self._check_sl_tp(prices)
        fills.extend(sl_tp_fills)

        if fills:
            self._update_equity(prices)
            self._save_state()
            self._persist_fills(fills)

        return fills

    def _try_fill(self, order: Order, market_price: float) -> Fill | None:
        """Attempt to fill an order. Returns Fill if filled, None otherwise."""
        can_fill = False

        if order.order_type == OrderType.MARKET:
            can_fill = True
            fill_price = market_price
        elif order.order_type == OrderType.LIMIT:
            if order.side == OrderSide.BUY and market_price <= order.limit_price:
                can_fill = True
                fill_price = order.limit_price
            elif order.side == OrderSide.SELL and market_price >= order.limit_price:
                can_fill = True
                fill_price = order.limit_price
        elif order.order_type == OrderType.STOP:
            if order.side == OrderSide.BUY and market_price >= order.stop_price:
                can_fill = True
                fill_price = market_price
            elif order.side == OrderSide.SELL and market_price <= order.stop_price:
                can_fill = True
                fill_price = market_price

        if not can_fill:
            return None

        # Apply slippage
        slippage_amount = fill_price * SLIPPAGE_BPS / 10000
        if order.side == OrderSide.BUY:
            fill_price += slippage_amount
        else:
            fill_price -= slippage_amount

        # Calculate fees
        commission = max(order.quantity * COMMISSION_PER_SHARE, MIN_COMMISSION)
        sec_fee = 0.0
        finra_fee = 0.0
        if order.side == OrderSide.SELL:
            notional = order.quantity * fill_price
            sec_fee = notional * SEC_FEE_RATE
            finra_fee = order.quantity * FINRA_TAF_RATE

        total_cost = order.quantity * fill_price + commission + sec_fee + finra_fee

        # Check cash for buys
        if order.side == OrderSide.BUY and total_cost > self.cash:
            # Reduce quantity to fit
            affordable = (self.cash - MIN_COMMISSION) / (fill_price * (1 + SLIPPAGE_BPS / 10000))
            if affordable < 1:
                return None
            order.quantity = int(affordable)
            total_cost = order.quantity * fill_price + commission + sec_fee + finra_fee

        # Execute fill
        order.status = OrderStatus.FILLED
        order.filled_quantity = order.quantity
        order.filled_price = fill_price
        order.commission = commission
        order.sec_fee = sec_fee
        order.finra_fee = finra_fee
        order.slippage = slippage_amount * order.quantity
        order.filled_at = datetime.now(BJT).isoformat()

        # Update cash
        if order.side == OrderSide.BUY:
            self.cash -= total_cost
            self._open_or_add_position(order, fill_price)
        else:
            self.cash += (order.quantity * fill_price) - commission - sec_fee - finra_fee
            self._close_or_reduce_position(order, fill_price)

        fill = Fill(
            fill_id=f"FILL-{uuid.uuid4().hex[:12]}",
            order_id=order.order_id,
            symbol=order.symbol,
            side=order.side.value,
            quantity=order.quantity,
            price=fill_price,
            commission=commission,
            sec_fee=sec_fee,
            finra_fee=finra_fee,
            slippage=slippage_amount * order.quantity,
            timestamp=datetime.now(BJT).isoformat(),
            reason=order.reason,
            ticket_id=order.parent_ticket_id,
        )
        self.fills.append(fill)
        return fill

    # ── Position Management ──────────────────────────────────────

    def _open_or_add_position(self, order: Order, fill_price: float):
        sym = order.symbol
        if sym in self.positions:
            pos = self.positions[sym]
            total_cost = pos.cost_basis + (order.quantity * fill_price)
            total_qty = pos.quantity + order.quantity
            pos.avg_price = total_cost / total_qty
            pos.quantity = total_qty
            pos.cost_basis = total_cost
        else:
            self.positions[sym] = Position(
                symbol=sym,
                side=PositionSide.LONG,
                quantity=order.quantity,
                avg_price=fill_price,
                cost_basis=order.quantity * fill_price,
                current_price=fill_price,
                opened_at=datetime.now(BJT).isoformat(),
                ticket_date=order.parent_ticket_date,
                ticket_id=order.parent_ticket_id,
                ticket_score=order.parent_ticket_score,
            )

    def _close_or_reduce_position(self, order: Order, fill_price: float):
        sym = order.symbol
        if sym not in self.positions:
            # Short sell to open
            self.positions[sym] = Position(
                symbol=sym,
                side=PositionSide.SHORT,
                quantity=order.quantity,
                avg_price=fill_price,
                cost_basis=order.quantity * fill_price,
                current_price=fill_price,
                opened_at=datetime.now(BJT).isoformat(),
                ticket_date=order.parent_ticket_date,
                ticket_id=order.parent_ticket_id,
                ticket_score=order.parent_ticket_score,
            )
            return

        pos = self.positions[sym]
        if order.quantity >= pos.quantity:
            # Full close
            pnl = self._calc_close_pnl(pos, fill_price, order.quantity)
            self.closed_trades.append({
                "symbol": sym,
                "side": pos.side.value,
                "entry_price": pos.avg_price,
                "exit_price": fill_price,
                "quantity": pos.quantity,
                "pnl": pnl,
                "pnl_pct": (pnl / pos.cost_basis * 100) if pos.cost_basis > 0 else 0,
                "held_from": pos.opened_at,
                "closed_at": datetime.now(BJT).isoformat(),
                "reason": order.reason,
                "ticket_id": pos.ticket_id,
            })
            del self.positions[sym]
        else:
            # Partial close
            pnl = self._calc_close_pnl(pos, fill_price, order.quantity)
            pos.quantity -= order.quantity
            pos.cost_basis = pos.quantity * pos.avg_price
            self.closed_trades.append({
                "symbol": sym,
                "side": pos.side.value,
                "entry_price": pos.avg_price,
                "exit_price": fill_price,
                "quantity": order.quantity,
                "pnl": pnl,
                "pnl_pct": (pnl / (order.quantity * pos.avg_price) * 100),
                "held_from": pos.opened_at,
                "closed_at": datetime.now(BJT).isoformat(),
                "reason": order.reason,
                "ticket_id": pos.ticket_id,
            })

    def _calc_close_pnl(self, pos: Position, exit_price: float, quantity: float) -> float:
        if pos.side == PositionSide.SHORT:
            return (pos.avg_price - exit_price) * quantity
        return (exit_price - pos.avg_price) * quantity

    # ── Stop-Loss / Take-Profit ──────────────────────────────────

    def set_sl_tp(self, symbol: str, stop_loss: float, take_profit: float):
        if symbol in self.positions:
            self.positions[symbol].stop_loss_price = stop_loss
            self.positions[symbol].take_profit_price = take_profit
            self._save_state()

    def _check_sl_tp(self, prices: dict[str, float]) -> list[Fill]:
        fills = []
        to_close = []

        for sym, pos in list(self.positions.items()):
            price = prices.get(sym, 0)
            if price <= 0:
                continue
            pos.update_price(price)

            triggered = False
            reason = ""

            if pos.side == PositionSide.LONG:
                if pos.stop_loss_price > 0 and price <= pos.stop_loss_price:
                    triggered, reason = True, "STOP_LOSS"
                elif pos.take_profit_price > 0 and price >= pos.take_profit_price:
                    triggered, reason = True, "TAKE_PROFIT"
            else:  # SHORT
                if pos.stop_loss_price > 0 and price >= pos.stop_loss_price:
                    triggered, reason = True, "STOP_LOSS"
                elif pos.take_profit_price > 0 and price <= pos.take_profit_price:
                    triggered, reason = True, "TAKE_PROFIT"

            if triggered:
                order = Order(
                    order_id=f"ORD-{uuid.uuid4().hex[:12]}",
                    symbol=sym,
                    side=OrderSide.SELL if pos.side == PositionSide.LONG else OrderSide.BUY,
                    order_type=OrderType.MARKET,
                    quantity=pos.quantity,
                    status=OrderStatus.PENDING,
                    created_at=datetime.now(BJT).isoformat(),
                    reason=reason,
                )
                fill = self._try_fill(order, price)
                if fill:
                    fills.append(fill)

        return fills

    # ── Risk Management ──────────────────────────────────────────

    def _risk_check(self, symbol: str, side: str | OrderSide, quantity: float, price: float) -> str | None:
        side = OrderSide(side) if isinstance(side, str) else side

        # Mode-specific limits
        max_pos_pct = MAX_POSITION_PCT_LIVE if self.mode == "live" else MAX_POSITION_PCT_PAPER
        max_concurrent = MAX_CONCURRENT_LIVE if self.mode == "live" else MAX_CONCURRENT_PAPER

        # Max drawdown check
        equity = self._calc_equity({})
        if equity < self.initial_capital * (1 - MAX_DRAWDOWN_PCT):
            self.halted = True
            self.halt_reason = f"Max drawdown {MAX_DRAWDOWN_PCT*100:.0f}% breached"
            return self.halt_reason

        # Max concurrent positions
        if side == OrderSide.BUY and len(self.positions) >= max_concurrent:
            return f"Max {max_concurrent} positions reached ({self.mode} mode)"

        # Position concentration
        notional = quantity * price
        if notional > equity * max_pos_pct:
            return f"Position ${notional:.0f} exceeds {max_pos_pct*100:.0f}% limit (${equity*max_pos_pct:.0f})"

        # Total exposure check
        total_exposure = sum(p.cost_basis for p in self.positions.values())
        if side == OrderSide.BUY and (total_exposure + notional) > equity * MAX_TOTAL_EXPOSURE:
            return f"Total exposure would exceed {MAX_TOTAL_EXPOSURE*100:.0f}% limit"

        # Duplicate position check
        if symbol in self.positions and side == OrderSide.BUY:
            existing = self.positions[symbol]
            if existing.side == PositionSide.LONG:
                # Allow adding to existing long, but check concentration
                if (existing.cost_basis + notional) > equity * MAX_POSITION_PCT:
                    return f"Adding to {symbol} would exceed concentration limit"

        return None

    def _reject_order(self, symbol: str, side, quantity: float, reason: str) -> Order:
        side = OrderSide(side) if isinstance(side, str) else side
        order = Order(
            order_id=f"ORD-{uuid.uuid4().hex[:12]}",
            symbol=symbol,
            side=side,
            order_type=OrderType.MARKET,
            quantity=quantity,
            status=OrderStatus.REJECTED,
            created_at=datetime.now(BJT).isoformat(),
            reason=reason,
        )
        self.rejected_orders.append(order)
        return order

    # ── Equity & State ───────────────────────────────────────────

    def _calc_equity(self, prices: dict[str, float]) -> float:
        equity = self.cash
        for pos in self.positions.values():
            price = prices.get(pos.symbol, pos.current_price)
            if price > 0:
                pos.update_price(price)
            equity += pos.market_value()
        return equity

    def _update_equity(self, prices: dict[str, float]):
        equity = self._calc_equity(prices)
        if equity > self.peak_equity:
            self.peak_equity = equity
        drawdown = (self.peak_equity - equity) / self.peak_equity if self.peak_equity > 0 else 0
        if drawdown > self.max_drawdown:
            self.max_drawdown = drawdown

        self.equity_curve.append({
            "timestamp": datetime.now(BJT).isoformat(),
            "equity": round(equity, 2),
            "cash": round(self.cash, 2),
            "positions": len(self.positions),
            "drawdown": round(drawdown * 100, 2),
        })
        self._persist_equity_snapshot(equity, drawdown)

    def _persist_equity_snapshot(self, equity: float, drawdown: float):
        """Persist equity snapshot to paper_equity_log table."""
        if not self.db_persist:
            return
        try:
            with SessionLocal() as session:
                session.execute(text("""
                    INSERT INTO paper_equity_log
                        (equity, cash, positions_count, drawdown_pct, logged_at)
                    VALUES
                        (:equity, :cash, :positions_count, :drawdown_pct, :logged_at)
                """), {
                    "equity": round(equity, 2),
                    "cash": round(self.cash, 2),
                    "positions_count": len(self.positions),
                    "drawdown_pct": round(drawdown * 100, 2),
                    "logged_at": datetime.now(BJT),
                })
                session.commit()
        except Exception:
            import logging
            logging.getLogger(__name__).warning("Failed to persist equity snapshot", exc_info=True)

    def get_state(self) -> dict:
        """Full engine state snapshot."""
        equity = self.cash + sum(p.market_value() for p in self.positions.values())
        total_fees = sum(f.commission + f.sec_fee + f.finra_fee for f in self.fills)
        wins = [t for t in self.closed_trades if t["pnl"] > 0]
        losses = [t for t in self.closed_trades if t["pnl"] <= 0]

        return {
            "initial_capital": self.initial_capital,
            "cash": round(self.cash, 2),
            "equity": round(equity, 2),
            "total_pnl": round(equity - self.initial_capital, 2),
            "total_pnl_pct": round((equity / self.initial_capital - 1) * 100, 2),
            "positions": {s: p.to_dict() for s, p in self.positions.items()},
            "position_count": len(self.positions),
            "open_orders": [o.to_dict() for o in self.open_orders],
            "open_order_count": len(self.open_orders),
            "total_fills": len(self.fills),
            "total_fees": round(total_fees, 2),
            "closed_trades": len(self.closed_trades),
            "wins": len(wins),
            "losses": len(losses),
            "win_rate": round(len(wins) / len(self.closed_trades) * 100, 1) if self.closed_trades else 0,
            "max_drawdown": round(self.max_drawdown * 100, 2),
            "halted": self.halted,
            "halt_reason": self.halt_reason,
            "recent_fills": [asdict(f) for f in self.fills[-20:]],
            "closed_trade_details": self.closed_trades[-20:],
            "updated_at": datetime.now(BJT).isoformat(),
        }

    def get_positions_for_monitor(self) -> list[dict]:
        """Return positions in the format expected by live_paper_monitor."""
        result = []
        for pos in self.positions.values():
            result.append({
                "symbol": pos.symbol,
                "direction": pos.side.value,
                "entry_price": pos.avg_price,
                "shares": pos.quantity,
                "cost": pos.cost_basis,
                "stop_loss_price": pos.stop_loss_price,
                "take_profit_price": pos.take_profit_price,
            })
        return result

    # ── Persistence ──────────────────────────────────────────────

    def _save_state(self):
        state = self.get_state()
        state["positions_for_monitor"] = self.get_positions_for_monitor()
        self.state_file.parent.mkdir(parents=True, exist_ok=True)
        self.state_file.write_text(json.dumps(state, indent=2, default=str))

    def _load_state(self):
        if not self.state_file.exists():
            return
        try:
            data = json.loads(self.state_file.read_text())
            self.cash = data.get("cash", self.initial_capital)
            self.halted = data.get("halted", False)
            self.halt_reason = data.get("halt_reason", "")
            self.max_drawdown = data.get("max_drawdown", 0) / 100
            self.peak_equity = max(self.initial_capital, data.get("equity", self.initial_capital))

            for s, pd in data.get("positions", {}).items():
                self.positions[s] = Position(
                    symbol=pd["symbol"],
                    side=PositionSide(pd["side"]),
                    quantity=pd["quantity"],
                    avg_price=pd["avg_price"],
                    cost_basis=pd["cost_basis"],
                    current_price=pd.get("current_price", 0),
                    stop_loss_price=pd.get("stop_loss_price", 0),
                    take_profit_price=pd.get("take_profit_price", 0),
                    opened_at=pd.get("opened_at", ""),
                    ticket_date=pd.get("ticket_date", ""),
                    ticket_id=pd.get("ticket_id"),
                    ticket_score=pd.get("ticket_score", 0),
                )
        except Exception:
            pass

    def _persist_fills(self, fills: list[Fill]):
        if not self.db_persist:
            return
        try:
            with SessionLocal() as session:
                for fill in fills:
                    d = asdict(fill)
                    # Map dataclass field 'timestamp' → DB column 'filled_at'
                    d["filled_at"] = d.pop("timestamp")
                    session.execute(text("""
                        INSERT INTO paper_fills
                            (fill_id, order_id, symbol, side, quantity, price,
                             commission, sec_fee, finra_fee, slippage, reason,
                             ticket_id, filled_at)
                        VALUES
                            (:fill_id, :order_id, :symbol, :side, :quantity, :price,
                             :commission, :sec_fee, :finra_fee, :slippage, :reason,
                             :ticket_id, :filled_at)
                        ON CONFLICT (fill_id) DO NOTHING
                    """), d)
                session.commit()
        except Exception:
            import logging
            logging.getLogger(__name__).warning("Failed to persist fills to DB", exc_info=True)
