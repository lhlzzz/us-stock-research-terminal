"""Obsidian research memory. Personal holdings never change market alpha."""
from __future__ import annotations

import hashlib
import json
import re
from datetime import date, datetime
from pathlib import Path
from typing import Any, Iterable, Mapping


TICKER_RE = re.compile(r"\b([A-Z]{1,5})(?:[:/]US)?\b")
POSITION_RE = re.compile(
    r"(持仓|持有|owned|position|watchlist|观察|thesis|买入|卖出|catalyst|管理层|估值|风险)",
    re.IGNORECASE,
)
HOLDING_RE = re.compile(r"(持仓|持有|\bowned\b|\bholding\b|\bposition\b)", re.IGNORECASE)
WATCH_RE = re.compile(r"(watchlist|观察名单|\bwatching\b|\bwatch\b)", re.IGNORECASE)
DATE_RE = re.compile(r"(20\d{2}-\d{2}-\d{2})")
NOTE_KINDS = ("holding", "watching", "mention", "research_target", "benchmark")
TICKER_STOP = {
    "US", "AI", "CEO", "IPO", "ETF", "SEC", "FDA", "GDP", "THE", "AND", "FOR",
    "README", "TODO", "USD", "USA", "NYSE", "NASDAQ", "AMEX", "GAAP", "IFRS",
    "EPS", "YOY", "QOQ", "TTM", "CAGR", "EBIT", "EBITDA", "FCF", "ROE", "ROA",
    "ROIC", "PE", "PEG", "EV", "ATM", "OTM", "ITM", "IV", "OI", "CPI", "PCE",
    "FED", "FOMC", "IMF", "WTO", "OECD", "ISO", "API", "GPU", "CPU", "HBM",
    "TSMC", "FAQ", "NOTE", "RISK", "CASH",
}
CORE_US_TICKERS = {
    "AAPL", "MSFT", "NVDA", "AMZN", "GOOGL", "GOOG", "META", "TSLA", "AVGO",
    "AMD", "AMAT", "TSM", "MU", "INTC", "QCOM", "ARM", "ASML", "LRCX", "KLAC",
    "SNPS", "CDNS", "ADI", "TXN", "MRVL", "SMCI", "DELL", "HPQ", "IBM", "ORCL",
    "CRM", "NOW", "SNOW", "PLTR", "PANW", "CRWD", "NET", "DDOG", "ADBE", "INTU",
    "NFLX", "DIS", "CMCSA", "T", "VZ", "JPM", "BAC", "WFC", "GS", "MS", "C",
    "V", "MA", "AXP", "BRK", "UNH", "JNJ", "LLY", "PFE", "MRK", "ABBV", "TMO",
    "XOM", "CVX", "COP", "CAT", "DE", "GE", "HON", "BA", "LMT", "RTX", "NOC",
    "COST", "WMT", "HD", "TGT", "NKE", "SBUX", "MCD", "KO", "PEP", "PG", "CL",
    "STX", "WDC", "KDP", "IR", "ANET", "CSCO", "AVGO", "NXPI", "ON", "MPWR",
}

DEFAULT_VAULTS = (
    Path("/mnt/d/obisidian/Obsidian/Project"),
    Path("/mnt/d/obisidian/Obsidian/神临"),
)


def _as_date(value: Any) -> date | None:
    if value in (None, ""):
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    text = str(value)[:10]
    try:
        return date.fromisoformat(text)
    except ValueError:
        return None


def parse_frontmatter(content: str) -> dict[str, Any]:
    metadata: dict[str, Any] = {}
    if not content.startswith("---"):
        return metadata
    end = content.find("---", 3)
    if end < 0:
        return metadata
    for line in content[3:end].splitlines():
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        metadata[key.strip()] = value.strip().strip('"').strip("'")
    return metadata


def document_dates(path: Path | None, content: str, metadata: Mapping[str, Any] | None = None, *, created_at: Any = None, updated_at: Any = None) -> dict[str, str | None]:
    meta = dict(metadata or {})
    if content and not meta:
        meta = parse_frontmatter(content)
    source_date = _as_date(meta.get("source_date") or meta.get("date") or meta.get("as_of"))
    effective = _as_date(meta.get("effective_date") or meta.get("as_of_date") or source_date)
    created = _as_date(created_at or meta.get("created_at") or meta.get("created"))
    updated = _as_date(updated_at or meta.get("updated_at") or meta.get("updated"))
    if path is not None:
        name_match = DATE_RE.search(path.name)
        if name_match and effective is None:
            effective = _as_date(name_match.group(1))
        if created is None:
            try:
                created = datetime.fromtimestamp(path.stat().st_ctime).date()
            except OSError:
                created = None
        if updated is None:
            try:
                updated = datetime.fromtimestamp(path.stat().st_mtime).date()
            except OSError:
                updated = None
    if effective is None:
        body_match = DATE_RE.search(content or "")
        if body_match:
            source_date = source_date or _as_date(body_match.group(1))
    return {
        "document_created_at": created.isoformat() if created else None,
        "document_updated_at": updated.isoformat() if updated else None,
        "effective_date": effective.isoformat() if effective else None,
        "source_date": source_date.isoformat() if source_date else None,
        "as_of_date": (effective or source_date or created).isoformat() if (effective or source_date or created) else None,
        "replay_eligible": bool(effective is not None),
    }


