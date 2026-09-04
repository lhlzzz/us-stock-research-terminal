"""SEC EDGAR ingestion. Parser emits facts only; never a production pick."""
from __future__ import annotations

import json
from typing import Any, Iterable, Mapping

from .boundary import PRODUCTION_BOUNDARY, assert_research_only
from .evidence import content_hash, research_evidence, utc_now
from .providers import DATA_GAP, record_provider_attempt
from .temporal import historical_claim_eligible, temporal_record

SEC_FORMS = ("10-K", "10-Q", "8-K", "DEF 14A", "13D", "13G", "3", "4", "5")
AMENDMENT_SUFFIX = "/A"
FORM_ALIASES = {
    "FORM 3": "3",
    "FORM 4": "4",
    "FORM 5": "5",
    "3": "3",
    "4": "4",
    "5": "5",
}
XBRL_CONCEPTS = {
    "revenue": (
        "RevenueFromContractWithCustomerExcludingAssessedTax",
        "Revenues",
        "SalesRevenueNet",
    ),
    "gross_profit": ("GrossProfit",),
    "operating_income": ("OperatingIncomeLoss",),
    "net_income": ("NetIncomeLoss",),
    "operating_cash_flow": ("NetCashProvidedByUsedInOperatingActivities",),
    "capex": ("PaymentsToAcquirePropertyPlantAndEquipment",),
    "cash": ("CashAndCashEquivalentsAtCarryingValue",),
    "debt": ("LongTermDebt", "LongTermDebtNoncurrent"),
    "shares": ("CommonStockSharesOutstanding", "EntityCommonStockSharesOutstanding"),
    "diluted_shares": ("WeightedAverageNumberOfDilutedSharesOutstanding",),
    "sbc": ("AllocatedShareBasedCompensationExpense", "ShareBasedCompensation"),
    "buyback": ("PaymentsForRepurchaseOfCommonStock", "StockRepurchasedDuringPeriodValue"),
    "rpo": ("RevenueRemainingPerformanceObligation",),
    "backlog": ("ContractWithCustomerLiability",),
    "eps_diluted": ("EarningsPerShareDiluted",),
}
PARSER_FIELDS = (
    "revenue", "gross_profit", "operating_income", "net_income", "fcf",
    "cash", "debt", "shares", "sbc", "buyback", "guidance", "segment",
    "customer_concentration", "backlog", "rpo",
)


def normalize_form(form: str | None) -> str | None:
    if form in (None, ""):
        return None
    text = str(form).strip().upper().replace("FORM ", "")
    return FORM_ALIASES.get(text, text)


def is_amendment(form: str | None) -> bool:
    label = normalize_form(form) or ""
    return label.endswith(AMENDMENT_SUFFIX)


def original_form(form: str | None) -> str | None:
    label = normalize_form(form)
    if not label:
        return None
    return label[:-2] if label.endswith(AMENDMENT_SUFFIX) else label


def filing_source_url(cik: str | int | None, accession: str | None, primary: str | None = None) -> str | None:
    if not cik or not accession:
        return None
    padded = str(int(str(cik).replace("CIK", ""))).zfill(10)
    accn = str(accession).replace("-", "")
    if primary:
        return f"https://www.sec.gov/Archives/edgar/data/{int(padded)}/{accn}/{primary}"
    return f"https://www.sec.gov/Archives/edgar/data/{int(padded)}/{accn}/"


def sec_raw_document(
    *,
    source_url: str | None,
    retrieved_at: str | None = None,
    published_at: str | None = None,
    effective_date: str | None = None,
    form: str | None = None,
    accession_number: str | None = None,
    cik: str | None = None,
    symbol: str | None = None,
    raw_payload: Mapping[str, Any] | None = None,
    document_id: str | None = None,
    company_name: str | None = None,
    filing_date: str | None = None,
    period_of_report: str | None = None,
    acceptance_datetime: str | None = None,
) -> dict[str, Any]:
    payload = dict(raw_payload or {})
    hashed = content_hash(payload)
    return {
        "document_id": document_id or hashed[:16],
        "source_url": source_url,
        "retrieved_at": retrieved_at or utc_now(),
        "content_hash": hashed,
        "published_at": published_at or filing_date,
        "effective_date": effective_date or published_at or filing_date,
        "form": normalize_form(form),
        "accession_number": accession_number,
        "cik": None if cik in (None, "") else str(cik).zfill(10),
        "symbol": None if symbol in (None, "") else str(symbol).upper(),
        "company_name": company_name,
        "filing_date": filing_date,
        "period_of_report": period_of_report,
        "acceptance_datetime": acceptance_datetime,
        "raw_payload": payload,
        "immutable": True,
        "produces_pick": False,
        "production_boundary": PRODUCTION_BOUNDARY,
    }


