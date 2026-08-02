from __future__ import annotations

import math
import re
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation, ROUND_CEILING
from typing import Any, Mapping

from django.conf import settings
from django.db import transaction
from django.db.models import Sum
from django.utils import timezone

from ai_assistant.application.limits import estimate_provider_request_tokens
from ai_assistant.application.pricing import estimate_cost_usd
from ai_assistant.domain import AssistantTurnRequest
from ai_assistant.infrastructure.providers import LLMProviderRequest

DEFAULT_PLAN_CODE = "free"
DEFAULT_CREDIT_REASON = "ai_turn_usage"
BLOCK_REASON_MONTHLY_LIMIT = "monthly_credit_limit_exceeded"
BLOCK_REASON_DAILY_LIMIT = "daily_credit_limit_exceeded"
BLOCK_REASON_ACCOUNT_WALLET = "account_credit_wallet_limit_exceeded"
ACCOUNT_CREDIT_REFERENCE_TYPE = "ai_assistant_turn"


@dataclass(frozen=True)
class AICreditPlan:
    code: str = DEFAULT_PLAN_CODE
    monthly_credit_limit: int = 0
    daily_credit_limit: int = 0
    block_on_exhaustion: bool = False

    @property
    def monthly_is_limited(self) -> bool:
        return self.monthly_credit_limit > 0 or self.block_on_exhaustion

    @property
    def daily_is_limited(self) -> bool:
        return self.daily_credit_limit > 0


@dataclass(frozen=True)
class AICreditCheck:
    allowed: bool
    enabled: bool
    plan: AICreditPlan
    estimated_credits: int = 0
    credits_used: int = 0
    daily_credits_used: int = 0
    reason: str = ""
    account_reservation: Mapping[str, Any] | None = None

    def as_metadata(self) -> dict[str, Any]:
        return {
            "enabled": self.enabled,
            "allowed": self.allowed,
            "plan_code": self.plan.code,
            "estimated_credits": self.estimated_credits,
            "monthly_credit_limit": self.plan.monthly_credit_limit,
            "daily_credit_limit": self.plan.daily_credit_limit,
            "credits_used": self.credits_used,
            "daily_credits_used": self.daily_credits_used,
            "reason": self.reason,
            "account_reservation": dict(self.account_reservation or {}),
        }