def portfolio_concentration(
    owned: Iterable[str] | None = None,
    weights: Mapping[str, Any] | None = None,
    *,
    sectors: Mapping[str, str] | None = None,
    themes: Mapping[str, str] | None = None,
    cash: float | None = None,
) -> dict[str, Any]:
    symbols = [str(item).upper() for item in owned or [] if str(item).upper() not in {"CASH", ""}]
    raw = {str(k).upper(): v for k, v in dict(weights or {}).items()}
    numeric: dict[str, float] = {}
    for symbol, value in raw.items():
        try:
            number = float(value)
        except (TypeError, ValueError):
            continue
        if number != number:
            continue
        numeric[symbol] = number
    if cash is not None:
        try:
            numeric["CASH"] = float(cash)
        except (TypeError, ValueError):
            pass
    has_weights = any(symbol in numeric for symbol in symbols)
    if not has_weights:
        return {
            "symbol_count": len(symbols),
            "position_count": len(symbols),
            "position_weight": "UNKNOWN",
            "portfolio_weight": "UNKNOWN",
            "sector_weight": "UNKNOWN",
            "theme_weight": "UNKNOWN",
            "top_position": "UNKNOWN",
            "top3_concentration": "UNKNOWN",
            "sector_concentration": "UNKNOWN",
            "theme_concentration": "UNKNOWN",
            "forged_equal_weight": False,
        }
    ordered = sorted(((symbol, numeric.get(symbol, 0.0)) for symbol in symbols), key=lambda item: item[1], reverse=True)
    top = ordered[0][1] if ordered else None
    top3 = sum(item[1] for item in ordered[:3]) if ordered else None
    sector_weights: dict[str, float] = {}
    theme_weights: dict[str, float] = {}
    for symbol, value in ordered:
        sector = str((sectors or {}).get(symbol) or "UNKNOWN")
        theme = str((themes or {}).get(symbol) or "UNKNOWN")
        sector_weights[sector] = sector_weights.get(sector, 0.0) + value
        theme_weights[theme] = theme_weights.get(theme, 0.0) + value
    return {
        "symbol_count": len(symbols),
        "position_count": len(symbols),
        "position_weight": {symbol: numeric.get(symbol, "UNKNOWN") for symbol in symbols},
        "portfolio_weight": dict(numeric),
        "sector_weight": sector_weights or "UNKNOWN",
        "theme_weight": theme_weights or "UNKNOWN",
        "top_position": top,
        "top3_concentration": top3,
        "sector_concentration": max(sector_weights.values()) if sector_weights else "UNKNOWN",
        "theme_concentration": max(theme_weights.values()) if theme_weights else "UNKNOWN",
        "forged_equal_weight": False,
    }


def recognized_ticker(symbol: str, universe: Iterable[str] | None = None) -> bool:
    token = str(symbol or "").upper()
    if not token or token in TICKER_STOP:
        return False
    extra = {str(item).upper() for item in universe or []}
    return token in CORE_US_TICKERS or token in extra


def extract_tickers(text: str, universe: Iterable[str] | None = None) -> list[str]:
    found = []
    for match in TICKER_RE.findall(text or ""):
        if match in TICKER_STOP or match in found:
            continue
        if not recognized_ticker(match, universe):
            continue
        found.append(match)
    return found


def _note_kind_from_metadata(metadata: Mapping[str, Any] | None) -> str | None:
    meta = dict(metadata or {})
    kind = str(meta.get("kind") or meta.get("note_kind") or "").strip().lower().replace(" ", "_")
    if kind in {"holding", "owned", "position"}:
        return "holding"
    if kind in {"watching", "watchlist", "watch"}:
        return "watching"
    if kind in {"research_target", "research", "thesis"}:
        return "research_target"
    if kind in {"benchmark", "index"}:
        return "benchmark"
    if kind in {"mention"}:
        return "mention"
    return None


