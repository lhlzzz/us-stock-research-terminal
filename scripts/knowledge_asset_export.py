"""
xiaomei knowledge asset export - Obsidian second brain writer.
Aligned with xiaogu's xiaogu_knowledge_asset_export.py architecture.

Exports picks + top10 candidates + returns to:
1. Summary JSON
2. Obsidian notes (Project/美股, 神临)
3. pgvector TOP10 embeddings
"""

from __future__ import annotations

import json
import logging
import os
from datetime import date, datetime
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# Obsidian paths (WSL mount)
OBSIDIAN_PROJECT_PATH = os.environ.get(
    "XIAOMEI_OBSIDIAN_PROJECT", "/mnt/d/obisidian/Obsidian/Project"
)
OBSIDIAN_SHENLIN_PATH = os.environ.get(
    "XIAOMEI_OBSIDIAN_SHENLIN", "/mnt/d/obisidian/Obsidian/神临"
)

# Summary output path
SUMMARY_DIR = Path(__file__).resolve().parent.parent / "research" / "knowledge-assets"


def _ensure_dir(path: Path) -> Path:
    """Create directory if not exists."""
    path.mkdir(parents=True, exist_ok=True)
    return path


def _format_score(score: float) -> str:
    """Format score for display."""
    if score is None:
        return "N/A"
    return f"{score:.4f}"


def _format_return(ret: float) -> str:
    """Format return for display."""
    if ret is None:
        return "pending"
    sign = "+" if ret >= 0 else ""
    return f"{sign}{ret*100:.2f}%"


