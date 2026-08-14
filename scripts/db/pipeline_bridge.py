"""Bridge between pipeline outputs and PostgreSQL database.

Called from pipeline's save_outputs to persist tickets, forward_tracking,
runtime_decisions, and research_runs to the database.
"""
from datetime import date, datetime
from typing import Any
from sqlalchemy.orm import Session


def _safe_float(val: Any, default: float = 0.0) -> float:
    """Safely convert value to float, returning default if None or invalid."""
    if val is None:
        return default
    try:
        return float(val)
    except (ValueError, TypeError):
        return default


def _safe_str(val: Any, default: str = "") -> str:
    """Safely convert value to string, returning default if None."""
    if val is None:
        return default
    return str(val)


def _safe_format_float(val: Any, fmt: str = ".3f", default: float = 0.0) -> str:
    """Safely format float value, returning formatted default if None."""
    return f"{_safe_float(val, default):{fmt}}"


def normalize_ticket(row: dict) -> dict:
    """Normalize ticket fields to ensure no None values cause format errors."""
    normalized = dict(row)

    # Numeric fields with safe defaults
    numeric_fields = {
        "market_score": 0.0,
        "catalyst_score": 0.0,
        "ticket_score": 0.0,
        "institutional_flow_score": 0.5,
        "social_sentiment_score": 0.3,
        "raw_market_score": 0.0,
        "blended_score": 0.0,
        "risk_penalty": 0.0,
        "confirmation_score": 0.0,
        "prior_5d_momentum": 0.0,
        "prior_20d_momentum": 0.0,
        "five_day_acceleration": 0.0,
        "relative_strength_vs_equal_weight": 0.0,
        "volume_weighted_momentum": 0.0,
        "rsi_14": 50.0,
        "momentum_quality": 0.0,
        "breakout_score": 0.0,
        "reversal_quality": 0.0,
        "volume_confirmation_ratio": 0.0,
        "closing_strength_5d": 0.0,
        "median_dollar_volume_20d": 0.0,
    }
    for field, default in numeric_fields.items():
        normalized[field] = _safe_float(normalized.get(field), default)

    # Text fields with safe defaults
    text_fields = {
        "symbol": "",
        "classification": "NEED_MORE_EVIDENCE",
        "evidence_gate_status": "",
        "risk_verdict": "",
        "quality_verdict": "",
        "lifecycle_stage": "",
        "narrative_title": "",
        "business_title": "",
        "risk_summary": "",
        "quality_summary": "",
        "panel_verdict": "",
        "market_regime": "",
        "entry_reason": "",
    }
    for field, default in text_fields.items():
        normalized[field] = _safe_str(normalized.get(field), default)

    # Ensure symbol is not empty
    if not normalized["symbol"]:
        normalized["symbol"] = "UNKNOWN"

    return normalized


