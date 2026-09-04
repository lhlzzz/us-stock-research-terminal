#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
import re
from datetime import datetime
from functools import lru_cache
from concurrent.futures import ThreadPoolExecutor, as_completed
from collections import Counter
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from historical_replay_baseline import (
    DEFAULT_BATCH_SIZE,
    DEFAULT_MIN_HISTORY_DAYS,
    DEFAULT_MIN_MEDIAN_DOLLAR_VOLUME,
    DEFAULT_MIN_PRICE,
    EASTMONEY_HISTORICAL_SOURCE_DISPLAY,
    build_close_panel,
    dedupe_preserve_order,
    fetch_universe,
    load_universe_source,
    output_date_string,
    project_root,
    serializable,
    write_csv,
    write_json,
    write_text,
)
from eastmoney_us import (
    candidate_enhanced_urls,
    information_coverage_audit,
    normalize_us_symbol,
)
from data_provider import get_provider
from market_calendar import CALENDAR, add_trading_days
from research.temporal import historical_claim_eligible

EASTMONEY_HISTORICAL_SOURCE_DISPLAY = "DataProvider historical OHLCV"
AKSHARE_HISTORICAL_SOURCE_DISPLAY = "DataProvider fallback historical OHLCV"
from research_panel import run_full_research_panel  # compatibility adapter → scripts.research
from risk_manager import (
    DEFAULT_RISK_PER_TRADE,
    MAX_CONSECUTIVE_LOSSES,
    RiskState,
    assess_trade_risk,
    build_candidate_risk_record,
    update_risk_state,
)
from market_regime import (
    classify_market_regime,
    get_regime_thresholds,
    format_regime_summary,
)
from dynamic_horizon import (
    batch_assign_horizons,
    get_dynamic_tracking_horizons,
    format_allocation_report,
)
from capital import build_capital_assessment
from capital.lifecycle import write_capital_learning_artifacts, write_daily_capital_report


LAST30DAYS_SCRIPT = Path("/root/.agents/skills/last30days/scripts/last30days.py")
LAST30DAYS_PYTHON = Path("/root/.local/share/hermes-tools/last30days-py312/bin/python")
DEFAULT_UNIVERSE_SOURCE = "nasdaq100_sp500_union"
DEFAULT_UNIVERSE_KEY = None
DEFAULT_PERIODS = ["1y", "6mo"]
DEFAULT_RUN_NAME = "profit-ticket-pipeline"
DEFAULT_TOP_K = 3
DEFAULT_CANDIDATE_POOL_SIZE = 50
MIN_TICKET_SCORE = 0.3  # Lowered: data shows low-score tickets outperform (contrarian edge)
DATA_SOURCE_MISMATCH_THRESHOLD = 0.01
QUOTE_SOURCE_DISPLAY = "DataProvider realtime quote (Scrapy-owned API transport)"
MARKET_DATA_SOURCE_DISPLAY = "DataProvider historical OHLCV + realtime quote"
TRACKING_HORIZONS = [1, 3, 5, 10]
CAPITAL_CANDIDATE_FIELDS = (
    "capital_model_version",
    "capital_validation_status",
    "statistical_score",
    "capital_behavior_score",
    "capital_score",
    "combined_score",
    "capital_strength",
    "dominant_direction",
    "dominant_pressure",
    "capital_state",
    "previous_capital_state",
    "state_transition",
    "state_duration",
    "capital_state_confidence",
    "capital_state_reason",
    "capital_intent",
    "capital_intent_confidence",
    "upward_pressure",
    "downward_pressure",
    "volume_pressure",
    "accumulation_score",
    "absorption_score",
    "supply_exhaustion_score",
    "demand_persistence_score",
    "markup_score",
    "distribution_score",
    "price_control_score",
    "upside_control_efficiency",
    "downside_control_efficiency",
    "crowding_score",
    "trap_score",
    "price_impact_score",
    "expected_direction",
    "path_type",
    "predicted_path",
    "path_confidence",
    "t1_probability",
    "t3_probability",
    "t5_probability",
    "capital_thesis",
    "invalidation_condition",
)
RUN_ARTIFACT_FILENAMES = {
    "summary": "summary-{output_date}.md",
    "metrics": "metrics-{output_date}.json",
    "candidates": "candidates-{output_date}.csv",
    "forward_tracking": "forward-tracking-{output_date}.csv",
    "runtime_context": "runtime-decision-context-{output_date}.json",
    "runtime_ledger": "runtime-decision-ledger.jsonl",
}
NARRATIVE_QUERY_SUFFIX = "stock catalyst earnings news"
LAST30DAYS_TIMEOUT_SECONDS = 20
LAST30DAYS_CACHE_DIR = Path(__file__).resolve().parent.parent / "data" / "last30days-cache"
# Public catalyst evidence is required for an official paper-review candidate.
# Set XIAOMEI_SKIP_LAST30DAYS=1 only for a watchlist-only research run.
SKIP_LAST30DAYS = os.environ.get("XIAOMEI_SKIP_LAST30DAYS", "0") == "1"

RESEARCH_DIR = Path(__file__).resolve().parent.parent / "research"
FEEDBACK_JSON = RESEARCH_DIR / "backtest-review-feedback.json"


def load_previous_capital_states(symbols: list[str]) -> dict[str, dict[str, Any]]:
    """Load the last persisted inferred state without making persistence required."""
    if not symbols:
        return {}
    try:
        from sqlalchemy import text
        from db.engine import SessionLocal

        with SessionLocal() as session:
            rows = session.execute(
                text(
                    """
                    SELECT DISTINCT ON (symbol) symbol, capital_state, state_duration
                    FROM capital_state_history
                    WHERE symbol = ANY(:symbols)
                    ORDER BY symbol, as_of_date DESC, id DESC
                    """
                ),
                {"symbols": symbols},
            ).mappings()
            return {
                str(row["symbol"]): {
                    "capital_state": row["capital_state"],
                    "state_duration": row["state_duration"],
                }
                for row in rows
            }
    except Exception:
        return {}


def fetch_realtime_quote(symbol: str) -> dict[str, Any] | None:
    """Return one quote through DataProvider and preserve explicit source state."""
    quote, provider_name, metadata = get_provider().fetch_realtime_quote(symbol)
    if quote is None:
        return None
    stamp = CALENDAR.quote_session_stamp()
    return {
        **quote,
        "provider": provider_name,
        "source_status": metadata.get("provider_status", "unavailable"),
        "source_attempts": metadata.get("source_attempts", []),
        "session_date": metadata.get("session_date") or stamp["session_date"],
        "quote_session": stamp["quote_session"],
        "prev_close_session": stamp["prev_close_session"],
        "bar_type": "SNAPSHOT",
        "is_complete": False,
        "time_basis": "latest_price",
        "prev_close_time_basis": "prev_close",
    }


def load_feedback() -> dict | None:
    if not FEEDBACK_JSON.exists():
        return None
    try:
        with open(FEEDBACK_JSON) as f:
            data = json.load(f)
        if data.get("status") != "OK":
            return None
        return data
    except Exception:
        return None
BUSINESS_QUERY_SUFFIX = "orders demand backlog guidance revenue customer contract"
AMBIGUOUS_TICKERS = {"COO", "MDT", "SJM"}
LEGAL_SUFFIX_TOKENS = {
    "inc",
    "incorporated",
    "corp",
    "corporation",
    "co",
    "company",
    "plc",
    "ltd",
    "limited",
    "holdings",
    "holding",
    "group",
}
NARRATIVE_CONTEXT_TERMS = {
    "stock",
    "stocks",
    "shares",
    "earnings",
    "earnings call",
    "news",
    "catalyst",
    "quarter",
    "results",
    "beat",
    "miss",
    "guidance",
    "analyst",
    "upgrade",
    "downgrade",
    "after hours",
    "premarket",
    "rally",
    "selloff",
}
BUSINESS_CONTEXT_TERMS = {
    "orders",
    "order",
    "demand",
    "backlog",
    "guidance",
    "revenue",
    "customer",
    "contract",
    "contracts",
    "sales",
    "shipment",
    "shipments",
    "bookings",
    "pipeline",
    "margin",
    "quarter",
    "results",
}
COMPANY_FALLBACKS: dict[str, dict[str, Any]] = {
    "COO": {
        "company_name": "The Cooper Companies, Inc.",
        "keywords": ["Cooper Companies", "CooperVision", "CooperSurgical"],
    },
    "MDT": {
        "company_name": "Medtronic plc",
        "keywords": ["Medtronic", "MiniMed", "InterStim", "Symplicity", "Hugo"],
    },
    "SJM": {
        "company_name": "The J. M. Smucker Company",
        "keywords": ["Smucker", "Jif", "Folgers", "Caf\u00e9 Bustelo", "Uncrustables", "Milk-Bone", "Meow Mix"],
    },
    "MRVL": {
        "company_name": "Marvell Technology, Inc.",
        "keywords": ["Marvell", "Marvell Technology", "Teralynx", "Brightlane"],
    },
    "HPE": {
        "company_name": "Hewlett Packard Enterprise Company",
        "keywords": ["Hewlett Packard Enterprise", "GreenLake", "Aruba", "Cray", "ProLiant", "Alletra"],
    },
    "DELL": {
        "company_name": "Dell Technologies Inc.",
        "keywords": ["Dell Technologies", "Dell", "PowerEdge", "PowerStore", "Dell AI"],
    },
    "APTV": {
        "company_name": "Aptiv PLC",
        "keywords": ["Aptiv"],
    },
    "CPT": {
        "company_name": "Camden Property Trust",
        "keywords": ["Camden Property Trust", "Camden"],
    },
    "BXP": {
        "company_name": "BXP, Inc.",
        "keywords": ["BXP", "Boston Properties"],
    },
    "CNC": {
        "company_name": "Centene Corporation",
        "keywords": ["Centene"],
    },
}
METHODOLOGY_REFERENCES = [
    {
        "name": "UZI-Skill",
        "use": "risk checklist and multi-dimensional review",
    },
    {
        "name": "TradingAgents",
        "use": "role-based research synthesis",
    },
    {
        "name": "Serenity Skill",
        "use": "theme and supply-chain catalyst mapping",
    },
    {
        "name": "Buffett Skills",
        "use": "quality, margin-of-safety, bear-case framing",
    },
    {
        "name": "QuantDinger",
        "use": "replay discipline and data-health guardrails",
    },
    {
        "name": "Factor Analysis (300-day IC)",
        "use": "scoring weight optimization based on historical information coefficient",
        "formula": "score = 0.40×RS + 0.30×VWM - 0.15×accel + 0.15×mom",
        "validation": "56.9% win rate, +1.75% avg return, 1.92 profit factor",
    },
]


class BlockedDataUnavailableError(RuntimeError):
    def __init__(self, error_type: str, message: str, cached_local_fallback_attempted: bool) -> None:
        super().__init__(message)
        self.error_type = error_type
        self.cached_local_fallback_attempted = bool(cached_local_fallback_attempted)


def repo_root() -> Path:
    return project_root()


def output_root(run_name: str) -> Path:
    return repo_root() / "research" / run_name


def artifact_paths(run_name: str, output_date: str) -> dict[str, Path]:
    run_root = output_root(run_name)
    return {
        name: run_root / pattern.format(output_date=output_date)
        for name, pattern in RUN_ARTIFACT_FILENAMES.items()
    }


def bday_date(date: pd.Timestamp, horizon: int) -> str:
    return add_trading_days(pd.Timestamp(date).date(), int(horizon)).isoformat()


def percentile_rank(series: pd.Series) -> pd.Series:
    if series.dropna().empty:
        return pd.Series(index=series.index, dtype=float)
    return series.rank(pct=True)


def slugify(value: str) -> str:
    return "".join(ch.lower() if ch.isalnum() else "-" for ch in value).strip("-")


def normalize_match_text(value: str) -> str:
    return " ".join(re.sub(r"[^a-z0-9]+", " ", (value or "").lower()).split())


def phrase_in_text(phrase: str, text: str) -> bool:
    normalized_phrase = normalize_match_text(phrase)
    if not normalized_phrase:
        return False
    return normalized_phrase in normalize_match_text(text)


def strip_legal_suffix(name: str) -> str:
    tokens = normalize_match_text(name).split()
    while tokens and tokens[-1] in LEGAL_SUFFIX_TOKENS:
        tokens.pop()
    if tokens and tokens[0] == "the" and len(tokens) > 1:
        tokens = tokens[1:]
    return " ".join(tokens)


def company_query_name(name: str) -> str:
    stripped = strip_legal_suffix(name)
    return stripped or normalize_match_text(name) or name.strip()


def parse_last30days_json(raw_output: str) -> dict[str, Any]:
    start = raw_output.find("{")
    if start == -1:
        raise RuntimeError("last30days output did not contain JSON")
    payload, _ = json.JSONDecoder().raw_decode(raw_output[start:])
    return payload


def _last30days_cache_key(topic: str) -> Path:
    import hashlib
    today = datetime.now().astimezone().strftime("%Y-%m-%d")
    h = hashlib.md5(f"{today}:{topic}".encode()).hexdigest()[:12]
    LAST30DAYS_CACHE_DIR.mkdir(parents=True, exist_ok=True)
    return LAST30DAYS_CACHE_DIR / f"{h}.json"


def _load_last30days_cache(topic: str) -> dict[str, Any] | None:
    cache_path = _last30days_cache_key(topic)
    if not cache_path.exists():
        return None
    try:
        return json.loads(cache_path.read_text())
    except Exception:
        return None


def _save_last30days_cache(topic: str, result: dict[str, Any]) -> None:
    try:
        cache_path = _last30days_cache_key(topic)
        cache_path.write_text(json.dumps(result, ensure_ascii=False))
    except Exception:
        pass


def run_last30days_topic(topic: str) -> dict[str, Any]:
    if SKIP_LAST30DAYS:
        return {
            "topic": topic,
            "returncode": 0,
            "stdout": "",
            "stderr": "SKIP_LAST30DAYS=1",
            "payload": {
                "items_by_source": {},
                "ranked_candidates": [],
                "clusters": [],
                "artifacts": {"resolved": {"entity": topic}},
                "range_from": None,
                "range_to": None,
            },
        }

    cached = _load_last30days_cache(topic)
    if cached is not None:
        return cached

    if not LAST30DAYS_SCRIPT.exists():
        raise RuntimeError(f"missing last30days script: {LAST30DAYS_SCRIPT}")
    if not LAST30DAYS_PYTHON.exists():
        raise RuntimeError(f"missing python 3.12 runtime: {LAST30DAYS_PYTHON}")

    cmd = [
        str(LAST30DAYS_PYTHON),
        str(LAST30DAYS_SCRIPT),
        topic,
        "--quick",
        "--days",
        "30",
        "--emit",
        "json",
    ]

    try:
        proc = subprocess.run(
            cmd,
            check=False,
            capture_output=True,
            text=True,
            env=os.environ.copy(),
            timeout=LAST30DAYS_TIMEOUT_SECONDS,
        )
        combined_output = proc.stdout if "{" in proc.stdout else proc.stderr if "{" in proc.stderr else proc.stdout + proc.stderr
        payload = parse_last30days_json(combined_output)

        if not payload.get("ranked_candidates"):
            payload = _fetch_yahoo_rss_fallback(topic, payload)

        result = {
            "topic": topic,
            "returncode": int(proc.returncode),
            "stdout": proc.stdout,
            "stderr": proc.stderr,
            "payload": payload,
        }
        _save_last30days_cache(topic, result)
        return result
    except subprocess.TimeoutExpired as exc:
        stdout = exc.stdout.decode("utf-8", errors="replace") if isinstance(exc.stdout, (bytes, bytearray)) else (exc.stdout or "")
        stderr = exc.stderr.decode("utf-8", errors="replace") if isinstance(exc.stderr, (bytes, bytearray)) else (exc.stderr or "")
        payload = {
            "items_by_source": {},
            "ranked_candidates": [],
            "clusters": [],
            "artifacts": {"resolved": {"entity": topic}},
            "range_from": None,
            "range_to": None,
        }
        payload = _fetch_yahoo_rss_fallback(topic, payload)
        result = {
            "topic": topic,
            "returncode": 124,
            "stdout": stdout,
            "stderr": stderr + "\nTIMEOUT",
            "payload": payload,
        }
        _save_last30days_cache(topic, result)
        return result
    except Exception as exc:  # noqa: BLE001
        payload = {
            "items_by_source": {},
            "ranked_candidates": [],
            "clusters": [],
            "artifacts": {"resolved": {"entity": topic}},
            "range_from": None,
            "range_to": None,
            "_error": str(exc),
        }
        payload = _fetch_yahoo_rss_fallback(topic, payload)
        result = {
            "topic": topic,
            "returncode": 1,
            "stdout": "",
            "stderr": str(exc),
            "payload": payload,
        }
        _save_last30days_cache(topic, result)
        return result


def _fetch_yahoo_rss_fallback(topic: str, payload: dict[str, Any]) -> dict[str, Any]:
    import urllib.request
    import xml.etree.ElementTree as ET

    words = topic.split()
    ticker = words[0].upper() if words else ""
    if not ticker or not ticker.isalpha() or len(ticker) > 5:
        ticker = None

    # Try Yahoo Finance RSS first
    if ticker:
        url = f"https://feeds.finance.yahoo.com/rss/2.0/headline?s={ticker}&region=US&lang=en-US"
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=10) as resp:
                xml_data = resp.read().decode()
                root = ET.fromstring(xml_data)
                items = root.findall(".//item")

                ranked = []
                for item in items[:10]:
                    title = item.find("title").text if item.find("title") is not None else ""
                    desc = item.find("description").text if item.find("description") is not None else ""
                    if title:
                        ranked.append({
                            "title": title,
                            "snippet": desc,
                            "source": "yahoo_finance_rss",
                            "url": "",
                            "score": None,
                            "source_quality": 0.4,
                            "primary_source": False,
                            "discovery_only": True,
                        })

                if ranked:
                    payload["ranked_candidates"] = ranked
                    payload["items_by_source"]["yahoo_finance_rss"] = ranked
                    return payload
        except Exception:
            pass

    # Fallback to Google News RSS
    query = urllib.request.quote(topic)
    url = f"https://news.google.com/rss/search?q={query}&hl=en-US&gl=US&ceid=US:en"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            xml_data = resp.read().decode()
            root = ET.fromstring(xml_data)
            items = root.findall(".//item")

            ranked = []
            for item in items[:10]:
                title = item.find("title").text if item.find("title") is not None else ""
                desc = item.find("description").text if item.find("description") is not None else ""
                link = item.find("link").text if item.find("link") is not None else ""
                if title:
                    ranked.append({
                        "title": title,
                        "snippet": desc,
                        "source": "google_news_rss",
                        "url": link,
                        "score": None,
                        "source_quality": 0.35,
                        "primary_source": False,
                        "discovery_only": True,
                    })

            if ranked:
                payload["ranked_candidates"] = ranked
                payload["items_by_source"]["google_news_rss"] = ranked
    except Exception:
        pass

    return payload