def classify_note(path: str, content: str, metadata: Mapping[str, Any] | None = None) -> dict[str, Any]:
    meta = dict(metadata or {})
    if content and not meta:
        meta = parse_frontmatter(content)
    text = f"{path}\n{content}"
    lower = text.lower()
    kinds = []
    mapping = (
        ("position", ("持仓", "持有", "position", "owned")),
        ("watchlist", ("watchlist", "观察名单", "观察")),
        ("thesis", ("thesis", "买入逻辑", "投资逻辑")),
        ("sell_logic", ("卖出逻辑", "sell thesis", "减仓")),
        ("risk", ("风险", "risk")),
        ("catalyst", ("catalyst", "催化")),
        ("management", ("管理层", "management")),
        ("valuation", ("估值", "valuation", "pe")),
        ("industry", ("行业", "赛道", "产业链")),
        ("event", ("重要事件", "earnings", "财报")),
        ("note", ("个人备注", "备注")),
    )
    for kind, needles in mapping:
        if any(needle in lower for needle in needles):
            kinds.append(kind)
    meta_ticker = str(meta.get("ticker") or meta.get("symbol") or "").upper() or None
    tickers = extract_tickers(text)
    if meta_ticker and recognized_ticker(meta_ticker) and meta_ticker not in tickers:
        tickers.insert(0, meta_ticker)
    note_kind = _note_kind_from_metadata(meta)
    if note_kind is None:
        if HOLDING_RE.search(text) and tickers:
            note_kind = "holding"
        elif WATCH_RE.search(text) and tickers:
            note_kind = "watching"
        elif any(kind in kinds for kind in ("thesis", "catalyst", "valuation", "industry")):
            note_kind = "research_target"
        elif tickers:
            note_kind = "mention"
        else:
            note_kind = "mention"
    return {
        "kinds": kinds or ["unclassified"],
        "tickers": tickers,
        "note_kind": note_kind,
        "metadata_ticker": meta_ticker,
        "personal": any(kind in {"position", "watchlist", "thesis", "note"} for kind in kinds) or note_kind in {"holding", "watching"},
    }


