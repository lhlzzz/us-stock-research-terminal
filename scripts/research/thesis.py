"""Thesis ledger, failure library, calibration, attribution, similarity."""
from __future__ import annotations

from typing import Any, Iterable, Mapping

from .boundary import PRODUCTION_BOUNDARY
from .evidence import observed_number

FAILURE_CLASSES = (
    "FALSE_BREAKOUT", "CATALYST_FAILURE", "DISTRIBUTION", "EARNINGS_MISS",
    "GUIDANCE_CUT", "LIQUIDITY_TRAP", "SHORT_PRESSURE", "VALUATION_TRAP",
    "THESIS_BREAK", "REGIME_MISMATCH",
)
THESIS_COMPARE = ("CONFLICT", "CONFIRM", "UPDATE")
SIMILARITY_DIMENSIONS = (
    "company", "industry", "setup", "capital", "thesis", "failure",
)


def thesis_ledger(facts: Mapping[str, Any] | None = None) -> dict[str, Any]:
    facts = dict(facts or {})
    return {
        "symbol": facts.get("symbol"),
        "thesis": facts.get("thesis"),
        "anti_thesis": facts.get("anti_thesis"),
        "invalidation": facts.get("invalidation"),
        "confidence": facts.get("confidence"),
        "entry_reason": facts.get("entry_reason"),
        "exit_reason": facts.get("exit_reason"),
        "change_log": list(facts.get("change_log") or []),
        "as_of": facts.get("as_of") or facts.get("as_of_date"),
        "produces_pick": False,
        "production_boundary": PRODUCTION_BOUNDARY,
    }


def compare_thesis(old: Mapping[str, Any] | None, new_evidence: Mapping[str, Any] | None) -> dict[str, Any]:
    old = dict(old or {})
    evidence = dict(new_evidence or {})
    old_text = str(old.get("thesis") or "")
    new_text = str(evidence.get("thesis") or old_text)
    if not old_text:
        status = "UPDATE"
    elif evidence.get("conflicts"):
        status = "CONFLICT"
    elif new_text == old_text:
        status = "CONFIRM"
    else:
        status = "UPDATE"
    log = list(old.get("change_log") or [])
    log.append({"status": status, "evidence": evidence.get("evidence"), "as_of": evidence.get("as_of")})
    return {
        "status": status,
        "old_thesis": old_text or None,
        "new_thesis": new_text or None,
        "change_log": log,
        "allowed": list(THESIS_COMPARE),
        "production_boundary": PRODUCTION_BOUNDARY,
    }


def thesis_learning(row: Mapping[str, Any] | None = None) -> dict[str, Any]:
    row = dict(row or {})
    predicted = row.get("prediction")
    outcome = row.get("outcome")
    failed = predicted is not None and outcome is not None and predicted != outcome
    return {
        "thesis": row.get("thesis"),
        "prediction": predicted,
        "outcome": outcome,
        "error": row.get("error") if failed else None,
        "thesis_failure_modes": list(row.get("failure_modes") or []) if failed else [],
        "not_just_ticket_return": True,
        "production_boundary": PRODUCTION_BOUNDARY,
    }


def failure_case(row: Mapping[str, Any] | None = None) -> dict[str, Any]:
    row = dict(row or {})
    klass = str(row.get("failure_reason") or row.get("class") or "").upper()
    if klass not in FAILURE_CLASSES:
        klass = None
    return {
        "failure_case": row.get("failure_case") or row.get("symbol"),
        "failure_reason": klass,
        "brain_at_entry": row.get("brain_at_entry"),
        "what_changed": row.get("what_changed"),
        "early_warning": row.get("early_warning"),
        "missed_signal": row.get("missed_signal"),
        "classes": list(FAILURE_CLASSES),
        "status": "DATA_GAP" if klass is None else "READY",
        "production_boundary": PRODUCTION_BOUNDARY,
    }


def similar_failures(query: Mapping[str, Any], library: Iterable[Mapping[str, Any]]) -> dict[str, Any]:
    reason = str((query or {}).get("failure_reason") or "").upper()
    matches = [dict(item) for item in library if str(item.get("failure_reason") or "").upper() == reason]
    return {
        "query": reason or None,
        "matches": matches,
        "count": len(matches),
        "question": "有没有以前犯过类似错误？",
        "production_boundary": PRODUCTION_BOUNDARY,
    }


def calibrate_brain(name: str, rows: Iterable[Mapping[str, Any]]) -> dict[str, Any]:
    buckets: dict[str, dict[str, float]] = {}
    for row in rows:
        conf = observed_number(row.get("confidence"))
        hit = row.get("hit")
        if conf is None or hit is None:
            continue
        bucket = f"{round(conf, 1):.1f}"
        item = buckets.setdefault(bucket, {"n": 0, "hits": 0})
        item["n"] += 1
        item["hits"] += 1 if hit else 0
    table = []
    errors = []
    for bucket, item in sorted(buckets.items()):
        actual = round(item["hits"] / item["n"], 4) if item["n"] else None
        expected = float(bucket)
        error = None if actual is None else round(abs(actual - expected), 4)
        if error is not None:
            errors.append(error)
        table.append({
            "confidence_bucket": bucket,
            "actual_hit_rate": actual,
            "calibration_error": error,
            "n": int(item["n"]),
        })
    return {
        "brain": name,
        "buckets": table,
        "mean_calibration_error": round(sum(errors) / len(errors), 4) if errors else None,
        "status": "VALIDATION_GAP" if not table else "READY",
        "production_boundary": PRODUCTION_BOUNDARY,
    }


def research_similarity(left: Mapping[str, Any], right: Mapping[str, Any]) -> dict[str, Any]:
    scores = {}
    for dim in SIMILARITY_DIMENSIONS:
        a = left.get(dim)
        b = right.get(dim)
        scores[dim] = 1.0 if a not in (None, "") and a == b else 0.0 if a and b else None
    usable = [value for value in scores.values() if value is not None]
    return {
        "dimensions": scores,
        "not_text_only": True,
        "composite": round(sum(usable) / len(usable), 4) if usable else None,
        "production_boundary": PRODUCTION_BOUNDARY,
    }


def attribution(row: Mapping[str, Any] | None = None) -> dict[str, Any]:
    row = dict(row or {})
    parts = {
        "company": observed_number(row.get("company_contribution") or row.get("alpha_from_company")),
        "industry": observed_number(row.get("industry_contribution") or row.get("alpha_from_industry")),
        "capital": observed_number(row.get("capital_contribution") or row.get("alpha_from_capital")),
        "market": observed_number(row.get("market_contribution") or row.get("alpha_from_market")),
        "event": observed_number(row.get("catalyst_contribution") or row.get("alpha_from_event")),
    }
    present = {key: value for key, value in parts.items() if value is not None}
    return {
        "company_contribution": parts["company"],
        "industry_contribution": parts["industry"],
        "capital_contribution": parts["capital"],
        "market_contribution": parts["market"],
        "catalyst_contribution": parts["event"],
        "alpha_from_company": parts["company"],
        "alpha_from_industry": parts["industry"],
        "alpha_from_capital": parts["capital"],
        "alpha_from_market": parts["market"],
        "alpha_from_event": parts["event"],
        "status": "VALIDATION_GAP" if not present else "READY",
        "production_boundary": PRODUCTION_BOUNDARY,
    }