def _as_of_ok(value: str | None, as_of: str | None) -> bool:
    if not as_of:
        return True
    if not value:
        return False
    return str(value)[:10] <= str(as_of)[:10]


def filings_as_of(filings: Iterable[Mapping[str, Any]] | None, *, as_of: str) -> list[dict[str, Any]]:
    visible = []
    for row in filings or []:
        payload = dict(row)
        published = payload.get("published_at") or payload.get("filing_date") or payload.get("acceptance_datetime")
        available = payload.get("available_at") or published
        gate = historical_claim_eligible(
            {
                "published_at": published,
                "effective_date": payload.get("effective_date") or published,
                "available_at": available,
                "retrieved_at": payload.get("retrieved_at"),
            },
            as_of=as_of,
        )
        payload["temporal"] = gate
        payload["as_of"] = as_of
        if not gate["eligible"]:
            payload["replay_status"] = "DO_NOT_USE_IN_HISTORICAL_REPLAY"
            continue
        visible.append(payload)
    return visible


def resolve_amendments(filings: Iterable[Mapping[str, Any]] | None, *, as_of: str) -> list[dict[str, Any]]:
    """Keep every version. Select the latest version already public as_of."""
    visible = filings_as_of(filings, as_of=as_of)
    groups: dict[tuple[str, str], list[dict[str, Any]]] = {}
    for row in visible:
        form = original_form(row.get("form") or row.get("filing_type"))
        period = str(row.get("period_of_report") or row.get("reportDate") or row.get("period_end") or "")
        groups.setdefault((form or "", period), []).append(row)
    selected = []
    for rows in groups.values():
        ordered = sorted(
            rows,
            key=lambda item: (
                str(item.get("acceptance_datetime") or item.get("filing_date") or item.get("published_at") or ""),
                1 if is_amendment(item.get("form") or item.get("filing_type")) else 0,
            ),
        )
        latest = ordered[-1]
        superseded = ordered[:-1]
        latest = dict(latest)
        latest["supersedes"] = [
            item.get("accession_number") or item.get("document_id")
            for item in superseded
        ]
        latest["versions_retained"] = len(ordered)
        latest["silent_overwrite"] = False
        selected.append(latest)
        for item in superseded:
            copy = dict(item)
            copy["superseded_by"] = latest.get("accession_number") or latest.get("document_id")
            copy["selected"] = False
            selected.append(copy)
        latest["selected"] = True
    return selected


def xbrl_fact_record(concept: str, unit: str, row: Mapping[str, Any], *, taxonomy: str = "us-gaap") -> dict[str, Any]:
    return {
        "concept": concept,
        "taxonomy": taxonomy,
        "unit": unit,
        "value": row.get("val"),
        "period": row.get("end") or row.get("instant"),
        "start": row.get("start"),
        "frame": row.get("frame"),
        "form": row.get("form"),
        "filed": row.get("filed"),
        "accn": row.get("accn"),
        "fy": row.get("fy"),
        "fp": row.get("fp"),
    }


def iter_xbrl_facts(companyfacts: Mapping[str, Any] | None) -> list[dict[str, Any]]:
    facts = []
    root = dict(companyfacts or {}).get("facts") or companyfacts or {}
    if not isinstance(root, Mapping):
        return facts
    for taxonomy, concepts in root.items():
        if not isinstance(concepts, Mapping):
            continue
        for concept, node in concepts.items():
            units = (node or {}).get("units") or {}
            for unit, rows in units.items():
                for row in rows or []:
                    facts.append(xbrl_fact_record(concept, unit, row, taxonomy=taxonomy))
    return facts


def xbrl_facts_as_of(facts: Iterable[Mapping[str, Any]] | None, *, as_of: str) -> list[dict[str, Any]]:
    visible = []
    for row in facts or []:
        filed = str(row.get("filed") or "")[:10]
        if not _as_of_ok(filed, as_of):
            continue
        visible.append(dict(row))
    return visible


