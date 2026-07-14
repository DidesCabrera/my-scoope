from __future__ import annotations

import json
from typing import Any, Mapping

import requests
from django.conf import settings

from ai_assistant.infrastructure.providers.contracts import (
    LLMProviderConfigurationError,
    LLMProviderRequest,
    LLMProviderRequestError,
    LLMProviderResponse,
    LLMProviderToolCall,
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
        input_items = [message.as_openai_input_item() for message in messages]
        input_items.extend(_continuation_input_items(request))
        if not input_items:
            raise LLMProviderRequestError(
                "OpenAI request requires messages, continuation items or tool outputs."
            )

        payload: dict[str, Any] = {
            "model": self.model,
            "input": input_items,
            "store": False,
            # Stateless reasoning/tool loops must return encrypted reasoning
            # items so they can be supplied again with function outputs.
            "include": ["reasoning.encrypted_content"],
        }
        text_format = _structured_text_format(request)
        if text_format:
            payload["text"] = text_format
        reasoning = _reasoning_config(request)
        if reasoning:
            payload["reasoning"] = reasoning
        tools = _provider_tools(request)
        if tools:
            payload["tools"] = tools
            if request.tool_choice is not None:
                payload["tool_choice"] = request.tool_choice
            if request.parallel_tool_calls is not None:
                payload["parallel_tool_calls"] = bool(request.parallel_tool_calls)
            # My Scoope enforces its function-call count locally. The API
            # ``max_tool_calls`` setting applies to built-in tools, not custom
            # functions, so forwarding it here would provide false assurance.
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
        tool_calls = _extract_tool_calls(data)
        if not text and not tool_calls:
            raise LLMProviderRequestError(
                "OpenAI provider response did not contain output text or function calls."
            )

        return LLMProviderResponse(
            provider=self.provider_name,
            model=str(data.get("model") or self.model),
            text=text,
            response_id=str(data.get("id") or ""),
            usage=_extract_usage(data),
            raw=data if isinstance(data, Mapping) else {},
            tool_calls=tool_calls,
            continuation_items=_extract_continuation_items(data),
        )

    def _validate_configuration(self) -> None:
        if not self.api_key:
            raise LLMProviderConfigurationError("AI_ASSISTANT_OPENAI_API_KEY is not configured.")
        if not self.model:
            raise LLMProviderConfigurationError("AI_ASSISTANT_OPENAI_MODEL is not configured.")
        if not self.base_url:
            raise LLMProviderConfigurationError("AI_ASSISTANT_OPENAI_BASE_URL is not configured.")



def _continuation_input_items(request: LLMProviderRequest) -> list[dict[str, Any]]:
    """Build a stateless Responses API continuation input.

    OpenAI requires model output items (including encrypted reasoning items for
    ``store=false``) to be supplied again alongside ``function_call_output``
    items. Only explicit continuation fields from the provider contract are
    forwarded.
    """

    items: list[dict[str, Any]] = []
    for item in tuple(request.continuation_items or ()):
        safe_item = _safe_continuation_item(item)
        if safe_item:
            items.append(safe_item)
    for tool_output in tuple(request.tool_outputs or ()):
        if not tool_output.call_id:
            continue
        output = tool_output.output
        if isinstance(output, Mapping):
            output_text = json.dumps(output, ensure_ascii=False, sort_keys=True)
        else:
            output_text = str(output or "")
        items.append(
            {
                "type": "function_call_output",
                "call_id": tool_output.call_id,
                "output": output_text,
            }
        )
    return items


def _safe_continuation_item(item: Mapping[str, Any]) -> dict[str, Any]:
    item_type = str(item.get("type") or "")
    allowed_keys_by_type = {
        "reasoning": {"type", "id", "summary", "encrypted_content", "status"},
        "function_call": {"type", "id", "call_id", "name", "arguments", "status"},
        "message": {"type", "id", "role", "content", "status", "phase"},
        "function_call_output": {"type", "id", "call_id", "output", "status"},
    }
    allowed_keys = allowed_keys_by_type.get(item_type)
    if not allowed_keys:
        return {}
    return {key: value for key, value in dict(item).items() if key in allowed_keys}


def _extract_continuation_items(data: Mapping[str, Any]) -> tuple[Mapping[str, Any], ...]:
    items: list[Mapping[str, Any]] = []
    for output_item in data.get("output", []) or []:
        if not isinstance(output_item, Mapping):
            continue
        safe_item = _safe_continuation_item(output_item)
        if safe_item:
            items.append(safe_item)
    return tuple(items)


def _provider_tools(request: LLMProviderRequest) -> list[dict[str, Any]]:
    """Whitelist provider-native function declarations from the request contract."""

    tools: list[dict[str, Any]] = []
    for item in tuple(request.tools or ()):
        if not isinstance(item, Mapping):
            continue
        name = "".join(
            character
            for character in str(item.get("name") or "").strip()
            if character.isalnum() or character in {"_", "-"}
        )[:64]
        parameters = item.get("parameters")
        if not name or not isinstance(parameters, Mapping):
            continue
        tools.append(
            {
                "type": "function",
                "name": name,
                "description": str(item.get("description") or "")[:1024],
                "parameters": dict(parameters),
                # Several My Scoope tools intentionally accept draft-shaped
                # objects whose properties are validated server-side. Keep
                # provider calling best-effort and preserve My Scoope as the
                # canonical validation boundary.
                "strict": bool(item.get("strict", False)),
            }
        )
    return tools


def _extract_tool_calls(data: Mapping[str, Any]) -> tuple[LLMProviderToolCall, ...]:
    calls: list[LLMProviderToolCall] = []
    for output_item in data.get("output", []) or []:
        if not isinstance(output_item, Mapping):
            continue
        if str(output_item.get("type") or "") != "function_call":
            continue
        raw_arguments = output_item.get("arguments")
        arguments: Mapping[str, Any] = {}
        parse_error = ""
        if isinstance(raw_arguments, Mapping):
            arguments = dict(raw_arguments)
        else:
            try:
                decoded = json.loads(str(raw_arguments or "{}"))
                if not isinstance(decoded, Mapping):
                    raise ValueError("function arguments must be a JSON object")
                arguments = dict(decoded)
            except (TypeError, ValueError, json.JSONDecodeError) as exc:
                parse_error = f"invalid_function_arguments:{exc.__class__.__name__}"
        calls.append(
            LLMProviderToolCall(
                name=str(output_item.get("name") or ""),
                arguments=arguments,
                call_id=str(output_item.get("call_id") or output_item.get("id") or ""),
                parse_error=parse_error,
            )
        )
    return tuple(calls)


def _structured_text_format(request: LLMProviderRequest) -> dict[str, Any]:
    """Whitelist the provider-enforced structured response contract.

    My Scoope sends the JSON Schema through internal request metadata; only this
    explicit transport field is forwarded. ``json_object`` remains a backwards
    compatible fallback for older internal callers without a schema.
    """

    metadata = dict(request.metadata or {})
    response_format = str(metadata.get("format") or "")
    if not response_format.startswith("ai_assistant_structured_response."):
        return {}

    schema = metadata.get("response_json_schema")
    if isinstance(schema, Mapping):
        name = str(metadata.get("response_schema_name") or "ai_assistant_structured_response")
        name = "".join(character for character in name if character.isalnum() or character in {"_", "-"})[:64]
        return {
            "format": {
                "type": "json_schema",
                "name": name or "ai_assistant_structured_response",
                "description": "Structured My Scoope assistant message and semantic intent.",
                "schema": dict(schema),
                "strict": bool(metadata.get("response_schema_strict", True)),
            },
            "verbosity": "low",
        }
    return {"format": {"type": "json_object"}, "verbosity": "low"}


def _reasoning_config(request: LLMProviderRequest) -> dict[str, str]:
    metadata = dict(request.metadata or {})
    effort = str(metadata.get("reasoning_effort") or "").strip().lower()
    if effort not in {"none", "minimal", "low", "medium", "high", "xhigh"}:
        return {}
    return {"effort": effort}


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
