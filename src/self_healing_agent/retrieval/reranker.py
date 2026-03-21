from __future__ import annotations

from typing import Any

from self_healing_agent.agent.state import StructuredInput


def _normalize_text(value: str | None) -> str:
    if not value:
        return ""
    return value.strip().lower()


def _normalize_metric_list(metric_names: list[str] | None) -> set[str]:
    if not metric_names:
        return set()
    return {
        metric.strip().lower()
        for metric in metric_names
        if isinstance(metric, str) and metric.strip()
    }


def _retrieval_level_bonus(retrieval_level: str | None) -> float:
    """
    Deterministic trust bias by retrieval stage.
    STRICT should be rewarded most, BROAD least.
    """
    if retrieval_level == "STRICT":
        return 0.08
    if retrieval_level == "METRIC_ONLY":
        return 0.04
    if retrieval_level == "BROAD":
        return 0.0
    return 0.0


def _bool_score(value: bool, weight: float) -> float:
    return weight if value else 0.0


def _build_rerank_signals(
    match: dict[str, Any],
    structured_input: StructuredInput,
) -> dict[str, Any]:
    input_service = _normalize_text(structured_input.get("service_domain"))
    input_datacenter = _normalize_text(structured_input.get("datacenter"))
    input_incident_type = _normalize_text(structured_input.get("incident_type"))
    input_app_name = _normalize_text(structured_input.get("app_name"))
    input_metric_names = _normalize_metric_list(structured_input.get("metric_names"))

    match_service = _normalize_text(match.get("service_domain"))
    match_datacenter = _normalize_text(match.get("datacenter"))
    match_incident_type = _normalize_text(match.get("incident_type"))
    match_app_name = _normalize_text(match.get("app_name"))
    match_metric_name = _normalize_text(match.get("metric_name"))

    service_match = bool(input_service and match_service and input_service == match_service)
    datacenter_match = bool(input_datacenter and match_datacenter and input_datacenter == match_datacenter)
    incident_type_match = bool(input_incident_type and match_incident_type and input_incident_type == match_incident_type)
    app_name_match = bool(input_app_name and match_app_name and input_app_name == match_app_name)
    metric_match = bool(match_metric_name and match_metric_name in input_metric_names)

    return {
        "service_match": service_match,
        "datacenter_match": datacenter_match,
        "incident_type_match": incident_type_match,
        "app_name_match": app_name_match,
        "metric_match": metric_match,
    }


def _compute_rerank_score(
    match: dict[str, Any],
    signals: dict[str, Any],
) -> float:
    """
    Deterministic weighted score.

    Base similarity is dominant, but exact operational matches can change rank.
    """
    similarity = float(match.get("similarity", 0.0))
    retrieval_level = match.get("retrieval_level")

    score = 0.0

    # Base semantic similarity dominates
    score += similarity * 0.55

    # Deterministic operational boosts
    score += _bool_score(signals.get("metric_match", False), 0.20)
    score += _bool_score(signals.get("incident_type_match", False), 0.10)
    score += _bool_score(signals.get("service_match", False), 0.08)
    score += _bool_score(signals.get("datacenter_match", False), 0.04)
    score += _bool_score(signals.get("app_name_match", False), 0.03)

    # Retrieval stage trust bias
    score += _retrieval_level_bonus(retrieval_level)

    return round(score, 6)


def rerank_candidates(
    matches: list[dict[str, Any]],
    structured_input: StructuredInput,
) -> list[dict[str, Any]]:
    """
    Re-rank retrieved incident matches using deterministic operational signals.

    Returns a new sorted list with:
    - rerank_score
    - rerank_signals
    """
    reranked: list[dict[str, Any]] = []

    for match in matches:
        signals = _build_rerank_signals(match, structured_input)
        rerank_score = _compute_rerank_score(match, signals)

        enriched_match = dict(match)
        enriched_match["rerank_score"] = rerank_score
        enriched_match["rerank_signals"] = signals

        reranked.append(enriched_match)

    reranked.sort(
        key=lambda item: (
            float(item.get("rerank_score", 0.0)),
            float(item.get("similarity", 0.0)),
        ),
        reverse=True,
    )

    return reranked