def resolve_fact_conflicts(facts: Iterable[Mapping[str, Any]] | None, *, as_of: str) -> dict[str, Any]:
    visible = xbrl_facts_as_of(facts, as_of=as_of)
    groups: dict[tuple[Any, Any, Any], list[dict[str, Any]]] = {}
    for row in visible:
        key = (row.get("concept"), row.get("period"), row.get("unit"))
        groups.setdefault(key, []).append(row)
    selected = []
    retained = []
    for rows in groups.values():
        ordered = sorted(rows, key=lambda item: str(item.get("filed") or ""))
        latest = dict(ordered[-1])
        latest["supersedes"] = [item.get("accn") for item in ordered[:-1] if item.get("accn") != latest.get("accn")]
        latest["silent_overwrite"] = False
        selected.append(latest)
        for item in ordered:
            copy = dict(item)
            copy["selected"] = copy.get("accn") == latest.get("accn") and copy.get("filed") == latest.get("filed")
            retained.append(copy)
    return {
        "as_of": as_of,
        "selected": selected,
        "all_evidence": retained,
        "conflict_count": sum(1 for rows in groups.values() if len(rows) > 1),
        "silent_overwrite": False,
        "produces_pick": False,
    }


def parse_sec_facts(facts: Iterable[Mapping[str, Any]] | None, *, as_of: str) -> dict[str, Any]:
    resolved = resolve_fact_conflicts(facts, as_of=as_of)
    by_concept: dict[str, list[dict[str, Any]]] = {}
    for row in resolved["selected"]:
        concept = row.get("concept")
        if concept:
            by_concept.setdefault(str(concept), []).append(row)
    parsed: dict[str, Any] = {}
    gaps = []
    for field, concepts in XBRL_CONCEPTS.items():
        match = None
        candidates = []
        for concept in concepts:
            candidates.extend(by_concept.get(concept) or [])
        candidates = [row for row in candidates if row.get("value") not in (None, "")]
        if candidates:
            match = sorted(candidates, key=lambda item: (str(item.get("filed") or ""), str(item.get("period") or "")))[-1]
        if match is None:
            parsed[field] = None
            gaps.append(field)
        else:
            parsed[field] = {
                "value": match.get("value"),
                "concept": match.get("concept"),
                "unit": match.get("unit"),
                "period": match.get("period"),
                "frame": match.get("frame"),
                "form": match.get("form"),
                "filed": match.get("filed"),
                "accn": match.get("accn"),
                "fy": match.get("fy"),
                "fp": match.get("fp"),
                "semantic": "OBSERVED",
            }
    ocf = parsed.get("operating_cash_flow")
    capex = parsed.get("capex")
    if ocf and capex and ocf.get("value") is not None and capex.get("value") is not None:
        parsed["fcf"] = {
            "value": float(ocf["value"]) - abs(float(capex["value"])),
            "semantic": "DERIVED",
            "derived_from": [ocf.get("concept"), capex.get("concept")],
        }
    else:
        parsed["fcf"] = None
        if "fcf" not in gaps:
            gaps.append("fcf")
    for name in ("guidance", "segment", "customer_concentration"):
        if parsed.get(name) in (None, ""):
            parsed[name] = None
            if name not in gaps:
                gaps.append(name)
    return {
        "as_of": as_of,
        "fields": parsed,
        "data_gaps": gaps,
        "status": "OBSERVED" if any(parsed.get(name) for name in PARSER_FIELDS) else DATA_GAP,
        "produces_pick": False,
        "production_boundary": PRODUCTION_BOUNDARY,
        "conflicts": resolved,
    }


def submissions_to_filings(submissions: Mapping[str, Any], *, symbol: str | None = None) -> list[dict[str, Any]]:
    company = submissions.get("name")
    cik = submissions.get("cik")
    tickers = submissions.get("tickers") or []
    ticker = symbol or (tickers[0] if tickers else None)
    recent = (submissions.get("filings") or {}).get("recent") or {}
    forms = recent.get("form") or []
    rows = []
    for index, form in enumerate(forms):
        accession = (recent.get("accessionNumber") or [None] * len(forms))[index]
        filing_date = (recent.get("filingDate") or [None] * len(forms))[index]
        report_date = (recent.get("reportDate") or [None] * len(forms))[index]
        accepted = (recent.get("acceptanceDateTime") or [None] * len(forms))[index]
        primary = (recent.get("primaryDocument") or [None] * len(forms))[index]
        normalized = normalize_form(form)
        if original_form(normalized) not in SEC_FORMS and normalized not in {item + AMENDMENT_SUFFIX for item in SEC_FORMS}:
            continue
        rows.append({
            "filing_id": accession,
            "accession_number": accession,
            "form": normalized,
            "filing_type": normalized,
            "filing_date": filing_date,
            "period_of_report": report_date,
            "period_end": report_date,
            "acceptance_datetime": accepted,
            "published_at": str(accepted or filing_date or "")[:10],
            "effective_date": str(filing_date or accepted or "")[:10],
            "available_at": str(accepted or filing_date or "")[:10],
            "company": company,
            "company_name": company,
            "cik": None if cik in (None, "") else str(cik).zfill(10),
            "ticker": None if ticker in (None, "") else str(ticker).upper(),
            "symbol": None if ticker in (None, "") else str(ticker).upper(),
            "primary_document": primary,
            "source_url": filing_source_url(cik, accession, primary),
            "source": "sec_edgar",
        })
    return rows


