from __future__ import annotations

import json
from typing import Any, get_args

from self_healing_agent.agent.state import Category, Confidence, Actionability  
from self_healing_agent.agent.state import (
    Actionability,
    Category,
    Confidence,
    ModelOutput,
)


VALID_CATEGORIES = set(get_args(Category))
VALID_CONFIDENCES = set(get_args(Confidence))
VALID_ACTIONABILITIES = set(get_args(Actionability))

class ModelOutputValidationError(ValueError):
    """Raised when LLM output is malformed or violates schema expectations."""


def _strip_code_fences(text: str) -> str:
    text = text.strip()
    if text.startswith("```"):
        lines = text.splitlines()
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        return "\n".join(lines).strip()
    return text


def _require_non_empty_string(value: Any, field_name: str) -> str:
    if not isinstance(value, str):
        raise ModelOutputValidationError(f"{field_name} must be a string.")
    cleaned = value.strip()
    if not cleaned:
        raise ModelOutputValidationError(f"{field_name} must not be empty.")
    return cleaned


def _validate_string_list(value: Any, field_name: str) -> list[str]:
    if not isinstance(value, list):
        raise ModelOutputValidationError(f"{field_name} must be a list of strings.")

    result: list[str] = []
    for idx, item in enumerate(value):
        if not isinstance(item, str):
            raise ModelOutputValidationError(
                f"{field_name}[{idx}] must be a string."
            )
        cleaned = item.strip()
        if not cleaned:
            raise ModelOutputValidationError(
                f"{field_name}[{idx}] must not be empty."
            )
        result.append(cleaned)

    return result


def _validate_evidence_ids(value: Any, evidence_count: int) -> list[int]:
    if not isinstance(value, list):
        raise ModelOutputValidationError("evidence_ids must be a list of integers.")

    result: list[int] = []
    for idx, item in enumerate(value):
        if not isinstance(item, int):
            raise ModelOutputValidationError(
                f"evidence_ids[{idx}] must be an integer."
            )

        if item < 1 or item > evidence_count:
            raise ModelOutputValidationError(
                f"evidence_ids[{idx}]={item} is out of range. "
                f"Allowed range is 1..{evidence_count}."
            )

        result.append(item)

    if not result:
        raise ModelOutputValidationError("evidence_ids must not be empty.")

    return result


def parse_and_validate_model_output(
    llm_raw: str,
    filtered_evidence: list[str],
) -> ModelOutput:
    """
    Parse and validate raw LLM JSON output.

    Validation rules:
    - JSON parses
    - category is valid enum
    - confidence is valid enum
    - actionability is valid enum
    - evidence_ids is a list of ints
    - each evidence id is in range 1..len(filtered_evidence)
    - remediation is a list[str]
    - hypotheses is a list[str]
    """
    if not isinstance(llm_raw, str) or not llm_raw.strip():
        raise ModelOutputValidationError("LLM raw output must be a non-empty string.")

    if not isinstance(filtered_evidence, list) or not filtered_evidence:
        raise ModelOutputValidationError(
            "filtered_evidence must be a non-empty list."
        )

    try:
        # Attempt to parse the raw LLM output as JSON
        payload = _strip_code_fences(llm_raw)
        payload = json.loads(payload)
    except json.JSONDecodeError as exc:
        raise ModelOutputValidationError(
            f"LLM output is not valid JSON: {exc}"
        ) from exc

    if not isinstance(payload, dict):
        raise ModelOutputValidationError("LLM output JSON must be an object.")

    category = _require_non_empty_string(payload.get("category"), "category")
    if category not in VALID_CATEGORIES:
        raise ModelOutputValidationError(
            f"category must be one of {sorted(VALID_CATEGORIES)}."
        )

    confidence = _require_non_empty_string(payload.get("confidence"), "confidence")
    if confidence not in VALID_CONFIDENCES:
        raise ModelOutputValidationError(
            f"confidence must be one of {sorted(VALID_CONFIDENCES)}."
        )

    actionability = _require_non_empty_string(
        payload.get("actionability"),
        "actionability",
    )
    if actionability not in VALID_ACTIONABILITIES:
        raise ModelOutputValidationError(
            f"actionability must be one of {sorted(VALID_ACTIONABILITIES)}."
        )

    description = _require_non_empty_string(
        payload.get("description"),
        "description",
    )

    evidence_ids = _validate_evidence_ids(
        payload.get("evidence_ids"),
        evidence_count=len(filtered_evidence),
    )

    remediation = _validate_string_list(
        payload.get("remediation"),
        "remediation",
    )

    hypotheses = _validate_string_list(
        payload.get("hypotheses"),
        "hypotheses",
    )

    validated_model_output: ModelOutput = {
        "category": category,
        "confidence": confidence,
        "actionability": actionability,
        "description": description,
        "evidence_ids": evidence_ids,
        "remediation": remediation,
        "hypotheses": hypotheses,
    }

    return validated_model_output