def summarize_last30days_result(
    result: dict[str, Any],
    company_profile: dict[str, Any],
    focus: str,
) -> dict[str, Any]:
    payload = result["payload"]
    items_by_source = payload.get("items_by_source", {}) or {}
    ranked = payload.get("ranked_candidates", []) or []
    clusters = payload.get("clusters", []) or []

    source_counts = {str(source): int(len(items or [])) for source, items in items_by_source.items()}
    nonzero_sources = [source for source, count in source_counts.items() if count > 0]
    scored_items = []
    for item in ranked:
        scored = score_evidence_item(item, company_profile, focus)
        scored_items.append(
            {
                "title": scored["title"],
                "source": item.get("source"),
                "url": item.get("url"),
                "snippet": scored["snippet"],
                "published_at": item.get("published_at"),
                "final_score": item.get("final_score"),
                "freshness": item.get("freshness"),
                "sources": item.get("sources", []),
                "subquery_labels": item.get("subquery_labels", []),
                "relevance_type": scored["relevance_type"],
                "relevance_score": scored["relevance_score"],
                "relevance_reason": scored["relevance_reason"],
                "matched_term": scored["matched_term"],
                "source_quality": item.get("source_quality"),
                "freshness": item.get("freshness"),
                "primary_source": bool(item.get("primary_source")),
                "discovery_only": bool(item.get("discovery_only")),
            }
        )
    top_items = scored_items[:3]
    relevant_items = [item for item in scored_items if item["relevance_type"] == "relevant"]
    source_diversity = int(len(nonzero_sources))
    primary_source = any(bool(item.get("primary_source")) for item in relevant_items)
    raw_top_score = None if not ranked else float(ranked[0].get("final_score") or 0.0)
    freshness_values = [float(item.get("freshness")) for item in ranked if item.get("freshness") is not None]
    if relevant_items:
        top_relevant_item = sorted(
            relevant_items,
            key=lambda item: (
                float(item.get("relevance_score") or 0.0),
                float(item.get("final_score") or 0.0),
                float(item.get("freshness") or 0.0),
            ),
            reverse=True,
        )[0]
        evidence_status = "found_relevant"
        evidence_title = top_relevant_item["title"]
        evidence_reason = top_relevant_item["relevance_reason"]
        relevance_score = float(top_relevant_item.get("relevance_score") or 0.0)
        matched_term = top_relevant_item.get("matched_term")
    elif scored_items:
        top_unrelated_item = scored_items[0]
        evidence_status = "found_unrelated"
        evidence_title = top_unrelated_item["title"]
        evidence_reason = top_unrelated_item["relevance_reason"]
        relevance_score = float(top_unrelated_item.get("relevance_score") or 0.0)
        matched_term = top_unrelated_item.get("matched_term")
    else:
        evidence_status = "missing"
        evidence_title = None
        evidence_reason = "no ranked candidates returned"
        relevance_score = 0.0
        matched_term = None

    return {
        "topic": result["topic"],
        "status": evidence_status,
        "source_counts": source_counts,
        "source_diversity": source_diversity,
        "cluster_count": int(len(clusters)),
        "ranked_candidate_count": int(len(ranked)),
        "top_score": raw_top_score,
        "relevance_score": relevance_score,
        "source_quality": None if not relevant_items else relevant_items[0].get("source_quality"),
        "freshness_max": None if not freshness_values else float(max(freshness_values)),
        "primary_source": primary_source,
        "corroboration": max(0, source_diversity - 1),
        "rss_fallback": any(str(item.get("source") or "").endswith("_rss") for item in scored_items),
        "evidence_strength": None if not relevant_items else round(
            float(relevance_score)
            * (0.5 + 0.25 * (1 if primary_source else 0) + 0.25 * min(1.0, source_diversity / 3.0)),
            4,
        ),
        "top_items": top_items,
        "top_evidence_title": evidence_title,
        "top_evidence_reason": evidence_reason,
        "top_evidence_matched_term": matched_term,
        "resolved_entity": payload.get("artifacts", {}).get("resolved", {}).get("entity"),
        "range_from": payload.get("range_from"),
        "range_to": payload.get("range_to"),
        "returncode": int(result["returncode"]),
        "focus": focus,
    }


def load_cached_universe_symbols() -> dict[str, Any]:
    cache_candidates: list[Path] = []
    for run_name in [DEFAULT_RUN_NAME, "universe-expansion-replay"]:
        run_root = output_root(run_name)
        if run_root.exists():
            cache_candidates.extend(sorted(run_root.glob("metrics-*.json"), reverse=True))
    cache_candidates.extend(
        sorted((repo_root() / "research" / "universe-expansion-replay").glob("metrics-*.json"), reverse=True)
    )
    for cache_path in cache_candidates:
        if not cache_path.exists():
            continue
        try:
            payload = json.loads(cache_path.read_text())
        except Exception:
            continue
        symbols = payload.get("selected_universe") or []
        if symbols:
            return {
                "symbols": [str(symbol).strip().upper() for symbol in symbols if str(symbol).strip()],
                "cache_path": cache_path,
            }
    return {}


def _build_realtime_intraday_fallback(
    symbols: list[str],
    sleep_seconds: float,
) -> dict[str, Any] | None:
    """Intraday display fallback. Never enters daily factors, ranking, or replay.

    choose_universe does not call this. The payload is tagged INTRADAY_PARTIAL
    with is_complete=False so daily_bar_gate rejects it.
    """
    symbol_frames: dict[str, pd.DataFrame] = {}
    for i, ticker in enumerate(symbols):
        normalized = normalize_us_symbol(ticker)
        try:
            quote = fetch_realtime_quote(normalized)
            time.sleep(sleep_seconds)
            intraday = fetch_intraday_data(normalized)
            time.sleep(sleep_seconds)
        except Exception:
            continue

        if not intraday:
            continue

        prices = [bar["price"] for bar in intraday if bar.get("price") is not None]
        volumes = [bar["volume"] for bar in intraday if bar.get("volume") is not None]
        if not prices:
            continue

        open_price = prices[0]
        close_price = prices[-1]
        high_price = max(prices)
        low_price = min(prices)
        total_volume = sum(volumes) if volumes else 0.0

        today = pd.Timestamp.now().normalize()
        df = pd.DataFrame(
            {
                "Open": [open_price],
                "High": [high_price],
                "Low": [low_price],
                "Close": [close_price],
                "Adj Close": [close_price],
                "Volume": [total_volume],
                "Dividends": [0.0],
                "Stock Splits": [0.0],
                "symbol": [normalized],
                "date": [today],
                "bar_type": ["INTRADAY_PARTIAL"],
                "is_complete": [False],
                "session_status": ["INTRADAY"],
                "market_open": [True],
                "market_closed": [False],
                "coverage_start": [intraday[0].get("time") if isinstance(intraday[0], dict) else None],
                "coverage_end": [intraday[-1].get("time") if isinstance(intraday[-1], dict) else None],
            },
            index=pd.DatetimeIndex([today], name="date"),
        )
        symbol_frames[normalized] = df

    if len(symbol_frames) < 2:
        return None

    close_frames = []
    adj_frames = []
    long_frames = []
    for symbol, frame in symbol_frames.items():
        close_frames.append(frame["Close"].rename(symbol))
        adj_frames.append(frame["Adj Close"].rename(symbol))
        long_frames.append(frame.reset_index(drop=True))

    close_panel = pd.concat(close_frames, axis=1).sort_index().astype(float)
    adj_panel = pd.concat(adj_frames, axis=1).sort_index().astype(float)
    long_panel = pd.concat(long_frames, ignore_index=True).sort_values(["date", "symbol"]).reset_index(drop=True)
    long_panel["date"] = pd.to_datetime(long_panel["date"]).dt.strftime("%Y-%m-%d")

    quality = {}
    included_symbols = []
    excluded_symbols = {}
    for symbol in symbols:
        normalized = normalize_us_symbol(symbol)
        if normalized in symbol_frames:
            quality[normalized] = {"include": True, "reasons": [], "history_days": 1,
                                   "last_close": float(symbol_frames[normalized]["Close"].iloc[0]),
                                   "median_dollar_volume": float(symbol_frames[normalized]["Volume"].iloc[0]),
                                   "adj_close_available": True}
            included_symbols.append(normalized)
        else:
            quality[normalized] = {"include": False, "reasons": ["intraday_unavailable"],
                                   "history_days": 0, "last_close": None,
                                   "median_dollar_volume": None, "adj_close_available": False}
            excluded_symbols[normalized] = quality[normalized]

    return {
        "results": {s: type("R", (), {"rows": 1, "adj_close_available": True, "frame": symbol_frames[s], "error": None, "symbol": s, "period": "realtime"})() for s in symbol_frames},
        "failures": [],
        "quality": quality,
        "included_symbols": included_symbols,
        "excluded_symbols": excluded_symbols,
        "close_panel": close_panel,
        "adj_panel": adj_panel,
        "long_panel": long_panel,
        "period_used": "realtime_intraday",
        "bar_type": "INTRADAY_PARTIAL",
        "is_complete": False,
        "usable_for_daily_factors": False,
        "usable_for_daily_ranking": False,
        "usable_for_historical_daily_replay": False,
        "display_enrichment_only": True,
    }


def choose_universe(
    universe_source_name: str,
    explicit_universe: list[str] | None,
    universe_key: str | None,
    periods: list[str],
    sleep_seconds: float,
    batch_size: int,
    min_history_days: int,
    min_price: float,
    min_median_dollar_volume: float,
) -> dict[str, Any]:
    cached_local_fallback_attempted = False
    try:
        source_config = load_universe_source(universe_source_name, explicit_universe=explicit_universe)
        source_mode = "live"
    except Exception:
        cached_local_fallback_attempted = True
        cached_universe = load_cached_universe_symbols()
        if not cached_universe:
            raise BlockedDataUnavailableError(
                "UNIVERSE_SOURCE_UNAVAILABLE",
                "unable to load live universe source and no cached fallback universe was available",
                cached_local_fallback_attempted,
            )
        source_mode = "cached_local"
        source_config = {
            "source_name": universe_source_name,
            "source_url": {"cache": str(cached_universe["cache_path"])},
            "universes": {
                "union": {
                    "symbols": cached_universe["symbols"],
                    "raw_count": len(cached_universe["symbols"]),
                    "source": "cached_selected_universe",
                }
            },
        }
    universes = source_config["universes"]
    selected_universe_key = universe_key or ("union" if "union" in universes else next(iter(universes)))
    if selected_universe_key not in universes and len(universes) == 1:
        selected_universe_key = next(iter(universes))
    if selected_universe_key not in universes:
        raise ValueError(f"unknown universe key: {selected_universe_key}")

    selected_universe_info = universes[selected_universe_key]
    selected_universe = list(selected_universe_info["symbols"])
    minimum_symbols = min(len(selected_universe), max(20, int(np.ceil(len(selected_universe) * 0.7)))) if selected_universe else 0

    attempts: list[dict[str, Any]] = []
    chosen_results: dict[str, Any] | None = None
    chosen_failures: list[dict[str, str]] = []
    chosen_quality: dict[str, Any] | None = None
    chosen_included_symbols: list[str] | None = None
    chosen_excluded_symbols: dict[str, Any] | None = None
    chosen_close_panel: pd.DataFrame | None = None
    chosen_adj_panel: pd.DataFrame | None = None
    chosen_long_panel: pd.DataFrame | None = None
    chosen_period: str | None = None

    for period in periods:
        results, failures = fetch_universe(
            period=period,
            universe=selected_universe,
            sleep_seconds=sleep_seconds,
            batch_size=batch_size,
        )

        quality = {
            symbol: _evaluate_symbol_quality(result, min_history_days, min_price, min_median_dollar_volume)
            for symbol, result in results.items()
        }
        included_symbols = [symbol for symbol in selected_universe if quality.get(symbol, {}).get("include")]
        excluded_symbols = {symbol: quality[symbol] for symbol in selected_universe if symbol not in included_symbols}
        filtered_results = {symbol: results[symbol] for symbol in included_symbols}

        anomaly_symbols = _detect_volume_anomalies(filtered_results)
        for sym in anomaly_symbols:
            if sym not in included_symbols and quality.get(sym, {}).get("include"):
                included_symbols.append(sym)
                filtered_results[sym] = results[sym]

        close_panel, adj_panel, long_panel = build_close_panel(filtered_results)
        close_panel = close_panel.sort_index().astype(float)
        adj_panel = adj_panel.reindex(close_panel.index).sort_index().astype(float)
        if not long_panel.empty and "date" in long_panel.columns:
            long_panel = long_panel[long_panel["date"].isin(close_panel.index.strftime("%Y-%m-%d"))].copy()

        source_counts: Counter = Counter()
        for symbol, result in results.items():
            source_counts[result.source] += 1
        dominant_kline_source = source_counts.most_common(1)[0][0] if source_counts else EASTMONEY_HISTORICAL_SOURCE_DISPLAY

        attempts.append(
            {
                "period": period,
                "raw_rows_per_symbol": {symbol: int(result.rows) for symbol, result in results.items()},
                "source_per_symbol": {symbol: result.source for symbol, result in results.items()},
                "kline_source_breakdown": dict(source_counts),
                "dominant_kline_source": dominant_kline_source,
                "quality_included_count": int(len(included_symbols)),
                "quality_excluded_count": int(len(excluded_symbols)),
                "quality_coverage_ratio": None
                if not selected_universe
                else float(len(included_symbols) / len(selected_universe)),
                "panel_rows": int(len(close_panel)),
                "failures": failures,
            }
        )

        if len(included_symbols) < minimum_symbols or close_panel.empty:
            chosen_failures = failures
            continue

        chosen_results = filtered_results
        chosen_failures = failures
        chosen_quality = quality
        chosen_included_symbols = included_symbols
        chosen_excluded_symbols = excluded_symbols
        chosen_close_panel = close_panel
        chosen_adj_panel = adj_panel
        chosen_long_panel = long_panel
        chosen_period = period
        break

    data_mode = "historical_kline"
    if (
        chosen_results is None
        or chosen_quality is None
        or chosen_included_symbols is None
        or chosen_excluded_symbols is None
        or chosen_close_panel is None
        or chosen_adj_panel is None
        or chosen_long_panel is None
        or chosen_period is None
    ):
        raise BlockedDataUnavailableError(
            "MARKET_DATA_PANEL_UNAVAILABLE",
            "unable to fetch usable Yahoo historical kline panel; attempts="
            + json.dumps(serializable(attempts), ensure_ascii=False),
            cached_local_fallback_attempted,
        )

    chosen_kline_source = EASTMONEY_HISTORICAL_SOURCE_DISPLAY
    if chosen_results:
        source_counter: Counter = Counter()
        for symbol, result in chosen_results.items():
            source_counter[result.source] += 1
        if source_counter:
            chosen_kline_source = source_counter.most_common(1)[0][0]

    return {
        "source_config": source_config,
        "selected_universe_key": selected_universe_key,
        "source_mode": source_mode,
        "cached_local_fallback_attempted": bool(cached_local_fallback_attempted),
        "selected_universe": selected_universe,
        "attempts": attempts,
        "failures": chosen_failures,
        "quality": chosen_quality,
        "included_symbols": chosen_included_symbols,
        "excluded_symbols": chosen_excluded_symbols,
        "close_panel": chosen_close_panel,
        "adj_panel": chosen_adj_panel,
        "long_panel": chosen_long_panel,
        "period_used": chosen_period,
        "minimum_required_symbols": int(minimum_symbols),
        "data_mode": data_mode,
        "kline_source": chosen_kline_source,
        "bar_type": "DAILY_COMPLETE",
        "is_complete": True,
        "usable_for_daily_factors": True,
    }


def _evaluate_symbol_quality(
    result: Any,
    min_history_days: int,
    min_price: float,
    min_median_dollar_volume: float,
) -> dict[str, Any]:
    frame = result.frame
    if frame is None or frame.empty:
        return {
            "include": False,
            "reasons": ["empty_frame"],
            "history_days": 0,
            "last_close": None,
            "median_dollar_volume": None,
        }

    frame = frame.sort_index()
    close = pd.to_numeric(frame["Close"], errors="coerce")
    volume = pd.to_numeric(frame["Volume"], errors="coerce")
    dollar_volume = close * volume
    last_close = None if close.dropna().empty else float(close.dropna().iloc[-1])
    median_dollar_volume = None if dollar_volume.dropna().empty else float(dollar_volume.dropna().median())

    reasons = []
    if result.rows < min_history_days:
        reasons.append(f"history_days<{min_history_days}")
    if not result.adj_close_available:
        reasons.append("adj_close_missing")
    if last_close is None or last_close < min_price:
        reasons.append(f"price_floor<{min_price}")
    if median_dollar_volume is None or median_dollar_volume < min_median_dollar_volume:
        reasons.append(f"median_dollar_volume<{min_median_dollar_volume}")

    return {
        "include": not reasons,
        "reasons": reasons,
        "history_days": int(result.rows),
        "last_close": last_close,
        "median_dollar_volume": median_dollar_volume,
        "adj_close_available": bool(result.adj_close_available),
    }


