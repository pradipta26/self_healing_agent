# self_healing_agent/src/self_healing_agent/llm/service.py
from __future__ import annotations

from typing import Any

from self_healing_agent.agent.state import StructuredInput, RetrievalConfidenceObject
from self_healing_agent.llm.llm_client import LLMRequest, LLMResponse, GeminiClient
from self_healing_agent.llm.prompts import build_llm_system_prompt, build_llm_user_prompt
from self_healing_agent.llm.schemas import MODEL_OUTPUT_SCHEMA
from self_healing_agent.llm.output_parser import parse_and_validate_model_output


def generate_model_output(
    client: GeminiClient,
    structured_input: StructuredInput,
    filtered_evidence: list[str],
    #rco: RetrievalConfidenceObject --> may be for future
) -> tuple[str, dict[str, Any]]:
    system_prompt = build_llm_system_prompt()
    user_prompt = build_llm_user_prompt(
        structured_input=structured_input,
        filtered_evidence=filtered_evidence,
    )

    llm_request = LLMRequest(
    system_prompt=system_prompt,
        user_prompt=user_prompt,
        temperature=0.0,
        max_output_tokens=3000,
    )
    llm_response: LLMResponse = client.generate(
        request=llm_request,
        response_schema=MODEL_OUTPUT_SCHEMA,
    )
    print("llm_response.raw_text", llm_response.raw_text)
    parsed = parse_and_validate_model_output(
        llm_raw=llm_response.raw_text, 
        filtered_evidence=filtered_evidence
    )

    return llm_response.raw_text, parsed