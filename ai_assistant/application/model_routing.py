from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from django.conf import settings

from ai_assistant.domain import AssistantTurnRequest

DEFAULT_ROUTE_CODE = "default"
DEFAULT_ACTION_TYPE = "assistant.chat"


@dataclass(frozen=True)
class AIModelRoute:
    """Provider/model route selected for one assistant action.

    Routes are configuration-only. They let My Scoope send cheap/simple actions
    to cheaper models while keeping complex or higher-risk actions on stronger
    models. They never change commercial credits directly; usage observability
    and credits continue to use the actual provider/model returned by the
    gateway.
    """

    action_type: str = DEFAULT_ACTION_TYPE
    provider: str = ""
    model: str = ""
    max_output_tokens: int | None = None
    reason: str = ""
    route_code: str = DEFAULT_ROUTE_CODE

    @property
    def is_specific(self) -> bool:
        return self.route_code not in {"", DEFAULT_ROUTE_CODE}

    def as_metadata(self) -> dict[str, Any]:
        return {
            "action_type": self.action_type,
            "provider": self.provider,
            "model": self.model,
            "max_output_tokens": self.max_output_tokens,
            "reason": self.reason,
            "route_code": self.route_code,
            "is_specific": self.is_specific,
        }


def resolve_model_route_for_turn(request: AssistantTurnRequest) -> AIModelRoute:
    """Resolve the configured provider/model route for a turn.

    The setting shape is intentionally small and environment-friendly:

    AI_ASSISTANT_LLM_MODEL_ROUTES = {
        "default": {"provider": "openai", "model": "gpt-..."},
        "assistant.chat": {"provider": "openai", "model": "gpt-...-mini"},
    }
    """

    action_type = action_type_from_request(request)
    return resolve_model_route(action_type)


def resolve_model_route(action_type: str) -> AIModelRoute:
    normalized_action = normalize_action_type(action_type) or DEFAULT_ACTION_TYPE
    routes = _routes_setting()
    selected_code, payload = _select_route_payload(routes, normalized_action)
    provider = str(payload.get("provider") or getattr(settings, "AI_ASSISTANT_LLM_PROVIDER", "openai") or "openai").strip()
    model = str(payload.get("model") or _default_model_for_provider(provider) or "").strip()
    return AIModelRoute(
        action_type=normalized_action,
        provider=provider,
        model=model,
        max_output_tokens=_positive_int_or_none(payload.get("max_output_tokens")),
        reason=str(payload.get("reason") or "")[:160],
        route_code=selected_code,
    )


def action_type_from_request(request: AssistantTurnRequest) -> str:
    metadata = dict(request.metadata or {})
    explicit = metadata.get("action_type") or metadata.get("ai_action_type")
    return normalize_action_type(explicit) or DEFAULT_ACTION_TYPE


def normalize_action_type(value: Any) -> str:
    return " ".join(str(value or "").split()).replace(" ", "_").lower()[:80]


def route_max_output_tokens(*, default_max_output_tokens: int | None, route: AIModelRoute) -> int | None:
    """Return a safe max_output_tokens for the routed call.

    A route may lower the output cap for cheap/simple actions. It cannot exceed
    the global orchestrator cap from technical guardrails.
    """

    route_cap = route.max_output_tokens
    if default_max_output_tokens is None:
        return route_cap
    if route_cap is None:
        return default_max_output_tokens
    return min(int(default_max_output_tokens), int(route_cap))


def _routes_setting() -> Mapping[str, Any]:
    routes = getattr(settings, "AI_ASSISTANT_LLM_MODEL_ROUTES", {}) or {}
    return routes if isinstance(routes, Mapping) else {}


def _select_route_payload(routes: Mapping[str, Any], action_type: str) -> tuple[str, Mapping[str, Any]]:
    exact = routes.get(action_type)
    if isinstance(exact, Mapping):
        return action_type, exact

    # Prefix routes allow configuring families such as "assistant.explain.*"
    # without adding one setting per action.
    best_prefix = ""
    best_payload: Mapping[str, Any] | None = None
    for key, value in routes.items():
        route_key = str(key or "")
        if not route_key.endswith(".*") or not isinstance(value, Mapping):
            continue
        prefix = route_key[:-2]
        if action_type.startswith(prefix) and len(prefix) > len(best_prefix):
            best_prefix = prefix
            best_payload = value
    if best_payload is not None:
        return f"{best_prefix}.*", best_payload

    default = routes.get(DEFAULT_ROUTE_CODE)
    if isinstance(default, Mapping):
        return DEFAULT_ROUTE_CODE, default
    return DEFAULT_ROUTE_CODE, {}


def _default_model_for_provider(provider: str) -> str:
    if str(provider or "").strip().lower() == "openai":
        return str(getattr(settings, "AI_ASSISTANT_OPENAI_MODEL", "") or "").strip()
    return ""


def _positive_int_or_none(value: Any) -> int | None:
    if value in (None, ""):
        return None
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return None
    return parsed if parsed > 0 else None