def _enrich_panels_with_realtime(
    close_panel: pd.DataFrame,
    adj_panel: pd.DataFrame,
    long_panel: pd.DataFrame,
    symbols: list[str],
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Display-only realtime overlay. Never mutates canonical daily bars."""
    return close_panel, adj_panel, long_panel


def display_enrichment_only(
    close_panel: pd.DataFrame,
    adj_panel: pd.DataFrame,
    long_panel: pd.DataFrame,
    symbols: list[str],
) -> dict[str, Any]:
    """Realtime quotes for display / cross-check. Not a daily bar."""
    quotes = {}
    for sym in symbols:
        try:
            q = fetch_realtime_quote(sym)
            if q and q.get("latest_price"):
                quotes[sym] = {
                    "latest_price": float(q["latest_price"]),
                    "bar_type": "SNAPSHOT",
                    "is_complete": False,
                    "usable_for_daily_factors": False,
                }
        except Exception:
            pass
    return {
        "display_enrichment_only": True,
        "quotes": quotes,
        "canonical_close_panel_unchanged": True,
        "close_panel": close_panel,
        "adj_panel": adj_panel,
        "long_panel": long_panel,
    }


def _detect_volume_anomalies(results: dict, volume_threshold: float = 2.0) -> list[str]:
    """Detect symbols with volume spike (>threshold x 20d median) in recent kline."""
    anomalies = []
    for sym, result in results.items():
        try:
            frame = result.frame
            if frame is None or frame.empty or len(frame) < 20:
                continue
            volume = pd.to_numeric(frame["Volume"], errors="coerce").dropna()
            if len(volume) < 20:
                continue
            recent_vol = float(volume.iloc[-1])
            median_20d = float(volume.iloc[-20:].median())
            if median_20d > 0 and recent_vol > median_20d * volume_threshold:
                anomalies.append(sym)
        except Exception:
            pass
    return anomalies


def build_structured_scores(
    feature_frame: pd.DataFrame,
) -> pd.Series:
    """Score observable large-participant footprint proxies only.

    This is not a claim about verified institutional ownership or order flow.
    A missing public observation stays unavailable and reduces confidence rather
    than receiving a neutral value.
    """
    scores = pd.DataFrame(index=feature_frame.index)

    volume_trend = feature_frame["volume_trend_20d"]
    momentum = feature_frame["prior_20d_momentum"]
    scores["relative_volume_expansion"] = percentile_rank(volume_trend)
    scores["volume_price_alignment"] = np.select(
        [
            volume_trend.notna() & momentum.notna() & (volume_trend > 1.0) & (momentum > 0),
            volume_trend.notna() & momentum.notna() & ((volume_trend > 1.0) | (momentum > 0)),
            volume_trend.notna() & momentum.notna(),
        ],
        [1.0, 0.5, 0.0],
        default=np.nan,
    )
    scores["close_strength"] = feature_frame["closing_strength_5d"].clip(0, 1)
    breakout_score = feature_frame.get(
        "breakout_score",
        pd.Series(np.nan, index=feature_frame.index, dtype=float),
    )
    scores["breakout_acceptance"] = breakout_score.clip(0, 1)
    scores["liquidity_quality"] = percentile_rank(feature_frame["median_dollar_volume_20d"])
    scores["relative_strength"] = percentile_rank(feature_frame["relative_strength_vs_equal_weight"])

    feature_frame["footprint_factor_coverage"] = scores.notna().mean(axis=1)
    feature_frame["footprint_factor_contributions"] = scores.to_dict(orient="index")
    return scores.mean(axis=1, skipna=True) * feature_frame["footprint_factor_coverage"]


def build_market_snapshot(
    close_panel: pd.DataFrame,
    adj_panel: pd.DataFrame,
    long_panel: pd.DataFrame,
    selected_universe: list[str],
    feedback: dict | None = None,
    kline_source: str | None = None,
    previous_capital_states: dict[str, dict[str, Any]] | None = None,
) -> dict[str, Any]:
    if close_panel.empty or adj_panel.empty:
        raise RuntimeError("empty price panel")

    price_basis = adj_panel.copy()
    price_basis = price_basis.where(price_basis.notna(), close_panel)
    price_basis = price_basis.sort_index().astype(float)
    close_panel = close_panel.sort_index().astype(float)
    volume_panel = (
        long_panel.assign(date=pd.to_datetime(long_panel["date"]))
        .pivot(index="date", columns="symbol", values="Volume")
        .reindex(price_basis.index)
        .sort_index()
        .astype(float)
    )

    as_of_date = price_basis.index[-1]
    prior_5d = price_basis / price_basis.shift(5) - 1.0
    prior_20d = price_basis / price_basis.shift(20) - 1.0
    five_day_acceleration = prior_5d - prior_20d
    dollar_volume = close_panel * volume_panel
    avg_dollar_volume_5d = dollar_volume.rolling(5, min_periods=5).mean()
    median_dollar_volume_20d = dollar_volume.rolling(20, min_periods=20).median()
    volume_confirmation = avg_dollar_volume_5d / median_dollar_volume_20d - 1.0
    equal_weight_20d_benchmark = float(prior_20d.loc[as_of_date].dropna().mean())
    relative_strength = prior_20d.loc[as_of_date] - equal_weight_20d_benchmark

    daily_high = long_panel.assign(date=pd.to_datetime(long_panel["date"])).pivot(
        index="date", columns="symbol", values="High"
    ).reindex(price_basis.index).sort_index().astype(float)
    daily_low = long_panel.assign(date=pd.to_datetime(long_panel["date"])).pivot(
        index="date", columns="symbol", values="Low"
    ).reindex(price_basis.index).sort_index().astype(float)
    daily_range = daily_high - daily_low
    closing_strength = (close_panel - daily_low) / daily_range.replace(0, np.nan)
    closing_strength_5d = closing_strength.rolling(5, min_periods=5).mean()
    prior_5d_volume = volume_panel.rolling(5, min_periods=5).mean()
    prior_20d_volume = volume_panel.rolling(20, min_periods=20).mean()
    volume_trend = prior_5d_volume / prior_20d_volume.replace(0, np.nan)
    volume_weighted_momentum = prior_20d * volume_trend

    feature_frame = pd.DataFrame(
        {
            "symbol": selected_universe,
            "close": close_panel.loc[as_of_date].reindex(selected_universe).values,
            "adj_close": price_basis.loc[as_of_date].reindex(selected_universe).values,
            "volume": volume_panel.loc[as_of_date].reindex(selected_universe).values,
            "prior_5d_momentum": prior_5d.loc[as_of_date].reindex(selected_universe).values,
            "prior_20d_momentum": prior_20d.loc[as_of_date].reindex(selected_universe).values,
            "five_day_acceleration": five_day_acceleration.loc[as_of_date].reindex(selected_universe).values,
            "relative_strength_vs_equal_weight": relative_strength.reindex(selected_universe).values,
            "volume_confirmation_ratio": volume_confirmation.loc[as_of_date].reindex(selected_universe).values,
            "median_dollar_volume_20d": median_dollar_volume_20d.loc[as_of_date].reindex(selected_universe).values,
            "closing_strength_5d": closing_strength_5d.loc[as_of_date].reindex(selected_universe).values,
            "volume_weighted_momentum": volume_weighted_momentum.loc[as_of_date].reindex(selected_universe).values,
            "volume_trend_20d": volume_trend.loc[as_of_date].reindex(selected_universe).values,
        }
    ).set_index("symbol")

    percentile_features = {
        "prior_20d_momentum": percentile_rank(feature_frame["prior_20d_momentum"]),
        "five_day_acceleration": percentile_rank(feature_frame["five_day_acceleration"]),
        "volume_confirmation_ratio": percentile_rank(feature_frame["volume_confirmation_ratio"]),
        "relative_strength_vs_equal_weight": percentile_rank(feature_frame["relative_strength_vs_equal_weight"]),
        "closing_strength_5d": percentile_rank(feature_frame["closing_strength_5d"]),
        "volume_weighted_momentum": percentile_rank(feature_frame["volume_weighted_momentum"]),
    }
    regime = classify_market_regime(close_panel, selected_universe)
    regime_thresholds = get_regime_thresholds(regime.name)
    sw = regime_thresholds.scoring_weights
    try:
        from weight_optimizer import load_weights, load_horizon_weights
        optimized = load_weights()
        sw = {**sw, **optimized}
        # Load horizon-specific weights for multi-horizon scoring
        horizon_weights = {
            h: load_horizon_weights(h) for h in [1, 3, 10]
        }
    except Exception:
        horizon_weights = {}

    sector_keywords = {
        "Technology": ["tech", "software", "semiconductor", "chip", "cloud", "cyber", "saas", "data", "digital", "ai", "network", "apple", "microsoft", "google", "meta", "nvidia", "amd", "intel", "cisco", "oracle", "salesforce", "adobe", "vmware", "paypal", "shopify", "zoom", "slack", "snowflake", "crowdstrike", "palo alto", "fortinet", "marvell", "broadcom", "qualcomm", "texas instruments", "micron", "applied materials", "lam research", "kla corp", "entegris", "on semiconductor", "analog devices", "xilinx", "altera"],
        "Healthcare": ["pharma", "bio", "medical", "health", "drug", "clinical", "diagnostic", "therapeutic", "unitedhealth", "cigna", "anthem", "aetna", "humana", "moderna", "pfizer", "johnson", "merck", "abbvie", "amgen", "gilead", "regeneron", "biogen", "vertex", "alnylam", "iqvia", "medtronic", "baxter", "becton", "abbott", "zimmer", "stryker", "medtronic", "edwards", "intuitive surgical"],
        "Financial": ["bank", "capital", "insurance", "financial", "securities", "investment", "credit", "jpmorgan", "goldman", "morgan stanley", "bank of america", "wells fargo", "citigroup", "visa", "mastercard", "american express", "blackrock", "schwab", "fidelity", "t rowe", "progressive", "allstate", "travelers", "chubb", "aon", "marsh"],
        "Consumer Cyclical": ["retail", "consumer", "ecommerce", "travel", "leisure", "restaurant", "hotel", "airline", "amazon", "tesla", "home depot", "lowes", "costco", "walmart", "target", "nordstrom", "macy", "kohls", "best buy", "starbucks", "mcdonald", "chipotle", "yum brands", "marriott", "hilton", "delta", "united airlines", "american airlines", "southwest", "expedia", "booking", "airbnb"],
        "Industrials": ["industrial", "manufacturing", "aerospace", "defense", "engineering", "construction", "transport", "caterpillar", "deere", "honeywell", "3m", "ge aerospace", "boeing", "lockheed", "raytheon", "northrop", "l3harris", "union pacific", "csx", "norfolk southern", "fedex", "ups", "uber", "lyft", "parker hannifin", "emerson", "rockwell", "eaton", "dover", "illinois tool", "fastenal", "waste management", "republic services"],
        "Energy": ["energy", "oil", "gas", "solar", "renewable", "battery", "nuclear", "exxon", "chevron", "conocophillips", "schlumberger", "halliburton", "nextera", "enphase", "first solar", "sunrun", "plug power", "bloom energy"],
        "Communication": ["media", "entertainment", "streaming", "telecom", "advertising", "content", "netflix", "disney", "comcast", "charter", "t-mobile", "verizon", "at&t", "alphabet", "meta platforms", "snap", "pinterest", "roku", "activision", "electronic arts", "take-two"],
        "Consumer Defensive": ["food", "beverage", "household", "staples", "personal care", "pepsico", "coca cola", "procter", "kimberly clark", "colgate", "general mills", "kellogg", "campbell soup", "smucker", "hormel", "tyson", "kraft heinz", "mondelez"],
        "Utilities": ["electric", "utility", "water", "gas utility", "dominion", "southern company", "duke energy", "nextera energy", "american electric", "xcel energy", "wec energy", "consolidated edison"],
        "Real Estate": ["reit", "property", "real estate", "trust", "prologis", "american tower", "crown castle", "equinix", "digital realty", "welltower", "public storage", "pei properties", "boston properties"],
        "Materials": ["mining", "chemical", "steel", "lithium", "material", "freeport mcmoran", "newmont", "nucor", "dow", "dupont", "linde", "air products", "eaton vance"],
    }
    sector_map = {}
    for sym in selected_universe:
        name_lower = sym.lower()
        assigned = "Unknown"
        for sector, keywords in sector_keywords.items():
            if any(kw in name_lower for kw in keywords):
                assigned = sector
                break
        if assigned == "Unknown":
            assigned = "Technology" if sym in {"AAPL","MSFT","GOOGL","GOOG","AMZN","META","NVDA","TSLA","AVGO","CSCO","ORCL","CRM","ADBE","INTC","AMD","QCOM","TXN","INTU","NOW","AMAT","LRCX","KLAC","ADI","MRVL","SNPS","CDNS","FTNT","PANW","CRWD","ZS","DDOG","NET","SNOW","COIN","SHOP","SQ","PYPL","ROKU","UBER","LYFT","ABNB","NFLX","DIS","CHTR","TMUS","VZ","T","CMCSA"} else "Unknown"
        sector_map[sym] = assigned

    structured_scores = build_structured_scores(feature_frame)
    feature_frame["structured_score"] = structured_scores

    intraday_data = {}
    for sym in selected_universe:
        try:
            q = fetch_realtime_quote(sym)
            if q and q.get("latest_price") and q.get("prev_close"):
                price = float(q["latest_price"])
                prev = float(q["prev_close"])
                high = float(q.get("high") or price)
                low = float(q.get("low") or price)
                intraday_pct = (price / prev - 1.0) if prev else 0.0
                day_range = (high - low) / low if low else 0.0
                close_pos = (price - low) / (high - low) if high != low else 0.5
                intraday_data[sym] = {
                    "intraday_momentum": intraday_pct,
                    "close_position": close_pos,
                    "day_range": day_range,
                }
        except Exception:
            pass

    feature_frame["intraday_momentum"] = feature_frame.index.map(
        lambda s: intraday_data.get(s, {}).get("intraday_momentum", np.nan)
    )
    feature_frame["close_position"] = feature_frame.index.map(
        lambda s: intraday_data.get(s, {}).get("close_position", np.nan)
    )

    accel_neg = feature_frame["five_day_acceleration"] < 0
    intraday_up = feature_frame["intraday_momentum"] > 0.005
    feature_frame["reversal_signal"] = (accel_neg & intraday_up).astype(float)

    daily_returns = close_panel.pct_change()
    rsi_14 = daily_returns.rolling(14, min_periods=14).apply(
        lambda x: 100.0 - 100.0 / (1.0 + x[x > 0].sum() / max(1e-9, abs(x[x < 0].sum()))),
        raw=True,
    )
    feature_frame["rsi_14"] = rsi_14.loc[as_of_date].reindex(selected_universe).values

    price_up_5d = (prior_5d.loc[as_of_date].reindex(selected_universe) > 0).values
    vol_up_5d = (volume_trend.loc[as_of_date].reindex(selected_universe) > 1.0).values
    feature_frame["momentum_quality"] = np.where(
        price_up_5d & vol_up_5d, 1.0,
        np.where(price_up_5d | vol_up_5d, 0.5, 0.0),
    )

    strong_mom = feature_frame["prior_20d_momentum"] > 0.05
    high_vol = feature_frame["volume_confirmation_ratio"] > 0.2
    feature_frame["breakout_score"] = np.where(
        strong_mom & high_vol,
        np.minimum(1.0, feature_frame["prior_20d_momentum"] * 3.0 + feature_frame["volume_confirmation_ratio"] * 0.5),
        0.0,
    )
    structured_scores = build_structured_scores(feature_frame)
    feature_frame["structured_score"] = structured_scores
    feature_frame["large_participant_footprint_score"] = structured_scores

    oversold = feature_frame["rsi_14"] < 35
    vol_spike = feature_frame["volume_confirmation_ratio"] > 0.3
    feature_frame["reversal_quality"] = np.where(
        oversold & vol_spike,
        np.minimum(1.0, (35.0 - feature_frame["rsi_14"]) / 35.0 + feature_frame["volume_confirmation_ratio"] * 0.5),
        0.0,
    )

    # Theme strength: momentum persistence + volume support
    # Strong theme = sustained momentum with volume confirmation
    mom_persistence = (feature_frame["prior_20d_momentum"] > 0.03) & (feature_frame["prior_5d_momentum"] > 0)
    vol_support = feature_frame["volume_confirmation_ratio"] > 0.1
    feature_frame["theme_strength"] = np.where(
        mom_persistence & vol_support,
        np.minimum(1.0, feature_frame["prior_20d_momentum"] * 2.0 + feature_frame["volume_confirmation_ratio"] * 0.3),
        np.where(
            mom_persistence,
            0.3,
            0.0
        )
    )

    # Announcement catalyst: RSI extremes + volume spike (proxy for news-driven moves)
    rsi_extreme_high = feature_frame["rsi_14"] > 70
    rsi_extreme_low = feature_frame["rsi_14"] < 30
    big_volume = feature_frame["volume_confirmation_ratio"] > 0.5
    feature_frame["announcement_catalyst"] = np.where(
        (rsi_extreme_high | rsi_extreme_low) & big_volume,
        0.8,
        np.where(
            big_volume,
            0.4,
            np.where(
                rsi_extreme_high | rsi_extreme_low,
                0.2,
                0.0
            )
        )
    )

    # Market participation is the observable cross-sectional environment, not
    # social sentiment. It is a small context term beside the stock footprint.
    market_participation = min(
        1.0,
        max(0.0, (float(regime.breadth) + float(regime.advance_ratio)) / 200.0),
    )
    feature_frame["market_participation_score"] = market_participation
    feature_frame["raw_market_score"] = feature_frame["large_participant_footprint_score"]
    feature_frame["blended_score"] = (
        feature_frame["large_participant_footprint_score"] * 0.85
        + feature_frame["market_participation_score"] * 0.15
    )

    momentum_exhaustion_mask = feature_frame["five_day_acceleration"] < regime_thresholds.exhaustion_threshold
    feature_frame["market_rule_flags"] = np.where(
        momentum_exhaustion_mask,
        "momentum_exhaustion_guard",
        "",
    )
    feature_frame["market_rule_adjustment"] = np.where(
        momentum_exhaustion_mask,
        regime_thresholds.exhaustion_adjustment,
        0.0,
    )
    feature_frame["market_score"] = feature_frame["blended_score"] + feature_frame["market_rule_adjustment"]
    feature_frame["social_sentiment_bonus"] = 0.0

    if feedback and feedback.get("symbol_penalties"):
        penalties = feedback["symbol_penalties"]
        feature_frame["feedback_penalty"] = feature_frame.index.map(
            lambda s: penalties.get(s, {}).get("penalty", 0.0)
        )
        feature_frame["market_score"] = feature_frame["market_score"] + feature_frame["feedback_penalty"]
    else:
        feature_frame["feedback_penalty"] = 0.0

    risk_penalty = pd.Series(0.0, index=feature_frame.index)
    risk_penalty = risk_penalty + np.where(
        feature_frame["five_day_acceleration"] < regime_thresholds.exhaustion_threshold * 1.5,
        0.08, 0.0,
    )
    risk_penalty = risk_penalty + np.where(
        feature_frame["five_day_acceleration"] < regime_thresholds.accel_hard_block_threshold,
        0.10, 0.0,
    )
    risk_penalty = risk_penalty + np.where(
        feature_frame["volume_confirmation_ratio"] < 0.0, 0.03, 0.0,
    )
    risk_penalty = risk_penalty + np.where(
        feature_frame["volume_weighted_momentum"] < 0, 0.03, 0.0,
    )

    blowoff_high_volume = feature_frame["volume_confirmation_ratio"] > regime_thresholds.blowoff_volume_threshold
    blowoff_price_rejection = (
        (feature_frame["closing_strength_5d"] < regime_thresholds.blowoff_closing_threshold)
        & (feature_frame["five_day_acceleration"] < regime_thresholds.blowoff_accel_threshold)
    )
    blowoff_mask = blowoff_high_volume & blowoff_price_rejection
    risk_penalty = risk_penalty + np.where(blowoff_mask, 0.15, 0.0)

    weak_close_mask = feature_frame["closing_strength_5d"] < 0.3
    risk_penalty = risk_penalty + np.where(weak_close_mask, 0.05, 0.0)

    accel_extreme_mask = feature_frame["five_day_acceleration"] < regime_thresholds.accel_hard_block_threshold * 1.5
    risk_penalty = risk_penalty + np.where(accel_extreme_mask, 0.12, 0.0)

    intraday_drop_mask = feature_frame["intraday_momentum"] < -0.03
    risk_penalty = risk_penalty + np.where(intraday_drop_mask, 0.25, 0.0)

    intraday_mild_drop = (feature_frame["intraday_momentum"] < -0.01) & (feature_frame["intraday_momentum"] >= -0.03)
    risk_penalty = risk_penalty + np.where(intraday_mild_drop, 0.10, 0.0)

    overbought_mask = feature_frame["rsi_14"] > 75
    risk_penalty = risk_penalty + np.where(overbought_mask, 0.06, 0.0)

    feature_frame["risk_penalty"] = risk_penalty
    feature_frame["market_score"] = feature_frame["market_score"] - feature_frame["risk_penalty"]

    feature_frame["blowoff_risk"] = np.where(blowoff_mask, "high_volume_rejection", "")
    feature_frame["confirmation_score"] = feature_frame["footprint_factor_coverage"]
    # Capital Brain runs beside observable_footprint_v1. It is never used to
    # alter the existing ranking or classification until validation gates pass.
    capital_columns: dict[str, dict[str, Any]] = {}
    previous_capital_states = previous_capital_states or {}
    for symbol in selected_universe:
        symbol_bars = long_panel[long_panel["symbol"] == symbol]
        previous = previous_capital_states.get(symbol, {})
        assessment = build_capital_assessment(
            symbol_bars,
            statistical_score=float(np.clip(feature_frame.at[symbol, "market_score"], 0.0, 1.0)),
            relative_strength=_safe_float(feature_frame.at[symbol, "relative_strength_vs_equal_weight"]),
            regime_alignment=market_participation,
            previous_state=previous.get("capital_state"),
            previous_duration=int(previous.get("state_duration") or 0),
        )
        evidence_values = {
            key: item["value"] for key, item in assessment["evidence"]["evidence"].items()
        }
        capital_columns[symbol] = {
            "capital_evidence": assessment["evidence"],
            "capital_model_version": assessment["model_version"],
            "capital_validation_status": assessment["validation_status"],
            **assessment["scores"],
            **assessment["control"],
            **assessment["state"],
            **assessment["intent"],
            **assessment["path"],
            "upward_pressure": evidence_values["upward_pressure"],
            "downward_pressure": evidence_values["downward_pressure"],
            "volume_pressure": evidence_values["volume_pressure"],
            "demand_persistence_score": evidence_values["demand_persistence"],
            "supply_exhaustion_score": evidence_values["supply_exhaustion"],
            "absorption_score": evidence_values["absorption"],
            "accumulation_score": evidence_values["accumulation"],
            "markup_score": evidence_values["markup"],
            "distribution_score": evidence_values["distribution"],
            "crowding_score": evidence_values["crowding"],
            "trap_score": evidence_values["trap"],
            "price_impact_score": evidence_values["price_impact"],
            "capital_thesis": (
                f"{assessment['control']['dominant_direction']} observable pressure has "
                f"the advantage; inferred state={assessment['state']['capital_state']}; "
                f"inferred intent={assessment['intent']['capital_intent']}; "
                f"predicted path={assessment['path']['path_type']}"
            ),
        }
    capital_frame = pd.DataFrame.from_dict(capital_columns, orient="index")
    feature_frame = feature_frame.join(capital_frame, how="left")
    feature_frame["market_rank"] = feature_frame["market_score"].rank(
        method="first",
        ascending=False,
        na_option="bottom",
    ).astype(int)
    feature_frame["dollar_volume_20d_median"] = feature_frame["median_dollar_volume_20d"]

    feature_frame = feature_frame.sort_values(["market_score", "prior_20d_momentum"], ascending=False, kind="mergesort")

    actual_kline_source = kline_source or EASTMONEY_HISTORICAL_SOURCE_DISPLAY
    pipeline_session = CALENDAR.pipeline_session()
    market_summary = {
        "as_of_date": as_of_date.strftime("%Y-%m-%d"),
        "target_session": pipeline_session["target_session"],
        "actual_previous_trading_session": pipeline_session["actual_previous_trading_session"],
        "pipeline_execution_time": pipeline_session["pipeline_execution_time"],
        "session_status": pipeline_session["session_status"],
        "market_data_source": MARKET_DATA_SOURCE_DISPLAY,
        "kline_source": actual_kline_source,
        "quote_source": QUOTE_SOURCE_DISPLAY,
        "price_basis": f"{actual_kline_source} Adj Close with Close fallback; EastMoney quote is used for realtime enrichment",
        "equal_weight_20d_benchmark": equal_weight_20d_benchmark,
        "universe_count": int(len(selected_universe)),
        "market_feature_medians": {
            "prior_5d_momentum": _safe_float(feature_frame["prior_5d_momentum"].median()),
            "prior_20d_momentum": _safe_float(feature_frame["prior_20d_momentum"].median()),
            "five_day_acceleration": _safe_float(feature_frame["five_day_acceleration"].median()),
            "relative_strength_vs_equal_weight": _safe_float(feature_frame["relative_strength_vs_equal_weight"].median()),
            "volume_confirmation_ratio": _safe_float(feature_frame["volume_confirmation_ratio"].median()),
            "median_dollar_volume_20d": _safe_float(feature_frame["median_dollar_volume_20d"].median()),
            "closing_strength_5d": _safe_float(feature_frame["closing_strength_5d"].median()),
            "volume_weighted_momentum": _safe_float(feature_frame["volume_weighted_momentum"].median()),
            "rsi_14_median": _safe_float(feature_frame["rsi_14"].median()),
            "momentum_quality_median": _safe_float(feature_frame["momentum_quality"].median()),
            "breakout_score_median": _safe_float(feature_frame["breakout_score"].median()),
        },
        "market_feature_spreads": {
            "prior_20d_momentum_p90": _safe_float(feature_frame["prior_20d_momentum"].quantile(0.9)),
            "market_score_p90": _safe_float(feature_frame["market_score"].quantile(0.9)),
        },
    }
    return {
        "as_of_date": as_of_date,
        "price_basis": price_basis,
        "feature_frame": feature_frame,
        "market_summary": market_summary,
        "regime": regime,
        "regime_thresholds": regime_thresholds,
    }


def _safe_float(value: Any) -> float | None:
    if value is None or pd.isna(value):
        return None
    return float(value)


def quote_cross_check(
    yahoo_close: Any,
    provider_profile: dict[str, Any],
    kline_source: str | None = None,
    *,
    historical_session: Any = None,
    quote_session: Any = None,
    quote_symbol: str | None = None,
    historical_symbol: str | None = None,
    time_basis: str | None = None,
    quote_time_basis: str | None = None,
) -> dict[str, Any]:
    from research.temporal import compatible_sessions

    historical_close = _safe_float(yahoo_close)
    prev_close = _safe_float(provider_profile.get("prev_close"))
    latest_price = _safe_float(provider_profile.get("latest_price"))
    hist_session = historical_session or provider_profile.get("historical_session")
    q_session = quote_session
    quote_basis_name = "prev_close" if prev_close not in (None, 0) else ("latest_price" if latest_price not in (None, 0) else "unavailable")
    if q_session is None:
        if quote_basis_name == "prev_close":
            q_session = provider_profile.get("prev_close_session") or provider_profile.get("quote_session")
        elif quote_basis_name == "latest_price":
            q_session = provider_profile.get("quote_session") or provider_profile.get("session_date")
    same_symbol = True
    if quote_symbol and historical_symbol:
        same_symbol = str(quote_symbol).upper() == str(historical_symbol).upper()
    same_session = compatible_sessions(hist_session, q_session) if hist_session and q_session else False
    compatible_basis = True
    hist_basis = time_basis or "close"
    quote_basis_label = quote_time_basis or quote_basis_name
    if hist_basis and quote_basis_label not in (None, "", "unavailable"):
        compatible_basis = hist_basis == quote_basis_label or (
            hist_basis in {"close", "adj_close"} and quote_basis_label == "prev_close"
        )
    if not same_symbol or not same_session or not compatible_basis or not hist_session or not q_session:
        return {
            "kline_source": kline_source or EASTMONEY_HISTORICAL_SOURCE_DISPLAY,
            "quote_source": QUOTE_SOURCE_DISPLAY,
            "quote_cross_check_basis": "CROSS_CHECK_NOT_COMPARABLE",
            "quote_cross_check_price": None,
            "quote_cross_check_gap_pct": None,
            "data_source_mismatch": False,
            "data_source_mismatch_reason": "CROSS_CHECK_NOT_COMPARABLE",
            "same_symbol": same_symbol,
            "same_session": same_session,
            "compatible_time_basis": compatible_basis,
        }
    quote_price = prev_close if prev_close not in (None, 0) else latest_price
    quote_basis = "prev_close" if prev_close not in (None, 0) else ("latest_price" if latest_price not in (None, 0) else "unavailable")
    gap_pct = None
    mismatch = False
    reason = "cross_check_unavailable"
    if historical_close not in (None, 0) and quote_price not in (None, 0):
        gap_pct = abs(float(quote_price) / float(historical_close) - 1.0)
        mismatch = bool(gap_pct > DATA_SOURCE_MISMATCH_THRESHOLD)
        reason = "DATA_SOURCE_MISMATCH" if mismatch else "ok"
    return {
        "kline_source": kline_source or EASTMONEY_HISTORICAL_SOURCE_DISPLAY,
        "quote_source": QUOTE_SOURCE_DISPLAY,
        "quote_cross_check_basis": quote_basis,
        "quote_cross_check_price": quote_price,
        "quote_cross_check_gap_pct": gap_pct,
        "data_source_mismatch": mismatch,
        "data_source_mismatch_reason": reason,
        "same_symbol": same_symbol,
        "same_session": True,
        "compatible_time_basis": True,
    }


@lru_cache(maxsize=256)
def resolve_company_profile(symbol: str) -> dict[str, Any]:
    ticker = normalize_us_symbol(symbol)
    fallback = COMPANY_FALLBACKS.get(ticker, {})
    company_name = str(fallback.get("company_name") or ticker).strip()
    company_name_source = "symbol"
    provider_profile = fetch_realtime_quote(ticker) or {}
    provider_name = str(provider_profile.get("name") or "").strip()

    if provider_name:
        company_name = provider_name
        company_name_source = "eastmoney_us"
    elif fallback.get("company_name"):
        company_name = str(fallback["company_name"]).strip()
        company_name_source = "fallback"

    query_name = company_query_name(company_name)
    aliases: list[dict[str, str]] = []
    seen: set[tuple[str, str]] = set()

    def add_term(term: str, kind: str) -> None:
        normalized = normalize_match_text(term)
        if not normalized:
            return
        key = (normalized, kind)
        if key in seen:
            return
        seen.add(key)
        aliases.append({"term": term, "kind": kind})

    for variant in [company_name, query_name, fallback.get("company_name", ""), provider_name]:
        if variant:
            add_term(str(variant), "company")
            stripped = strip_legal_suffix(str(variant))
            if stripped and stripped != normalize_match_text(variant):
                add_term(stripped, "company")

    for keyword in fallback.get("keywords", []) or []:
        add_term(str(keyword), "keyword")

    if ticker not in AMBIGUOUS_TICKERS:
        add_term(ticker, "ticker")

    return {
        "symbol": ticker,
        "company_name": company_name,
        "company_query_name": query_name,
        "company_name_source": company_name_source,
        "provider_name": provider_name,
        "provider_profile": provider_profile,
        "match_terms": aliases,
        "keywords": list(fallback.get("keywords", []) or []),
    }


def score_evidence_item(item: dict[str, Any], company_profile: dict[str, Any], focus: str) -> dict[str, Any]:
    title = str(item.get("title") or "").strip()
    snippet = str(item.get("snippet") or "").strip()
    body = str(item.get("body") or item.get("content") or item.get("summary") or "").strip()
    why_relevant = str(item.get("why_relevant") or "").strip()
    text = " ".join(part for part in [title, snippet, body, why_relevant] if part)
    focus_terms = NARRATIVE_CONTEXT_TERMS if focus == "narrative" else BUSINESS_CONTEXT_TERMS
    matched_focus_terms = [term for term in focus_terms if phrase_in_text(term, text)]
    matched_terms = [
        term_info
        for term_info in company_profile["match_terms"]
        if phrase_in_text(term_info["term"], text)
    ]
    matched_company_terms = [term for term in matched_terms if term["kind"] in {"company", "keyword"}]
    matched_ticker_terms = [term for term in matched_terms if term["kind"] == "ticker"]

    relevance_score = 0.0
    relevance_reason = ""
    relevance_type = "unrelated"
    matched_term = None
    matched_focus = matched_focus_terms[0] if matched_focus_terms else None

    if matched_company_terms and matched_focus_terms:
        matched_term = matched_company_terms[0]
        relevance_score = 1.0 if matched_term["kind"] == "keyword" else 0.95
        relevance_reason = (
            f"matched {matched_term['kind']} term '{matched_term['term']}' "
            f"with {focus} context '{matched_focus}'"
        )
        relevance_type = "relevant"
    elif matched_ticker_terms and matched_focus_terms:
        matched_term = matched_ticker_terms[0]
        relevance_score = 0.75
        relevance_reason = (
            f"matched ticker boundary '{matched_term['term']}' "
            f"with {focus} context '{matched_focus}'"
        )
        relevance_type = "relevant"
    else:
        if matched_company_terms:
            matched_term = matched_company_terms[0]
            relevance_reason = (
                f"matched {matched_term['kind']} term '{matched_term['term']}' "
                f"but no {focus} context term"
            )
        elif matched_ticker_terms:
            matched_term = matched_ticker_terms[0]
            relevance_reason = (
                f"matched ticker boundary '{matched_term['term']}' but no {focus} context term"
            )
        elif matched_focus_terms:
            relevance_reason = (
                f"found {focus} context '{matched_focus}' but no company/product match"
            )
        else:
            relevance_reason = "no company/product/ticker match in title or snippet"

    return {
        "title": title,
        "snippet": snippet,
        "body": body,
        "text": text,
        "focus_terms": matched_focus_terms,
        "matched_terms": matched_terms,
        "matched_company_terms": matched_company_terms,
        "matched_ticker_terms": matched_ticker_terms,
        "relevance_type": relevance_type,
        "relevance_score": float(relevance_score),
        "relevance_reason": relevance_reason,
        "matched_term": matched_term,
    }


def format_evidence_line(summary: dict[str, Any]) -> str:
    if summary["status"] == "found_relevant":
        return f"{summary['top_evidence_title']} | {summary['top_evidence_reason']}"
    if summary["status"] == "found_unrelated":
        return f"UNRELATED: {summary['top_evidence_title']} | {summary['top_evidence_reason']}"
    return f"MISSING: {summary['top_evidence_reason']}"


def build_evidence_note(narrative: dict[str, Any], business: dict[str, Any]) -> str:
    return f"narrative={format_evidence_line(narrative)}; business={format_evidence_line(business)}"


def build_catalyst_summary(narrative: dict[str, Any], business: dict[str, Any]) -> str:
    titles = []
    if narrative["status"] == "found_relevant" and narrative["top_evidence_title"]:
        titles.append(str(narrative["top_evidence_title"]))
    if business["status"] == "found_relevant" and business["top_evidence_title"]:
        business_title = str(business["top_evidence_title"])
        if business_title not in titles:
            titles.append(business_title)
    if not titles:
        return "No relevant public catalyst evidence found."
    return "; ".join(titles)


def build_risk_summary(row: dict[str, Any], narrative: dict[str, Any], business: dict[str, Any]) -> str:
    pieces = [
        "Track 1d/3d/5d/10d closes against the universe.",
        "Invalidate on loss of 20d momentum or 5d acceleration.",
        "Watch for volume confirmation to fade back below the 20d median.",
    ]
    if narrative["status"] != "found_relevant" and business["status"] != "found_relevant":
        pieces.append("No company-specific public catalyst evidence yet.")
    elif narrative["status"] != "found_relevant" or business["status"] != "found_relevant":
        pieces.append("Evidence is partial; keep the candidate under review only if the relevant side is strong.")
    return " ".join(pieces)


def catalyst_score(narrative: dict[str, Any], business: dict[str, Any]) -> float:
    """Score independently observed public catalyst evidence, or zero if absent."""
    n_rel = _safe_float(narrative.get("relevance_score")) or 0.0
    b_rel = _safe_float(business.get("relevance_score")) or 0.0
    n_ok = narrative["status"] == "found_relevant" and n_rel >= 0.7
    b_ok = business["status"] == "found_relevant" and b_rel >= 0.7
    if not (n_ok or b_ok):
        return 0.0
    strongest_relevance = max(n_rel if n_ok else 0.0, b_rel if b_ok else 0.0)
    source_diversity = max(
        int(narrative.get("source_diversity", 0) or 0),
        int(business.get("source_diversity", 0) or 0),
    )
    corroborated = 1.0 if n_ok and b_ok else 0.0
    return min(
        1.0,
        strongest_relevance * 0.70
        + min(1.0, source_diversity / 3.0) * 0.15
        + corroborated * 0.15,
    )


def evidence_bonus(narrative: dict[str, Any], business: dict[str, Any]) -> float:
    return catalyst_score(narrative, business)


def build_evidence_gap_reason(
    narrative_summary: dict[str, Any],
    business_summary: dict[str, Any],
    gate_pass: bool,
    market_evidence_pass: bool,
) -> str:
    if gate_pass:
        return "paper_review_gate_passed"

    if (
        int(narrative_summary["ranked_candidate_count"]) == 0
        and int(business_summary["ranked_candidate_count"]) == 0
    ):
        return "last30days_returned_zero_ranked_candidates"

    reasons: list[str] = []
    if narrative_summary["status"] == "found_unrelated" or business_summary["status"] == "found_unrelated":
        reasons.append("found_unrelated_public_items")
    if narrative_summary["status"] != "found_relevant":
        reasons.append("relevant_narrative_missing")
    if business_summary["status"] != "found_relevant":
        reasons.append("relevant_business_missing")
    if not reasons:
        reasons.append("market_rank_below_cutoff" if not market_evidence_pass else "relevant_evidence_below_gate")
    return ";".join(dict.fromkeys(reasons))


def _empty_evidence_summary(side: str) -> dict[str, Any]:
    """Return a neutral evidence summary when last30days is skipped."""
    return {
        "topic": f"{side} (disabled)",
        "status": "missing",
        "source_counts": {},
        "source_diversity": 0,
        "cluster_count": 0,
        "ranked_candidate_count": 0,
        "top_score": None,
        "relevance_score": 0.0,
        "freshness_max": None,
        "top_items": [],
        "top_evidence_title": None,
        "top_evidence_reason": "evidence disabled (noise reduction)",
        "matched_term": None,
    }


def build_candidate_record(
    row: dict[str, Any],
    as_of_date: pd.Timestamp,
    market_cutoff: int,
    feedback: dict | None = None,
    regime_thresholds: Any = None,
    kline_source: str | None = None,
) -> dict[str, Any]:
    symbol = str(row["symbol"])
    company_profile = resolve_company_profile(symbol)

    # Skip last30days social/news data to reduce noise
    if SKIP_LAST30DAYS:
        narrative_summary = _empty_evidence_summary("narrative")
        business_summary = _empty_evidence_summary("business")
    else:
        narrative_topic = f"{symbol} {company_profile['company_query_name']} {NARRATIVE_QUERY_SUFFIX}"
        business_topic = f"{symbol} {company_profile['company_query_name']} {BUSINESS_QUERY_SUFFIX}"
        narrative_result = run_last30days_topic(narrative_topic)
        business_result = run_last30days_topic(business_topic)
        narrative_summary = summarize_last30days_result(narrative_result, company_profile, "narrative")
        business_summary = summarize_last30days_result(business_result, company_profile, "business")

    research = run_full_research_panel(symbol, row, narrative_summary, business_summary, company_profile)
    provider_profile = company_profile.get("provider_profile", {}) or {}
    historical_session = str(pd.Timestamp(as_of_date).date())
    quote_basis_hint = "prev_close" if provider_profile.get("prev_close") not in (None, 0, "") else "latest_price"
    quote_session = provider_profile.get("prev_close_session") if quote_basis_hint == "prev_close" else provider_profile.get("quote_session")
    cross_check = quote_cross_check(
        row.get("close"),
        provider_profile,
        kline_source=kline_source,
        historical_session=historical_session,
        quote_session=quote_session,
        historical_symbol=symbol,
        quote_symbol=provider_profile.get("symbol") or symbol,
        time_basis="close",
        quote_time_basis=quote_basis_hint,
    )
    eastmoney_detail_urls = candidate_enhanced_urls(symbol)
    information_coverage = information_coverage_audit(symbol)

    market_evidence_pass = bool(int(row["market_rank"]) <= int(market_cutoff))
    has_relevant_evidence = narrative_summary["status"] == "found_relevant" or business_summary["status"] == "found_relevant"
    strongest_relevance = float(max(narrative_summary["relevance_score"], business_summary["relevance_score"]))
    data_source_ok = not bool(cross_check["data_source_mismatch"]) and cross_check.get("data_source_mismatch_reason") != "CROSS_CHECK_NOT_COMPARABLE"
    rss_only = bool(narrative_summary.get("rss_fallback") or business_summary.get("rss_fallback"))
    corroboration = int(max(narrative_summary.get("corroboration") or 0, business_summary.get("corroboration") or 0))
    primary_source = bool(narrative_summary.get("primary_source") or business_summary.get("primary_source"))
    source_count = int(max(narrative_summary.get("source_diversity") or 0, business_summary.get("source_diversity") or 0))
    weak_rss = rss_only and source_count <= 1 and not primary_source and corroboration <= 0
    research_evidence_pass = has_relevant_evidence and strongest_relevance >= 0.7 and not weak_rss
    data_complete = data_source_ok
    temporal_ok = bool(historical_claim_eligible(
        {
            "published_at": narrative_summary.get("range_to") or business_summary.get("range_to") or historical_session,
            "effective_date": historical_session,
            "retrieved_at": provider_profile.get("as_of"),
            "as_of": historical_session,
        },
        as_of=historical_session,
    ).get("eligible", False))
    risk_recommendation = research["risk_checklist"].get("recommendation")
    risk_evidence_pass = risk_recommendation not in {"NEED_MORE_EVIDENCE", "DO_NOT_ADVANCE"}
    gate_pass = bool(
        market_evidence_pass
        and research_evidence_pass
        and risk_evidence_pass
        and data_complete
        and temporal_ok
    )
    watchlist_pass = bool(market_evidence_pass and not gate_pass)

    risk_verdict = research["risk_checklist"].get("risk_verdict", "UNAVAILABLE")
    quality_verdict = research["quality_check"].get("quality_verdict", "UNAVAILABLE")
    panel_verdict = research["research_panel"].get("panel_verdict", "MIXED")

    accel_block = regime_thresholds.accel_hard_block_threshold if regime_thresholds else -0.12
    has_reversal = float(row.get("reversal_signal", 0)) > 0
    has_intraday_up = float(row.get("intraday_momentum", 0)) > 0.005
    accel_extreme = float(row["five_day_acceleration"]) <= accel_block

    if risk_verdict == "BLOCKED":
        classification = "BLOCKED_BY_RISK"
        evidence_gate_status = "BLOCKED_BY_RISK"
    elif bool(cross_check["data_source_mismatch"]):
        classification = "MARKET_WATCHLIST_NEEDS_EVIDENCE"
        evidence_gate_status = "DATA_SOURCE_MISMATCH"
    elif gate_pass and accel_extreme and not has_reversal:
        classification = "MARKET_WATCHLIST_NEEDS_EVIDENCE"
        evidence_gate_status = "MOMENTUM_EXHAUSTION_HARD_BLOCK"
    elif gate_pass and accel_extreme and has_reversal:
        classification = "CANDIDATE_FOR_PAPER_REVIEW"
        evidence_gate_status = "REVERSAL_OVERRIDE"
    elif gate_pass and str(row.get("blowoff_risk", "")) == "high_volume_rejection" and not has_intraday_up:
        classification = "MARKET_WATCHLIST_NEEDS_EVIDENCE"
        evidence_gate_status = "BLOWOFF_RISK_HARD_BLOCK"
    elif gate_pass and float(row.get("confirmation_score", 1.0)) < 0.4 and not has_intraday_up:
        classification = "MARKET_WATCHLIST_NEEDS_EVIDENCE"
        evidence_gate_status = "LOW_CONFIRMATION_BLOCK"
    elif gate_pass:
        classification = "CANDIDATE_FOR_PAPER_REVIEW"
        evidence_gate_status = "CANDIDATE_FOR_PAPER_REVIEW"
    elif watchlist_pass:
        classification = "MARKET_WATCHLIST_NEEDS_EVIDENCE"
        evidence_gate_status = "MARKET_WATCHLIST_NEEDS_EVIDENCE"
    else:
        classification = "NEED_MORE_EVIDENCE"
        evidence_gate_status = (
            "REJECTED_EVIDENCE_UNRELATED"
            if narrative_summary["status"] == "found_unrelated" or business_summary["status"] == "found_unrelated"
            else "NEED_MORE_EVIDENCE"
        )
    evidence_gap_reason = build_evidence_gap_reason(
        narrative_summary,
        business_summary,
        gate_pass=gate_pass,
        market_evidence_pass=market_evidence_pass,
    )
    if bool(cross_check["data_source_mismatch"]):
        evidence_gap_reason = ";".join(dict.fromkeys(["DATA_SOURCE_MISMATCH", evidence_gap_reason]))

    catalyst = catalyst_score(narrative_summary, business_summary)
    ticket_score = float(row["market_score"]) * 0.75 + catalyst * 0.25
    forward_dates = {
        f"{horizon}d": bday_date(pd.Timestamp(as_of_date), horizon)
        for horizon in TRACKING_HORIZONS
    }

    risk_params = {"win_rate": 0.5, "avg_win_pct": 0.04, "avg_loss_pct": 0.02}
    if feedback and feedback.get("adjusted_risk_params"):
        rp = feedback["adjusted_risk_params"]
        risk_params = {
            "win_rate": rp.get("win_rate", 0.5),
            "avg_win_pct": rp.get("avg_win_pct", 0.04),
            "avg_loss_pct": rp.get("avg_loss_pct", 0.02),
        }
    sl_mult = 1.0
    tp_mult = 1.0
    kelly_cap = 1.0
    pos_cap = 0.10
    if regime_thresholds is not None:
        sl_mult = getattr(regime_thresholds, "stop_loss_multiplier", 1.0)
        tp_mult = getattr(regime_thresholds, "take_profit_multiplier", 1.0)
        kelly_cap = getattr(regime_thresholds, "kelly_fraction_cap", 1.0)
        pos_cap = getattr(regime_thresholds, "position_cap_pct", 0.10)
    risk_record = build_candidate_risk_record(
        symbol=symbol,
        entry_price=_safe_float(row["close"]) or 0.0,
        current_price=_safe_float(provider_profile.get("latest_price")) or _safe_float(row["close"]) or 0.0,
        account_balance=100_000.0,
        win_rate=risk_params["win_rate"],
        avg_win_pct=risk_params["avg_win_pct"],
        avg_loss_pct=risk_params["avg_loss_pct"],
        atr=None,
        risk_per_trade=regime_thresholds.risk_per_trade if regime_thresholds else None,
        max_single_position_pct=regime_thresholds.max_single_position_pct if regime_thresholds else None,
        max_total_exposure_pct=regime_thresholds.max_total_exposure_pct if regime_thresholds else None,
        max_consecutive_losses=regime_thresholds.max_consecutive_losses if regime_thresholds else None,
        daily_max_loss_r=regime_thresholds.daily_max_loss_r if regime_thresholds else None,
        default_stop_loss_pct=regime_thresholds.default_stop_loss_pct if regime_thresholds else None,
    )
    raw_sl = risk_record.get("stop_loss", 0.0) or 0.0
    raw_tp = risk_record.get("take_profit", 0.0) or 0.0
    entry = _safe_float(row["close"]) or 0.0
    if entry > 0 and raw_sl > 0:
        sl_distance = entry - raw_sl
        adjusted_sl = entry - sl_distance * sl_mult
        risk_record["stop_loss"] = adjusted_sl
    if entry > 0 and raw_tp > 0:
        tp_distance = raw_tp - entry
        adjusted_tp = entry + tp_distance * tp_mult
        risk_record["take_profit"] = adjusted_tp
    raw_kelly = risk_record.get("kelly_fraction", 0.0)
    if raw_kelly is None:
        raw_kelly = 0.0
    risk_record["kelly_fraction"] = min(raw_kelly, kelly_cap)
    raw_pos = risk_record.get("position_size_pct")
    if raw_pos is None:
        raw_pos = DEFAULT_RISK_PER_TRADE
    risk_record["position_size_pct"] = min(raw_pos, pos_cap)
    if risk_record["kelly_fraction"] > 0 and risk_record["position_size_pct"] > risk_record["kelly_fraction"]:
        risk_record["position_size_pct"] = risk_record["kelly_fraction"]

    return {
        "symbol": symbol,
        "company_name": company_profile["company_name"],
        "company_name_source": company_profile["company_name_source"],
        "company_query_name": company_profile["company_query_name"],
        "as_of_date": pd.Timestamp(as_of_date).strftime("%Y-%m-%d"),
        "close": _safe_float(row["close"]),
        "adj_close": _safe_float(row["adj_close"]),
        "volume": _safe_float(row["volume"]),
        "market_data_source": MARKET_DATA_SOURCE_DISPLAY,
        "kline_source": cross_check["kline_source"],
        "quote_source": cross_check["quote_source"],
        "quote_source_status": provider_profile.get("source_status", "unavailable"),
        "quote_cross_check_basis": cross_check["quote_cross_check_basis"],
        "quote_cross_check_price": cross_check["quote_cross_check_price"],
        "quote_cross_check_gap_pct": cross_check["quote_cross_check_gap_pct"],
        "data_source_mismatch": cross_check["data_source_mismatch"],
        "data_source_mismatch_reason": cross_check["data_source_mismatch_reason"],
        "eastmoney_quote_detail_url": eastmoney_detail_urls["quote_detail"],
        "eastmoney_news_url": eastmoney_detail_urls["news_detail"],
        "eastmoney_company_url": eastmoney_detail_urls["company_detail"],
        "information_coverage_audit": information_coverage,
        "latest_price": _safe_float(provider_profile.get("latest_price")),
        "prev_close": _safe_float(provider_profile.get("prev_close")),
        "intraday_pct_chg": _safe_float(provider_profile.get("pct_chg")),
        "pe_ttm": _safe_float(provider_profile.get("pe_ttm")),
        "roe": _safe_float(provider_profile.get("roe")),
        "dividend_yield": _safe_float(provider_profile.get("dividend_yield")),
        "raw_market_score": _safe_float(row["raw_market_score"]),
        "blended_score": _safe_float(row.get("blended_score", 0.0)),
        "large_participant_footprint_score": _safe_float(row.get("large_participant_footprint_score")),
        "footprint_factor_coverage": _safe_float(row.get("footprint_factor_coverage")),
        "footprint_factor_contributions": row.get("footprint_factor_contributions") or {},
        "market_participation_score": _safe_float(row.get("market_participation_score")),
        "breakout_score": _safe_float(row.get("breakout_score", 0.0)),
        "confirmation_score": _safe_float(row.get("confirmation_score", 0.0)),
        "market_score": _safe_float(row["market_score"]),
        "market_rule_flags": str(row["market_rule_flags"]),
        "market_rule_adjustment": _safe_float(row["market_rule_adjustment"]),
        "market_rank": int(row["market_rank"]),
        "prior_5d_momentum": _safe_float(row["prior_5d_momentum"]),
        "prior_20d_momentum": _safe_float(row["prior_20d_momentum"]),
        "five_day_acceleration": _safe_float(row["five_day_acceleration"]),
        "relative_strength_vs_equal_weight": _safe_float(row["relative_strength_vs_equal_weight"]),
        "volume_confirmation_ratio": _safe_float(row["volume_confirmation_ratio"]),
        "median_dollar_volume_20d": _safe_float(row["median_dollar_volume_20d"]),
        "closing_strength_5d": _safe_float(row.get("closing_strength_5d")),
        "volume_weighted_momentum": _safe_float(row.get("volume_weighted_momentum")),
        "volume_trend_20d": _safe_float(row.get("volume_trend_20d")),
        "risk_penalty": _safe_float(row.get("risk_penalty", 0.0)),
        "market_evidence_pass": market_evidence_pass,
        "strongest_relevance": strongest_relevance,
        "narrative_topic": narrative_topic if not SKIP_LAST30DAYS else f"{symbol} (evidence disabled)",
        "narrative_status": narrative_summary["status"],
        "narrative_returncode": int(narrative_result["returncode"]) if not SKIP_LAST30DAYS else 0,
        "narrative_source_diversity": int(narrative_summary.get("source_diversity", 0)),
        "narrative_cluster_count": int(narrative_summary.get("cluster_count", 0)),
        "narrative_ranked_candidate_count": int(narrative_summary.get("ranked_candidate_count", 0)),
        "narrative_top_title": narrative_summary.get("top_evidence_title", ""),
        "narrative_top_score": narrative_summary.get("top_score", 0.0),
        "narrative_relevance_score": narrative_summary["relevance_score"],
        "narrative_relevance_reason": narrative_summary.get("top_evidence_reason", ""),
        "business_topic": business_topic if not SKIP_LAST30DAYS else f"{symbol} (evidence disabled)",
        "business_status": business_summary["status"],
        "business_returncode": int(business_result["returncode"]) if not SKIP_LAST30DAYS else 0,
        "business_source_diversity": int(business_summary.get("source_diversity", 0)),
        "business_cluster_count": int(business_summary.get("cluster_count", 0)),
        "business_ranked_candidate_count": int(business_summary.get("ranked_candidate_count", 0)),
        "business_top_title": business_summary.get("top_evidence_title", ""),
        "business_top_score": business_summary.get("top_score", 0.0),
        "business_relevance_score": business_summary["relevance_score"],
        "business_relevance_reason": business_summary.get("top_evidence_reason", ""),
        "quality_check": research["quality_check"],
        "risk_checklist": research["risk_checklist"],
        "supply_chain_map": research["supply_chain_map"],
        "research_panel": research["research_panel"],
        "replay_hypothesis": research["replay_hypothesis"],
        "research_gate": {
            "market_evidence": market_evidence_pass,
            "research_evidence": research_evidence_pass,
            "risk_evidence": risk_evidence_pass,
            "risk_recommendation": risk_recommendation,
            "data_completeness": data_complete,
            "temporal_validity": temporal_ok,
            "rss_cannot_auto_pass": True,
            "weak_rss": weak_rss,
        },
        "catalyst_score": catalyst,
        "ticket_score": ticket_score,
        "news_quality_score": catalyst,
        "sector_propagation_bonus": 0.0,
        "contrarian_penalty": 0.0,
        "capital_flow_proxy_score": _safe_float(row.get("large_participant_footprint_score")),
        "capital_flow_status": "OBSERVED_PRICE_VOLUME_FOOTPRINT",
        "social_sentiment_status": "UNAVAILABLE_NO_VALIDATED_CORPUS",
        "capital_evidence": row.get("capital_evidence") or {},
        "capital_model_version": str(row.get("capital_model_version") or "capital_behavior_v2"),
        "capital_validation_status": str(row.get("capital_validation_status") or "UNVALIDATED_NO_FIXED_CHAIN"),
        "statistical_score": _safe_float(row.get("statistical_score")),
        "capital_behavior_score": _safe_float(row.get("capital_behavior_score") or row.get("capital_score")),
        "capital_score": _safe_float(row.get("capital_score")),
        "combined_score": _safe_float(row.get("combined_score")),
        "capital_strength": _safe_float(row.get("capital_strength")),
        "dominant_direction": str(row.get("dominant_direction") or "UNKNOWN"),
        "dominant_pressure": _safe_float(row.get("dominant_pressure")),
        "capital_state": str(row.get("capital_state") or "UNKNOWN"),
        "previous_capital_state": str(row.get("previous_capital_state") or "UNKNOWN"),
        "state_transition": str(row.get("state_transition") or "UNKNOWN"),
        "state_duration": int(row.get("state_duration") or 0),
        "capital_state_confidence": _safe_float(row.get("state_confidence")),
        "capital_state_reason": str(row.get("state_reason") or ""),
        "capital_intent": str(row.get("capital_intent") or "UNKNOWN"),
        "capital_intent_confidence": _safe_float(row.get("intent_confidence")),
        "accumulation_score": _safe_float(row.get("accumulation_score")),
        "absorption_score": _safe_float(row.get("absorption_score")),
        "supply_exhaustion_score": _safe_float(row.get("supply_exhaustion_score")),
        "demand_persistence_score": _safe_float(row.get("demand_persistence_score")),
        "markup_score": _safe_float(row.get("markup_score")),
        "distribution_score": _safe_float(row.get("distribution_score")),
        "price_control_score": _safe_float(row.get("price_control_score")),
        "upside_control_efficiency": _safe_float(row.get("upside_control_efficiency")),
        "downside_control_efficiency": _safe_float(row.get("downside_control_efficiency")),
        "crowding_score": _safe_float(row.get("crowding_score")),
        "trap_score": _safe_float(row.get("trap_score")),
        "price_impact_score": _safe_float(row.get("price_impact_score")),
        "expected_direction": str(row.get("expected_direction") or "UNKNOWN"),
        "path_type": str(row.get("path_type") or "UNKNOWN"),
        "path_confidence": _safe_float(row.get("path_confidence")),
        "t1_probability": _safe_float(row.get("t1_probability")),
        "t3_probability": _safe_float(row.get("t3_probability")),
        "t5_probability": _safe_float(row.get("t5_probability")),
        "capital_thesis": str(row.get("capital_thesis") or ""),
        "invalidation_condition": str(row.get("invalidation_condition") or ""),
        "research_only": True,
        "allow_trade": False,
        "auto_order": False,
        "no_broker_api": True,
        "evidence_note": build_evidence_note(narrative_summary, business_summary),
        "catalyst_summary": build_catalyst_summary(narrative_summary, business_summary),
        "risk_summary": build_risk_summary(row, narrative_summary, business_summary),
        "classification": classification,
        "watchlist_pass": watchlist_pass,
        "evidence_gate_status": evidence_gate_status,
        "evidence_gate_pass": gate_pass,
        "evidence_gap_reason": evidence_gap_reason,
        "evidence_gate_reason": (
            f"market_pass={market_evidence_pass}; watchlist_pass={watchlist_pass}; "
            f"relevant_pass={has_relevant_evidence}; strongest_relevance={strongest_relevance}; "
            f"data_source_ok={data_source_ok}; data_source_mismatch={cross_check['data_source_mismatch']}; "
            f"quote_cross_check_gap_pct={cross_check['quote_cross_check_gap_pct']}; "
            f"footprint_coverage={_safe_float(row.get('footprint_factor_coverage'))}; "
            f"narrative={narrative_summary['status']}; business={business_summary['status']}; "
            f"quality={quality_verdict}; risk={risk_verdict}; panel={panel_verdict}"
        ),
        "forward_dates": forward_dates,
        "risk_record": risk_record,
        "risk_allowed": risk_record["risk_allowed"],
        "risk_block_reason": risk_record["risk_block_reason"],
        "risk_stop_loss": risk_record["stop_loss"],
        "risk_take_profit": risk_record["take_profit"],
        "risk_reward_ratio": risk_record["risk_reward_ratio"],
        "risk_position_size_pct": risk_record["position_size_pct"],
        "risk_kelly_fraction": risk_record["kelly_fraction"],
        "risk_score": risk_record["risk_score"],
        "risk_confidence": risk_record["confidence"],
        "narrative_evidence": narrative_summary,
        "business_evidence": business_summary,
        "narrative_raw": narrative_result if not SKIP_LAST30DAYS else {"topic": "disabled", "returncode": 0, "payload": {}},
        "business_raw": business_result if not SKIP_LAST30DAYS else {"topic": "disabled", "returncode": 0, "payload": {}},
    }


def candidate_lifecycle_stage(row: dict[str, Any]) -> str:
    classification = str(row.get("classification") or "")
    if classification == "CANDIDATE_FOR_PAPER_REVIEW":
        return "paper_review_candidate"
    if classification == "MARKET_WATCHLIST_NEEDS_EVIDENCE":
        return "market_watchlist"
    if classification == "BLOCKED_BY_RISK":
        return "blocked_by_risk"
    return "needs_more_evidence"


def build_best_watch_candidate(candidate_rows: list[dict[str, Any]]) -> dict[str, Any] | None:
    if not candidate_rows:
        return None
    watch_rows = [
        row for row in candidate_rows
        if row.get("classification") != "CANDIDATE_FOR_PAPER_REVIEW"
    ]
    if not watch_rows:
        return None
    sorted_rows = sorted(
        watch_rows,
        key=lambda row: (
            float(row.get("ticket_score") or 0.0),
            float(row.get("market_score") or 0.0),
            float(row.get("strongest_relevance") or 0.0),
        ),
        reverse=True,
    )
    best = dict(sorted_rows[0])
    best["watch_reason"] = (
        f"classification={best.get('classification')}; "
        f"risk={best.get('risk_checklist', {}).get('risk_verdict', 'UNAVAILABLE')}; "
        f"evidence={best.get('evidence_gate_status', 'UNKNOWN')}"
    )
    return best


def build_runtime_decision_context(
    top_candidates: list[dict[str, Any]],
    final_classification: str,
    market_summary: dict[str, Any],
    best_watch_candidate: dict[str, Any] | None,
) -> dict[str, Any]:
    return {
        "as_of_date": market_summary.get("as_of_date"),
        "market_data_source": market_summary.get("market_data_source"),
        "kline_source": market_summary.get("kline_source"),
        "quote_source": market_summary.get("quote_source"),
        "final_classification": final_classification,
        "top_candidates": [
            {
                "symbol": row.get("symbol"),
                "ticket_rank": row.get("ticket_rank"),
                "classification": row.get("classification"),
                "lifecycle_stage": candidate_lifecycle_stage(row),
                "ticket_score": row.get("ticket_score"),
                "market_score": row.get("market_score"),
                "strongest_relevance": row.get("strongest_relevance"),
                "risk_allowed": row.get("risk_allowed"),
                "risk_block_reason": row.get("risk_block_reason"),
                "evidence_gate_status": row.get("evidence_gate_status"),
                "evidence_gap_reason": row.get("evidence_gap_reason"),
                "capital_validation_status": row.get("capital_validation_status"),
                "capital_score": row.get("capital_score"),
                "capital_state": row.get("capital_state"),
                "capital_intent": row.get("capital_intent"),
                "distribution_score": row.get("distribution_score"),
                "trap_score": row.get("trap_score"),
                "path_type": row.get("path_type"),
            }
            for row in top_candidates
        ],
        "best_watch_candidate": None
        if not best_watch_candidate
        else {
            "symbol": best_watch_candidate.get("symbol"),
            "classification": best_watch_candidate.get("classification"),
            "lifecycle_stage": candidate_lifecycle_stage(best_watch_candidate),
            "ticket_score": best_watch_candidate.get("ticket_score"),
            "market_score": best_watch_candidate.get("market_score"),
            "watch_reason": best_watch_candidate.get("watch_reason"),
            "capital_state": best_watch_candidate.get("capital_state"),
            "capital_score": best_watch_candidate.get("capital_score"),
            "path_type": best_watch_candidate.get("path_type"),
        },
    }


def build_forward_tracking_rows(
    candidate_rows: list[dict[str, Any]],
    output_date: str,
    close_panel: pd.DataFrame | None = None,
    dynamic_horizon: bool = True,
) -> list[dict[str, Any]]:
    """Build forward tracking rows with optional dynamic horizon allocation.

    When dynamic_horizon=True and close_panel is provided, assigns horizons
    based on stock volatility: high vol → short horizon, low vol → long horizon.
    """
    rows = []

    # Get dynamic horizon allocations if enabled
    horizon_allocations = {}
    if dynamic_horizon and close_panel is not None and not close_panel.empty:
        symbols = [row["symbol"] for row in candidate_rows]
        horizon_allocations = batch_assign_horizons(close_panel, symbols)

    for row in candidate_rows:
        symbol = row["symbol"]
        alloc = horizon_allocations.get(symbol)

        # Determine which horizons to track
        if alloc:
            # Dynamic: primary horizon + all standard horizons for comparison
            primary_horizon = alloc.assigned_horizon
            horizons_to_track = sorted(set([primary_horizon] + list(TRACKING_HORIZONS)))
        else:
            # Fallback: use standard horizons
            horizons_to_track = TRACKING_HORIZONS

        for horizon in horizons_to_track:
            # Adjust risk parameters based on horizon and volatility
            base_stop_loss = row.get("risk_stop_loss", 0.0)
            base_take_profit = row.get("risk_take_profit", 0.0)
            entry_price = row.get("adj_close", 0.0) or row.get("close", 0.0)

            if alloc and entry_price and entry_price > 0:
                # Use dynamic stop-loss/take-profit based on volatility
                stop_loss_pct = alloc.stop_loss_pct
                take_profit_pct = alloc.take_profit_pct

                # Calculate absolute prices
                dynamic_stop_loss = entry_price * (1 - stop_loss_pct)
                dynamic_take_profit = entry_price * (1 + take_profit_pct)
                dynamic_rr_ratio = take_profit_pct / stop_loss_pct if stop_loss_pct > 0 else 0.0

                is_primary = (horizon == primary_horizon)
            else:
                # Use original risk parameters
                dynamic_stop_loss = base_stop_loss
                dynamic_take_profit = base_take_profit
                dynamic_rr_ratio = row.get("risk_reward_ratio", 0.0)
                is_primary = False

            rows.append(
                {
                    "symbol": symbol,
                    "ticket_rank": int(row["ticket_rank"]),
                    "market_rank": int(row["market_rank"]),
                    "as_of_date": row["as_of_date"],
                    "horizon_days": int(horizon),
                    "due_date": bday_date(pd.Timestamp(row["as_of_date"]), horizon),
                    "review_window": f"{horizon}d",
                    "check_status": "pending",
                    "track_key": f"{output_date}:{symbol}:{horizon}d:{row.get('ticket_id') or row.get('id') or ''}",
                    "as_of_close": row["adj_close"],
                    "as_of_adj_close": row["adj_close"],
                    "kline_source": row["kline_source"],
                    "quote_source": row["quote_source"],
                    "quote_cross_check_gap_pct": row["quote_cross_check_gap_pct"],
                    "data_source_mismatch": row["data_source_mismatch"],
                    "market_score": row["market_score"],
                    "catalyst_score": row["catalyst_score"],
                    "ticket_score": row["ticket_score"],
                    "capital_model_version": row.get("capital_model_version"),
                    "capital_validation_status": row.get("capital_validation_status"),
                    "capital_state_at_entry": row.get("capital_state"),
                    "capital_intent_at_entry": row.get("capital_intent"),
                    "capital_strength_at_entry": row.get("capital_strength"),
                    "capital_quality_at_entry": row.get("capital_quality"),
                    "predicted_path": row.get("predicted_path") or row.get("path_type"),
                    "capital_score_at_entry": row.get("capital_score"),
                    "distribution_score_at_entry": row.get("distribution_score"),
                    "trap_score_at_entry": row.get("trap_score"),
                    "distribution_probability_at_entry": row.get("distribution_probability"),
                    "trap_probability_at_entry": row.get("trap_probability"),
                    "quality_label_at_entry": row.get("quality_label"),
                    "intent_probability_at_entry": row.get("intent_probability"),
                    "path_distribution_at_entry": row.get("paths"),
                    "lifecycle_stage": candidate_lifecycle_stage(row),
                    "research_only": row["research_only"],
                    "allow_trade": row["allow_trade"],
                    "auto_order": row["auto_order"],
                    "no_broker_api": row["no_broker_api"],
                    "classification": row["classification"],
                    "risk_allowed": row.get("risk_allowed", True),
                    "risk_stop_loss": dynamic_stop_loss,
                    "risk_take_profit": dynamic_take_profit,
                    "risk_reward_ratio": dynamic_rr_ratio,
                    "risk_position_size_pct": row.get("risk_position_size_pct"),
                    "risk_kelly_fraction": row.get("risk_kelly_fraction"),
                    "risk_score": row.get("risk_score"),
                    "dynamic_horizon": is_primary,
                    "vol_category": alloc.vol_category if alloc else None,
                    "volatility_pct": alloc.volatility_pct if alloc else None,
                }
            )
    return rows


def build_summary_md(
    package: dict[str, Any],
    output_date: str,
) -> str:
    market_summary = package["market_summary"]
    top_candidates = package["top_candidates"]
    candidate_rows = package["candidate_rows"]
    market_rows = package["market_rows"]
    paper_review_rows = [row for row in top_candidates if row["classification"] == "CANDIDATE_FOR_PAPER_REVIEW"]
    watchlist_rows = [row for row in top_candidates if row["classification"] == "MARKET_WATCHLIST_NEEDS_EVIDENCE"]

    def append_candidate_section(title: str, rows: list[dict[str, Any]]) -> None:
        lines.extend(["", f"## {title}"])
        if not rows:
            lines.append("- none")
            return
        lines.extend(
            [
                "|rank|symbol|company|latest|intraday|source_gap|market_score|catalyst_score|ticket_score|narrative|business|gate_status|",
                "|---|---|---|---|---|---|---|---|---|---|---|---|",
            ]
        )
        for row in rows:
            lines.append(
                "|{ticket_rank}|{symbol}|{company_name}|{latest}|{intraday}|{source_gap}|{market_score}|{catalyst_score}|{ticket_score}|{narrative}|{business}|{gate_status}|".format(
                    ticket_rank=row["ticket_rank"],
                    symbol=row["symbol"],
                    company_name=row["company_name"],
                    latest=_safe_float(row.get("latest_price")),
                    intraday=_safe_float(row.get("intraday_pct_chg")),
                    source_gap=_safe_float(row.get("quote_cross_check_gap_pct")),
                    market_score=_safe_float(row["market_score"]),
                    catalyst_score=_safe_float(row.get("catalyst_score")),
                    ticket_score=_safe_float(row["ticket_score"]),
                    narrative=row["narrative_status"],
                    business=row["business_status"],
                    gate_status=row["evidence_gate_status"],
                )
            )
            lines.extend(
                [
                    f"  - ticket_card: research_only={str(row.get('research_only', True)).lower()} allow_trade={str(row.get('allow_trade', False)).lower()} auto_order={str(row.get('auto_order', False)).lower()} no_broker_api={str(row.get('no_broker_api', True)).lower()}",
                    f"  - lifecycle_stage: {row.get('lifecycle_stage', candidate_lifecycle_stage(row))}",
                    f"  - kline_source: {row.get('kline_source', EASTMONEY_HISTORICAL_SOURCE_DISPLAY)}",
                    f"  - quote_source: {row.get('quote_source', QUOTE_SOURCE_DISPLAY)} | status={row.get('quote_source_status', 'unavailable')} | prev_close={_safe_float(row.get('prev_close'))} | cross_check_basis={row.get('quote_cross_check_basis', 'unavailable')} | gap={_safe_float(row.get('quote_cross_check_gap_pct'))} | mismatch={str(row.get('data_source_mismatch', False)).lower()}",
                    f"  - eastmoney_tabs: detail={row.get('eastmoney_quote_detail_url', '')} | news={row.get('eastmoney_news_url', '')} | company={row.get('eastmoney_company_url', '')}",
                    f"  - catalyst: {row.get('catalyst_summary', '')}",
                ]
            )


    lines = [
        "# XIAOMEI US Profit Ticket Pipeline V0",
        "",
        "RESEARCH_ONLY",
        "NOT_TRADING_ADVICE",
        "NO_BROKER",
        "NO_ORDER",
        "NO_LEDGER",
        "NO_LIVE_TRADE",
        "",
        f"- output_date: {output_date}",
        f"- as_of_date: {market_summary['as_of_date']}",
        f"- target_session: {market_summary.get('target_session')}",
        f"- actual_previous_trading_session: {market_summary.get('actual_previous_trading_session')}",
        f"- pipeline_execution_time: {market_summary.get('pipeline_execution_time')}",
        f"- session_status: {market_summary.get('session_status')}",
        f"- market_data_source: {market_summary.get('market_data_source', MARKET_DATA_SOURCE_DISPLAY)}",
        f"- kline_source: {market_summary.get('kline_source', EASTMONEY_HISTORICAL_SOURCE_DISPLAY)}",
        f"- quote_source: {market_summary.get('quote_source', QUOTE_SOURCE_DISPLAY)}",
        f"- data_source_mismatch_threshold: {DATA_SOURCE_MISMATCH_THRESHOLD}",
        "- eastmoney_required_tabs: us_quote_center",
        "- eastmoney_enhanced_tabs: us_quote_detail, us_quote_news, us_quote_company",
        "- eastmoney_evidence_domains: market_overview, quote_detail, company_detail, news_detail",
        "- research_only: true",
        "- allow_trade: false",
        "- auto_order: false",
        "- no_broker_api: true",
        f"- universe_source: {package['source_config']['source_name']}",
        f"- source_mode: {package.get('source_mode', 'live')}",
        f"- data_mode: {package.get('data_mode', 'historical_kline')}",
        f"- universe_key: {package['selected_universe_key']}",
        f"- universe_total_symbols: {package['source_universe_total_symbols']}",
        f"- universe_included_symbols: {package['source_universe_included_symbols']}",
        f"- period_used: {package['period_used']}",
        f"- classification: {package['final_classification']}",
        f"- candidate_pool_size: {len(candidate_rows)}",
        f"- top_k: {len(top_candidates)}",
        f"- paper_review_count: {package['paper_review_count']}",
        f"- market_watchlist_count: {package['market_watchlist_count']}",
        f"- zero_paper_review_is_valid_output: {package['paper_review_count'] == 0}",
        f"- artifact_summary: {package['artifact_paths']['summary']}",
        f"- artifact_metrics: {package['artifact_paths']['metrics']}",
        f"- artifact_candidates: {package['artifact_paths']['candidates']}",
        f"- artifact_forward_tracking: {package['artifact_paths']['forward_tracking']}",
        f"- artifact_runtime_context: {package['artifact_paths']['runtime_context']}",
        f"- artifact_runtime_ledger: {package['artifact_paths']['runtime_ledger']}",
        "",
    ]
    if package.get("feedback_applied"):
        fb_wr = package.get("feedback_win_rate", 0) or 0
        fb_pen = package.get("feedback_symbol_penalties", [])
        lines.extend([
            "## Backtest Feedback Applied",
            f"- feedback_win_rate: {fb_wr:.0%}",
            f"- symbol_penalties: {', '.join(fb_pen) if fb_pen else 'none'}",
            "",
        ])

    regime = package.get("regime")
    if regime is not None:
        lines.extend([
            format_regime_summary(regime, package.get("regime_thresholds")),
            "",
        ])

    lines.extend([
        "## Methodology References",
    ])
    for ref in METHODOLOGY_REFERENCES:
        lines.append(f"- {ref['name']}: {ref['use']}")

    lines.extend(
        [
            "",
            "## Price-Volume Summary",
            f"- equal_weight_20d_benchmark: {market_summary['equal_weight_20d_benchmark']}",
            f"- median_20d_momentum: {market_summary['market_feature_medians']['prior_20d_momentum']}",
            f"- median_5d_acceleration: {market_summary['market_feature_medians']['five_day_acceleration']}",
            f"- median_volume_confirmation: {market_summary['market_feature_medians']['volume_confirmation_ratio']}",
            f"- median_relative_strength: {market_summary['market_feature_medians']['relative_strength_vs_equal_weight']}",
            f"- top_market_score_p90: {market_summary['market_feature_spreads']['market_score_p90']}",
        ]
    )
    append_candidate_section("Paper Review Candidates", paper_review_rows)
    append_candidate_section("Market Watchlist Needs Evidence", watchlist_rows)

    catalyst_titles = Counter()
    for row in top_candidates:
        if row["narrative_status"] == "found_relevant" and row["narrative_top_title"]:
            catalyst_titles[str(row["narrative_top_title"])] += 1
        if row["business_status"] == "found_relevant" and row["business_top_title"]:
            catalyst_titles[str(row["business_top_title"])] += 1

    best_watch_candidate = package.get("best_watch_candidate")
    lines.extend(
        [
            "",
            "## Catalyst Summary",
            f"- candidates_with_narrative_relevant: {sum(1 for row in top_candidates if row['narrative_status'] == 'found_relevant')}",
            f"- candidates_with_business_relevant: {sum(1 for row in top_candidates if row['business_status'] == 'found_relevant')}",
            f"- top_shared_titles: {json.dumps(catalyst_titles.most_common(5), ensure_ascii=False)}",
            "",
            "## Lifecycle Snapshot",
            f"- paper_review_candidates: {sum(1 for row in top_candidates if row['classification'] == 'CANDIDATE_FOR_PAPER_REVIEW')}",
            f"- market_watchlist_candidates: {sum(1 for row in top_candidates if row['classification'] == 'MARKET_WATCHLIST_NEEDS_EVIDENCE')}",
            f"- blocked_by_risk_candidates: {sum(1 for row in top_candidates if row['classification'] == 'BLOCKED_BY_RISK')}",
            f"- best_watch_candidate: {best_watch_candidate.get('symbol') if best_watch_candidate else 'none'}",
            f"- best_watch_reason: {best_watch_candidate.get('watch_reason') if best_watch_candidate else 'none'}",
            "",
            "## Evidence Gaps",
        ]
    )
    for row in top_candidates:
        lines.extend(
            [
                f"### {row['ticket_rank']}. {row['symbol']}",
                f"- company: {row['company_name']} ({row['company_name_source']})",
                f"- narrative query: {row['narrative_topic']}",
                f"- business query: {row['business_topic']}",
                f"- narrative ranked candidates: {row['narrative_ranked_candidate_count']} | status: {row['narrative_status']} | returncode: {row['narrative_returncode']}",
                f"- business ranked candidates: {row['business_ranked_candidate_count']} | status: {row['business_status']} | returncode: {row['business_returncode']}",
                f"- evidence gap reason: {row['evidence_gap_reason']}",
            ]
        )

    lines.extend(["", "## Quality Check (Buffett Skills)"])
    for row in top_candidates:
        qc = row.get("quality_check", {})
        lines.append(f"### {row['symbol']}: {qc.get('quality_verdict', 'N/A')} (score={qc.get('overall_quality_score', 0):.2f})")
        for dim, score in qc.get("scores", {}).items():
            lines.append(f"  - {dim}: {score:.2f}")

    lines.extend(["", "## Risk Checklist (UZI-Skill)"])
    for row in top_candidates:
        rc = row.get("risk_checklist", {})
        lines.append(f"### {row['symbol']}: {rc.get('risk_verdict', 'N/A')} (red={rc.get('red_count', 0)}, yellow={rc.get('yellow_count', 0)})")
        for check_name, check_data in rc.get("checks", {}).items():
            lines.append(f"  - {check_name}: [{check_data.get('flag', 'N/A')}] {check_data.get('detail', '')}")

    lines.extend(["", "## Research Panel (TradingAgents)"])
    for row in top_candidates:
        panel = row.get("research_panel", {})
        lines.append(f"### {row['symbol']}: {panel.get('panel_verdict', 'N/A')} (pos={panel.get('positive_signals', 0)}, neg={panel.get('negative_signals', 0)})")
        for agent_name, agent_data in panel.get("agents", {}).items():
            lines.append(f"  - {agent_name}: {agent_data.get('summary', '')}")

    lines.extend(["", "## Supply Chain Map (Serenity Skill)"])
    for row in top_candidates:
        sc = row.get("supply_chain_map", {})
        lines.append(f"- {row['symbol']}: {sc.get('supply_chain_summary', 'N/A')} | themes={sc.get('themes_found', [])}")

    lines.extend(["", "## Replay Hypothesis (QuantDinger)"])
    for row in top_candidates:
        rh = row.get("replay_hypothesis", {})
        lines.append(f"- {row['symbol']}: {rh.get('hypothesis', 'N/A')}")

    lines.extend(["", "## Risk Management (Cross-Platform Best Practices)"])
    for row in top_candidates:
        rr = row.get("risk_record", {})
        allowed_str = "ALLOWED" if rr.get("risk_allowed", True) else "BLOCKED"
        block = rr.get("risk_block_reason", "")
        sl = rr.get("stop_loss")
        tp = rr.get("take_profit")
        rr_ratio = rr.get("risk_reward_ratio")
        kelly = rr.get("kelly_fraction")
        score = rr.get("risk_score")
        conf = rr.get("confidence")
        lines.append(f"### {row['symbol']}: {allowed_str}")
        if block:
            lines.append(f"  - block_reason: {block}")
        lines.append(f"  - stop_loss: ${sl:.2f}" if sl else "  - stop_loss: N/A")
        lines.append(f"  - take_profit: ${tp:.2f}" if tp else "  - take_profit: N/A")
        lines.append(f"  - risk_reward: {rr_ratio:.2f}" if rr_ratio else "  - risk_reward: N/A")
        lines.append(f"  - kelly_fraction: {kelly:.3f}" if kelly else "  - kelly_fraction: N/A")
        lines.append(f"  - risk_score: {score:.2f}" if score else "  - risk_score: N/A")
        lines.append(f"  - confidence: {conf:.2f}" if conf else "  - confidence: N/A")

    lines.extend(
        [
            "",
            "## Forward Tracking",
            "|symbol|rank|horizon|due_date|status|",
            "|---|---|---|---|---|",
        ]
    )
    if package["forward_tracking_rows"]:
        for row in package["forward_tracking_rows"]:
            lines.append(
                "|{symbol}|{ticket_rank}|{review_window}|{due_date}|{check_status}|".format(
                    symbol=row["symbol"],
                    ticket_rank=row["ticket_rank"],
                    review_window=row["review_window"],
                    due_date=row["due_date"],
                    check_status=row["check_status"],
                )
            )
    else:
        lines.append("|-|-|-|-|no candidate rows passed the evidence gate|")

    regime_t = package.get("regime_thresholds")
    _eth = regime_t.exhaustion_threshold if regime_t else -0.15
    _eadj = regime_t.exhaustion_adjustment if regime_t else -0.08
    lines.extend(
        [
            "",
            "## Market Snapshot Top 10",
            f"- momentum_exhaustion_guard_threshold: {_eth}",
            f"- momentum_exhaustion_guard_adjustment: {_eadj}",
            "|rank|symbol|raw_market_score|market_score|rule|prior_20d|accel_5d|volume_confirm|closing_strength|vwmomentum|",
            "|---|---|---|---|---|---|---|---|---|---|",
        ]
    )
    for row in market_rows[:10]:
        lines.append(
            "|{market_rank}|{symbol}|{raw_market_score}|{market_score}|{market_rule_flags}|{prior_20d}|{accel_5d}|{volume_confirm}|{closing}|{vwm}|".format(
                market_rank=row["market_rank"],
                symbol=row["symbol"],
                raw_market_score=_safe_float(row["raw_market_score"]),
                market_score=_safe_float(row["market_score"]),
                market_rule_flags=row["market_rule_flags"] or "",
                prior_20d=_safe_float(row["prior_20d_momentum"]),
                accel_5d=_safe_float(row["five_day_acceleration"]),
                volume_confirm=_safe_float(row["volume_confirmation_ratio"]),
                closing=_safe_float(row.get("closing_strength_5d")),
                vwm=_safe_float(row.get("volume_weighted_momentum")),
            )
        )

    lines.append("")

    # Add Dynamic Horizon Allocation Report
    if package.get("dynamic_horizon_enabled"):
        allocations = package.get("horizon_allocations", {})
        if allocations:
            lines.extend([
                "## Dynamic Horizon Allocation (Volatility-Based)",
                f"- enabled: true",
                f"- total_symbols: {len(allocations)}",
                "",
                "| Symbol | Volatility | Category | Primary Horizon | Stop Loss | Take Profit | R:R |",
                "|--------|------------|----------|-----------------|-----------|-------------|-----|",
            ])
            for sym, alloc in sorted(allocations.items(), key=lambda x: x[1].volatility_pct, reverse=True)[:15]:
                lines.append(
                    f"| {sym} | {alloc.volatility_pct:.4f} | {alloc.vol_category} | "
                    f"{alloc.assigned_horizon}d | {alloc.stop_loss_pct:.1%} | {alloc.take_profit_pct:.1%} | "
                    f"{alloc.risk_reward_ratio:.1f} |"
                )
            lines.append("")

    lines.append("## Final Classification")
    lines.append(f"- {package['final_classification']}")
    return "\n".join(lines) + "\n"


def append_runtime_decision_ledger(ledger_path: Path, payload: dict[str, Any]) -> None:
    ledger_path.parent.mkdir(parents=True, exist_ok=True)
    with ledger_path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(serializable(payload), ensure_ascii=False) + "\n")



def save_outputs(package: dict[str, Any], output_date: str, save_db: bool = False) -> dict[str, Path]:
    run_root = output_root(package["run_name"])
    run_root.mkdir(parents=True, exist_ok=True)

    paths = artifact_paths(package["run_name"], output_date)
    summary_path = paths["summary"]
    metrics_path = paths["metrics"]
    candidates_path = paths["candidates"]
    tracking_path = paths["forward_tracking"]
    runtime_context_path = paths["runtime_context"]
    runtime_ledger_path = paths["runtime_ledger"]

    write_text(summary_path, build_summary_md(package, output_date))
    write_json(metrics_path, package["metrics"])
    write_csv(candidates_path, package["candidate_frame"])
    write_csv(tracking_path, package["tracking_frame"])
    write_json(runtime_context_path, package["runtime_decision_context"])
    append_runtime_decision_ledger(runtime_ledger_path, package["runtime_decision_ledger_entry"])
    capital_report_paths = write_daily_capital_report(
        RESEARCH_DIR,
        output_date,
        package.get("candidate_rows", []),
    )

    if save_db:
        try:
            import sys
            from pathlib import Path
            sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
            from scripts.db.engine import SessionLocal
            from scripts.db.pipeline_bridge import save_pipeline_to_db
            db = SessionLocal()
            db_counts = save_pipeline_to_db(
                db, output_date, package["metrics"],
                package.get("top_candidates", []),
                package.get("forward_tracking_rows", []),
                candidate_rows=package.get("candidate_rows", []),
            )
            db.close()
            learning_paths = write_capital_learning_artifacts(RESEARCH_DIR, output_date)
            print(json.dumps({"db_save": db_counts}, ensure_ascii=False), flush=True)
        except Exception as exc:
            print(json.dumps({"db_save_error": str(exc)}, ensure_ascii=False), flush=True)

    result = {**paths, "capital_json": capital_report_paths["json"], "capital_markdown": capital_report_paths["markdown"]}
    if save_db and "learning_paths" in locals():
        result.update({f"capital_learning_{key}": value for key, value in learning_paths.items()})
    return result


def emit_blocked_data_unavailable(args: argparse.Namespace, error: BlockedDataUnavailableError) -> None:
    print(
        json.dumps(
            {
                "status": "RESEARCH_ONLY",
                "run_status": "BLOCKED_DATA_UNAVAILABLE",
                "final_classification": "BLOCKED_DATA_UNAVAILABLE",
                "output_date": args.output_date,
                "universe_source": args.universe_source,
                "universe_key": args.universe_key,
                "no_broker": True,
                "no_order": True,
                "no_ledger": True,
                "no_live_trade": True,
                "no_buy_sell_wording": True,
                "allow_trade": False,
                "auto_order": False,
                "no_broker_api": True,
                "market_data_source": MARKET_DATA_SOURCE_DISPLAY,
                "kline_source": EASTMONEY_HISTORICAL_SOURCE_DISPLAY,
                "quote_source": QUOTE_SOURCE_DISPLAY,
                "error_type": error.error_type,
                "error_message": str(error),
                "cached_local_fallback_attempted": bool(error.cached_local_fallback_attempted),
                "artifact_write_policy": "preserve_existing_success_artifacts",
            },
            ensure_ascii=False,
        ),
        flush=True,
    )


class HelpFormatter(argparse.ArgumentDefaultsHelpFormatter, argparse.RawDescriptionHelpFormatter):
    pass


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Research-only US profit ticket pipeline for xiaomei.\n\n"
            "Boundary:\n"
            "- no broker\n"
            "- no order\n"
            "- no ledger\n"
            "- no live trade\n"
            "- no BUY/SELL wording\n\n"
            "Daily run writes reviewable artifacts for ticket/no-trade review."
        ),
        formatter_class=HelpFormatter,
        epilog=(
            "Artifacts:\n"
            f"- {RUN_ARTIFACT_FILENAMES['summary']}\n"
            f"- {RUN_ARTIFACT_FILENAMES['metrics']}\n"
            f"- {RUN_ARTIFACT_FILENAMES['candidates']}\n"
            f"- {RUN_ARTIFACT_FILENAMES['forward_tracking']}\n\n"
            "Daily output includes source mode, output date, universe controls, final classification, "
            "and artifact paths."
        ),
    )
    parser.add_argument("--universe-source", default=DEFAULT_UNIVERSE_SOURCE)
    parser.add_argument("--universe", nargs="+", default=None, help="Explicit ticker universe when --universe-source explicit is used.")
    parser.add_argument("--universe-key", default=DEFAULT_UNIVERSE_KEY)
    parser.add_argument("--run-name", default=DEFAULT_RUN_NAME)
    parser.add_argument("--period", default=None)
    parser.add_argument("--output-date", default=output_date_string())
    parser.add_argument("--sleep-seconds", type=float, default=0.5)
    parser.add_argument("--batch-size", type=int, default=DEFAULT_BATCH_SIZE)
    parser.add_argument("--min-history-days", type=int, default=DEFAULT_MIN_HISTORY_DAYS)
    parser.add_argument("--min-price", type=float, default=DEFAULT_MIN_PRICE)
    parser.add_argument("--min-median-dollar-volume", type=float, default=DEFAULT_MIN_MEDIAN_DOLLAR_VOLUME)
    parser.add_argument("--top-k", type=int, default=DEFAULT_TOP_K)
    parser.add_argument("--candidate-pool-size", type=int, default=DEFAULT_CANDIDATE_POOL_SIZE)
    parser.add_argument("--skip-last30days", action="store_true", help="Skip last30days evidence queries for faster output.")
    parser.add_argument("--save-db", action="store_true", help="Save pipeline outputs to PostgreSQL database.")
    parser.add_argument("--dynamic-horizon", action="store_true", default=True, help="Use dynamic horizon allocation based on volatility.")
    parser.add_argument("--no-dynamic-horizon", dest="dynamic_horizon", action="store_false", help="Disable dynamic horizon allocation.")
    return parser.parse_args(argv)


def main(argv: list[str]) -> int:
    args = parse_args(argv)
    if args.skip_last30days:
        global SKIP_LAST30DAYS
        SKIP_LAST30DAYS = True
    periods = [args.period] if args.period else list(DEFAULT_PERIODS)
    top_k = max(1, int(args.top_k))
    pool_size = max(top_k, int(args.candidate_pool_size))
    feedback = load_feedback()

    try:
        universe = choose_universe(
            universe_source_name=args.universe_source,
            explicit_universe=args.universe,
            universe_key=args.universe_key,
            periods=periods,
            sleep_seconds=args.sleep_seconds,
            batch_size=args.batch_size,
            min_history_days=args.min_history_days,
            min_price=args.min_price,
            min_median_dollar_volume=args.min_median_dollar_volume,
        )
        if universe["close_panel"].empty or universe["adj_panel"].empty or universe["long_panel"].empty:
            raise BlockedDataUnavailableError(
                "MARKET_DATA_PANEL_UNAVAILABLE",
                "unable to fetch usable Yahoo historical kline panel",
                universe.get("source_mode") == "cached_local",
            )
        actual_kline_source = universe.get("kline_source", EASTMONEY_HISTORICAL_SOURCE_DISPLAY)
        close_panel, adj_panel, long_panel = _enrich_panels_with_realtime(
            universe["close_panel"], universe["adj_panel"], universe["long_panel"],
            universe["included_symbols"],
        )
        universe["close_panel"] = close_panel
        universe["adj_panel"] = adj_panel
        universe["long_panel"] = long_panel
        previous_capital_states = load_previous_capital_states(universe["included_symbols"])
        market_snapshot = build_market_snapshot(
            close_panel,
            adj_panel,
            long_panel,
            universe["included_symbols"],
            feedback=feedback,
            kline_source=actual_kline_source,
            previous_capital_states=previous_capital_states,
        )
        feature_frame = market_snapshot["feature_frame"]
        market_rows = feature_frame.reset_index().to_dict(orient="records")
        candidate_rows: list[dict[str, Any]] = []
        regime_thresholds = market_snapshot.get("regime_thresholds")
        with ThreadPoolExecutor(max_workers=min(pool_size, 5)) as executor:
            futures = {
                executor.submit(
                    build_candidate_record,
                    row,
                    market_snapshot["as_of_date"],
                    pool_size,
                    feedback,
                    regime_thresholds,
                    actual_kline_source,
                ): row
                for row in market_rows[:pool_size]
            }
            for future in as_completed(futures):
                candidate_rows.append(future.result())
                time.sleep(0.05)

        sector_keywords = {
            "Technology": ["tech", "software", "semiconductor", "chip", "cloud", "cyber", "saas", "data", "digital", "ai", "network", "apple", "microsoft", "google", "meta", "nvidia", "amd", "intel", "cisco", "oracle", "salesforce", "adobe", "vmware", "paypal", "shopify", "zoom", "slack", "snowflake", "crowdstrike", "palo alto", "fortinet", "marvell", "broadcom", "qualcomm", "texas instruments", "micron", "applied materials", "lam research", "kla corp", "entegris", "on semiconductor", "analog devices", "xilinx", "altera"],
            "Healthcare": ["pharma", "bio", "medical", "health", "drug", "clinical", "diagnostic", "therapeutic", "unitedhealth", "cigna", "anthem", "aetna", "humana", "moderna", "pfizer", "johnson", "merck", "abbvie", "amgen", "gilead", "regeneron", "biogen", "vertex", "alnylam", "iqvia", "medtronic", "baxter", "becton", "abbott", "zimmer", "stryker", "medtronic", "edwards", "intuitive surgical"],
            "Financial": ["bank", "capital", "insurance", "financial", "securities", "investment", "credit", "jpmorgan", "goldman", "morgan stanley", "bank of america", "wells fargo", "citigroup", "visa", "mastercard", "american express", "blackrock", "schwab", "fidelity", "t rowe", "progressive", "allstate", "travelers", "chubb", "aon", "marsh"],
            "Consumer Cyclical": ["retail", "consumer", "ecommerce", "travel", "leisure", "restaurant", "hotel", "airline", "amazon", "tesla", "home depot", "lowes", "costco", "walmart", "target", "nordstrom", "macy", "kohls", "best buy", "starbucks", "mcdonald", "chipotle", "yum brands", "marriott", "hilton", "delta", "united airlines", "american airlines", "southwest", "expedia", "booking", "airbnb"],
            "Industrials": ["industrial", "manufacturing", "aerospace", "defense", "engineering", "construction", "transport", "caterpillar", "deere", "honeywell", "3m", "ge aerospace", "boeing", "lockheed", "raytheon", "northrop", "l3harris", "union pacific", "csx", "norfolk southern", "fedex", "ups", "uber", "lyft", "parker hannifin", "emerson", "rockwell", "eaton", "dover", "illinois tool", "fastenal", "waste management", "republic services"],
            "Energy": ["energy", "oil", "gas", "solar", "renewable", "battery", "nuclear", "exxon", "chevron", "conocophillips", "schlumberger", "halliburton", "nextera", "enphase", "first solar", "sunrun", "plug power", "bloom energy"],
            "Communication": ["media", "entertainment", "streaming", "telecom", "advertising", "content", "netflix", "disney", "comcast", "charter", "t-mobile", "verizon", "at&t", "alphabet", "meta platforms", "snap", "pinterest", "roku", "activision", "electronic arts", "take-two"],
            "Consumer Defensive": ["food", "beverage", "household", "staples", "personal care", "pepsico", "coca cola", "procter", "kimberly clark", "colgate", "general mills", "kellogg", "campbell soup", "smucker", "hormel", "tyson", "kraft heinz", "mondelez"],
            "Utilities": ["electric", "utility", "water", "gas utility", "dominion", "southern company", "duke energy", "nextera energy", "american electric", "xcel energy", "wec energy", "consolidated edison"],
            "Real Estate": ["reit", "property", "real estate", "trust", "prologis", "american tower", "crown castle", "equinix", "digital realty", "welltower", "public storage", "pei properties", "boston properties"],
            "Materials": ["mining", "chemical", "steel", "lithium", "material", "freeport mcmoran", "newmont", "nucor", "dow", "dupont", "linde", "air products", "eaton vance"],
        }
        sector_map = {}
        for sym in universe["included_symbols"]:
            name_lower = sym.lower()
            assigned = "Unknown"
            for sector, keywords in sector_keywords.items():
                if any(kw in name_lower for kw in keywords):
                    assigned = sector
                    break
            if assigned == "Unknown":
                assigned = "Technology" if sym in {"AAPL","MSFT","GOOGL","GOOG","AMZN","META","NVDA","TSLA","AVGO","CSCO","ORCL","CRM","ADBE","INTC","AMD","QCOM","TXN","INTU","NOW","AMAT","LRCX","KLAC","ADI","MRVL","SNPS","CDNS","FTNT","PANW","CRWD","ZS","DDOG","NET","SNOW","COIN","SHOP","SQ","PYPL","ROKU","UBER","LYFT","ABNB","NFLX","DIS","CHTR","TMUS","VZ","T","CMCSA"} else "Unknown"
            sector_map[sym] = assigned

        evidence_summaries = {}
        for row in candidate_rows:
            sym = row["symbol"]
            narr = row.get("narrative_evidence", {}) or {}
            biz = row.get("business_evidence", {}) or {}
            evidence_summaries[sym] = {
                "source_diversity": max(narr.get("source_diversity", 0), biz.get("source_diversity", 0)),
                "cluster_count": max(narr.get("cluster_count", 0), biz.get("cluster_count", 0)),
                "ranked_candidate_count": max(narr.get("ranked_candidate_count", 0), biz.get("ranked_candidate_count", 0)),
                "relevance_score": max(narr.get("relevance_score", 0.0), biz.get("relevance_score", 0.0)),
            }

        sector_evidence_density = {}
        if sector_map:
            sector_counts: dict[str, int] = {}
            sector_relevant: dict[str, int] = {}
            for sym, ev in evidence_summaries.items():
                sector = sector_map.get(sym, "Unknown")
                sector_counts[sector] = sector_counts.get(sector, 0) + 1
                if ev.get("relevance_score", 0) > 0.3:
                    sector_relevant[sector] = sector_relevant.get(sector, 0) + 1
            for sector in sector_counts:
                total = sector_counts[sector]
                relevant = sector_relevant.get(sector, 0)
                sector_evidence_density[sector] = relevant / total if total > 0 else 0.0

        def _news_quality_score(sym: str) -> float:
            ev = evidence_summaries.get(sym, {})
            source_div = min(1.0, ev.get("source_diversity", 0) / 3.0)
            cluster_bonus = min(0.3, ev.get("cluster_count", 0) * 0.1)
            candidate_bonus = min(0.3, ev.get("ranked_candidate_count", 0) * 0.05)
            relevance = ev.get("relevance_score", 0.0)
            return min(1.0, source_div * 0.3 + cluster_bonus + candidate_bonus + relevance * 0.4)

        for row in candidate_rows:
            row["news_evidence_status"] = (
                "OBSERVED"
                if max(
                    float((row.get("narrative_evidence") or {}).get("relevance_score", 0) or 0),
                    float((row.get("business_evidence") or {}).get("relevance_score", 0) or 0),
                ) > 0
                else "UNAVAILABLE"
            )
            row["market_score_decay"] = 0.0
            row["contrarian_penalty"] = 0.0

        candidate_rows = sorted(
            candidate_rows,
            key=lambda row: (row["ticket_score"], row["market_score"], row["volume_confirmation_ratio"]),
            reverse=True,
        )

        # Filter out weak candidates below minimum score threshold
        pre_filter_count = len(candidate_rows)
        candidate_rows = [r for r in candidate_rows if r.get("ticket_score", 0) >= MIN_TICKET_SCORE]
        if len(candidate_rows) < pre_filter_count:
            print(f"[SELECT] Filtered {pre_filter_count - len(candidate_rows)} candidates below MIN_TICKET_SCORE={MIN_TICKET_SCORE}")

        for index, row in enumerate(candidate_rows, start=1):
            row["ticket_rank"] = int(index)

        top_candidates = candidate_rows[:top_k]
        best_watch_candidate = build_best_watch_candidate(candidate_rows)
        forward_tracking_rows = build_forward_tracking_rows(
            [
                row
                for row in top_candidates
                if row["classification"] in {
                    "CANDIDATE_FOR_PAPER_REVIEW",
                    "MARKET_WATCHLIST_NEEDS_EVIDENCE",
                }
            ],
            args.output_date,
            close_panel=close_panel,
            dynamic_horizon=True,
        )
        tracking_frame = pd.DataFrame(
            forward_tracking_rows,
            columns=[
                "symbol",
                "ticket_rank",
                "market_rank",
                "as_of_date",
                "horizon_days",
                "due_date",
                "review_window",
                "check_status",
                "track_key",
                "as_of_close",
                "as_of_adj_close",
                "kline_source",
                "quote_source",
                "quote_cross_check_gap_pct",
                "data_source_mismatch",
                "market_score",
                "catalyst_score",
                "ticket_score",
                "research_only",
                "allow_trade",
                "auto_order",
                "no_broker_api",
                "classification",
                "risk_allowed",
                "risk_stop_loss",
                "risk_take_profit",
                "risk_reward_ratio",
                "risk_position_size_pct",
                "risk_kelly_fraction",
                "risk_score",
                *CAPITAL_CANDIDATE_FIELDS,
            ],
        )
        candidate_frame = pd.DataFrame(
            [
                {
                    "symbol": row["symbol"],
                    "company_name": row["company_name"],
                    "company_name_source": row["company_name_source"],
                    "company_query_name": row["company_query_name"],
                    "ticket_rank": int(row["ticket_rank"]),
                    "market_rank": int(row["market_rank"]),
                    "as_of_date": row["as_of_date"],
                    "close": row["close"],
                    "adj_close": row["adj_close"],
                    "volume": row["volume"],
                    "market_data_source": row["market_data_source"],
                    "kline_source": row["kline_source"],
                    "quote_source": row["quote_source"],
                    "quote_source_status": row["quote_source_status"],
                    "quote_cross_check_basis": row["quote_cross_check_basis"],
                    "quote_cross_check_price": row["quote_cross_check_price"],
                    "quote_cross_check_gap_pct": row["quote_cross_check_gap_pct"],
                    "data_source_mismatch": row["data_source_mismatch"],
                    "data_source_mismatch_reason": row["data_source_mismatch_reason"],
                    "latest_price": row["latest_price"],
                    "prev_close": row["prev_close"],
                    "intraday_pct_chg": row["intraday_pct_chg"],
                    "pe_ttm": row["pe_ttm"],
                    "roe": row["roe"],
                    "dividend_yield": row["dividend_yield"],
                    "raw_market_score": row["raw_market_score"],
                    "market_score": row["market_score"],
                    "large_participant_footprint_score": row.get("large_participant_footprint_score"),
                    "footprint_factor_coverage": row.get("footprint_factor_coverage"),
                    "footprint_factor_contributions": row.get("footprint_factor_contributions"),
                    "market_participation_score": row.get("market_participation_score"),
                    "market_rule_flags": row["market_rule_flags"],
                    "market_rule_adjustment": row["market_rule_adjustment"],
                    "catalyst_score": row["catalyst_score"],
                     "ticket_score": row["ticket_score"],
                     "news_quality_score": row.get("news_quality_score", 0.0),
                     "sector_propagation_bonus": row.get("sector_propagation_bonus", 0.0),
                     "contrarian_penalty": row.get("contrarian_penalty", 0.0),
                    **{field: row.get(field) for field in CAPITAL_CANDIDATE_FIELDS},
                    "distribution_risk": row.get("distribution_score"),
                    "trap_risk": row.get("trap_score"),
                     "lifecycle_stage": candidate_lifecycle_stage(row),
                     "research_only": row["research_only"],
                     "allow_trade": row["allow_trade"],

                    "auto_order": row["auto_order"],
                    "no_broker_api": row["no_broker_api"],
                    "prior_5d_momentum": row["prior_5d_momentum"],
                    "prior_20d_momentum": row["prior_20d_momentum"],
                    "five_day_acceleration": row["five_day_acceleration"],
                    "relative_strength_vs_equal_weight": row["relative_strength_vs_equal_weight"],
                    "volume_confirmation_ratio": row["volume_confirmation_ratio"],
                    "median_dollar_volume_20d": row["median_dollar_volume_20d"],
                    "closing_strength_5d": row.get("closing_strength_5d"),
                    "volume_weighted_momentum": row.get("volume_weighted_momentum"),
                    "volume_trend_20d": row.get("volume_trend_20d"),
                    "risk_penalty": row.get("risk_penalty", 0.0),
                    "market_evidence_pass": row["market_evidence_pass"],
                    "strongest_relevance": row["strongest_relevance"],
                    "narrative_status": row["narrative_status"],
                    "narrative_source_diversity": row["narrative_source_diversity"],
                    "narrative_cluster_count": row["narrative_cluster_count"],
                    "narrative_ranked_candidate_count": row["narrative_ranked_candidate_count"],
                    "narrative_top_title": row["narrative_top_title"],
                    "narrative_top_score": row["narrative_top_score"],
                    "narrative_relevance_score": row["narrative_relevance_score"],
                    "narrative_relevance_reason": row["narrative_relevance_reason"],
                    "business_status": row["business_status"],
                    "business_source_diversity": row["business_source_diversity"],
                    "business_cluster_count": row["business_cluster_count"],
                    "business_ranked_candidate_count": row["business_ranked_candidate_count"],
                    "business_top_title": row["business_top_title"],
                    "business_top_score": row["business_top_score"],
                    "business_relevance_score": row["business_relevance_score"],
                    "business_relevance_reason": row["business_relevance_reason"],
                    "narrative_topic": row["narrative_topic"],
                    "narrative_returncode": row["narrative_returncode"],
                    "business_topic": row["business_topic"],
                    "business_returncode": row["business_returncode"],
                    "catalyst_summary": row["catalyst_summary"],
                    "risk_summary": row["risk_summary"],
                    "watchlist_pass": row["watchlist_pass"],
                    "evidence_gate_status": row["evidence_gate_status"],
                    "evidence_gate_pass": row["evidence_gate_pass"],
                    "evidence_gap_reason": row["evidence_gap_reason"],
                    "evidence_gate_reason": row["evidence_gate_reason"],
                    "classification": row["classification"],
                    "risk_allowed": row.get("risk_allowed", True),
                    "risk_block_reason": row.get("risk_block_reason", ""),
                    "risk_stop_loss": row.get("risk_stop_loss"),
                    "risk_take_profit": row.get("risk_take_profit"),
                    "risk_reward_ratio": row.get("risk_reward_ratio"),
                    "risk_position_size_pct": row.get("risk_position_size_pct"),
                    "risk_kelly_fraction": row.get("risk_kelly_fraction"),
                    "risk_score": row.get("risk_score"),
                    "risk_confidence": row.get("risk_confidence"),
                    "forward_1d": row["forward_dates"]["1d"],
                    "forward_3d": row["forward_dates"]["3d"],
                    "forward_10d": row["forward_dates"]["10d"],
                    "evidence_note": row["evidence_note"],
                }
                for row in candidate_rows
            ]
        )

        top_candidate_classifications = {row["classification"] for row in top_candidates}
        if "CANDIDATE_FOR_PAPER_REVIEW" in top_candidate_classifications:
            final_classification = "CANDIDATE_FOR_PAPER_REVIEW"
        elif "MARKET_WATCHLIST_NEEDS_EVIDENCE" in top_candidate_classifications:
            final_classification = "MARKET_WATCHLIST_NEEDS_EVIDENCE"
        else:
            final_classification = "NEED_MORE_EVIDENCE"
        classification_counts = Counter(row["classification"] for row in top_candidates)
        artifact_paths_map = artifact_paths(args.run_name, args.output_date)
        zero_paper_review_is_valid_output = int(classification_counts.get("CANDIDATE_FOR_PAPER_REVIEW", 0)) == 0
        runtime_decision_context = build_runtime_decision_context(
            top_candidates,
            final_classification,
            market_snapshot["market_summary"],
            best_watch_candidate,
        )
        runtime_decision_ledger_entry = {
            "record_type": "RUNTIME_DECISION",
            "generated_at": pd.Timestamp.now(tz="Asia/Shanghai").isoformat(),
            "output_date": args.output_date,
            "run_name": args.run_name,
            "as_of_date": market_snapshot["market_summary"]["as_of_date"],
            "final_classification": final_classification,
            "paper_review_count": int(classification_counts.get("CANDIDATE_FOR_PAPER_REVIEW", 0)),
            "market_watchlist_count": int(classification_counts.get("MARKET_WATCHLIST_NEEDS_EVIDENCE", 0)),
            "best_watch_candidate": None if not best_watch_candidate else best_watch_candidate.get("symbol"),
            "top_candidates": [
                {
                    "symbol": row["symbol"],
                    "ticket_rank": int(row["ticket_rank"]),
                    "classification": row["classification"],
                    "lifecycle_stage": candidate_lifecycle_stage(row),
                    "ticket_score": row["ticket_score"],
                    "market_score": row["market_score"],
                    "evidence_gate_status": row["evidence_gate_status"],
                    "risk_allowed": row.get("risk_allowed", True),
                }
                for row in top_candidates
            ],
        }
        package = {
            "run_name": args.run_name,
            "source_config": universe["source_config"],
            "source_mode": universe["source_mode"],
            "data_mode": universe.get("data_mode", "historical_kline"),
            "selected_universe_key": universe["selected_universe_key"],
            "source_universe_total_symbols": int(len(universe["selected_universe"])),
            "source_universe_included_symbols": int(len(universe["included_symbols"])),
            "period_used": universe["period_used"],
            "source_universe_minimum_required_symbols": int(universe["minimum_required_symbols"]),
            "source_universe_quality_filter": {
                "min_history_days": int(args.min_history_days),
                "min_price": float(args.min_price),
                "min_median_dollar_volume": float(args.min_median_dollar_volume),
            },
            "attempts": universe["attempts"],
            "failures": universe["failures"],
            "market_summary": market_snapshot["market_summary"],
            "regime": market_snapshot.get("regime"),
            "regime_thresholds": market_snapshot.get("regime_thresholds"),
            "market_rows": market_rows,
            "candidate_rows": candidate_rows,
            "top_candidates": top_candidates,
            "best_watch_candidate": best_watch_candidate,
            "forward_tracking_rows": forward_tracking_rows,
            "final_classification": final_classification,
            "top_candidate_classification_counts": dict(classification_counts),
            "selected_universe": universe["included_symbols"],
            "runtime_decision_context": runtime_decision_context,
            "runtime_decision_ledger_entry": runtime_decision_ledger_entry,
            "paper_review_count": int(classification_counts.get("CANDIDATE_FOR_PAPER_REVIEW", 0)),
            "market_watchlist_count": int(classification_counts.get("MARKET_WATCHLIST_NEEDS_EVIDENCE", 0)),
            "evidence_missing_count": int(
                sum(1 for row in top_candidates if row["classification"] != "CANDIDATE_FOR_PAPER_REVIEW")
            ),
            "artifact_paths": {key: str(value) for key, value in artifact_paths_map.items()},
            "zero_paper_review_is_valid_output": bool(zero_paper_review_is_valid_output),
            "feedback_applied": feedback is not None,
            "feedback_win_rate": feedback.get("win_rate") if feedback else None,
            "feedback_symbol_penalties": list(feedback.get("symbol_penalties", {}).keys()) if feedback else [],
            "dynamic_horizon_enabled": True,
            "horizon_allocations": batch_assign_horizons(close_panel, [row["symbol"] for row in top_candidates]) if close_panel is not None and not close_panel.empty else {},
        }
        regime_snapshot = market_snapshot.get("regime")
        metrics = {
            "task": "XIAOMEI_US_PROFIT_TICKET_PIPELINE_V0",
            "generated_at": pd.Timestamp.now(tz="Asia/Shanghai").isoformat(),
            "output_date": args.output_date,
            "run_name": args.run_name,
            "run_group": args.run_name,
            "as_of_date": market_snapshot["market_summary"]["as_of_date"],
            "target_session": market_snapshot["market_summary"].get("target_session"),
            "actual_previous_trading_session": market_snapshot["market_summary"].get("actual_previous_trading_session"),
            "pipeline_execution_time": market_snapshot["market_summary"].get("pipeline_execution_time"),
            "session_status": market_snapshot["market_summary"].get("session_status"),
            "status": "RESEARCH_ONLY",
            "final_classification": final_classification,
            "run_category": "pipeline",
            "regime": getattr(regime_snapshot, "name", None),
            "regime_source": "market_snapshot",
            "regime_breadth": getattr(regime_snapshot, "breadth", None),
            "regime_momentum": getattr(regime_snapshot, "momentum", None),
            "regime_volatility": getattr(regime_snapshot, "volatility", None),
            "regime_advance_ratio": getattr(regime_snapshot, "advance_ratio", None),
            "data_mode": universe.get("data_mode", "historical_kline"),
            "strategy_version": "observable_footprint_v1",
            "strategy_definition": (
                "public price-volume footprint, catalyst evidence, market participation, "
                "and explicit risk penalties; no verified institutional-flow inference"
            ),
            "not_trading_advice": True,
            "market_data_source": MARKET_DATA_SOURCE_DISPLAY,
            "kline_source": actual_kline_source,
            "quote_source": QUOTE_SOURCE_DISPLAY,
            "data_source_mismatch_threshold": DATA_SOURCE_MISMATCH_THRESHOLD,
            "no_broker": True,
            "no_order": True,
            "no_ledger": True,
            "no_live_trade": True,
            "no_buy_sell_wording": True,
            "allow_trade": False,
            "auto_order": False,
            "no_broker_api": True,
            "source_config": universe["source_config"],
            "source_mode": universe["source_mode"],
            "selected_universe_key": universe["selected_universe_key"],
            "source_universe_total_symbols": int(len(universe["selected_universe"])),
            "source_universe_included_symbols": int(len(universe["included_symbols"])),
            "period_used": universe["period_used"],
            "candidate_pool_size": int(pool_size),
            "top_k": int(top_k),
            "paper_review_count": int(classification_counts.get("CANDIDATE_FOR_PAPER_REVIEW", 0)),
            "market_watchlist_count": int(classification_counts.get("MARKET_WATCHLIST_NEEDS_EVIDENCE", 0)),
            "evidence_missing_count": int(
                sum(1 for row in top_candidates if row["classification"] != "CANDIDATE_FOR_PAPER_REVIEW")
            ),
            "zero_paper_review_is_valid_output": bool(zero_paper_review_is_valid_output),
            "market_summary": market_snapshot["market_summary"],
            "candidate_rows": [
                {
                    key: serializable(value)
                    for key, value in row.items()
                    if key not in {"narrative_raw", "business_raw"}
                }
                for row in candidate_rows
            ],
            "top_candidates": [
                {
                    key: serializable(value)
                    for key, value in row.items()
                    if key not in {"narrative_raw", "business_raw"}
                }
                for row in top_candidates
            ],
            "forward_tracking_rows": [serializable(row) for row in forward_tracking_rows],
            "attempts": serializable(universe["attempts"]),
            "failures": serializable(universe["failures"]),
            "methodology_references": METHODOLOGY_REFERENCES,
            "market_snapshot_top10": [
                {key: serializable(value) for key, value in row.items()}
                for row in market_rows[:10]
            ],
            "top_candidate_classification_counts": dict(classification_counts),
            "narrative_queries": [
                {
                    "symbol": row["symbol"],
                    "company_name": row["company_name"],
                    "topic": row["narrative_topic"],
                    "evidence": serializable(row["narrative_evidence"]),
                }
                for row in candidate_rows
            ],
            "business_queries": [
                {
                    "symbol": row["symbol"],
                    "company_name": row["company_name"],
                    "topic": row["business_topic"],
                    "evidence": serializable(row["business_evidence"]),
                }
                for row in candidate_rows
            ],
            "selected_universe": universe["included_symbols"],
            "selected_universe_dropped": universe["excluded_symbols"],
        }
        package["metrics"] = metrics
        package["candidate_frame"] = candidate_frame
        package["tracking_frame"] = tracking_frame
        paths = save_outputs(package, args.output_date, save_db=args.save_db)
    except BlockedDataUnavailableError as exc:
        emit_blocked_data_unavailable(args, exc)
        return 2
    except Exception as exc:  # noqa: BLE001
        raise RuntimeError(f"profit-ticket pipeline failed: {exc}") from exc

    print(
        json.dumps(
            {
                "status": "RESEARCH_ONLY",
                "run_status": "SUCCESS",
                "source_mode": universe["source_mode"],
                "data_mode": universe.get("data_mode", "historical_kline"),
                "market_data_source": MARKET_DATA_SOURCE_DISPLAY,
                "kline_source": actual_kline_source,
                "quote_source": QUOTE_SOURCE_DISPLAY,
                "universe_source": universe["source_config"]["source_name"],
                "universe_key": universe["selected_universe_key"],
                "output_date": args.output_date,
                "final_classification": final_classification,
                "as_of_date": market_snapshot["market_summary"]["as_of_date"],
                "target_session": market_snapshot["market_summary"].get("target_session"),
                "actual_previous_trading_session": market_snapshot["market_summary"].get("actual_previous_trading_session"),
                "pipeline_execution_time": market_snapshot["market_summary"].get("pipeline_execution_time"),
                "session_status": market_snapshot["market_summary"].get("session_status"),
             "top_candidates": [row["symbol"] for row in top_candidates],
             "best_watch_candidate": best_watch_candidate["symbol"] if best_watch_candidate else None,
             "candidate_pool_size": int(pool_size),

                "top_k": int(top_k),
                "paper_review_count": int(classification_counts.get("CANDIDATE_FOR_PAPER_REVIEW", 0)),
                "market_watchlist_count": int(classification_counts.get("MARKET_WATCHLIST_NEEDS_EVIDENCE", 0)),
                "zero_paper_review_is_valid_output": bool(zero_paper_review_is_valid_output),
                "paths": {key: str(value) for key, value in paths.items()},
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
