from __future__ import annotations

import re

from self_healing_agent.agent.state import (
    GroundingCheckResult,
    ModelOutput,
    RetrievedDoc,
)


def _normalize_text(value: str | None) -> str:
    if not value:
        return ""
    text = value.lower().strip()
    text = re.sub(r"[^a-z0-9\s]", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def _tokenize(value: str | None) -> set[str]:
    text = _normalize_text(value)
    if not text:
        return set()

    stop_words = {
        "the", "a", "an", "for", "to", "of", "in", "on", "and", "or",
        "is", "are", "was", "were", "be", "by", "with",
    }
    return {
        token
        for token in text.split()
        if token not in stop_words and len(token) > 1
    }


def _classify_action_family(text: str) -> str:
    text = _normalize_text(text)

    if any(term in text for term in ["restart", "restarted"]):
        return "RESTART"
    if any(term in text for term in ["start", "started", "bring up"]):
        return "START"
    if any(term in text for term in ["kill", "killed", "clear", "cleared"]):
        return "CLEAR_OR_KILL"
    if any(term in text for term in ["suppress", "moratorium", "shutdown", "not yet", "yet to bring up"]):
        return "SUPPRESS_OR_DEFER"

    return "OTHER"


def _is_action_family_supported(
    step_action: str,
    cited_action_families: set[str],
) -> bool:
    if step_action in cited_action_families:
        return True

    compatibility_map = {
        "RESTART": {"START", "RESTART"},
        "START": {"START", "RESTART"},
        "CLEAR_OR_KILL": {"CLEAR_OR_KILL"},
        "SUPPRESS_OR_DEFER": {"SUPPRESS_OR_DEFER"},
        "OTHER": {"OTHER"},
    }

    allowed_families = compatibility_map.get(step_action, {step_action})
    return bool(allowed_families & cited_action_families)


def _has_minimum_token_overlap(
    claim: str,
    evidence_texts: list[str],
    min_overlap: int = 2,
) -> bool:
    claim_tokens = _tokenize(claim)
    if not claim_tokens:
        return False

    evidence_tokens: set[str] = set()
    for text in evidence_texts:
        evidence_tokens.update(_tokenize(text))

    overlap = claim_tokens & evidence_tokens
    return len(overlap) >= min_overlap


def _collect_used_evidence_doc_ids(
    evidence_ids: list[int],
    evidence_candidates: list[RetrievedDoc],
) -> list[str]:
    doc_ids: list[str] = []

    for evidence_id in evidence_ids:
        idx = evidence_id - 1
        if 0 <= idx < len(evidence_candidates):
            doc_id = evidence_candidates[idx].get("doc_id")
            if doc_id:
                doc_ids.append(doc_id)

    return doc_ids


def check_grounding(
    model_output: ModelOutput,
    filtered_evidence: list[str],
    evidence_candidates: list[RetrievedDoc],
) -> GroundingCheckResult:
    notes: list[str] = []
    missing_claims: list[str] = []

    evidence_ids = model_output.get("evidence_ids", [])
    description = model_output.get("description", "")
    remediation = model_output.get("remediation", [])
    hypotheses = model_output.get("hypotheses", [])

    # -----------------------------
    # citation presence / shape
    # -----------------------------
    if not isinstance(evidence_ids, list) or not evidence_ids:
        return {
            "verdict": "NOT_GROUNDED",
            "ok": False,
            "missing_claims": ["No evidence_ids provided by model."],
            "used_evidence_doc_ids": [],
            "notes": ["Model output has no usable citations."],
        }

    if any(not isinstance(eid, int) for eid in evidence_ids):
        return {
            "verdict": "NOT_GROUNDED",
            "ok": False,
            "missing_claims": ["evidence_ids must be a list of integers."],
            "used_evidence_doc_ids": [],
            "notes": ["Model citation format invalid."],
        }

    max_evidence_id = len(filtered_evidence)
    if any(eid < 1 or eid > max_evidence_id for eid in evidence_ids):
        return {
            "verdict": "NOT_GROUNDED",
            "ok": False,
            "missing_claims": ["One or more evidence_ids are out of range."],
            "used_evidence_doc_ids": [],
            "notes": [f"Allowed evidence_id range is 1..{max_evidence_id}."],
        }

    cited_evidence_texts = [filtered_evidence[eid - 1] for eid in evidence_ids]
    used_evidence_doc_ids = _collect_used_evidence_doc_ids(
        evidence_ids,
        evidence_candidates,
    )

    # -----------------------------
    # description support
    # -----------------------------
    if description and not _has_minimum_token_overlap(description, cited_evidence_texts):
        missing_claims.append(
            "Description is not sufficiently supported by cited evidence."
        )

    # -----------------------------
    # remediation support
    # -----------------------------
    cited_action_families = {
        _classify_action_family(text)
        for text in cited_evidence_texts
        if text
    }

    for step in remediation:
        step_action = _classify_action_family(step)
        if step_action != "OTHER" and not _is_action_family_supported(step_action, cited_action_families):
            missing_claims.append(
                f"Remediation step not supported by cited evidence: {step}"
            )

    # -----------------------------
    # hypotheses: weaker check
    # -----------------------------
    unsupported_hypotheses = 0
    for hypothesis in hypotheses:
        if hypothesis and not _has_minimum_token_overlap(
            hypothesis,
            cited_evidence_texts,
            min_overlap=1,
        ):
            unsupported_hypotheses += 1

    if unsupported_hypotheses:
        notes.append(
            f"{unsupported_hypotheses} hypothesis entries were weakly grounded."
        )

    # -----------------------------
    # verdict
    # -----------------------------
    if not missing_claims:
        return {
            "verdict": "GROUNDED",
            "ok": True,
            "missing_claims": [],
            "used_evidence_doc_ids": used_evidence_doc_ids,
            "notes": notes or ["All primary claims grounded in cited evidence."],
        }

    primary_claim_count = 1 + len(remediation)  # description + remediation
    if len(missing_claims) < primary_claim_count:
        return {
            "verdict": "PARTIALLY_GROUNDED",
            "ok": False,
            "missing_claims": missing_claims,
            "used_evidence_doc_ids": used_evidence_doc_ids,
            "notes": notes + ["Some claims were grounded, but not all."],
        }

    return {
        "verdict": "NOT_GROUNDED",
        "ok": False,
        "missing_claims": missing_claims,
        "used_evidence_doc_ids": used_evidence_doc_ids,
        "notes": notes + ["Primary model claims are not grounded in cited evidence."],
    }