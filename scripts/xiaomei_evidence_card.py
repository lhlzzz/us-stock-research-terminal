"""
xiaomei evidence card generator.
Aligned with xiaogu's xiaogu_evidence_card.py architecture.

Generates compact one-page evidence digests for official picks.
"""

from __future__ import annotations

import json
import logging
from datetime import date
from typing import Optional

logger = logging.getLogger(__name__)


def generate_evidence_card(
    engine,
    trade_date: date,
    symbol: str,
) -> dict:
    """Generate evidence card for a specific pick.

    Returns: {symbol, date, scores, factors, returns, risk_assessment}
    """
    from sqlalchemy import text

    with engine.connect() as conn:
        # Get ticket
        result = conn.execute(text("""
            SELECT symbol, ticket_score, market_score, catalyst_score,
                   classification, risk_verdict, quality_verdict, entry_reason
            FROM tickets
            WHERE output_date = :trade_date AND symbol = :symbol
        """), {"trade_date": trade_date, "symbol": symbol})
        ticket = result.fetchone()

        if not ticket:
            return {"error": f"No ticket found for {symbol} on {trade_date}"}

        # Get daily candidate details
        result = conn.execute(text("""
            SELECT factor_snapshot, ranking_basis, selection_reason,
                   candidate_entry_reason, auxiliary_evidence_snapshot
            FROM daily_candidates
            WHERE trade_date = :trade_date AND symbol = :symbol
        """), {"trade_date": trade_date, "symbol": symbol})
        candidate = result.fetchone()

        # Get returns
        result = conn.execute(text("""
            SELECT ft.horizon_days, ft.forward_return, ft.check_status
            FROM forward_tracking ft
            JOIN tickets t ON ft.ticket_id = t.id
            WHERE t.output_date = :trade_date AND t.symbol = :symbol
            ORDER BY ft.horizon_days
        """), {"trade_date": trade_date, "symbol": symbol})
        returns = [dict(row._mapping) for row in result.fetchall()]

        # Get similar historical cases
        result = conn.execute(text("""
            SELECT trade_date, symbol, final_score, t1_return,
                   1 - (embedding <=> (
                       SELECT embedding FROM pick_case_embeddings
                       WHERE trade_date = :trade_date AND symbol = :symbol
                       LIMIT 1
                   )) as similarity
            FROM pick_case_embeddings
            WHERE trade_date != :trade_date
            AND embedding IS NOT NULL
            ORDER BY embedding <=> (
                SELECT embedding FROM pick_case_embeddings
                WHERE trade_date = :trade_date AND symbol = :symbol
                LIMIT 1
            )
            LIMIT 5
        """), {"trade_date": trade_date, "symbol": symbol})
        similar_cases = [dict(row._mapping) for row in result.fetchall()]

    # Build evidence card
    ticket_dict = dict(ticket._mapping)
    candidate_dict = dict(candidate._mapping) if candidate else {}

    card = {
        "symbol": symbol,
        "trade_date": trade_date.isoformat(),
        "scores": {
            "ticket": ticket_dict.get("ticket_score"),
            "market": ticket_dict.get("market_score"),
            "catalyst": ticket_dict.get("catalyst_score"),
        },
        "classification": ticket_dict.get("classification"),
        "risk": {
            "verdict": ticket_dict.get("risk_verdict"),
            "quality": ticket_dict.get("quality_verdict"),
        },
        "entry_reason": ticket_dict.get("entry_reason"),
        "selection_reason": candidate_dict.get("selection_reason"),
        "factors": candidate_dict.get("factor_snapshot"),
        "ranking_basis": candidate_dict.get("ranking_basis"),
        "returns": returns,
        "similar_cases": similar_cases,
        "evidence_summary": _build_evidence_summary(ticket_dict, candidate_dict, returns),
    }

    return card


def _build_evidence_summary(
    ticket: dict,
    candidate: dict,
    returns: list[dict],
) -> str:
    """Build compact evidence summary."""
    parts = []

    # Score summary
    score = ticket.get("ticket_score")
    market = ticket.get("market_score")
    if score and market:
        parts.append(f"Score: {score:.3f} (market={market:.3f})")

    # Risk
    risk = ticket.get("risk_verdict")
    if risk:
        parts.append(f"Risk: {risk}")

    # Returns
    completed_returns = [r for r in returns if r.get("check_status") == "completed"]
    if completed_returns:
        best_return = max(completed_returns, key=lambda x: x.get("forward_return", 0) or 0)
        worst_return = min(completed_returns, key=lambda x: x.get("forward_return", 0) or 0)
        parts.append(f"Best: {best_return['horizon_days']}d={best_return['forward_return']*100:.2f}%")
        parts.append(f"Worst: {worst_return['horizon_days']}d={worst_return['forward_return']*100:.2f}%")

    # Entry reason (truncated)
    entry_reason = ticket.get("entry_reason", "")
    if entry_reason:
        parts.append(f"Reason: {entry_reason[:100]}")

    return " | ".join(parts)


