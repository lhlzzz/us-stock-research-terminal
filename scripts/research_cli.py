#!/usr/bin/env python3
"""Xiaomei 2.2 research CLI. Research OS only; never production ranking."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))


def _provider():
    from data_provider import DataProvider

    return DataProvider()


def _print(payload) -> None:
    print(json.dumps(payload, indent=2, default=str, sort_keys=True))


def cmd_research_company(args: argparse.Namespace) -> int:
    from research.runtime import run_symbol_research

    payload = run_symbol_research(
        symbol=args.symbol,
        as_of=args.as_of,
        provider=_provider(),
        persist=not args.no_persist,
    )
    summary = {
        "run_id": payload.get("run_id"),
        "symbol": payload.get("symbol"),
        "as_of": payload.get("as_of"),
        "classification": payload.get("classification"),
        "readiness": payload.get("readiness"),
        "data_gaps": payload.get("data_gaps"),
        "evidence_count": payload.get("evidence_count"),
        "providers": payload.get("providers"),
        "produces_pick": payload.get("produces_pick"),
        "ranking_owner": payload.get("ranking_owner"),
        "production_ranking_key": payload.get("production_ranking_key"),
        "reused": payload.get("reused"),
        "why_not": payload.get("why_not"),
        "thesis": payload.get("thesis"),
        "contradictions": {
            "status": (payload.get("contradictions") or {}).get("status"),
            "bull": (payload.get("contradictions") or {}).get("bull"),
            "bear": (payload.get("contradictions") or {}).get("bear"),
        },
        "sec_status": (payload.get("sec") or {}).get("status"),
        "earnings_status": (payload.get("earnings") or {}).get("status"),
        "revision_status": (payload.get("revisions") or {}).get("status"),
        "industry_status": (payload.get("industry") or {}).get("status"),
        "universe_status": (payload.get("universe") or {}).get("status"),
        "chokepoint_status": ((payload.get("industry") or {}).get("chokepoint") or {}).get("status"),
    }
    _print(summary if not args.full else payload)
    return 0


def cmd_show_evidence(args: argparse.Namespace) -> int:
    from research.store import connect, evidence_lineage

    conn = connect()
    _print(evidence_lineage(conn, symbol=args.symbol, as_of=args.as_of))
    conn.close()
    return 0


def cmd_why_not(args: argparse.Namespace) -> int:
    from research.query import research_query
    from research.runtime import run_symbol_research

    payload = run_symbol_research(symbol=args.symbol, as_of=args.as_of, provider=_provider())
    _print(research_query(f"research why-not {args.symbol}", company=payload))
    return 0


def cmd_failure_show(args: argparse.Namespace) -> int:
    from research.failure import retrieve_failures
    from research.store import connect, load_failures

    conn = connect()
    stored = load_failures(conn, symbol=args.symbol or None)
    conn.close()
    memory = retrieve_failures(symbol=args.symbol or None, failure_type=args.failure_type or None)
    _print({"stored": stored, "memory": memory, "produces_pick": False})
    return 0


def cmd_learning_show(args: argparse.Namespace) -> int:
    from research.failure import retrieve_patterns
    from research.store import connect, load_patterns

    conn = connect()
    stored = load_patterns(conn)
    conn.close()
    _print({"stored": stored, "memory": retrieve_patterns(pattern_type=args.pattern_type or None), "produces_pick": False})
    return 0


def cmd_seed_learning(args: argparse.Namespace) -> int:
    from research.runtime import seed_demo_learning

    _print(seed_demo_learning(symbol=args.symbol, as_of=args.as_of))
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Xiaomei 2.2 research CLI")
    sub = parser.add_subparsers(dest="command", required=True)

    company = sub.add_parser("research")
    company_sub = company.add_subparsers(dest="research_kind", required=True)
    company_cmd = company_sub.add_parser("company")
    company_cmd.add_argument("symbol")
    company_cmd.add_argument("--as-of", required=True)
    company_cmd.add_argument("--full", action="store_true")
    company_cmd.add_argument("--no-persist", action="store_true")
    company_cmd.set_defaults(func=cmd_research_company)

    evidence = sub.add_parser("show")
    evidence_sub = evidence.add_subparsers(dest="show_kind", required=True)
    evidence_cmd = evidence_sub.add_parser("evidence")
    evidence_cmd.add_argument("symbol")
    evidence_cmd.add_argument("--as-of")
    evidence_cmd.set_defaults(func=cmd_show_evidence)

    why = sub.add_parser("why-not")
    why.add_argument("symbol")
    why.add_argument("--as-of", required=True)
    why.set_defaults(func=cmd_why_not)

    failure = sub.add_parser("failure")
    failure_sub = failure.add_subparsers(dest="failure_kind", required=True)
    failure_cmd = failure_sub.add_parser("show")
    failure_cmd.add_argument("symbol", nargs="?")
    failure_cmd.add_argument("--failure-type")
    failure_cmd.set_defaults(func=cmd_failure_show)

    learning = sub.add_parser("learning")
    learning_sub = learning.add_subparsers(dest="learning_kind", required=True)
    learning_cmd = learning_sub.add_parser("show")
    learning_cmd.add_argument("--pattern-type")
    learning_cmd.set_defaults(func=cmd_learning_show)
    seed = learning_sub.add_parser("seed")
    seed.add_argument("symbol")
    seed.add_argument("--as-of", required=True)
    seed.set_defaults(func=cmd_seed_learning)

    args = parser.parse_args(argv)
    return int(args.func(args) or 0)


if __name__ == "__main__":
    raise SystemExit(main())