def sec_research_bundle(
    *,
    symbol: str,
    as_of: str,
    submissions: Mapping[str, Any] | None = None,
    companyfacts: Mapping[str, Any] | None = None,
    retrieved_at: str | None = None,
    status: str = "OBSERVED",
    error: str | None = None,
) -> dict[str, Any]:
    ticker = str(symbol).upper()
    if status in {DATA_GAP, "ERROR"} or submissions in (None, {}):
        payload = {
            "symbol": ticker,
            "as_of": as_of,
            "status": status if status in {DATA_GAP, "ERROR"} else DATA_GAP,
            "reason": error or "sec submissions not ingested",
            "filings": [],
            "documents": [],
            "facts": [],
            "parsed": {"status": DATA_GAP, "fields": {}, "data_gaps": list(PARSER_FIELDS)},
            "produces_pick": False,
            "production_boundary": PRODUCTION_BOUNDARY,
        }
        assert_research_only(payload)
        return payload
    filings = submissions_to_filings(submissions, symbol=ticker)
    documents = [
        sec_raw_document(
            source_url=row.get("source_url"),
            retrieved_at=retrieved_at,
            published_at=row.get("published_at"),
            effective_date=row.get("effective_date"),
            form=row.get("form"),
            accession_number=row.get("accession_number"),
            cik=row.get("cik"),
            symbol=ticker,
            raw_payload=row,
            company_name=row.get("company_name"),
            filing_date=row.get("filing_date"),
            period_of_report=row.get("period_of_report"),
            acceptance_datetime=row.get("acceptance_datetime"),
        )
        for row in filings
    ]
    visible_docs = []
    blocked_docs = []
    for doc in documents:
        gate = historical_claim_eligible(doc, as_of=as_of)
        if gate["eligible"]:
            visible_docs.append(doc)
        else:
            blocked_docs.append({**doc, "replay_status": "DO_NOT_USE_IN_HISTORICAL_REPLAY", "temporal": gate})
    versions = resolve_amendments(filings, as_of=as_of)
    xbrl = iter_xbrl_facts(companyfacts)
    parsed = parse_sec_facts(xbrl, as_of=as_of)
    evidence = [
        research_evidence(
            symbol=ticker,
            as_of=as_of,
            published_at=doc.get("published_at"),
            effective_date=doc.get("effective_date"),
            available_at=doc.get("published_at"),
            retrieved_at=doc.get("retrieved_at"),
            source="sec_edgar",
            source_type="sec_filing",
            source_url=doc.get("source_url"),
            document_id=doc.get("document_id"),
            status="OBSERVED",
            level="LEVEL_1",
            raw_hash=doc.get("content_hash"),
            facts={"form": doc.get("form"), "accession_number": doc.get("accession_number")},
        )
        for doc in visible_docs
    ]
    payload = {
        "symbol": ticker,
        "as_of": as_of,
        "status": "OBSERVED" if visible_docs else DATA_GAP,
        "cik": (submissions or {}).get("cik"),
        "company_name": (submissions or {}).get("name"),
        "sic": (submissions or {}).get("sic"),
        "sic_description": (submissions or {}).get("sicDescription"),
        "filings": versions,
        "documents": visible_docs,
        "blocked_documents": blocked_docs,
        "xbrl_facts": xbrl_facts_as_of(xbrl, as_of=as_of),
        "parsed": parsed,
        "evidence": evidence,
        "temporal": temporal_record(as_of=as_of, retrieved_at=retrieved_at),
        "produces_pick": False,
        "production_boundary": PRODUCTION_BOUNDARY,
    }
    record_provider_attempt(
        provider="sec_edgar",
        request="sec_research_bundle",
        symbol=ticker,
        as_of=as_of,
        status=payload["status"],
        source="sec_edgar",
    )
    assert_research_only(payload)
    return payload
