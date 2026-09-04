"""Thesis ledger, failure library, calibration, attribution, similarity."""
from __future__ import annotations

from typing import Any, Iterable, Mapping

from .boundary import PRODUCTION_BOUNDARY
from .evidence import observed_number

FAILURE_CLASSES = (
    "FALSE_BREAKOUT", "CATALYST_FAILURE", "DISTRIBUTION", "EARNINGS_MISS",
    "GUIDANCE_CUT", "LIQUIDITY_TRAP", "SHORT_PRESSURE", "VALUATION_TRAP",
    "THESIS_BREAK", "REGIME_MISMATCH",
    "THESIS_FAILURE", "TIMING_FAILURE", "DATA_FAILURE", "VALUATION_FAILURE",
    "CAPITAL_BEHAVIOR_FAILURE", "INDUSTRY_ASSUMPTION_FAILURE", "RISK_UNDERESTIMATION",
)
THESIS_FIELDS = (
    "company", "industry", "catalyst", "capital_behavior", "valuation", "risk", "evidence", "confidence",
)
THESIS_DIFF = ("ADDED", "REMOVED", "CHANGED", "UNCHANGED", "CONTRADICTED")
THESIS_COMPARE = ("CONFLICT", "CONFIRM", "UPDATE", *THESIS_DIFF)
SIMILARITY_DIMENSIONS = (
    "company", "industry", "setup", "capital", "thesis", "failure",
)
SIMILARITY_COMPONENTS = (
    "ticker", "industry", "thesis", "factor", "market_regime", "capital_behavior", "outcome",
)
FAILURE_MEMORY: list[dict[str, Any]] = []
CONTRADICTION_PAIRS = {
    ("cheap", "expensive"), ("cheap", "rich"), ("cheap", "dear"),
    ("undervalued", "overvalued"), ("bullish", "bearish"),
    ("accumulation", "distribution"), ("strong", "weak"),
}


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


def _thesis_structure(payload: Mapping[str, Any] | None) -> dict[str, Any]:
    payload = dict(payload or {})
    nested = payload.get("thesis")
    if isinstance(nested, Mapping):
        source = dict(nested)
    else:
        source = dict(payload)
    structured = {}
    for field in THESIS_FIELDS:
        value = source.get(field)
        if value in (None, ""):
            continue
        structured[field] = value
    if not structured and nested not in (None, ""):
        structured["company"] = nested
    return structured


def _contradicted(old: Any, new: Any) -> bool:
    a = str(old or "").strip().lower()
    b = str(new or "").strip().lower()
    if not a or not b or a == b:
        return False
    pair = tuple(sorted((a, b)))
    if pair in {tuple(sorted(item)) for item in CONTRADICTION_PAIRS}:
        return True
    if a.startswith("not ") and a[4:] == b:
        return True
    if b.startswith("not ") and b[4:] == a:
        return True
    return False


