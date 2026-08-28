#!/usr/bin/env python3
"""US regular-session intraday paper strategy.

This is a paper-only strategy runner. It records simulated entries and exits
from fresh public quotes plus the latest completed daily research context. It
does not import broker clients, submit orders, or expose a live mode.
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, time
from pathlib import Path
from typing import Any

from sqlalchemy import text

SCRIPTS_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPTS_DIR))

from data_provider import DataProvider
from db.engine import SessionLocal
from risk_manager import RiskState, assess_trade_risk
from trading_engine import (
    COMMISSION_PER_SHARE,
    FINRA_TAF_RATE,
    MIN_COMMISSION,
    SEC_FEE_RATE,
    SLIPPAGE_BPS,
)
from capital.intraday import build_intraday_capital_assessment
from xiaomei_scheduler import US_HOLIDAYS

try:
    from zoneinfo import ZoneInfo
    ET = ZoneInfo("America/New_York")
except ImportError:  # pragma: no cover
    from datetime import timezone, timedelta
    ET = timezone(timedelta(hours=-4))

STRATEGY_VERSION = "intraday_paper_v1"
MAX_QUOTE_AGE_SECONDS = 90.0
MAX_CONTEXT_CANDIDATES = 25
ENTRY_SCORE = 0.68
SHORT_ENTRY_SCORE = 0.72
MAX_VOLUME_PARTICIPATION = 0.01


def now_et() -> datetime:
    return datetime.now(ET)


def is_us_regular_session(now: datetime | None = None) -> bool:
    """Return whether ``now`` falls in a non-holiday 09:30-16:00 ET session."""
    current = (now or now_et()).astimezone(ET)
    if current.weekday() >= 5 or current.date() in US_HOLIDAYS:
        return False
    return time(9, 30) <= current.time().replace(tzinfo=None) < time(16, 0)


def quote_age_seconds(quote: dict[str, Any], now: datetime | None = None) -> float | None:
    raw = quote.get("as_of")
    if not raw:
        return None
    try:
        observed = datetime.fromisoformat(str(raw).replace("Z", "+00:00"))
    except ValueError:
        return None
    if observed.tzinfo is None:
        observed = observed.replace(tzinfo=ET)
    reference = now or now_et()
    return max(0.0, (reference.astimezone(ET) - observed.astimezone(ET)).total_seconds())


def quote_is_fresh(quote: dict[str, Any], now: datetime | None = None) -> bool:
    age = quote_age_seconds(quote, now)
    return age is not None and age <= MAX_QUOTE_AGE_SECONDS


def score_intraday_quote(context: dict[str, Any], quote: dict[str, Any]) -> tuple[float, dict[str, Any]]:
    """Score a quote without using the in-progress session as a daily bar."""
    price = float(quote.get("latest_price") or 0)
    prev_close = float(quote.get("prev_close") or 0)
    high = float(quote.get("high") or price)
    low = float(quote.get("low") or price)
    daily_score = min(1.0, max(0.0, float(context.get("final_score") or 0)))
    pct_change = (price / prev_close - 1.0) if prev_close > 0 else 0.0
    momentum = min(1.0, max(0.0, (pct_change + 0.02) / 0.06))
    range_position = (price - low) / (high - low) if high > low else 0.5
    score = 0.55 * daily_score + 0.30 * momentum + 0.15 * range_position
    return round(min(1.0, max(0.0, score)), 6), {
        "daily_context": round(daily_score, 6),
        "session_momentum": round(momentum, 6),
        "range_position": round(range_position, 6),
        "pct_change": round(pct_change, 6),
    }


def score_intraday_short_quote(
    context: dict[str, Any],
    quote: dict[str, Any],
) -> tuple[float, dict[str, float]]:
    """Score downside continuation independently from the long score."""
    price = float(quote.get("latest_price") or 0)
    prev_close = float(quote.get("prev_close") or 0)
    high = float(quote.get("high") or price)
    low = float(quote.get("low") or price)
    daily_weakness = 1.0 - min(1.0, max(0.0, float(context.get("final_score") or 0)))
    pct_change = (price / prev_close - 1.0) if prev_close > 0 else 0.0
    downside = min(1.0, max(0.0, (-pct_change - 0.01) / 0.05))
    range_weakness = (high - price) / (high - low) if high > low else 0.5
    score = 0.45 * daily_weakness + 0.40 * downside + 0.15 * range_weakness
    return round(min(1.0, max(0.0, score)), 6), {
        "daily_weakness": round(daily_weakness, 6),
        "downside_continuation": round(downside, 6),
        "range_weakness": round(range_weakness, 6),
        "pct_change": round(pct_change, 6),
    }


def borrow_state(quote: dict[str, Any]) -> dict[str, Any]:
    """Return only explicit borrow evidence; unavailable is a hard rejection."""
    available = quote.get("borrow_available")
    rate = quote.get("borrow_rate_daily")
    if available is not True or rate is None:
        return {
            "available": False,
            "rate_daily": None,
            "reason": "UNAVAILABLE_NO_BORROW_SOURCE",
        }
    try:
        rate_value = float(rate)
    except (TypeError, ValueError):
        return {
            "available": False,
            "rate_daily": None,
            "reason": "INVALID_BORROW_RATE",
        }
    if rate_value < 0:
        return {
            "available": False,
            "rate_daily": None,
            "reason": "INVALID_BORROW_RATE",
        }
    return {"available": True, "rate_daily": rate_value, "reason": "OBSERVED"}


def evaluate_short_model(
    context: dict[str, Any],
    quote: dict[str, Any] | None,
    now: datetime,
) -> tuple[str, str, str, float | None, dict[str, Any]]:
    """Audit the unavailable short model without creating a short position."""
    if not quote or not quote_is_fresh(quote, now):
        return (
            "PAPER_SHORT_REJECTED",
            "STALE_OR_MISSING_QUOTE",
            "quote_missing_or_stale",
            None,
            {"borrow": {}},
        )

    score, components = score_intraday_short_quote(context, quote)
    borrow = borrow_state(quote)
    components["borrow"] = borrow
    if not borrow["available"]:
        return (
            "PAPER_SHORT_REJECTED",
            "BORROW_UNAVAILABLE",
            str(borrow["reason"]),
            score,
            components,
        )
    if score < SHORT_ENTRY_SCORE or components["pct_change"] >= 0:
        return (
            "PAPER_SHORT_REJECTED",
            "SCORE_BELOW_ENTRY_GATE",
            "short_score_or_downside_gate",
            score,
            components,
        )
    return (
        "PAPER_SHORT_REJECTED",
        "UNVALIDATED_PAPER_SHORT",
        "short_model_requires_completed_sample_gate",
        score,
        components,
    )


def _latest_context(session) -> list[dict[str, Any]]:
    rows = session.execute(text("""
        SELECT dc.symbol, dc.final_score, dc.market_score, dc.catalyst_score,
               dc.research_run_id,
               cds.capital_score, cds.capital_strength, cds.capital_quality,
               cds.distribution_risk, cds.trap_risk,
               cds.distribution_probability, cds.trap_probability,
               cds.path_distribution,
               cds.dominant_direction, cds.dominant_pressure,
               csh.capital_state, csh.state_confidence,
               ci.capital_intent, ci.intent_confidence,
               cpp.path_type, cpp.t1_probability, cpp.t3_probability,
               cpp.t5_probability, cpp.path_distribution AS prediction_path_distribution,
               cpp.path_sequence, cpp.path_invalidation
        FROM daily_candidates dc
        JOIN research_runs rr ON rr.run_id = dc.research_run_id
        LEFT JOIN capital_daily_snapshot cds
          ON cds.symbol = dc.symbol AND cds.research_run_id = dc.research_run_id
        LEFT JOIN capital_state_history csh
          ON csh.symbol = dc.symbol AND csh.research_run_id = dc.research_run_id
        LEFT JOIN capital_intent ci
          ON ci.symbol = dc.symbol AND ci.research_run_id = dc.research_run_id
        LEFT JOIN capital_path_prediction cpp
          ON cpp.symbol = dc.symbol AND cpp.research_run_id = dc.research_run_id
        WHERE rr.status = 'done'
          AND dc.trade_date = (
              SELECT MAX(dc2.trade_date)
              FROM daily_candidates dc2
              JOIN research_runs rr2 ON rr2.run_id = dc2.research_run_id
              WHERE rr2.status = 'done'
          )
        ORDER BY dc.final_score DESC NULLS LAST, dc.rank ASC NULLS LAST
        LIMIT :limit
    """), {"limit": MAX_CONTEXT_CANDIDATES}).mappings()
    return [dict(row) for row in rows]


def _open_positions(session) -> list[dict[str, Any]]:
    rows = session.execute(text("""
        SELECT id, symbol, entry_price, current_price, quantity,
               stop_loss_price, take_profit_price, decision_id, entry_fees
        FROM intraday_paper_positions
        WHERE status = 'OPEN'
    """)).mappings()
    return [dict(row) for row in rows]


def _close_position(session, position: dict[str, Any], price: float, reason: str) -> None:
    entry = float(position["entry_price"])
    quantity = float(position["quantity"])
    fill_price = price * (1 - SLIPPAGE_BPS / 10_000)
    commission = max(quantity * COMMISSION_PER_SHARE, MIN_COMMISSION)
    sec_fee = quantity * fill_price * SEC_FEE_RATE
    finra_fee = quantity * FINRA_TAF_RATE
    fees = commission + sec_fee + finra_fee
    pnl = (fill_price - entry) * quantity - float(position.get("entry_fees") or 0) - fees
    order_id = session.execute(text("""
        INSERT INTO intraday_paper_orders (
            decision_id, position_id, session_date, symbol, side, order_type,
            requested_quantity, remaining_quantity, status, reason
        ) VALUES (
            :decision_id, :position_id, CURRENT_DATE, :symbol, 'LONG_EXIT', 'MARKET',
            :quantity, 0, 'FILLED', :reason
        ) RETURNING id
    """), {
        "decision_id": position["decision_id"],
        "position_id": position["id"],
        "symbol": position["symbol"],
        "quantity": quantity,
        "reason": reason,
    }).scalar_one()
    session.execute(text("""
        INSERT INTO intraday_paper_fills (
            order_id, decision_id, symbol, quantity, price, commission, sec_fee,
            finra_fee, slippage, source_snapshot
        ) VALUES (
            :order_id, :decision_id, :symbol, :quantity, :price, :commission,
            :sec_fee, :finra_fee, :slippage, '{}'::jsonb
        )
    """), {
        "order_id": order_id,
        "decision_id": position["decision_id"],
        "symbol": position["symbol"],
        "quantity": quantity,
        "price": fill_price,
        "commission": commission,
        "sec_fee": sec_fee,
        "finra_fee": finra_fee,
        "slippage": abs(price - fill_price) * quantity,
    })
    session.execute(text("""
        UPDATE intraday_paper_positions
        SET status = 'CLOSED', current_price = :price, exit_price = :price,
            exit_reason = :reason, realized_pnl = :pnl, exit_fees = :fees,
            closed_at = NOW(), updated_at = NOW()
        WHERE id = :id
    """), {
        "id": position["id"], "price": fill_price, "reason": reason,
        "pnl": pnl, "fees": fees,
    })


def _create_entry_order(
    session,
    *,
    decision_id: int,
    session_date,
    symbol: str,
    quote: dict[str, Any],
    requested_quantity: float,
    stop_loss: float,
    take_profit: float,
) -> bool:
    """Queue and fill at most one percent of observed cumulative volume."""
    price = float(quote["latest_price"])
    available_quantity = int(float(quote.get("volume") or 0) * MAX_VOLUME_PARTICIPATION)
    fill_quantity = min(int(requested_quantity), available_quantity)
    remaining_quantity = max(0, int(requested_quantity) - fill_quantity)
    order_status = "QUEUED" if fill_quantity < 1 else (
        "PARTIALLY_FILLED" if remaining_quantity else "FILLED"
    )
    order_id = session.execute(text("""
        INSERT INTO intraday_paper_orders (
            decision_id, session_date, symbol, side, order_type,
            requested_quantity, remaining_quantity, status, reason
        ) VALUES (
            :decision_id, :session_date, :symbol, 'LONG_ENTRY', 'MARKET',
            :requested_quantity, :remaining_quantity, :status, :reason
        ) RETURNING id
    """), {
        "decision_id": decision_id,
        "session_date": session_date,
        "symbol": symbol,
        "requested_quantity": requested_quantity,
        "remaining_quantity": remaining_quantity,
        "status": order_status,
        "reason": "intraday_score_and_risk_gate",
    }).scalar_one()
    if fill_quantity < 1:
        return False

    fill_price = price * (1 + SLIPPAGE_BPS / 10_000)
    commission = max(fill_quantity * COMMISSION_PER_SHARE, MIN_COMMISSION)
    position_id = session.execute(text("""
        INSERT INTO intraday_paper_positions (
            decision_id, session_date, symbol, entry_price, current_price,
            quantity, stop_loss_price, take_profit_price, entry_fees,
            source_snapshot
        ) VALUES (
            :decision_id, :session_date, :symbol, :price, :price, :quantity,
            :stop_loss, :take_profit, :entry_fees, CAST(:snapshot AS jsonb)
        )
        ON CONFLICT (session_date, symbol) DO NOTHING
        RETURNING id
    """), {
        "decision_id": decision_id, "session_date": session_date, "symbol": symbol,
        "price": fill_price, "quantity": fill_quantity, "stop_loss": stop_loss,
        "take_profit": take_profit, "entry_fees": commission,
        "snapshot": json.dumps(quote),
    }).scalar_one_or_none()
    if position_id is None:
        session.execute(text("""
            UPDATE intraday_paper_orders
            SET status = 'REJECTED', reason = 'position_already_exists', updated_at = NOW()
            WHERE id = :id
        """), {"id": order_id})
        return False
    session.execute(text("""
        UPDATE intraday_paper_orders
        SET position_id = :position_id, updated_at = NOW() WHERE id = :id
    """), {"id": order_id, "position_id": position_id})
    session.execute(text("""
        INSERT INTO intraday_paper_fills (
            order_id, decision_id, symbol, quantity, price, commission, sec_fee,
            finra_fee, slippage, source_snapshot
        ) VALUES (
            :order_id, :decision_id, :symbol, :quantity, :price, :commission,
            0, 0, :slippage, CAST(:snapshot AS jsonb)
        )
    """), {
        "order_id": order_id, "decision_id": decision_id, "symbol": symbol,
        "quantity": fill_quantity, "price": fill_price, "commission": commission,
        "slippage": abs(fill_price - price) * fill_quantity,
        "snapshot": json.dumps(quote),
    })
    return True


def run_once(provider: DataProvider | None = None, now: datetime | None = None,
             account_balance: float = 100_000.0) -> dict[str, Any]:
    """Run one auditable paper-strategy decision cycle."""
    current = (now or now_et()).astimezone(ET)
    if not is_us_regular_session(current):
        return {"status": "SKIPPED_OUTSIDE_REGULAR_SESSION", "at": current.isoformat()}

    provider = provider or DataProvider()
    with SessionLocal() as session:
        context = _latest_context(session)
        if not context:
            return {"status": "BLOCKED_NO_COMPLETED_RESEARCH_CONTEXT", "at": current.isoformat()}

        quotes = provider.fetch_batch_quotes()
        context_run_id = context[0].get("research_run_id")
        run = session.execute(text("""
            INSERT INTO intraday_strategy_runs (
                session_date, strategy_version, context_research_run_id, status,
                candidate_count, source_state
            ) VALUES (
                :session_date, :version, :context_run_id, 'running', :candidate_count,
                CAST(:source_state AS jsonb)
            ) RETURNING id
        """), {
            "session_date": current.date(),
            "version": STRATEGY_VERSION,
            "context_run_id": context_run_id,
            "candidate_count": len(context),
            "source_state": json.dumps(provider.get_source_status()),
        }).scalar_one()

        entries = 0
        decisions = 0
        open_by_symbol = {row["symbol"]: row for row in _open_positions(session)}
        for position in open_by_symbol.values():
            quote = quotes.get(position["symbol"])
            if not quote or not quote_is_fresh(quote, current):
                continue
            price = float(quote["latest_price"])
            if price <= float(position["stop_loss_price"]):
                _close_position(session, position, price, "PAPER_STOP")
            elif price >= float(position["take_profit_price"]):
                _close_position(session, position, price, "PAPER_TARGET")
            else:
                session.execute(text("""
                    UPDATE intraday_paper_positions
                    SET current_price = :price, updated_at = NOW() WHERE id = :id
                """), {"id": position["id"], "price": price})

        for row in context:
            symbol = str(row["symbol"])
            quote = quotes.get(symbol)
            age = quote_age_seconds(quote or {}, current)
            decision = "PAPER_REJECTED"
            status = "STALE_OR_MISSING_QUOTE"
            score = None
            components: dict[str, float] = {}
            reason = "quote_missing_or_stale"
            if quote and quote_is_fresh(quote, current):
                score, components = score_intraday_quote(row, quote)
                capital_assessment = build_intraday_capital_assessment(row, quote)
                components["capital"] = capital_assessment
                if symbol in open_by_symbol:
                    decision, status, reason = "PAPER_HOLD", "OPEN_POSITION", "position_already_open"
                elif (
                    capital_assessment["intraday_distribution_risk"] >= 0.70
                    or capital_assessment["intraday_trap_risk"] >= 0.70
                    or float(row.get("distribution_risk") or 0.0) >= 0.70
                    or float(row.get("trap_risk") or 0.0) >= 0.70
                ):
                    status, reason = "CAPITAL_RISK_BLOCKED", "distribution_or_trap_gate"
                elif score >= ENTRY_SCORE and components["pct_change"] > 0:
                    risk = assess_trade_risk(
                        symbol=symbol, entry_price=float(quote["latest_price"]),
                        current_price=float(quote["latest_price"]),
                        account_balance=account_balance, risk_state=RiskState(),
                    )
                    if risk.allowed and risk.suggested_position_size >= 1:
                        decision, status, reason = "PAPER_ENTRY", "ACCEPTED", "fresh_quote_and_score_gate"
                    else:
                        status, reason = "RISK_BLOCKED", risk.block_reason or "risk_size_below_one_share"
                else:
                    status, reason = "SCORE_BELOW_ENTRY_GATE", "intraday_score_or_momentum_gate"

            result = session.execute(text("""
                INSERT INTO intraday_strategy_decisions (
                    run_id, session_date, symbol, decision, decision_status,
                    strategy_score, score_components, quote_snapshot, quote_source,
                    quote_age_seconds, context_research_run_id, reason
                ) VALUES (
                    :run_id, :session_date, :symbol, :decision, :status, :score,
                    CAST(:components AS jsonb), CAST(:quote AS jsonb), :source,
                    :age, :context_run_id, :reason
                ) RETURNING id
            """), {
                "run_id": run, "session_date": current.date(), "symbol": symbol,
                "decision": decision, "status": status, "score": score,
                "components": json.dumps(components), "quote": json.dumps(quote or {}),
                "source": (quote or {}).get("source") or (quote or {}).get("provider"),
                "age": age, "context_run_id": row.get("research_run_id"), "reason": reason,
            })
            decision_id = result.scalar_one()
            decisions += 1
            short_decision, short_status, short_reason, short_score, short_components = (
                evaluate_short_model(row, quote, current)
            )
            session.execute(text("""
                INSERT INTO intraday_strategy_decisions (
                    run_id, session_date, symbol, direction, decision, decision_status,
                    strategy_score, score_components, quote_snapshot, quote_source,
                    quote_age_seconds, context_research_run_id, reason
                ) VALUES (
                    :run_id, :session_date, :symbol, 'SHORT', :decision, :status, :score,
                    CAST(:components AS jsonb), CAST(:quote AS jsonb), :source,
                    :age, :context_run_id, :reason
                )
            """), {
                "run_id": run, "session_date": current.date(), "symbol": symbol,
                "decision": short_decision, "status": short_status, "score": short_score,
                "components": json.dumps(short_components), "quote": json.dumps(quote or {}),
                "source": (quote or {}).get("source") or (quote or {}).get("provider"),
                "age": age, "context_run_id": row.get("research_run_id"), "reason": short_reason,
            })
            decisions += 1
            if decision != "PAPER_ENTRY":
                continue
            price = float(quote["latest_price"])
            risk = assess_trade_risk(symbol, price, price, account_balance, risk_state=RiskState())
            quantity = float(int(min(risk.suggested_position_size, account_balance * 0.10 / price)))
            if quantity < 1:
                continue
            if _create_entry_order(
                session,
                decision_id=decision_id,
                session_date=current.date(),
                symbol=symbol,
                quote=quote,
                requested_quantity=quantity,
                stop_loss=risk.suggested_stop_loss,
                take_profit=risk.suggested_take_profit,
            ):
                entries += 1

        session.execute(text("""
            UPDATE intraday_strategy_runs
            SET status = 'done', finished_at = NOW() WHERE id = :id
        """), {"id": run})
        session.commit()
    return {"status": "PAPER_STRATEGY_COMPLETE", "run_id": run, "decisions": decisions,
            "entries": entries, "at": current.isoformat()}


def main() -> int:
    parser = argparse.ArgumentParser(description="xiaomei intraday paper strategy")
    parser.add_argument("--once", action="store_true", help="Run one paper-strategy cycle.")
    parser.add_argument("--capital", type=float, default=100_000.0)
    args = parser.parse_args()
    result = run_once(account_balance=args.capital)
    print(json.dumps(result, default=str))
    return 0 if result["status"] in {"PAPER_STRATEGY_COMPLETE", "SKIPPED_OUTSIDE_REGULAR_SESSION"} else 2


if __name__ == "__main__":
    raise SystemExit(main())