def save_pipeline_to_db(
    db: Session,
    output_date: str,
    metrics: dict[str, Any],
    top_candidates: list[dict],
    forward_tracking_rows: list[dict],
) -> dict[str, int]:
    """Save pipeline outputs to PostgreSQL.

    Returns counts of inserted records.
    """
    from scripts.db.crud import (
        create_ticket, upsert_forward_tracking,
        create_runtime_decision, create_research_run,
        upsert_market_snapshot, upsert_factor_snapshot,
    )

    counts = {"tickets": 0, "forward_tracking": 0, "runtime_decisions": 0}
    ticket_ids: dict[tuple[str, str], int] = {}

    # Save research run
    run = create_research_run(
        db,
        run_name=metrics.get("run_name", "pipeline"),
        output_date=output_date,
        status="done",
        candidate_count=metrics.get("paper_review_count", 0) + metrics.get("market_watchlist_count", 0),
        pass_count=metrics.get("paper_review_count", 0),
    )

    # Save tickets
    for row in top_candidates:
        try:
            # Normalize ticket to handle None values
            row = normalize_ticket(row)

            # 构建出票理由
            narrative_title = row.get("narrative_top_title") or row.get("narrative_title", "")
            business_title = row.get("business_top_title") or row.get("business_title", "")
            risk_summary = row.get("risk_summary", "")

            # 从嵌套结构提取
            quality_check = row.get("quality_check", {})
            quality_verdict_str = quality_check.get("quality_verdict", "") if isinstance(quality_check, dict) else ""
            quality_score_val = quality_check.get("overall_quality_score") if isinstance(quality_check, dict) else None
            quality_summary = quality_verdict_str
            if quality_score_val is not None:
                quality_summary += f" (score={_safe_float(quality_score_val):.2f})"

            risk_checklist = row.get("risk_checklist", {})
            risk_verdict_detail = risk_checklist.get("risk_verdict", "") if isinstance(risk_checklist, dict) else ""
            red_count = risk_checklist.get("red_count", 0) if isinstance(risk_checklist, dict) else 0
            yellow_count = risk_checklist.get("yellow_count", 0) if isinstance(risk_checklist, dict) else 0
            if risk_verdict_detail:
                risk_summary = f"{risk_verdict_detail} (red={red_count}, yellow={yellow_count})"

            research_panel = row.get("research_panel", {})
            panel_verdict = research_panel.get("panel_verdict", "") if isinstance(research_panel, dict) else ""
            panel_summary = research_panel.get("summary", "") if isinstance(research_panel, dict) else ""

            market_regime = metrics.get("regime", "")
            if hasattr(market_regime, "name"):
                market_regime = market_regime.name

            # 构建 entry_reason (使用 safe format)
            entry_parts = []
            if narrative_title:
                entry_parts.append(f"catalyst: {narrative_title}")
            if business_title:
                entry_parts.append(f"business: {business_title}")
            ms = _safe_float(row.get("market_score"))
            cs = _safe_float(row.get("catalyst_score"))
            entry_parts.append(f"scores: market={ms:.3f} catalyst={cs:.3f}")
            if panel_verdict:
                entry_parts.append(f"panel: {panel_verdict}")
            if risk_verdict_detail:
                entry_parts.append(f"risk: {risk_verdict_detail}")
            entry_reason = " | ".join(entry_parts)

            ticket = create_ticket(
                db,
                output_date=output_date,
                symbol=row["symbol"],
                as_of_date=row.get("as_of_date", output_date),
                ticket_rank=row.get("ticket_rank"),
                market_score=row.get("market_score"),
                catalyst_score=row.get("catalyst_score"),
                ticket_score=row.get("ticket_score"),
                classification=row.get("classification"),
                evidence_gate_status=row.get("evidence_gate_status"),
                risk_verdict=risk_verdict_detail or row.get("risk_verdict"),
                quality_verdict=quality_verdict_str or row.get("quality_verdict"),
                lifecycle_stage=row.get("lifecycle_stage"),
                run_name=metrics.get("run_name"),
                narrative_title=narrative_title,
                business_title=business_title,
                risk_summary=risk_summary,
                quality_summary=quality_summary,
                panel_verdict=panel_verdict,
                market_regime=market_regime,
                entry_reason=entry_reason,
                institutional_flow_score=row.get("institutional_flow_score"),
                social_sentiment_score=row.get("social_sentiment_score"),
                raw_market_score=row.get("raw_market_score"),
                blended_score=row.get("blended_score"),
                breakout_score=row.get("breakout_score"),
                risk_penalty=row.get("risk_penalty"),
                confirmation_score=row.get("confirmation_score"),
            )
            as_of_date = row.get("as_of_date", output_date)
            ticket_ids[(row["symbol"], str(as_of_date))] = ticket.id
            ticket_ids.setdefault((row["symbol"], str(output_date)), ticket.id)
            counts["tickets"] += 1
        except Exception as e:
            print(f"  DB ticket save error for {row.get('symbol', 'UNKNOWN')}: {e}")

    # Save forward tracking rows
    for ft in forward_tracking_rows:
        try:
            track_key = ft.get("track_key") or f"{output_date}:{ft['symbol']}:{ft.get('horizon_days', '')}d"
            as_of_date = ft.get("as_of_date", output_date)
            ticket_id = ft.get("ticket_id")
            if ticket_id is None:
                ticket_id = ticket_ids.get((ft["symbol"], str(as_of_date)))
            if ticket_id is None:
                ticket_id = ticket_ids.get((ft["symbol"], str(output_date)))
            upsert_forward_tracking(
                db,
                track_key=track_key,
                output_date=output_date,
                symbol=ft["symbol"],
                as_of_date=ft.get("as_of_date", output_date),
                horizon_days=ft.get("horizon_days"),
                due_date=ft.get("due_date"),
                as_of_close=ft.get("as_of_close"),
                check_status="pending",
                ticket_id=ticket_id,
            )
            counts["forward_tracking"] += 1
        except Exception as e:
            print(f"  DB tracking save error for {ft.get('symbol', 'UNKNOWN')}: {e}")

    # Save runtime decision
    try:
        regime = None
        regime_data = metrics.get("regime")
        if regime_data and hasattr(regime_data, "name"):
            regime = regime_data.name
        elif isinstance(regime_data, str):
            regime = regime_data

        create_runtime_decision(
            db,
            output_date=output_date,
            run_name=metrics.get("run_name"),
            final_classification=metrics.get("final_classification"),
            paper_review_count=metrics.get("paper_review_count", 0),
            market_watchlist_count=metrics.get("market_watchlist_count", 0),
            universe_count=metrics.get("source_universe_included_symbols"),
            regime=regime,
            summary=metrics,
        )
        counts["runtime_decisions"] += 1
    except Exception as e:
        print(f"  DB runtime_decision save error: {e}")

    # Save market snapshot
    try:
        as_of = metrics.get("as_of_date")
        if as_of:
            market_summary = metrics.get("market_summary", {})
            upsert_market_snapshot(
                db,
                trade_date=date.fromisoformat(as_of),
                regime=regime,
                universe_count=metrics.get("source_universe_included_symbols"),
            )
    except Exception as e:
        print(f"  DB market_snapshot save error: {e}")

    # Save factor snapshots for top candidates
    for row in top_candidates:
        try:
            row = normalize_ticket(row)
            as_of = row.get("as_of_date")
            if as_of:
                upsert_factor_snapshot(
                    db,
                    trade_date=date.fromisoformat(as_of) if isinstance(as_of, str) else as_of,
                    symbol=row["symbol"],
                    prior_5d_momentum=row.get("prior_5d_momentum"),
                    prior_20d_momentum=row.get("prior_20d_momentum"),
                    five_day_acceleration=row.get("five_day_acceleration"),
                    relative_strength=row.get("relative_strength_vs_equal_weight"),
                    volume_weighted_momentum=row.get("volume_weighted_momentum"),
                    rsi_14=row.get("rsi_14"),
                    momentum_quality=row.get("momentum_quality"),
                    breakout_score=row.get("breakout_score"),
                    reversal_quality=row.get("reversal_quality"),
                    volume_confirmation=row.get("volume_confirmation_ratio"),
                    closing_strength_5d=row.get("closing_strength_5d"),
                    dollar_volume_20d=row.get("median_dollar_volume_20d"),
                    market_score=row.get("market_score"),
                    blended_score=row.get("blended_score"),
                    theme_strength=row.get("theme_strength"),
                    announcement_catalyst=row.get("announcement_catalyst"),
                    regime=regime,
                )
        except Exception as e:
            print(f"  DB factor_snapshot save error for {row.get('symbol', 'UNKNOWN')}: {e}")

    # Save signals for top candidates
    SIGNAL_FIELDS = [
        "market_score", "catalyst_score", "ticket_score",
        "prior_20d_momentum", "five_day_acceleration",
        "relative_strength_vs_equal_weight", "volume_weighted_momentum",
        "volume_confirmation_ratio", "closing_strength_5d",
        "rsi_14", "momentum_quality", "breakout_score", "reversal_quality",
        "theme_strength", "announcement_catalyst",
    ]
    for row in top_candidates:
        try:
            row = normalize_ticket(row)
            as_of = row.get("as_of_date")
            if not as_of:
                continue
            trade_date = date.fromisoformat(as_of) if isinstance(as_of, str) else as_of
            symbol = row["symbol"]
            for signal_key in SIGNAL_FIELDS:
                signal_value = row.get(signal_key)
                if signal_value is not None:
                    from scripts.db.crud import upsert_signal
                    upsert_signal(db, trade_date, symbol, signal_key, float(signal_value))
        except Exception as e:
            print(f"  DB signal save error for {row.get('symbol', 'UNKNOWN')}: {e}")

    db.commit()
    return counts