class DjangoAICreditService:
    """Settings-driven AI credit quota service.

    Tokens and provider costs remain internal. This service exposes only AI
    credits as the commercial quota unit. Local development may disable it,
    while the deployment guard requires enforcement for the active runtime.
    """

    def check_turn_allowed(
        self,
        *,
        request: AssistantTurnRequest,
        provider_request: LLMProviderRequest,
        provider: str = "",
        model: str = "",
    ) -> AICreditCheck:
        if not credits_enabled():
            return AICreditCheck(
                allowed=True,
                enabled=False,
                plan=AICreditPlan(),
                estimated_credits=0,
            )

        user = user_from_request(request)
        plan = resolve_credit_plan(user)
        estimated_credits = estimate_request_credits(
            request=request,
            provider_request=provider_request,
            provider=provider,
            model=model,
        )
        if user is None or not getattr(user, "pk", None):
            return AICreditCheck(
                allowed=True,
                enabled=True,
                plan=plan,
                estimated_credits=estimated_credits,
                reason="anonymous_user_not_metered",
            )

        quota = get_or_create_user_credit_quota(user=user, plan=plan)
        daily_used = get_daily_credits_used(user=user)
        if quota.hard_blocked:
            return AICreditCheck(
                allowed=False,
                enabled=True,
                plan=plan,
                estimated_credits=estimated_credits,
                credits_used=quota.credits_used,
                daily_credits_used=daily_used,
                reason="credit_quota_hard_blocked",
            )

        if plan.monthly_is_limited and quota.credits_used + estimated_credits > plan.monthly_credit_limit:
            return AICreditCheck(
                allowed=False,
                enabled=True,
                plan=plan,
                estimated_credits=estimated_credits,
                credits_used=quota.credits_used,
                daily_credits_used=daily_used,
                reason=BLOCK_REASON_MONTHLY_LIMIT,
            )
        if plan.daily_is_limited and daily_used + estimated_credits > plan.daily_credit_limit:
            return AICreditCheck(
                allowed=False,
                enabled=True,
                plan=plan,
                estimated_credits=estimated_credits,
                credits_used=quota.credits_used,
                daily_credits_used=daily_used,
                reason=BLOCK_REASON_DAILY_LIMIT,
            )
        account_reservation = self._reserve_account_credits_for_turn(
            request=request,
            user=user,
            plan=plan,
            estimated_credits=estimated_credits,
            provider=provider,
            model=model,
        )
        if account_reservation.get("blocked"):
            return AICreditCheck(
                allowed=False,
                enabled=True,
                plan=plan,
                estimated_credits=estimated_credits,
                credits_used=quota.credits_used,
                daily_credits_used=daily_used,
                reason=BLOCK_REASON_ACCOUNT_WALLET,
                account_reservation=account_reservation,
            )
        return AICreditCheck(
            allowed=True,
            enabled=True,
            plan=plan,
            estimated_credits=estimated_credits,
            credits_used=quota.credits_used,
            daily_credits_used=daily_used,
            account_reservation=account_reservation,
        )

    def charge_usage_event(self, usage_event: Any) -> Mapping[str, Any]:
        if not credits_enabled():
            return {"charged": False, "disabled": True}
        user = getattr(usage_event, "user", None)
        if user is None or not getattr(user, "pk", None):
            return {"charged": False, "reason": "anonymous_user_not_metered"}

        plan = resolve_credit_plan(user)
        status = str(getattr(usage_event, "status", "") or "")
        if status != "completed":
            outcome = {
                "charged": False,
                "reason": "non_completed_turn",
                "plan_code": plan.code,
                "account_wallet": self._release_account_reservation_for_event(usage_event),
            }
            persist_usage_event_credit_outcome(
                usage_event,
                outcome=outcome,
                plan_code=plan.code,
                charged_credits=0,
            )
            return outcome

        credits = calculate_event_credits(usage_event)
        if credits <= 0:
            outcome = {
                "charged": False,
                "reason": "zero_credit_turn",
                "plan_code": plan.code,
                "account_wallet": self._release_account_reservation_for_event(usage_event),
            }
            persist_usage_event_credit_outcome(
                usage_event,
                outcome=outcome,
                plan_code=plan.code,
                charged_credits=0,
            )
            return outcome

        from ai_assistant.models import AICreditLedger, AIUserCreditQuota

        with transaction.atomic():
            quota, _created = AIUserCreditQuota.objects.select_for_update().get_or_create(
                user=user,
                period=current_period(),
                defaults={
                    "plan_code": plan.code,
                    "monthly_credit_limit": plan.monthly_credit_limit,
                    "daily_credit_limit": plan.daily_credit_limit,
                },
            )
            quota.plan_code = plan.code
            quota.monthly_credit_limit = plan.monthly_credit_limit
            quota.daily_credit_limit = plan.daily_credit_limit
            quota.credits_used = int(quota.credits_used or 0) + credits
            quota.save(
                update_fields=[
                    "plan_code",
                    "monthly_credit_limit",
                    "daily_credit_limit",
                    "credits_used",
                    "updated_at",
                ]
            )
            ledger = AICreditLedger.objects.create(
                user=user,
                usage_event=usage_event,
                period=quota.period,
                plan_code=plan.code,
                action_type=getattr(usage_event, "action_type", ""),
                credits=credits,
                reason=DEFAULT_CREDIT_REASON,
                metadata={
                    "usage_event_id": usage_event.pk,
                    "estimated_cost_usd": str(getattr(usage_event, "estimated_cost_usd", "") or ""),
                    "provider": getattr(usage_event, "provider", ""),
                    "model_name": getattr(usage_event, "model_name", ""),
                },
            )

        account_wallet_summary = self._consume_account_reservation_for_event(usage_event, credits=credits)
        outcome = {
            "charged": True,
            "ledger_id": ledger.pk,
            "plan_code": plan.code,
            "credits": credits,
            "credits_used_after": quota.credits_used,
            "monthly_credit_limit": quota.monthly_credit_limit,
            "daily_credit_limit": quota.daily_credit_limit,
            "account_wallet": account_wallet_summary,
        }
        persist_usage_event_credit_outcome(
            usage_event,
            outcome=outcome,
            plan_code=plan.code,
            charged_credits=credits,
        )
        return outcome

    def _reserve_account_credits_for_turn(
        self,
        *,
        request: AssistantTurnRequest,
        user: Any,
        plan: AICreditPlan,
        estimated_credits: int,
        provider: str = "",
        model: str = "",
    ) -> Mapping[str, Any]:
        reference_id = _credit_reference_from_request(request)
        if not reference_id:
            return {"reserved": False, "reason": "missing_turn_reference"}
        try:
            from accounts.services.credits import InsufficientAccountCredits, reserve_account_credits

            return reserve_account_credits(
                user=user,
                credits=estimated_credits,
                reference_type=ACCOUNT_CREDIT_REFERENCE_TYPE,
                reference_id=reference_id,
                reason="ai_turn_estimated_credit_reservation",
                metadata={
                    "plan_code": plan.code,
                    "provider": provider,
                    "model": model,
                    "estimated_credits": estimated_credits,
                    "source": "ai_assistant.preflight",
                },
            )
        except InsufficientAccountCredits:
            return {"reserved": False, "blocked": True, "reason": "insufficient_account_credits"}
        except Exception as exc:  # pragma: no cover - defensive optional integration
            return {"reserved": False, "reason": "account_wallet_unavailable", "error_type": exc.__class__.__name__}

    def _consume_account_reservation_for_event(self, usage_event: Any, *, credits: int) -> Mapping[str, Any]:
        reference_id = _credit_reference_from_event(usage_event)
        if not reference_id:
            return {"consumed": False, "reason": "missing_turn_reference"}
        try:
            from accounts.services.credits import InsufficientAccountCredits, consume_account_credit_reservation

            return consume_account_credit_reservation(
                user=getattr(usage_event, "user", None),
                credits=credits,
                reference_type=ACCOUNT_CREDIT_REFERENCE_TYPE,
                reference_id=reference_id,
                reason="ai_turn_actual_credit_consumption",
                metadata={
                    "usage_event_id": getattr(usage_event, "pk", None),
                    "provider": getattr(usage_event, "provider", ""),
                    "model_name": getattr(usage_event, "model_name", ""),
                    "charged_credits": credits,
                    "source": "ai_assistant.usage_event",
                },
            )
        except InsufficientAccountCredits:
            return {"consumed": False, "blocked": True, "reason": "insufficient_account_credits"}
        except Exception as exc:  # pragma: no cover - defensive optional integration
            return {"consumed": False, "reason": "account_wallet_unavailable", "error_type": exc.__class__.__name__}

    def _release_account_reservation_for_event(self, usage_event: Any) -> Mapping[str, Any]:
        reference_id = _credit_reference_from_event(usage_event)
        if not reference_id:
            return {"released": False, "reason": "missing_turn_reference"}
        try:
            from accounts.services.credits import release_account_credit_reservation

            return release_account_credit_reservation(
                user=getattr(usage_event, "user", None),
                reference_type=ACCOUNT_CREDIT_REFERENCE_TYPE,
                reference_id=reference_id,
                reason="ai_turn_credit_release_after_non_completed_event",
                metadata={
                    "usage_event_id": getattr(usage_event, "pk", None),
                    "status": getattr(usage_event, "status", ""),
                    "source": "ai_assistant.usage_event",
                },
            )
        except Exception as exc:  # pragma: no cover - defensive optional integration
            return {"released": False, "reason": "account_wallet_unavailable", "error_type": exc.__class__.__name__}