def _as_dict(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return value
    if isinstance(value, str):
        try:
            parsed = json.loads(value)
        except json.JSONDecodeError:
            return {}
        return parsed if isinstance(parsed, dict) else {}
    return {}


def _build_case_text(ticket: dict[str, Any]) -> str:
    """Make one self-contained, retrieval-ready research case."""
    factor_snapshot = _as_dict(ticket.get("factor_snapshot"))
    source_layers = _as_dict(ticket.get("source_layers"))
    outcomes = ticket.get("outcomes") or {}
    factor_names = [
        "large_participant_footprint_score",
        "footprint_factor_coverage",
        "market_participation_score",
        "breakout_score",
        "relative_strength_vs_equal_weight",
        "volume_confirmation_ratio",
        "closing_strength_5d",
        "risk_penalty",
    ]
    factor_text = ", ".join(
        f"{name}={factor_snapshot[name]}"
        for name in factor_names
        if factor_snapshot.get(name) is not None
    ) or "unavailable"
    outcome_text = "; ".join(
        f"{horizon}: status={item.get('status')}, return={_format_return(item.get('forward_return'))}, "
        f"outcome={item.get('outcome_classification') or 'PENDING'}, "
        f"reason={item.get('outcome_reason') or 'unavailable'}"
        for horizon, item in sorted(outcomes.items())
    ) or "no forward-tracking record"
    return "\n".join(
        [
            f"US research case: {ticket.get('symbol', 'unknown')}",
            f"Selection: {ticket.get('entry_reason') or ticket.get('selection_reason') or 'unavailable'}",
            f"Classification: {ticket.get('classification') or 'unavailable'}",
            f"Research run: {ticket.get('research_run_id') or 'UNAVAILABLE_HISTORICAL'}; "
            f"commit: {ticket.get('git_commit') or 'UNAVAILABLE_HISTORICAL'}",
            f"Observable footprint: {factor_text}",
            f"Evidence availability: {json.dumps(source_layers, ensure_ascii=False, default=str)}",
            f"Lifecycle outcome: {outcome_text}",
        ]
    )


def _build_ticket_section(ticket: dict, returns: dict = None) -> str:
    """Build markdown section for a ticket."""
    symbol = ticket.get("symbol", "unknown")
    score = ticket.get("ticket_score")
    market = ticket.get("market_score")
    catalyst = ticket.get("catalyst_score")
    classification = ticket.get("classification", "")
    risk = ticket.get("risk_verdict", "")
    entry_reason = ticket.get("entry_reason", "")

    lines = [
        f"### {symbol}",
        f"- **Score**: {_format_score(score)} (market={_format_score(market)}, catalyst={_format_score(catalyst)})",
        f"- **Classification**: {classification}",
        f"- **Risk**: {risk}",
    ]

    if entry_reason:
        lines.append(f"- **Reason**: {entry_reason[:200]}")

    lines.append(
        f"- **Research version**: run={ticket.get('research_run_id') or 'UNAVAILABLE_HISTORICAL'}, "
        f"commit={ticket.get('git_commit') or 'UNAVAILABLE_HISTORICAL'}"
    )
    factor_snapshot = _as_dict(ticket.get("factor_snapshot"))
    if factor_snapshot:
        lines.append(
            "- **Observable footprint**: "
            f"score={factor_snapshot.get('large_participant_footprint_score', 'N/A')}, "
            f"coverage={factor_snapshot.get('footprint_factor_coverage', 'N/A')}, "
            f"risk_penalty={factor_snapshot.get('risk_penalty', 'N/A')}"
        )

    if returns:
        lines.append("- **Returns**:")
        for horizon in [1, 3, 5, 10]:
            ret = returns.get(f"forward_{horizon}d")
            if ret is not None:
                lines.append(f"  - {horizon}d: {_format_return(ret)}")
    for horizon, outcome in sorted((ticket.get("outcomes") or {}).items()):
        lines.append(
            f"- **{horizon} attribution**: "
            f"{outcome.get('outcome_classification') or outcome.get('status') or 'PENDING'}; "
            f"{outcome.get('outcome_reason') or 'unavailable'}"
        )

    return "\n".join(lines)


def _build_top10_table(candidates: list[dict]) -> str:
    """Build markdown table for top10 candidates."""
    lines = [
        "| Rank | Symbol | Score | Market | Catalyst | Decision |",
        "|------|--------|-------|--------|----------|----------|",
    ]

    for i, c in enumerate(candidates[:10], 1):
        symbol = c.get("symbol", "?")
        score = _format_score(c.get("final_score"))
        market = _format_score(c.get("market_score"))
        catalyst = _format_score(c.get("catalyst_score"))
        decision = c.get("decision", "")
        lines.append(f"| {i} | {symbol} | {score} | {market} | {catalyst} | {decision} |")

    return "\n".join(lines)


def export_daily_knowledge(
    engine,
    trade_date: date,
    force: bool = False,
) -> dict:
    """Export daily knowledge assets.

    Returns: {summary_path, obsidian_project_path, obsidian_shenlin_path, vector_count}
    """
    from sqlalchemy import text

    # 1. Fetch tickets with their immutable run, evidence, and factor context.
    with engine.connect() as conn:
        result = conn.execute(text("""
            SELECT
                t.id AS ticket_id,
                t.symbol,
                t.ticket_score,
                t.market_score,
                t.catalyst_score,
                t.classification,
                t.risk_verdict,
                t.quality_verdict,
                t.entry_reason,
                t.research_run_id,
                rr.git_commit,
                rr.config AS research_config,
                dc.source_layers,
                dc.factor_snapshot,
                dc.ranking_basis,
                dc.selection_reason
            FROM tickets t
            LEFT JOIN research_runs rr ON rr.run_id = t.research_run_id
            LEFT JOIN daily_candidates dc
              ON dc.trade_date = t.output_date
             AND dc.symbol = t.symbol
            WHERE t.output_date = :trade_date
            ORDER BY t.ticket_score DESC
        """), {"trade_date": trade_date})
        tickets = [dict(row._mapping) for row in result.fetchall()]

    if not tickets:
        logger.warning(f"No tickets found for {trade_date}")
        return {"error": "no tickets"}

    # 2. Fetch candidates with their reproducible ranking context.
    with engine.connect() as conn:
        result = conn.execute(text("""
            SELECT symbol, stock_name, final_score, market_score, catalyst_score,
                   decision, candidate_entry_reason, selection_reason,
                   source_layers, factor_snapshot, ranking_basis, research_run_id
            FROM daily_candidates
            WHERE trade_date = :trade_date
            ORDER BY final_score DESC NULLS LAST
            LIMIT 10
        """), {"trade_date": trade_date})
        top10 = [dict(row._mapping) for row in result.fetchall()]

    # 3. Fetch complete forward-tracking outcomes for every ticket.
    with engine.connect() as conn:
        result = conn.execute(text("""
            SELECT
                t.id AS ticket_id,
                t.symbol,
                ft.horizon_days,
                ft.check_status,
                ft.forward_return,
                ft.outcome_classification,
                ft.outcome_reason,
                ft.due_date
            FROM tickets t
            LEFT JOIN forward_tracking ft ON t.id = ft.ticket_id
            WHERE t.output_date = :trade_date
            ORDER BY t.symbol, ft.horizon_days
        """), {"trade_date": trade_date})
        tracking_rows = [dict(row._mapping) for row in result.fetchall()]

    outcomes_by_ticket: dict[int, dict[str, dict[str, Any]]] = {}
    returns_map: dict[str, dict[str, Any]] = {}
    for tracking in tracking_rows:
        if tracking.get("horizon_days") is None:
            continue
        horizon = f"{tracking['horizon_days']}d"
        outcome = {
            "status": tracking.get("check_status"),
            "forward_return": tracking.get("forward_return"),
            "outcome_classification": tracking.get("outcome_classification"),
            "outcome_reason": tracking.get("outcome_reason"),
            "due_date": tracking.get("due_date"),
        }
        outcomes_by_ticket.setdefault(int(tracking["ticket_id"]), {})[horizon] = outcome
        returns_map.setdefault(str(tracking["symbol"]), {})[f"forward_{tracking['horizon_days']}d"] = tracking.get("forward_return")

    # 4. Include non-return paper and journal records from the single trace view.
    with engine.connect() as conn:
        result = conn.execute(text("""
            SELECT ticket_id, record_type, record_status, horizon_days,
                   forward_return, pnl, outcome_classification, outcome_reason, paper_reason
            FROM research_trade_trace
            WHERE output_date = :trade_date
              AND ticket_id IS NOT NULL
            ORDER BY ticket_id, record_type, horizon_days NULLS FIRST
        """), {"trade_date": trade_date})
        traces_by_ticket: dict[int, list[dict[str, Any]]] = {}
        for row in result.fetchall():
            trace = dict(row._mapping)
            traces_by_ticket.setdefault(int(trace["ticket_id"]), []).append(trace)

    for ticket in tickets:
        ticket_id = int(ticket["ticket_id"])
        ticket["outcomes"] = outcomes_by_ticket.get(ticket_id, {})
        ticket["trace_records"] = traces_by_ticket.get(ticket_id, [])
        ticket["research_case_text"] = _build_case_text(ticket)

    # 5. Build summary JSON.
    summary = {
        "trade_date": trade_date.isoformat(),
        "exported_at": datetime.now().isoformat(),
        "tickets": tickets,
        "top10": top10,
        "returns": returns_map,
        "tracking": tracking_rows,
        "ticket_count": len(tickets),
        "top10_count": len(top10),
    }

    summary_dir = _ensure_dir(SUMMARY_DIR)
    summary_path = summary_dir / f"{trade_date.isoformat()}_knowledge.json"
    summary_path.write_text(json.dumps(summary, indent=2, ensure_ascii=False, default=str))
    logger.info(f"Summary written: {summary_path}")

    # 6. Write Obsidian project note
    obsidian_project_path = None
    if os.path.exists(OBSIDIAN_PROJECT_PATH):
        inbox_dir = _ensure_dir(Path(OBSIDIAN_PROJECT_PATH) / "美股" / "inbox")
        note_path = inbox_dir / f"{trade_date.isoformat()}-知识资产.md"

        # Build note content
        lines = [
            f"# {trade_date.isoformat()} 美股知识资产",
            "",
            f"**Exported**: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
            f"**Tickets**: {len(tickets)}",
            "",
            "## 正式票",
            "",
        ]

        for ticket in tickets:
            symbol = ticket.get("symbol")
            returns = returns_map.get(symbol, {})
            lines.append(_build_ticket_section(ticket, returns))
            lines.append("")

        if top10:
            lines.extend([
                "## Top10 候选池",
                "",
                _build_top10_table(top10),
                "",
            ])

        lines.extend([
            "## 向量层",
            "",
            f"- **Backend**: sentence-transformers (neural)",
            f"- **Dimension**: 384",
            f"- **Index**: HNSW cosine",
            "",
            "## 使用指南",
            "",
            "1. 回顾正式票的 entry_reason 和 returns",
            "2. 分析 Top10 中未入选的原因",
            "3. 使用 pgvector 检索相似历史案例",
            "4. 结合因子分析优化权重",
        ])

        note_path.write_text("\n".join(lines))
        obsidian_project_path = str(note_path)
        logger.info(f"Obsidian project note written: {note_path}")

        # Update status.md
        status_path = Path(OBSIDIAN_PROJECT_PATH) / "美股" / "状态.md"
        if status_path.exists():
            status_content = status_path.read_text()
            # Update head section with stamped status block
            status_block = f"""
## 最新状态 (自动更新)

- **日期**: {trade_date.isoformat()}
- **出票数**: {len(tickets)}
- **Top1**: {tickets[0].get('symbol', 'N/A')} ({_format_score(tickets[0].get('ticket_score'))})
- **更新时间**: {datetime.now().strftime('%Y-%m-%d %H:%M')}
"""
            # Replace existing status block or append
            if "## 最新状态 (自动更新)" in status_content:
                import re
                status_content = re.sub(
                    r"## 最新状态 \(自动更新\).*?(?=\n## |\Z)",
                    status_block.strip() + "\n",
                    status_content,
                    flags=re.DOTALL
                )
            else:
                status_content = status_block + status_content

            status_path.write_text(status_content)
            logger.info(f"Obsidian status updated: {status_path}")

    # 7. Write 神临 pointer note
    obsidian_shenlin_path = None
    if os.path.exists(OBSIDIAN_SHENLIN_PATH):
        ideas_dir = _ensure_dir(Path(OBSIDIAN_SHENLIN_PATH) / "想法池")
        pointer_path = ideas_dir / f"{trade_date.isoformat()}-xiaomei知识资产指针.md"

        pointer_content = f"""# xiaomei 知识资产指针

**日期**: {trade_date.isoformat()}
**出票数**: {len(tickets)}

## 正式票

{', '.join(t.get('symbol', '?') for t in tickets)}

## 详细资产

见: `Project/美股/inbox/{trade_date.isoformat()}-知识资产.md`

## 向量检索

```sql
SELECT * FROM pick_case_embeddings
WHERE trade_date = '{trade_date.isoformat()}'
ORDER BY embedding <=> (SELECT embedding FROM pick_case_embeddings WHERE symbol = '{tickets[0].get("symbol", "AAPL")}' LIMIT 1)
LIMIT 5;
```
"""
        pointer_path.write_text(pointer_content)
        obsidian_shenlin_path = str(pointer_path)
        logger.info(f"Obsidian shenlin pointer written: {pointer_path}")

    # 8. Upsert full official-ticket lifecycle cases in the existing vector store.
    vector_count = 0
    try:
        from neural_vector_store import upsert_pick_case, upsert_top10_cases_from_db

        for ticket in tickets:
            first_return = (ticket.get("outcomes") or {}).get("1d", {}).get("forward_return")
            upsert_pick_case(
                engine,
                trade_date,
                ticket["symbol"],
                "TICKET_LIFECYCLE",
                ticket,
                t1_return=first_return,
            )
            vector_count += 1
        vector_count += upsert_top10_cases_from_db(engine, trade_date)
    except Exception as e:
        logger.warning(f"Failed to upsert TOP10 vectors: {e}")

    return {
        "summary_path": str(summary_path),
        "obsidian_project_path": obsidian_project_path,
        "obsidian_shenlin_path": obsidian_shenlin_path,
        "vector_count": vector_count,
        "ticket_count": len(tickets),
        "top10_count": len(top10),
    }


def backfill_knowledge_assets(
    engine,
    start_date: date = None,
    end_date: date = None,
) -> list[dict]:
    """Backfill knowledge assets for historical dates.

    Returns: list of export results
    """
    from sqlalchemy import text

    if end_date is None:
        end_date = date.today()

    with engine.connect() as conn:
        if start_date:
            result = conn.execute(text("""
                SELECT DISTINCT output_date
                FROM tickets
                WHERE output_date BETWEEN :start AND :end
                ORDER BY output_date
            """), {"start": start_date, "end": end_date})
        else:
            result = conn.execute(text("""
                SELECT DISTINCT output_date
                FROM tickets
                ORDER BY output_date
            """))

        dates = [row[0] for row in result.fetchall()]

    results = []
    for d in dates:
        try:
            r = export_daily_knowledge(engine, d)
            results.append(r)
            logger.info(f"Exported knowledge for {d}: {r.get('ticket_count', 0)} tickets")
        except Exception as e:
            logger.error(f"Failed to export knowledge for {d}: {e}")
            results.append({"trade_date": d.isoformat(), "error": str(e)})

    return results


if __name__ == "__main__":
    import argparse
    from sqlalchemy import create_engine

    logging.basicConfig(level=logging.INFO)

    parser = argparse.ArgumentParser(description="Export knowledge assets")
    parser.add_argument("--date", type=str, help="Trade date (YYYY-MM-DD)")
    parser.add_argument("--backfill", action="store_true", help="Backfill all dates")
    parser.add_argument("--start-date", type=str, help="Backfill start date")
    args = parser.parse_args()

    db_url = os.environ.get("DATABASE_URL", "postgresql://xiaomei:xiaomei2026@localhost:5432/xiaomei")
    engine = create_engine(db_url)

    if args.backfill:
        start = date.fromisoformat(args.start_date) if args.start_date else None
        results = backfill_knowledge_assets(engine, start)
        print(json.dumps(results, indent=2, default=str))
    elif args.date:
        trade_date = date.fromisoformat(args.date)
        result = export_daily_knowledge(engine, trade_date)
        print(json.dumps(result, indent=2, default=str))
    else:
        # Default: today
        result = export_daily_knowledge(engine, date.today())
        print(json.dumps(result, indent=2, default=str))
