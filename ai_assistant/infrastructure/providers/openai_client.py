from __future__ import annotations

import json
import logging
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

logger = logging.getLogger(__name__)


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
        payload = build_openai_responses_payload(request, model=self.model)

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
            raise _provider_request_error_from_http(response)

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



def build_openai_responses_payload(
    request: LLMProviderRequest,
    *,
    model: str,
) -> dict[str, Any]:
    """Build the exact payload sent to the OpenAI Responses API.

    PT02 diagnostics import this helper so the payload printed by the probe is
    produced by the same code path as production. Keeping one builder prevents
    a simplified probe from going green while the real orchestrator request is
    malformed.
    """

    messages = request.normalized_messages
    input_items = [message.as_openai_input_item() for message in messages]
    input_items.extend(_continuation_input_items(request))
    validate_openai_responses_continuation(input_items)
    if not input_items:
        raise LLMProviderRequestError(
            "OpenAI request requires messages, continuation items or tool outputs."
        )

    payload: dict[str, Any] = {
        "model": str(model or "").strip(),
        "input": input_items,
        "store": False,
        # Stateless reasoning/tool loops must return encrypted reasoning items
        # so they can be supplied again with function outputs.
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
    return payload


def validate_openai_responses_continuation(input_items: list[dict[str, Any]]) -> None:
    """Validate the stateless Responses continuation before provider I/O.

    PT05 makes this contract reusable by both the real OpenAI adapter and the
    fake provider used in orchestration tests. A fake that accepts malformed
    call correlation or unreplayable reasoning would recreate the blind spot
    that allowed the production follow-up failure to stay green offline.
    """

    _validate_function_call_correlations(input_items)
    _validate_reasoning_continuity(input_items)


def _validate_function_call_correlations(input_items: list[dict[str, Any]]) -> None:
    """Require an exact one-to-one mapping between function calls and outputs.

    ``call_id`` is an opaque, case-sensitive provider identifier. A missing,
    rewritten or duplicated output would otherwise produce a remote 400 after
    the tool has already executed. Fail locally with a precise transport error
    before any HTTP request is sent.
    """

    function_call_ids: list[str] = []
    function_output_ids: list[str] = []
    for item in input_items:
        item_type = str(item.get("type") or "")
        if item_type == "function_call":
            call_id = str(item.get("call_id") or "")
            if not call_id:
                raise LLMProviderRequestError(
                    "OpenAI continuation contains a function_call without call_id."
                )
            function_call_ids.append(call_id)
        elif item_type == "function_call_output":
            call_id = str(item.get("call_id") or "")
            if not call_id:
                raise LLMProviderRequestError(
                    "OpenAI continuation contains a function_call_output without call_id."
                )
            function_output_ids.append(call_id)

    if not function_call_ids and not function_output_ids:
        return

    missing = [call_id for call_id in function_call_ids if function_output_ids.count(call_id) == 0]
    duplicates = [
        call_id
        for call_id in dict.fromkeys(function_output_ids)
        if function_output_ids.count(call_id) > 1
    ]
    unexpected = [call_id for call_id in function_output_ids if call_id not in function_call_ids]
    if missing or duplicates or unexpected:
        details: list[str] = []
        if missing:
            details.append(f"missing outputs for {missing}")
        if duplicates:
            details.append(f"duplicate outputs for {duplicates}")
        if unexpected:
            details.append(f"outputs without calls {unexpected}")
        raise LLMProviderRequestError(
            "Invalid OpenAI function-call continuation: " + "; ".join(details)
        )


def _validate_reasoning_continuity(input_items: list[dict[str, Any]]) -> None:
    """Require replayable encrypted reasoning for stateless continuations.

    With ``store=false`` the Responses API cannot recover a prior reasoning
    item by id. Any replayed reasoning item therefore needs the opaque
    ``encrypted_content`` returned by the provider. Empty or stripped content
    is rejected locally instead of becoming a remote post-tool 400.
    """

    invalid_ids: list[str] = []
    for item in input_items:
        if str(item.get("type") or "") != "reasoning":
            continue
        if not str(item.get("encrypted_content") or "").strip():
            invalid_ids.append(str(item.get("id") or "<missing-id>"))
    if invalid_ids:
        raise LLMProviderRequestError(
            "Invalid OpenAI reasoning continuation: encrypted_content is required "
            f"for reasoning items {invalid_ids}."
        )


def _provider_request_error_from_http(response: requests.Response) -> LLMProviderRequestError:
    """Preserve the provider error body instead of discarding it.

    OpenAI returns ``{"error": {"message", "type", "code", "param"}}`` on 4xx/5xx.
    That message names the exact defect (for example an unmatched
    ``function_call_output`` call_id, or a reasoning item supplied without its
    encrypted content under ``store=false``). Keeping and logging it is the
    difference between guessing and reading the cause. The API key is never
    logged, and only a bounded slice of the body is retained.
    """

    status_code = response.status_code
    request_id = str(getattr(response, "headers", {}).get("x-request-id") or "")
    error_type = error_code = error_message = error_param = ""
    try:
        body = response.json()
    except ValueError:
        body = None
    if isinstance(body, Mapping):
        error_obj = body.get("error")
        if isinstance(error_obj, Mapping):
            error_type = str(error_obj.get("type") or "")
            error_code = str(error_obj.get("code") or "")
            error_message = str(error_obj.get("message") or "")
            param = error_obj.get("param")
            error_param = "" if param is None else str(param)
    if not error_message:
        # Fall back to a bounded slice of the raw body so nothing is lost.
        error_message = str(getattr(response, "text", "") or "").strip()[:600]

    logger.warning(
        "OpenAI provider request failed: status=%s type=%s code=%s param=%s request_id=%s message=%s",
        status_code,
        error_type or "-",
        error_code or "-",
        error_param or "-",
        request_id or "-",
        error_message[:600] or "-",
    )
    return LLMProviderRequestError(
        f"OpenAI provider request failed with status {status_code}"
        + (f": {error_message}" if error_message else "."),
        status_code=status_code,
        error_type=error_type,
        error_code=error_code,
        error_message=error_message,
        error_param=error_param,
        request_id=request_id,
    )


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