def credits_enabled() -> bool:
    return _settings_bool("AI_ASSISTANT_CREDITS_ENABLED", False)


def current_period() -> str:
    return timezone.localdate().strftime("%Y-%m")


def resolve_credit_plan(user: Any | None) -> AICreditPlan:
    account_plan = _account_credit_plan(user)
    if account_plan is not None:
        return AICreditPlan(**account_plan.as_ai_credit_plan_kwargs())

    plans = _credit_plans_setting()
    aliases = _credit_plan_aliases_setting()
    candidates = _plan_candidates(user)
    for candidate in candidates:
        aliased = aliases.get(candidate, candidate)
        raw_plan = plans.get(aliased)
        if isinstance(raw_plan, Mapping):
            return _coerce_credit_plan(code=aliased, payload=raw_plan)
        # ACC07 keeps aliases such as member -> basic for the new account
        # plans, but legacy tests/deployments may still override only the old
        # member/nutritionist setting keys. In that case, prefer the explicit
        # candidate instead of falling through to free/default.
        raw_candidate = plans.get(candidate)
        if isinstance(raw_candidate, Mapping):
            return _coerce_credit_plan(code=candidate, payload=raw_candidate)
    raw_default = plans.get(DEFAULT_PLAN_CODE, {})
    return _coerce_credit_plan(code=DEFAULT_PLAN_CODE, payload=raw_default if isinstance(raw_default, Mapping) else {})


