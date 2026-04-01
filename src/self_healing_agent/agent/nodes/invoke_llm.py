from __future__ import annotations

from typing import Any
import os

from self_healing_agent.agent.state import AgentState
from self_healing_agent.llm.llm_client import GeminiClient
from self_healing_agent.llm.llm_service import generate_model_output
from self_healing_agent.llm.output_parser import ModelOutputValidationError


def invoke_llm(state: AgentState) -> dict[str, Any]:
    structured_input = state["structured_input"]
    filtered_evidence = state.get("filtered_evidence", [])

    warnings = list(state.get("warnings", []))
    trace = list(state.get("trace", []))

    # -----------------------------
    # model init
    # -----------------------------
    try:
        llm_client = GeminiClient(
            model_name=os.getenv("LLM_MODEL", "gemini-2.5-flash"),
            api_key=os.getenv("GOOGLE_API_KEY"),
            use_vertex_ai=os.getenv("USE_VERTEX_AI", "False") == "True",
            project=os.getenv("GCP_PROJECT"),
            location=os.getenv("GCP_LOCATION"),
        )
    except Exception as exc:
        warnings.append("MODEL_OUTPUT_SCHEMA_VIOLATION")
        trace.append("invoke_llm:init_error")
        return {
            "warnings": warnings,
            "trace": trace,
            "error_flag": True,
            "error_message": f"Failed to initialize LLM client: {exc}",
        }

    # -----------------------------
    # model invoke + parse
    # -----------------------------
    try:
        llm_raw, model_output = generate_model_output(
            client=llm_client,
            structured_input=structured_input,
            filtered_evidence=filtered_evidence,
        )

        trace.append("invoke_llm:ok")
        return {
            "llm_model_name": llm_client.model_name or None,
            "llm_model_version": None,
            "llm_raw": llm_raw,
            "model_output": model_output,
            "warnings": warnings,
            "trace": trace,
            "error_flag": False,
            "error_message": None,
        }

    except ModelOutputValidationError as exc:
        warnings.append("MODEL_OUTPUT_SCHEMA_VIOLATION")
        trace.append("invoke_llm:schema_violation")
        return {
            "llm_model_name": llm_client.model_name or None,
            "llm_model_version": None,
            "llm_raw": None,
            "model_output": {},
            "warnings": warnings,
            "trace": trace,
            "error_flag": True,
            "error_message": f"LLM output validation failed: {exc}",
        }

    except ValueError as exc:
        warnings.append("MODEL_OUTPUT_SCHEMA_VIOLATION")
        trace.append("invoke_llm:value_error")
        return {
            "llm_model_name": llm_client.model_name or None,
            "llm_model_version": None,
            "llm_raw": None,
            "model_output": {},
            "warnings": warnings,
            "trace": trace,
            "error_flag": True,
            "error_message": f"LLM processing failed: {exc}",
        }

    except Exception as exc:
        trace.append("invoke_llm:error")
        return {
            "llm_model_name": llm_client.model_name or None,
            "llm_model_version": None,
            "llm_raw": None,
            "model_output": {},
            "warnings": warnings,
            "trace": trace,
            "error_flag": True,
            "error_message": f"Unexpected LLM invocation failure: {exc}",
        }