def generate_daily_evidence_cards(
    engine,
    trade_date: date,
) -> list[dict]:
    """Generate evidence cards for all picks on a given date.

    Returns: list of evidence cards
    """
    from sqlalchemy import text

    with engine.connect() as conn:
        result = conn.execute(text("""
            SELECT symbol
            FROM tickets
            WHERE output_date = :trade_date
            ORDER BY ticket_score DESC
        """), {"trade_date": trade_date})
        symbols = [row[0] for row in result.fetchall()]

    cards = []
    for symbol in symbols:
        card = generate_evidence_card(engine, trade_date, symbol)
        cards.append(card)

    return cards


def format_evidence_card_markdown(card: dict) -> str:
    """Format evidence card as markdown."""
    lines = [
        f"# Evidence Card: {card['symbol']}",
        f"**Date**: {card['trade_date']}",
        "",
        "## Scores",
        f"- Ticket: {card['scores'].get('ticket', 'N/A')}",
        f"- Market: {card['scores'].get('market', 'N/A')}",
        f"- Catalyst: {card['scores'].get('catalyst', 'N/A')}",
        "",
        "## Classification",
        f"- {card.get('classification', 'N/A')}",
        "",
        "## Risk",
        f"- Verdict: {card['risk'].get('verdict', 'N/A')}",
        f"- Quality: {card['risk'].get('quality', 'N/A')}",
        "",
    ]

    if card.get("entry_reason"):
        lines.extend([
            "## Entry Reason",
            card["entry_reason"],
            "",
        ])

    if card.get("returns"):
        lines.extend([
            "## Returns",
            "| Horizon | Return | Status |",
            "|---------|--------|--------|",
        ])
        for r in card["returns"]:
            ret = r.get("forward_return")
            ret_str = f"{ret*100:.2f}%" if ret is not None else "pending"
            lines.append(f"| {r['horizon_days']}d | {ret_str} | {r.get('check_status', 'N/A')} |")
        lines.append("")

    if card.get("similar_cases"):
        lines.extend([
            "## Similar Historical Cases",
            "| Date | Symbol | Score | Return | Similarity |",
            "|------|--------|-------|--------|------------|",
        ])
        for c in card["similar_cases"][:5]:
            ret = c.get("t1_return")
            ret_str = f"{ret*100:.2f}%" if ret is not None else "N/A"
            sim = c.get("similarity")
            sim_str = f"{sim:.3f}" if sim is not None else "N/A"
            lines.append(f"| {c.get('trade_date', 'N/A')} | {c.get('symbol', 'N/A')} | {c.get('final_score', 'N/A')} | {ret_str} | {sim_str} |")
        lines.append("")

    if card.get("evidence_summary"):
        lines.extend([
            "## Summary",
            card["evidence_summary"],
        ])

    return "\n".join(lines)


if __name__ == "__main__":
    import argparse
    from sqlalchemy import create_engine
    from db.engine import DATABASE_URL

    logging.basicConfig(level=logging.INFO)

    parser = argparse.ArgumentParser(description="Generate evidence cards")
    parser.add_argument("--date", type=str, required=True, help="Trade date (YYYY-MM-DD)")
    parser.add_argument("--symbol", type=str, help="Specific symbol (optional)")
    parser.add_argument("--format", choices=["json", "markdown"], default="json")
    args = parser.parse_args()

    engine = create_engine(DATABASE_URL)

    trade_date = date.fromisoformat(args.date)

    if args.symbol:
        card = generate_evidence_card(engine, trade_date, args.symbol)
        if args.format == "markdown":
            print(format_evidence_card_markdown(card))
        else:
            print(json.dumps(card, indent=2, default=str))
    else:
        cards = generate_daily_evidence_cards(engine, trade_date)
        if args.format == "markdown":
            for card in cards:
                print(format_evidence_card_markdown(card))
                print("\n---\n")
        else:
            print(json.dumps(cards, indent=2, default=str))
