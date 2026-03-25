from __future__ import annotations

from self_healing_agent.utils.incident_normalizer import extract_reason_signal
from self_healing_agent.agent.state import QueryRewriteArtifact, StructuredInput
from self_healing_agent.utils.incident_normalizer import (
    build_retry_query_text,
    get_primary_metric,
)

METRIC_EXPANSION: dict[str, list[str]] = {
    "readtimeout elk": [
        "read timeout",
        "socket timeout",
        "downstream timeout",
    ],
    "active threads": [
        "jvm threads",
        "thread pool exhaustion",
        "stuck threads",
    ],
    "oracle db tablespace": [
        "tablespace full",
        "add datafile",
        "increase tablespace",
    ],
    "mssql sqldb alwayson health": [
        "always on ag",
        "availability group",
        "replica secondary",
    ],
    "jvm mismatch": [
        "jvm status mismatch",
        "missing jvms",
        "jvm status check",
    ],
}


def _clean_text(value: str | None) -> str:
    if not value:
        return ""
    return value.strip()


def _normalize_lookup_key(value: str | None) -> str:
    if not value:
        return ""
    return " ".join(
        value.strip().lower().replace("_", " ").replace("-", " ").split()
    )


def _get_metric_expansions(metric_name: str | None) -> list[str]:
    lookup_key = _normalize_lookup_key(metric_name)
    return METRIC_EXPANSION.get(lookup_key, [])


def _dedupe_keep_order(values: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []

    for value in values:
        cleaned = value.strip()
        if not cleaned:
            continue

        normalized = cleaned.lower()
        if normalized in seen:
            continue

        seen.add(normalized)
        result.append(cleaned)

    return result


def build_deterministic_query_rewrite(
    original_query: str,
    structured_input: StructuredInput,
    context_validity: str | None = None,
) -> QueryRewriteArtifact:
    """
    Build a deterministic, audit-friendly retrieval retry query.

    Design:
    - always preserve strong operational anchors
    - remove noisy host-specific text from retry query
    - add metric-aware lexical expansions into artifact fields
    - only append a small number of expansion hints to rewritten query
      for EMPTY / LOW_QUALITY cases
    """

    service_domain = _clean_text(structured_input.get("service_domain"))
    incident_type = _clean_text(structured_input.get("incident_type"))
    datacenter = _clean_text(structured_input.get("datacenter"))
    app_name = _clean_text(structured_input.get("app_name"))
    metric_names = structured_input.get("metric_names", []) or []
    primary_metric = get_primary_metric(metric_names)
    reason = _clean_text(structured_input.get("reason"))

    metric_expansions = _get_metric_expansions(primary_metric)

    lexical_boost_terms: list[str] = []
    embedding_hints: list[str] = []
    safety_notes: list[str] = []

    facts: dict[str, object] = {
        "rewrite_goal": "",
        "removed_hosts": True,
        "used_service_domain": bool(service_domain),
        "used_incident_type": bool(incident_type),
        "used_datacenter": bool(datacenter),
        "used_app_name": bool(app_name),
        "used_primary_metric": bool(primary_metric),
        "metric_expansion_count": len(metric_expansions),
        "appended_expansion_hints_to_query": 0,
    }

    # These are really retrieval anchor terms, not just metric expansions.

    if app_name:
        embedding_hints.append(app_name)

    if primary_metric:
        lexical_boost_terms.append(primary_metric)
        embedding_hints.append(primary_metric)

    if reason:
        reason_signal = extract_reason_signal(reason, primary_metric)
        embedding_hints.append(reason_signal)

    expansion_hints_for_query: list[str] = []

    if context_validity == "EMPTY":
        facts["rewrite_goal"] = "broaden_recall"
        safety_notes.append("Removed host-specific noise to improve recall.")
        safety_notes.append("Added limited metric-aware expansion hints for broader retrieval.")
        expansion_hints_for_query = metric_expansions[:2]

    elif context_validity == "LOW_QUALITY":
        facts["rewrite_goal"] = "improve_precision"
        safety_notes.append("Retained core operational anchors and removed noisy host detail.")
        safety_notes.append("Added limited metric-aware expansion hints to improve retrieval quality.")
        expansion_hints_for_query = metric_expansions[:1]

    elif context_validity == "CONFLICTING":
        facts["rewrite_goal"] = "reduce_conflict"
        safety_notes.append("Narrowed retry query toward exact service/app/metric anchors.")
        safety_notes.append("Did not broaden aggressively to avoid increasing cross-service conflict.")
        expansion_hints_for_query = []

    else:
        facts["rewrite_goal"] = "canonicalize"
        safety_notes.append("Applied deterministic canonical query rewrite.")
        expansion_hints_for_query = []

    facts["appended_expansion_hints_to_query"] = len(expansion_hints_for_query)
    
    lexical_boost_terms.extend(expansion_hints_for_query)
    embedding_hints.extend(expansion_hints_for_query)
    
    lexical_boost_terms = _dedupe_keep_order(lexical_boost_terms)
    embedding_hints = _dedupe_keep_order(embedding_hints)
    safety_notes = _dedupe_keep_order(safety_notes)

    rewritten_query = build_retry_query_text(
        structured_input,
        include_hosts=False,
        expansion_hints=expansion_hints_for_query,
    )

    return {
        "original_query": original_query,
        "rewritten_query": rewritten_query,
        "rewrite_type": "DETERMINISTIC_CANONICALIZE",
        "lexical_boost_terms": lexical_boost_terms,
        "embedding_hints": embedding_hints,
        "safety_notes": safety_notes,
        "facts": facts,
    }   