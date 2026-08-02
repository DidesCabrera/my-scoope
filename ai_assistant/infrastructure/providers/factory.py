from __future__ import annotations

from django.conf import settings

from ai_assistant.infrastructure.providers.contracts import (
    LLMClient,
    LLMProviderConfigurationError,
)
from ai_assistant.infrastructure.providers.fake_client import FakeLLMClient
from ai_assistant.infrastructure.providers.openai_client import OpenAIResponsesClient


def get_llm_client(provider_name: str | None = None, model_name: str | None = None) -> LLMClient:
    """Build the configured LLM provider client.

    Patch 43 exposes the gateway only. Future patches decide when the chat
    orchestrator consumes this factory.
    """

    resolved_provider = (provider_name or getattr(settings, "AI_ASSISTANT_LLM_PROVIDER", "openai")).strip().lower()
    if resolved_provider == "fake":
        return FakeLLMClient(model=model_name or "fake-llm")
    if resolved_provider == "openai":
        return OpenAIResponsesClient(model=model_name)
    raise LLMProviderConfigurationError(
        f"Unsupported AI_ASSISTANT_LLM_PROVIDER: {resolved_provider or '<empty>'}."
    )