def compare_thesis(old: Mapping[str, Any] | None, new_evidence: Mapping[str, Any] | None) -> dict[str, Any]:
    old = dict(old or {})
    evidence = dict(new_evidence or {})
    old_struct = _thesis_structure(old)
    new_struct = _thesis_structure(evidence)
    if not new_struct and not evidence:
        new_struct = old_struct
    fields: dict[str, str] = {}
    all_keys = list(dict.fromkeys([*old_struct, *new_struct, *THESIS_FIELDS]))
    for field in all_keys:
        before = old_struct.get(field)
        after = new_struct.get(field)
        if before in (None, "") and after in (None, ""):
            continue
        if before in (None, "") and after not in (None, ""):
            fields[field] = "ADDED"
        elif before not in (None, "") and after in (None, ""):
            fields[field] = "REMOVED"
        elif _contradicted(before, after) or (evidence.get("conflicts") and field in {"valuation", "risk", "company"} and before != after):
            fields[field] = "CONTRADICTED"
        elif before != after:
            fields[field] = "CHANGED"
        else:
            fields[field] = "UNCHANGED"
    old_text = str(old.get("thesis") or "")
    new_text = str(evidence.get("thesis") or old_text)
    if evidence.get("conflicts") or "CONTRADICTED" in fields.values():
        status = "CONFLICT"
    elif not old_struct and new_struct:
        status = "UPDATE"
    elif fields and all(value == "UNCHANGED" for value in fields.values()):
        status = "CONFIRM"
    elif not old_text and not old_struct:
        status = "UPDATE"
    elif new_text == old_text and (not fields or all(value == "UNCHANGED" for value in fields.values())):
        status = "CONFIRM"
    else:
        status = "UPDATE"
    log = list(old.get("change_log") or [])
    log.append({"status": status, "fields": fields, "evidence": evidence.get("evidence"), "as_of": evidence.get("as_of")})
    return {
        "status": status,
        "old_thesis": old_text or old_struct or None,
        "new_thesis": new_text or new_struct or None,
        "fields": fields,
        "diff": fields,
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


def similar_failures(query: Mapping[str, Any], library: Iterable[Mapping[str, Any]] | None = None) -> dict[str, Any]:
    reason = str((query or {}).get("failure_reason") or (query or {}).get("class") or "").upper()
    rows = [dict(item) for item in (library if library is not None else FAILURE_MEMORY)]
    matches = [item for item in rows if str(item.get("failure_reason") or item.get("class") or "").upper() == reason]
    if not matches and (query or {}).get("symbol"):
        symbol = str(query.get("symbol")).upper()
        matches = [item for item in rows if str(item.get("symbol") or item.get("failure_case") or "").upper() == symbol]
    return {
        "query": reason or None,
        "matches": matches,
        "count": len(matches),
        "question": "有没有以前犯过类似错误？",
        "role": "evidence / warning",
        "not_a_production_signal": True,
        "production_boundary": PRODUCTION_BOUNDARY,
    }


def research_failure_lifecycle(
    conclusion: Mapping[str, Any] | None = None,
    outcome: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    conclusion = dict(conclusion or {})
    outcome = dict(outcome or {})
    predicted = conclusion.get("prediction") or conclusion.get("thesis")
    realized = outcome.get("outcome") or outcome.get("result")
    failed = bool(conclusion.get("failed") or outcome.get("failed"))
    if predicted is not None and realized is not None and predicted != realized:
        failed = True
    klass = str(conclusion.get("failure_reason") or outcome.get("failure_reason") or conclusion.get("class") or "").upper()
    if failed and klass not in FAILURE_CLASSES:
        klass = "THESIS_FAILURE"
    if not failed:
        klass = None
    record = {
        "symbol": conclusion.get("symbol") or outcome.get("symbol"),
        "research_conclusion": conclusion,
        "outcome": outcome,
        "failed_hypothesis": failed,
        "failure_reason": klass,
        "class": klass,
        "root_cause": conclusion.get("root_cause") or outcome.get("root_cause"),
        "evidence_conflict": conclusion.get("evidence_conflict") or outcome.get("evidence_conflict"),
        "role": "evidence / warning",
        "not_a_production_signal": True,
        "produces_pick": False,
        "production_boundary": PRODUCTION_BOUNDARY,
    }
    if failed:
        FAILURE_MEMORY.append(record)
        record["memory"] = True
        record["retrievable"] = True
    else:
        record["memory"] = False
        record["retrievable"] = False
    return record


def retrieve_failure_context(query: Mapping[str, Any] | None = None) -> dict[str, Any]:
    payload = similar_failures(query or {}, FAILURE_MEMORY)
    payload["future_research_context"] = True
    payload["not_a_production_signal"] = True
    return payload


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


def _component_score(left: Mapping[str, Any], right: Mapping[str, Any], key: str, aliases: tuple[str, ...]) -> float | None:
    a = None
    b = None
    for name in (key, *aliases):
        if a in (None, ""):
            a = left.get(name)
        if b in (None, ""):
            b = right.get(name)
    if a in (None, "") or b in (None, ""):
        return None
    if a == b:
        return 1.0
    if isinstance(a, str) and isinstance(b, str):
        left_tokens = {token for token in a.lower().replace(",", " ").split() if token}
        right_tokens = {token for token in b.lower().replace(",", " ").split() if token}
        if not left_tokens or not right_tokens:
            return 0.0
        overlap = len(left_tokens & right_tokens) / len(left_tokens | right_tokens)
        return round(overlap, 4)
    return 0.0


def research_similarity(left: Mapping[str, Any], right: Mapping[str, Any]) -> dict[str, Any]:
    scores = {}
    for dim in SIMILARITY_DIMENSIONS:
        a = left.get(dim)
        b = right.get(dim)
        scores[dim] = 1.0 if a not in (None, "") and a == b else 0.0 if a and b else None
    components = {
        "ticker": _component_score(left, right, "ticker", ("company", "symbol")),
        "industry": _component_score(left, right, "industry", ("sector",)),
        "thesis": _component_score(left, right, "thesis", ("company_thesis",)),
        "factor": _component_score(left, right, "factor", ("setup", "factors")),
        "market_regime": _component_score(left, right, "market_regime", ("regime",)),
        "capital_behavior": _component_score(left, right, "capital_behavior", ("capital", "capital_state")),
        "outcome": _component_score(left, right, "outcome", ("failure",)),
    }
    weights = {
        "ticker": 0.20,
        "industry": 0.15,
        "thesis": 0.20,
        "factor": 0.10,
        "market_regime": 0.15,
        "capital_behavior": 0.15,
        "outcome": 0.05,
    }
    numer = 0.0
    present = 0
    for key, weight in weights.items():
        value = components.get(key)
        if value is None:
            continue
        numer += weight * value
        present += 1
    score = round(numer / sum(weights.values()), 4) if present else None
    explained = {key: value for key, value in components.items() if value is not None}
    dim_usable = [value for value in scores.values() if value is not None]
    return {
        "score": score,
        "components": explained,
        "dimensions": scores,
        "not_text_only": True,
        "same_industry_is_not_automatic_one": True,
        "composite": score if score is not None else (round(sum(dim_usable) / len(dim_usable), 4) if dim_usable else None),
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
