from typing import Any

def get_cited_evidence(
    model_output: dict[str, Any],
    filtered_evidence: list[str],
) -> list[str]:
    evidence_ids = model_output.get("evidence_ids", [])
    return [
        filtered_evidence[eid - 1]
        for eid in evidence_ids
        if isinstance(eid, int) and 1 <= eid <= len(filtered_evidence)
    ]

def get_cited_evidence_or_fallback(
    model_output: dict[str, Any],
    filtered_evidence: list[str],
    fallback_limit: int = 3,
) -> list[str]:
    cited = get_cited_evidence(model_output, filtered_evidence)
    return cited or filtered_evidence[:fallback_limit]