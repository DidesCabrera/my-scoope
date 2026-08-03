from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from accounts.models import AccountPlan
from accounts.services.credits import DEFAULT_ACCOUNT_PLAN_SLUG, resolve_account_plan_for_user

NUTRITION_WORKSPACE_KEY = "nutrition_workspace"

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
    """Commercial capabilities resolved exclusively from the accounts domain."""

    plan_slug: str
    plan_name: str
    source: str
    nutrition_workspace: Mapping[str, Any]

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
    if user is None or not getattr(user, "pk", None):
        return None

    account_plan = resolve_account_plan_for_user(user)
    if account_plan is None:
        return AccountEntitlements(
            plan_slug=DEFAULT_ACCOUNT_PLAN_SLUG,
            plan_name="Sin plan comercial",
            source="built_in_defaults",
            nutrition_workspace=dict(DEFAULT_NUTRITION_WORKSPACE_ENTITLEMENTS),
        )

    merged = dict(DEFAULT_NUTRITION_WORKSPACE_ENTITLEMENTS)
    merged.update(_account_nutrition_entitlements(account_plan))
    return AccountEntitlements(
        plan_slug=account_plan.slug,
        plan_name=account_plan.name,
        source="accounts_account_plan",
        nutrition_workspace=merged,
    )


def _account_nutrition_entitlements(plan: AccountPlan) -> Mapping[str, Any]:
    entitlements = plan.entitlements or {}
    values = entitlements.get(NUTRITION_WORKSPACE_KEY) or {}
    return dict(values) if isinstance(values, Mapping) else {}
