from __future__ import annotations

from self_healing_agent.agent.state import StructuredInput, RetrievalConfidenceObject


def build_llm_system_prompt() -> str:
    return """
You are an incident reasoning assistant for a production-governed self-healing system.

Your task is to analyze the incident context and provided evidence, then return a structured JSON assessment.

Rules:
1. Use only the provided evidence. Do not invent facts.
2. Cite only evidence IDs that appear in the evidence list.
3. If evidence is conflicting, set actionability to CONFLICTING_SIGNALS or HUMAN_REQUIRED.
4. If evidence is insufficient, set actionability to INSUFFICIENT_EVIDENCE.
5. Do not decide execution autonomy.
6. Keep description concise and operational.
7. Return valid JSON only, with no markdown and no extra text.
""".strip()


def build_llm_user_prompt(
    structured_input: StructuredInput,
    filtered_evidence: list[str],
    # rco: RetrievalConfidenceObject, --> may be for future
) -> str:
    metric_names = structured_input.get("metric_names", []) or []
    metric_text = ", ".join(metric_names)

    evidence_lines = []
    for idx, evidence in enumerate(filtered_evidence, start=1):
        evidence_lines.append(f"[{idx}] {evidence}")

    evidence_block = "\n".join(evidence_lines) if evidence_lines else "[none]"

    return f"""
Incident context:
- Incident type: {structured_input.get("incident_type")}
- Environment: {structured_input.get("env")}
- Service domain: {structured_input.get("service_domain")}
- Datacenter: {structured_input.get("datacenter")}
- Application: {structured_input.get("app_name")}
- Metric names: {metric_text}
- Reason: {structured_input.get("reason")}

Evidence candidates:
{evidence_block}

Return JSON with this exact structure:
{{
  "category": "CPU| MEMORY | NETWORK | APPLICATION | DATABASE | JVM | STORAGE | DEPENDENCY | CONFIGURATION | UNKNOWN",
  "confidence": "HIGH | MEDIUM | LOW | UNKNOWN",
  "actionability": "SAFE_TO_PROPOSE | HUMAN_REQUIRED | INSUFFICIENT_EVIDENCE | CONFLICTING_SIGNALS",
  "description": "short evidence-based summary",
  "evidence_ids": [1],
  "remediation": ["step 1"],
  "hypotheses": ["optional alternative explanation"]
}}

Requirements:
- Use only the listed evidence.
- Cite the evidence IDs you relied on.
- If evidence is conflicting, reflect that in actionability.
- If evidence is insufficient, reflect that in actionability.
- Return JSON only.
""".strip()

# TODO: Will see if we add RCO info to prompt in future
"""
Retrieval summary:
- Retrieval confidence: {rco.get("confidence")}
- Retrieval validity: {rco.get("validity")}
- Retrieval summary: {rco.get("summary")}
"""