def ingest_note(
    *,
    path: str,
    content: str,
    created_at: Any = None,
    updated_at: Any = None,
    metadata: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    dates = document_dates(Path(path) if path else None, content, metadata, created_at=created_at, updated_at=updated_at)
    classified = classify_note(path, content, metadata)
    return {
        "source_path": path,
        "title": next((line[2:].strip() for line in content.splitlines() if line.startswith("# ")), Path(path).stem),
        "content_hash": hashlib.sha256(content.encode("utf-8")).hexdigest(),
        **dates,
        **classified,
        "source": "obsidian",
        "source_type": "obsidian",
    }


def filter_obsidian_as_of(notes: Iterable[Mapping[str, Any]], as_of: date | str, *, historical: bool = True) -> list[dict[str, Any]]:
    """Historical replay may only use notes with proven effective_date <= as_of."""
    cutoff = _as_date(as_of)
    visible = []
    for note in notes:
        payload = dict(note)
        effective = _as_date(payload.get("effective_date"))
        if historical:
            if effective is None:
                payload["replay_use"] = "DO_NOT_USE_IN_HISTORICAL_REPLAY"
                continue
            if cutoff is not None and effective > cutoff:
                payload["replay_use"] = "DO_NOT_USE_IN_HISTORICAL_REPLAY"
                continue
            payload["replay_use"] = "OK"
        else:
            payload["replay_use"] = "LIVE_OK"
        visible.append(payload)
    return visible


def portfolio_context(
    notes: Iterable[Mapping[str, Any]],
    *,
    as_of: date | str | None = None,
    symbol: str | None = None,
    historical: bool | None = None,
) -> dict[str, Any]:
    """Personal holdings as context. Never a market-score increment."""
    scoped = list(notes)
    if as_of is not None:
        use_historical = True if historical is None else historical
        scoped = filter_obsidian_as_of(scoped, as_of, historical=use_historical)
    owned = []
    watch = []
    mentions = []
    theses = []
    industries: dict[str, int] = {}
    weights: dict[str, float] = {}
    for note in scoped:
        tickers = [item.upper() for item in note.get("tickers") or []]
        kinds = set(note.get("kinds") or [])
        note_kind = str(note.get("note_kind") or "")
        if note_kind == "holding" or "position" in kinds:
            owned.extend(tickers)
        elif note_kind == "watching" or "watchlist" in kinds:
            watch.extend(tickers)
        else:
            mentions.extend(tickers)
        if "thesis" in kinds or note_kind == "research_target":
            theses.append({"path": note.get("source_path"), "tickers": tickers, "title": note.get("title")})
        weight = note.get("position_weight") or note.get("weight")
        try:
            if weight not in (None, "", "UNKNOWN"):
                for ticker in tickers:
                    weights[ticker] = float(weight)
        except (TypeError, ValueError):
            pass
        for industry in note.get("industries") or []:
            industries[str(industry)] = industries.get(str(industry), 0) + 1
    owned_unique = sorted(set(owned))
    watch_unique = sorted(set(watch) - set(owned_unique))
    mention_unique = sorted(set(mentions) - set(owned_unique) - set(watch_unique))
    target = (symbol or "").upper() or None
    already_owned = bool(target and target in owned_unique)
    same_sector = False
    if target:
        for note in scoped:
            if target in [item.upper() for item in note.get("tickers") or []] and "industry" in (note.get("kinds") or []):
                same_sector = True
    relevance = "NEW_EXPOSURE"
    if already_owned:
        relevance = "PORTFOLIO_RELEVANCE"
    elif same_sector:
        relevance = "PORTFOLIO_CONCENTRATION_RISK"
    concentration = portfolio_concentration(owned_unique, weights)
    flags = []
    if already_owned:
        flags.append("PORTFOLIO_RELEVANCE")
        top = concentration.get("top_position")
        if isinstance(top, (int, float)) and top >= 0.25:
            flags.append("PORTFOLIO_CONCENTRATION_RISK")
    if same_sector:
        flags.append("PORTFOLIO_CONCENTRATION_RISK")
    if target and any(target in (item.get("tickers") or []) for item in theses):
        flags.append("EXISTING_THESIS")
    if not flags:
        flags.append("NEW_EXPOSURE")
    return {
        "context_type": "PERSONAL_PORTFOLIO_CONTEXT",
        "not_market_research": True,
        "does_not_change_alpha": True,
        "owned_symbols": owned_unique,
        "watchlist_symbols": watch_unique,
        "mentioned_symbols": mention_unique,
        "position_size": None,
        "entry_context": [note.get("source_path") for note in scoped if "position" in (note.get("kinds") or [])],
        "personal_thesis": theses,
        "conviction": None,
        "portfolio_exposure": owned_unique,
        "industry_exposure": industries,
        "existing_risk": [note.get("source_path") for note in scoped if "risk" in (note.get("kinds") or [])],
        "existing_notes": [note.get("source_path") for note in scoped],
        "last_updated": max((note.get("document_updated_at") or "") for note in scoped) if scoped else None,
        "already_owned": already_owned,
        "current_thesis": next((item for item in theses if not target or target in item["tickers"]), None),
        "concentration": concentration,
        "top_position": concentration.get("top_position"),
        "top3_concentration": concentration.get("top3_concentration"),
        "flags": flags,
        "relevance": relevance,
        "market_alpha_adjustment": 0,
    }


def ingest_obsidian_assets(rows: Iterable[Mapping[str, Any]]) -> list[dict[str, Any]]:
    ingested = []
    for row in rows:
        ingested.append(
            ingest_note(
                path=str(row.get("source_path") or row.get("path") or ""),
                content=str(row.get("content") or ""),
                created_at=row.get("created_at"),
                updated_at=row.get("updated_at"),
                metadata=row.get("metadata") if isinstance(row.get("metadata"), Mapping) else {},
            )
        )
    return ingested


def scan_obsidian_vault(roots: Iterable[Path] | None = None) -> list[dict[str, Any]]:
    """Read existing US-equity notes. Prefer vault files over inventing a new library."""
    notes = []
    for root in roots or DEFAULT_VAULTS:
        root = Path(root)
        if not root.exists():
            continue
        targets = []
        for relative in ("美股", "xiaomei-trades"):
            candidate = root / relative
            if candidate.exists():
                targets.append(candidate)
        for target in targets or [root]:
            for path in target.rglob("*.md"):
                rel = str(path.relative_to(root)).lower()
                if not targets and ("xiaomei" not in rel and "美股" not in rel):
                    continue
                try:
                    content = path.read_text(encoding="utf-8", errors="replace")
                except OSError:
                    continue
                notes.append(ingest_note(path=str(path), content=content))
    return notes


def load_knowledge_assets(conn) -> list[dict[str, Any]]:
    from sqlalchemy import text

    rows = conn.execute(text(
        "SELECT source_path, title, content, metadata, created_at, updated_at FROM knowledge_assets"
    )).mappings()
    notes = []
    for row in rows:
        metadata = row.get("metadata") or {}
        if isinstance(metadata, str):
            try:
                metadata = json.loads(metadata)
            except json.JSONDecodeError:
                metadata = {}
        notes.append(
            ingest_note(
                path=str(row.get("source_path") or ""),
                content=str(row.get("content") or ""),
                created_at=row.get("created_at"),
                updated_at=row.get("updated_at"),
                metadata=metadata,
            )
        )
    return notes
