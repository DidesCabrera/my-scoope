from __future__ import annotations

from collections import deque
from collections.abc import Iterable

from ai_assistant.infrastructure.providers.contracts import (
    LLMProviderRequest,
    LLMProviderRequestError,
    LLMProviderResponse,
)
from ai_assistant.infrastructure.providers.openai_client import (
    _continuation_input_items,
    validate_openai_responses_continuation,
)


class FakeLLMClient:
    """Deterministic fake provider used by tests and local orchestration work.

    The fake client records calls and returns scripted responses without network
    access or API keys. It still validates stateless continuation items against
    the production Responses transport contract so malformed post-tool requests
    fail offline instead of being accepted only by the test double.
    """

    provider_name = "fake"

    def __init__(self, responses: Iterable[str] | None = None, *, model: str = "fake-llm"):
        self.model = model
        self._responses = deque(responses or [])
        self.requests: list[LLMProviderRequest] = []
        self.generated_responses: list[LLMProviderResponse] = []

    def generate(self, request: LLMProviderRequest) -> LLMProviderResponse:
        normalized_request = LLMProviderRequest(
            messages=request.normalized_messages,
            max_output_tokens=request.max_output_tokens,
            metadata=request.metadata,
            tools=request.tools,
            tool_choice=request.tool_choice,
            parallel_tool_calls=request.parallel_tool_calls,
            max_tool_calls=request.max_tool_calls,
            continuation_items=request.continuation_items,
            tool_outputs=request.tool_outputs,
        )
        continuation_input = _continuation_input_items(normalized_request)
        has_native_continuation = any(
            str(item.get("type") or "") in {"function_call", "reasoning"}
            for item in tuple(normalized_request.continuation_items or ())
        )
        if has_native_continuation:
            validate_openai_responses_continuation(continuation_input)
        self.requests.append(normalized_request)

        if self._responses:
            text = self._responses.popleft()
        else:
            text = self._build_default_response(normalized_request)

        if text is None:
            raise LLMProviderRequestError("Fake LLM response was configured as empty.")

        response = LLMProviderResponse(
            provider=self.provider_name,
            model=self.model,
            text=text,
            response_id=f"fake-response-{len(self.requests)}",
            raw={"fake": True},
        )
        self.generated_responses.append(response)
        return response

    def _build_default_response(self, request: LLMProviderRequest) -> str:
        last_user_message = next(
            (message.content for message in reversed(request.normalized_messages) if message.role == "user"),
            "",
        )
        if not last_user_message:
            return "Respuesta fake del AI Assistant."
        return f"Respuesta fake del AI Assistant para: {last_user_message}"