def estimate_request_credits(
    *,
    request: AssistantTurnRequest,
    provider_request: LLMProviderRequest,
    provider: str = "",
    model: str = "",
) -> int:
    input_tokens = estimate_provider_request_tokens(provider_request)
    cost = estimate_cost_usd(
        provider=provider,
        model=model,
        input_tokens=input_tokens,
        cached_input_tokens=0,
        output_tokens=provider_request.max_output_tokens or 0,
    )
    action_type = _action_type_from_request(request)
    return _credits_from_cost_or_default(cost=cost, action_type=action_type)


def calculate_event_credits(usage_event: Any) -> int:
    return _credits_from_cost_or_default(
        cost=getattr(usage_event, "estimated_cost_usd", None),
        action_type=getattr(usage_event, "action_type", ""),
    )


def persist_usage_event_credit_outcome(
    usage_event: Any,
    *,
    outcome: Mapping[str, Any],
    plan_code: str,
    charged_credits: int,
) -> None:
    """Attach the final commercial credit outcome to the AI usage event.

    `AIUsageEvent` remains the operational source of truth for provider/model,
    tokens, cost and status. The account wallet owns commercial balances, so the
    event stores only a sanitized correlation summary back to the account ledger.
    """

    if usage_event is None or not getattr(usage_event, "pk", None):
        return
    metadata = dict(getattr(usage_event, "metadata", {}) or {})
    metadata["account_credit_outcome"] = _sanitize_credit_outcome(outcome)
    usage_event.metadata = metadata
    usage_event.credit_plan_code = str(plan_code or "")[:50]
    usage_event.charged_credits = _non_negative_int(charged_credits)
    usage_event.save(update_fields=["credit_plan_code", "charged_credits", "metadata"])


def _sanitize_credit_outcome(value: Any, *, depth: int = 0) -> Any:
    if depth > 3:
        return str(value)[:200]
    if isinstance(value, Mapping):
        return {str(key)[:80]: _sanitize_credit_outcome(item, depth=depth + 1) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_sanitize_credit_outcome(item, depth=depth + 1) for item in value[:20]]
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    return str(value)[:200]


def get_or_create_user_credit_quota(*, user: Any, plan: AICreditPlan):
    from ai_assistant.models import AIUserCreditQuota

    quota, _created = AIUserCreditQuota.objects.get_or_create(
        user=user,
        period=current_period(),
        defaults={
            "plan_code": plan.code,
            "monthly_credit_limit": plan.monthly_credit_limit,
            "daily_credit_limit": plan.daily_credit_limit,
        },
    )
    update_fields: list[str] = []
    if quota.plan_code != plan.code:
        quota.plan_code = plan.code
        update_fields.append("plan_code")
    if quota.monthly_credit_limit != plan.monthly_credit_limit:
        quota.monthly_credit_limit = plan.monthly_credit_limit
        update_fields.append("monthly_credit_limit")
    if quota.daily_credit_limit != plan.daily_credit_limit:
        quota.daily_credit_limit = plan.daily_credit_limit
        update_fields.append("daily_credit_limit")
    if update_fields:
        update_fields.append("updated_at")
        quota.save(update_fields=update_fields)
    return quota


def get_daily_credits_used(*, user: Any) -> int:
    from ai_assistant.models import AICreditLedger

    today = timezone.localdate()
    value = (
        AICreditLedger.objects.filter(user=user, created_at__date=today)
        .aggregate(total=Sum("credits"))
        .get("total")
    )
    return int(value or 0)


def user_from_request(request: AssistantTurnRequest) -> Any | None:
    metadata = dict(request.metadata or {})
    return metadata.get("tool_user") or metadata.get("user") or metadata.get("current_user")


def _credits_from_cost_or_default(*, cost: Any, action_type: str) -> int:
    base_credits = _default_credits_per_turn()
    decimal_cost = _decimal_or_none(cost)
    credit_value = _usd_per_credit()
    if decimal_cost is not None and credit_value is not None and credit_value > 0:
        base_credits = int((decimal_cost / credit_value).to_integral_value(rounding=ROUND_CEILING))
    base_credits = max(1, int(base_credits or 1))
    multiplier = _action_multiplier(action_type)
    credits = Decimal(base_credits) * multiplier
    return max(1, int(credits.to_integral_value(rounding=ROUND_CEILING)))


def _action_multiplier(action_type: str) -> Decimal:
    mapping = getattr(settings, "AI_ASSISTANT_ACTION_CREDIT_MULTIPLIERS", {}) or {}
    raw = mapping.get(action_type) or mapping.get("default") or "1"
    try:
        return max(Decimal("0"), Decimal(str(raw)))
    except (InvalidOperation, TypeError, ValueError):
        return Decimal("1")


