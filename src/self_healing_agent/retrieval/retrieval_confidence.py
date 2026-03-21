from __future__ import annotations

from typing import Any


def build_retrieval_confidence(status: str, matches: list[dict[str, Any]]) -> dict[str, Any]:
    if not matches:
        return {
            "is_sufficient": False,
            "confidence": "UNKNOWN",
            "validity": "EMPTY",
            "summary": "No retrieval matches found.",
            "signals": {
                "match_count": 0,
                "top_similarity": None,
                "top_retrieval_level": None,
                "strict_count": 0,
                "metric_only_count": 0,
                "broad_count": 0,
            },
            "top_parent_ids": [],
        }

    top_match = matches[0]
    top_similarity = float(top_match.get("similarity", 0.0))
    top_retrieval_level = top_match.get("retrieval_level")
    match_count = len(matches)

    strict_count = sum(1 for match in matches if match.get("retrieval_level") == "STRICT")
    metric_only_count = sum(1 for match in matches if match.get("retrieval_level") == "METRIC_ONLY")
    broad_count = sum(1 for match in matches if match.get("retrieval_level") == "BROAD")

    if top_retrieval_level == "STRICT" and top_similarity >= 0.93 and match_count >= 2 and strict_count >= 2:
        confidence = "HIGH"
        validity = "VALID"
        is_sufficient = True
        summary = "Strong strict retrieval match with high similarity."
    elif top_similarity >= 0.88 and match_count >= 2 and (strict_count >= 1 or metric_only_count >= 2):
        confidence = "MEDIUM"
        validity = "VALID"
        is_sufficient = True
        summary = "Retrieval produced usable matches with moderate confidence."
    else:
        confidence = "LOW"
        validity = "LOW_QUALITY"
        is_sufficient = False
        summary = "Retrieved matches are weak or low quality."

    if confidence == "HIGH" and status == "PARTIAL_ERROR":
        confidence = "MEDIUM"
        summary = "Retrieval produced confidence is downgrade to MEDIUM due to partial retriever errors."
    return {
        "is_sufficient": is_sufficient,
        "confidence": confidence,
        "validity": validity,
        "summary": summary,
        "signals": {
            "match_count": match_count,
            "top_similarity": top_similarity,
            "top_retrieval_level": top_retrieval_level,
            "strict_count": strict_count,
            "metric_only_count": metric_only_count,
            "broad_count": broad_count,
        },
        "top_parent_ids": [match.get("parent_id") for match in matches[:3]],
    }