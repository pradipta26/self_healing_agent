from __future__ import annotations

from typing import Any

from self_healing_agent.utils.utils import get_logger
from self_healing_agent.agent.state import StructuredInput
from self_healing_agent.retrieval.hybrid_retriever import hybrid_retrieve
from self_healing_agent.retrieval.retrieval_confidence import build_retrieval_confidence
from self_healing_agent.utils.incident_normalizer import normalize_reason_text
from self_healing_agent.retrieval.reranker import rerank_candidates
from self_healing_agent.agent.state import (
    RetrievalConfidenceObject,
    RetrievalStageResult,
    RetrievedDoc
)

log = get_logger(__name__)


def _create_retrieved_docs(env: str, reranked_matches: list[dict[str, Any]]) -> list[RetrievedDoc]:

    retrieved_docs: list[RetrievedDoc] = []
    
    for match in reranked_matches:
        problem = match.get("problem_text_normalized")
        resolution = match.get("resolution_text_normalized")

        if problem and resolution:
            snippet = f"{problem} -> {resolution}"
        elif problem:
            snippet = problem
        elif resolution:
            snippet = resolution
        else:
            snippet = ""

        retrieved_doc: RetrievedDoc = {
            "doc_id": str(match["parent_id"]),
            "source": "PRDB",
            "incident_id": str(match["parent_id"]),
            "service": match.get("service_domain"),
            "env": env,
            "vector_score": match.get("similarity"),
            "lexical_score": None,
            "rerank_score": match.get("rerank_score"),
            "snippet": snippet,
            "metadata": {
                "app_name": match.get("app_name"),
                "datacenter": match.get("datacenter"),
                "incident_type": match.get("incident_type"),
                "metric_name": match.get("metric_name"),
                "retrieval_level": match.get("retrieval_level"),
                "rerank_signals": match.get("rerank_signals"),
                "problem_text": match.get("problem_text"),
                "problem_text_normalized": match.get("problem_text_normalized"),
                "resolution_text": match.get("resolution_text"),
                "resolution_text_normalized": match.get("resolution_text_normalized"),
                },
            }
        retrieved_docs.append(retrieved_doc)

    return retrieved_docs


def _create_retrieval_stage_result(
    status: str,
    query_text: str,
    retrieved_docs: list[RetrievedDoc],
    error_list: list[dict[str, Any]],
) -> RetrievalStageResult:
    stage_candidates: list[RetrievedDoc] = []

    if retrieved_docs:
        # take top 3 for stage candidates
        for doc in retrieved_docs[:3]:
            stage_candidate: RetrievedDoc = {
                    "doc_id": doc.get("doc_id"),
                    "source": doc.get("source"),
                    "incident_id": doc.get("incident_id"),
                    "service": doc.get("service"),
                    "env": doc.get("env"),
                    "vector_score": doc.get("vector_score"),
                    "lexical_score": doc.get("lexical_score"),
                    "rerank_score": doc.get("rerank_score"),
                    "snippet": doc.get("snippet"),
                    "metadata": {
                        "retrieval_level": doc.get("metadata", {}).get("retrieval_level"),
                    },
                }
            stage_candidates.append(stage_candidate)

    return {
        "stage": "STAGE1_HYBRID_RETRIEVE",
        "strategy": "HYBRID",
        "k": len(stage_candidates),
        "query_used": query_text,
        "candidates": stage_candidates,
        "metrics": {
            "match_count": len(retrieved_docs),
            "top_vector_score": retrieved_docs[0].get("vector_score") if retrieved_docs else None,
            "top_rerank_score": retrieved_docs[0].get("rerank_score") if retrieved_docs else None,
            "status": status,
            "error_count": len(error_list),
        },
    }


def _create_retrieval_confidence(status: str, reranked_matches: list[dict[str, Any]]) -> RetrievalConfidenceObject:
    pass




def retrieve_incident_context(
    structured_input: StructuredInput,
    limit: int = 5,
) -> dict[str, Any]:
    metric_names = structured_input.get("metric_names", []) or []
    primary_metric = metric_names[0] if metric_names else None
    incident_type = structured_input.get("incident_type")

    query_text = normalize_reason_text(structured_input)

    retrieval_result = hybrid_retrieve(
        query_text=query_text,
        metric_name=primary_metric,
        incident_type=incident_type,
        limit=limit,
    )

    status = retrieval_result.get("status", "ERROR")
    matches = retrieval_result.get("matches", [])
    error_list = retrieval_result.get("errors", [])
    reranked_matches = rerank_candidates(matches, structured_input)
    retrieval_confidence = build_retrieval_confidence(status, reranked_matches)

    # error = None
    # error_type = None

    # if error_list:
    #     error = "; ".join(err.get("message", "") for err in error_list if err.get("message"))
    #     error_type = ",".join(
    #         sorted({err.get("error_type", "UNKNOWN_ERROR") for err in error_list})
    #     )
    
    retrieved_docs = _create_retrieved_docs(structured_input.get("env"), reranked_matches)
    stage_result =_create_retrieval_stage_result(status, query_text, retrieved_docs, error_list)
    return {
        "status": status,
        "query_text": query_text,
        "primary_metric": primary_metric,
        "incident_type": incident_type,
        "matches": reranked_matches,
        "retrieved_docs": retrieved_docs,
        "retrieval_stages": [stage_result],
        "retrieval_confidence": retrieval_confidence,
        "errors": error_list,
    }

if __name__ == "__main__":
    from pprint import pprint

    structured_input = {
        "incident_type": "Host Infrastructure",
        "env": "DEV",
        "service_domain": "H0JV",
        "datacenter": "CDC",
        "metric_names": [
            "jvm mismatch"
        ],
        "app_name": "H0JV-JVM-STATUS",
        "hosts": [
            "CDC-S POS-MS LP 2.0 H0JV Jvm Status Mismatch"
        ],
        "instances": [
            "Reference List: CDC.POS-MS-LP.jvmlistx"
        ],
        "instance_hosts": [],
        "reason": "jvm mismatch >= 0.0"
    }


    result = retrieve_incident_context(structured_input)
    pprint(result)
    # for match in result["matches"]:
    #     pprint({
    #         "parent_id": match["parent_id"],
    #         "similarity": match["similarity"],
    #         "retrieval_level": match["retrieval_level"],
    #         "rerank_score": match["rerank_score"],
    #         "rerank_signals": match["rerank_signals"],
    #         "resolution_text_normalized": match["resolution_text_normalized"],
    #     })