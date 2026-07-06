from __future__ import annotations

from typing import Any, Mapping

import requests
from django.conf import settings

from ai_assistant.infrastructure.providers.contracts import (
    LLMProviderConfigurationError,
    LLMProviderRequest,
    LLMProviderRequestError,
    LLMProviderResponse,
)

OPENAI_RESPONSES_PATH = "/responses"


class OpenAIResponsesClient:
    """OpenAI Responses API gateway.

    This adapter is intentionally infrastructure-only. It does not know about
    My Scoope tools, proposals, Food Catalog or operational nutrition models.
    """

    provider_name = "openai"

    def __init__(
        self,
        *,
        api_key: str | None = None,
        model: str | None = None,
        base_url: str | None = None,
        timeout_seconds: int | float | None = None,
        session: requests.Session | None = None,
    ):
        self.api_key = (api_key if api_key is not None else getattr(settings, "AI_ASSISTANT_OPENAI_API_KEY", "")).strip()
        self.model = (model if model is not None else getattr(settings, "AI_ASSISTANT_OPENAI_MODEL", "")).strip()
        self.base_url = (base_url if base_url is not None else getattr(settings, "AI_ASSISTANT_OPENAI_BASE_URL", "")).strip().rstrip("/")
        self.timeout_seconds = timeout_seconds if timeout_seconds is not None else getattr(
            settings,
            "AI_ASSISTANT_OPENAI_TIMEOUT_SECONDS",
            30,
        )
        self.session = session or requests.Session()

    def generate(self, request: LLMProviderRequest) -> LLMProviderResponse:
        self._validate_configuration()
        messages = request.normalized_messages
        if not messages:
            raise LLMProviderRequestError("OpenAI request requires at least one non-empty message.")

        payload: dict[str, Any] = {
            "model": self.model,
            "input": [message.as_openai_input_item() for message in messages],
            "store": False,
        }
        if request.max_output_tokens is not None:
            payload["max_output_tokens"] = int(request.max_output_tokens)

        response = self.session.post(
            f"{self.base_url}{OPENAI_RESPONSES_PATH}",
            json=payload,
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            timeout=self.timeout_seconds,
        )

        if response.status_code >= 400:
            raise LLMProviderRequestError(
                f"OpenAI provider request failed with status {response.status_code}."
            )

        try:
            data = response.json()
        except ValueError as exc:
            raise LLMProviderRequestError("OpenAI provider returned invalid JSON.") from exc

        text = _extract_output_text(data)
        if not text:
            raise LLMProviderRequestError("OpenAI provider response did not contain output text.")

        return LLMProviderResponse(
            provider=self.provider_name,
            model=str(data.get("model") or self.model),
            text=text,
            response_id=str(data.get("id") or ""),
            usage=_extract_usage(data),
            raw=data if isinstance(data, Mapping) else {},
        )

    def _validate_configuration(self) -> None:
        if not self.api_key:
            raise LLMProviderConfigurationError("AI_ASSISTANT_OPENAI_API_KEY is not configured.")
        if not self.model:
            raise LLMProviderConfigurationError("AI_ASSISTANT_OPENAI_MODEL is not configured.")
        if not self.base_url:
            raise LLMProviderConfigurationError("AI_ASSISTANT_OPENAI_BASE_URL is not configured.")


def _extract_output_text(data: Mapping[str, Any]) -> str:
    direct_text = data.get("output_text")
    if isinstance(direct_text, str) and direct_text.strip():
        return direct_text.strip()

    chunks: list[str] = []
    for output_item in data.get("output", []) or []:
        if not isinstance(output_item, Mapping):
            continue
        for content_item in output_item.get("content", []) or []:
            if not isinstance(content_item, Mapping):
                continue
            text = content_item.get("text")
            if isinstance(text, str) and text.strip():
                chunks.append(text.strip())
    return "\n".join(chunks).strip()


def _extract_usage(data: Mapping[str, Any]) -> Mapping[str, Any]:
    usage = data.get("usage")
    return usage if isinstance(usage, Mapping) else {}