def _default_credits_per_turn() -> int:
    try:
        return max(1, int(getattr(settings, "AI_ASSISTANT_DEFAULT_CREDITS_PER_TURN", 1)))
    except (TypeError, ValueError):
        return 1


def _usd_per_credit() -> Decimal | None:
    value = getattr(settings, "AI_ASSISTANT_USD_PER_AI_CREDIT", "0.001")
    try:
        decimal_value = Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError):
        return None
    return decimal_value if decimal_value > 0 else None


def _decimal_or_none(value: Any) -> Decimal | None:
    if value in (None, ""):
        return None
    try:
        return Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError):
        return None


def _account_credit_plan(user: Any | None) -> Any | None:
    try:
        from accounts.services.credits import resolve_account_credit_plan_snapshot

        return resolve_account_credit_plan_snapshot(user)
    except Exception:  # pragma: no cover - account integration must not break the assistant
        return None


def _credit_reference_from_request(request: AssistantTurnRequest) -> str:
    metadata = dict(request.metadata or {})
    for key in ("turn_id", "message_id", "request_id", "chat_message_id"):
        value = metadata.get(key)
        if value:
            return str(value)[:120]
    conversation_id = metadata.get("conversation_id") or metadata.get("chat_id")
    action_type = _action_type_from_request(request)
    if conversation_id:
        return f"{conversation_id}:{action_type}"[:120]
    return ""


def _credit_reference_from_event(usage_event: Any) -> str:
    for value in (
        getattr(usage_event, "turn_id", ""),
        dict(getattr(usage_event, "metadata", {}) or {}).get("turn_id"),
        dict(getattr(usage_event, "metadata", {}) or {}).get("message_id"),
    ):
        if value:
            return str(value)[:120]
    conversation_id = getattr(usage_event, "conversation_id", "")
    action_type = getattr(usage_event, "action_type", "")
    if conversation_id:
        return f"{conversation_id}:{action_type}"[:120]
    return ""



def _credit_plans_setting() -> Mapping[str, Any]:
    plans = getattr(settings, "AI_ASSISTANT_CREDIT_PLANS", {}) or {}
    return plans if isinstance(plans, Mapping) else {}


def _credit_plan_aliases_setting() -> Mapping[str, str]:
    aliases = getattr(settings, "AI_ASSISTANT_CREDIT_PLAN_ALIASES", {}) or {}
    if not isinstance(aliases, Mapping):
        return {}
    return {str(key): str(value) for key, value in aliases.items()}


def _coerce_credit_plan(*, code: str, payload: Mapping[str, Any]) -> AICreditPlan:
    return AICreditPlan(
        code=str(payload.get("code") or code or DEFAULT_PLAN_CODE)[:50],
        monthly_credit_limit=_non_negative_int(payload.get("monthly_credit_limit", 0)),
        daily_credit_limit=_non_negative_int(payload.get("daily_credit_limit", 0)),
        block_on_exhaustion=_truthy(payload.get("block_on_exhaustion", False)),
    )


def _non_negative_int(value: Any) -> int:
    try:
        return max(0, int(value or 0))
    except (TypeError, ValueError):
        return 0


def _settings_bool(name: str, default: bool) -> bool:
    return _truthy(getattr(settings, name, default))


def _truthy(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"1", "true", "yes", "on"}


def _plan_candidates(user: Any | None) -> tuple[str, ...]:
    if user is None or not getattr(user, "pk", None):
        return (DEFAULT_PLAN_CODE,)
    candidates: list[str] = []
    profile = getattr(user, "profile", None)
    plan = getattr(profile, "plan", None)
    for value in (
        getattr(plan, "name", ""),
        getattr(plan, "role", ""),
        getattr(profile, "role", ""),
        DEFAULT_PLAN_CODE,
    ):
        normalized = _slugify_plan_code(value)
        if normalized and normalized not in candidates:
            candidates.append(normalized)
    return tuple(candidates or [DEFAULT_PLAN_CODE])


def _slugify_plan_code(value: Any) -> str:
    text = str(value or "").strip().lower()
    text = re.sub(r"[^a-z0-9]+", "_", text).strip("_")
    return text[:50]


def _action_type_from_request(request: AssistantTurnRequest) -> str:
    value = dict(request.metadata or {}).get("action_type") or "assistant.chat"
    return " ".join(str(value or "").split()).replace(" ", "_").lower()[:80]
