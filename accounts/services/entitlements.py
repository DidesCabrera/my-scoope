from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from accounts.models import AccountPlan
from accounts.services.credits import DEFAULT_ACCOUNT_PLAN_SLUG, resolve_account_plan_for_user

NUTRITION_WORKSPACE_KEY = "nutrition_workspace"

_BOOL_ENTITLEMENTS = (
    "can_create_food",
    "can_create_meal",
    "can_create_dailyplan",
    "can_create_program",
    "can_publish",
    "can_fork",
    "can_copy",
)
_INT_ENTITLEMENTS = (
    "max_program_duration_days",
    "max_active_subscriptions",
)

DEFAULT_NUTRITION_WORKSPACE_ENTITLEMENTS: dict[str, Any] = {
    "can_create_food": True,
    "can_create_meal": True,
    "can_create_dailyplan": True,
    "can_create_program": False,
    "can_publish": False,
    "can_fork": True,
    "can_copy": False,
    "max_program_duration_days": None,
    "max_active_subscriptions": None,
}


@dataclass(frozen=True)
class AccountEntitlements:
    """Resolved commercial entitlements for product features.

    ACC07 makes `accounts` the preferred source for capabilities while keeping
    `notas.Profile.plan` as an explicit fallback during the migration window.
    """

    plan_slug: str
    plan_name: str
    source: str
    nutrition_workspace: Mapping[str, Any]
    legacy_plan_role: str = ""

    def enabled(self, key: str, *, default: bool = False) -> bool:
        return bool(self.nutrition_workspace.get(key, default))

    def limit(self, key: str) -> int | None:
        value = self.nutrition_workspace.get(key)
        if value in (None, ""):
            return None
        try:
            return max(int(value), 0)
        except (TypeError, ValueError):
            return None



def resolve_account_entitlements(user: Any | None) -> AccountEntitlements | None:
    """Resolve feature entitlements for a user.

    Priority:
    1. Active `accounts.AccountSubscription` / effective `AccountPlan`.
    2. Legacy `notas.Profile.plan` values for missing keys or missing account plan.
    3. Conservative built-in defaults.
    """

    if user is None or not getattr(user, "pk", None):
        return None

    profile = getattr(user, "profile", None)
    legacy = _legacy_nutrition_entitlements(profile)
    account_plan = resolve_account_plan_for_user(user)

    if account_plan is None:
        merged = _merge_nutrition_entitlements(None, legacy)
        return AccountEntitlements(
            plan_slug=DEFAULT_ACCOUNT_PLAN_SLUG,
            plan_name="Plan legacy",
            source="legacy_profile_plan",
            nutrition_workspace=merged,
            legacy_plan_role=_legacy_plan_role(profile),
        )

    account_values = _account_nutrition_entitlements(account_plan)
    merged = _merge_nutrition_entitlements(account_values, legacy)
    return AccountEntitlements(
        plan_slug=account_plan.slug,
        plan_name=account_plan.name,
        source="accounts_account_plan",
        nutrition_workspace=merged,
        legacy_plan_role=_legacy_plan_role(profile),
    )


def _account_nutrition_entitlements(plan: AccountPlan) -> Mapping[str, Any]:
    entitlements = plan.entitlements or {}
    values = entitlements.get(NUTRITION_WORKSPACE_KEY) or {}
    if not isinstance(values, Mapping):
        return {}
    return dict(values)


def _legacy_nutrition_entitlements(profile: Any | None) -> Mapping[str, Any]:
    plan = getattr(profile, "plan", None)
    if plan is None:
        return {}
    values: dict[str, Any] = {}
    for key in _BOOL_ENTITLEMENTS:
        if hasattr(plan, key):
            values[key] = bool(getattr(plan, key))
    for key in _INT_ENTITLEMENTS:
        if hasattr(plan, key):
            values[key] = getattr(plan, key)
    return values


def _merge_nutrition_entitlements(
    account_values: Mapping[str, Any] | None,
    legacy_values: Mapping[str, Any] | None,
) -> dict[str, Any]:
    merged = dict(DEFAULT_NUTRITION_WORKSPACE_ENTITLEMENTS)
    for key, value in (legacy_values or {}).items():
        if value is not None:
            merged[key] = value
    for key, value in (account_values or {}).items():
        if value is not None:
            merged[key] = value
    return merged


def _legacy_plan_role(profile: Any | None) -> str:
    plan = getattr(profile, "plan", None)
    return str(getattr(plan, "role", "") or getattr(profile, "role", "") or "")
