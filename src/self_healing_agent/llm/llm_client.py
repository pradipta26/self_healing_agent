from __future__ import annotations

from dataclasses import dataclass
import os
from typing import Any
from abc import ABC, abstractmethod
from google import genai
from google.genai import types

@dataclass(frozen=True)
class LLMRequest:
    system_prompt: str
    user_prompt: str
    temperature: float = 0.0
    max_output_tokens: int = 3000


@dataclass(frozen=True)
class LLMResponse:
    raw_text: str
    model_name: str


class LLMClient(ABC):
    @abstractmethod
    def generate(self, request: LLMRequest,response_schema: dict[str, Any] | None = None,
    ) -> LLMResponse:
        pass


class GeminiClient(LLMClient):
    """
    Production-oriented Gemini wrapper.

    Notes:
    - Keep SDK usage isolated here.
    - Keep temperature low for operational workflows.
    - Prefer JSON schema / structured output for machine-readability.
    """

    def __init__(
        self,
        model_name: str,
        api_key: str | None = None,
        use_vertex_ai: bool = False,
        project: str | None = None,
        location: str | None = None,
    ) -> None:
        self.model_name = model_name
        self.use_vertex_ai = use_vertex_ai

        if use_vertex_ai:
            if not project or not location:
                raise ValueError("project and location are required when use_vertex_ai=True")

            self.client = genai.Client(
                vertexai=True,
                project=project,
                location=location,
            )
        else:
            resolved_api_key = api_key or os.getenv("GEMINI_API_KEY")
            if not resolved_api_key:
                raise ValueError("GEMINI_API_KEY is required for Gemini Developer API")

            self.client = genai.Client(api_key=resolved_api_key)

    def generate(
        self,
        request: LLMRequest,
        response_schema: dict[str, Any] | None = None,
    ) -> LLMResponse:
        contents = [
            types.Content(
                role="user",
                parts=[types.Part.from_text(text=request.user_prompt)],
            )
        ]

        config_kwargs: dict[str, Any] = {
            "system_instruction": request.system_prompt,
            "temperature": request.temperature,
            "max_output_tokens": request.max_output_tokens,
        }

        if response_schema:
            config_kwargs["response_mime_type"] = "application/json"
            config_kwargs["response_schema"] = response_schema

        response = self.client.models.generate_content(
            model=self.model_name,
            contents=contents,
            config=types.GenerateContentConfig(**config_kwargs),
        )

        text = response.text or ""
        return LLMResponse(raw_text=text, model_name=self.model_name)