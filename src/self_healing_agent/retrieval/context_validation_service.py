from __future__ import annotations

from self_healing_agent.agent.state import (
    ContextValidationResult,
    RetrievedDoc,
    RetrievalConfidenceObject,
)


def _normalize_text(value: str | None) -> str:
    if not value:
        return ""
    return value.strip().lower()


def _classify_action_family(text: str) -> str:
    text = _normalize_text(text)

    if any(term in text for term in ["suppress", "moratorium", "shutdown", "not yet", "yet to bring up"]):
        return "SUPPRESS_OR_DEFER"
    if any(term in text for term in ["restart", "restarted", "started jvms", "bring up"]):
        return "RESTART"
    if any(term in text for term in ["kill", "killed", "clear", "cleared"]):
        return "CLEAR_OR_KILL"
    return "OTHER"


def validate_retrieval_context(
    retrieved_docs: list[RetrievedDoc],
    filtered_evidence: list[str],
    rco: RetrievalConfidenceObject,
) -> ContextValidationResult:
    issues: list[str] = []

    doc_count = len(retrieved_docs)
    evidence_count = len(filtered_evidence)

    if doc_count == 0 or evidence_count == 0:
        return {
            "ok": False,
            "validity": "EMPTY",
            "issues": ["EMPTY_RETRIEVAL_EVIDENCE: No retrieval evidence available."],
            "facts": {
                "doc_count": doc_count,
                "evidence_count": evidence_count,
                "unique_evidence_count": 0,
                "action_families": [],
            },
        }

    normalized_evidence = [
        _normalize_text(text)
        for text in filtered_evidence
        if _normalize_text(text)
    ]
    unique_evidence_count = len(set(normalized_evidence))

    if not rco.get("is_sufficient", False):
        issues.append("LOW_QUALITY_RETRIEVAL_EVIDENCE: Retrieval confidence is insufficient.")

    if unique_evidence_count < min(2, evidence_count):
        issues.append("LOW_QUALITY_RETRIEVAL_EVIDENCE: Evidence set has low diversity or duplicate snippets.")

    action_families = sorted(
        {
            _classify_action_family(text)
            for text in normalized_evidence
            if text
        }
    )

    conflicting = "RESTART" in action_families and "SUPPRESS_OR_DEFER" in action_families

    if conflicting:
        return {
            "ok": False,
            "validity": "CONFLICTING",
            "issues": issues + ["CONFLICTING_RETRIEVAL_EVIDENCE: Retrieved evidence contains conflicting action patterns."],
            "facts": {
                "doc_count": doc_count,
                "evidence_count": evidence_count,
                "unique_evidence_count": unique_evidence_count,
                "action_families": action_families,
            },
        }

    if issues:
        return {
            "ok": False,
            "validity": "LOW_QUALITY",
            "issues": issues,
            "facts": {
                "doc_count": doc_count,
                "evidence_count": evidence_count,
                "unique_evidence_count": unique_evidence_count,
                "action_families": action_families,
            },
        }

    return {
        "ok": True,
        "validity": "VALID",
        "issues": [],
        "facts": {
            "doc_count": doc_count,
            "evidence_count": evidence_count,
            "unique_evidence_count": unique_evidence_count,
            "action_families": action_families,
        },
    }