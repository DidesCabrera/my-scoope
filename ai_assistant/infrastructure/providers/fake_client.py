from __future__ import annotations

from collections import deque
from collections.abc import Iterable

from ai_assistant.infrastructure.providers.contracts import (
    LLMProviderRequest,
    LLMProviderRequestError,
    LLMProviderResponse,
)


class FakeLLMClient:
    """Deterministic fake provider used by tests and local orchestration work.

    The fake client records calls and returns scripted responses without network
    access, API keys or provider dependencies.
    """

    provider_name = "fake"

    def __init__(self, responses: Iterable[str] | None = None, *, model: str = "fake-llm"):
        self.model = model
        self._responses = deque(responses or [])
        self.requests: list[LLMProviderRequest] = []

    def generate(self, request: LLMProviderRequest) -> LLMProviderResponse:
        normalized_request = LLMProviderRequest(
            messages=request.normalized_messages,
            max_output_tokens=request.max_output_tokens,
            metadata=request.metadata,
        )
        self.requests.append(normalized_request)

        if self._responses:
            text = self._responses.popleft()
        else:
            text = self._build_default_response(normalized_request)

        if text is None:
            raise LLMProviderRequestError("Fake LLM response was configured as empty.")

        return LLMProviderResponse(
            provider=self.provider_name,
            model=self.model,
            text=text,
            response_id=f"fake-response-{len(self.requests)}",
            raw={"fake": True},
        )

    def _build_default_response(self, request: LLMProviderRequest) -> str:
        last_user_message = next(
            (message.content for message in reversed(request.normalized_messages) if message.role == "user"),
            "",
        )
        if not last_user_message:
            return "Respuesta fake del AI Assistant."
        return f"Respuesta fake del AI Assistant para: {last_user_message}"
