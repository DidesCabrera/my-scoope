"""Cross-channel commercial limits for nutrition workspace actions."""

from __future__ import annotations

from accounts.services.entitlements import resolve_account_entitlements
from notas.domain.models import DailyPlan, Meal, Program, SavedComparison


class CommercialLimitReached(ValueError):
    """A new action exceeds the effective plan; existing content stays available."""


_LIMIT_KEYS = {
    "meal": "max_meals",
    "dailyplan": "max_dailyplans",
    "program": "max_programs",
    "comparison": "max_saved_comparisons",
}


def workspace_usage(user) -> dict[str, int]:
    """Count personal library objects, excluding embedded composition snapshots."""

    return {
        "meal": Meal.objects.filter(created_by=user, pending_dailyplan__isnull=True, dailyplanmeal__isnull=True).count(),
        "dailyplan": DailyPlan.objects.filter(created_by=user).exclude(source=DailyPlan.SOURCE_PROGRAM).count(),
        "program": Program.objects.filter(created_by=user).count(),
        "comparison": SavedComparison.objects.filter(owner=user).count(),
    }


def require_new_workspace_item(user, kind: str) -> None:
    """Call inside the insertion transaction to serialize checks per account."""

    key = _LIMIT_KEYS[kind]
    user.__class__.objects.select_for_update().get(pk=user.pk)
    entitlements = resolve_account_entitlements(user)
    if entitlements is None:
        raise CommercialLimitReached("account_plan_unavailable")
    capability = {
        "meal": "can_create_meal",
        "dailyplan": "can_create_dailyplan",
        "program": "can_create_program",
    }.get(kind)
    if capability is not None and not entitlements.enabled(capability):
        raise CommercialLimitReached(f"{capability}_disabled")
    if not entitlements.allows_new(key, current_count=workspace_usage(user)[kind]):
        raise CommercialLimitReached(f"{key}_reached")


def require_program_duration(user, weeks: int) -> None:
    entitlements = resolve_account_entitlements(user)
    if entitlements is None:
        raise CommercialLimitReached("account_plan_unavailable")
    days = entitlements.limit("max_program_duration_days")
    if days is not None and weeks * 7 > days:
        raise CommercialLimitReached("max_program_duration_days_reached")


def require_new_program_week(program: Program) -> None:
    """Downgrade never truncates existing weeks, but cannot extend past its cap."""

    require_program_duration(program.created_by, program.normalized_duration_weeks + 1)


def shared_imports_used_this_month(user) -> int:
    from django.utils import timezone

    from notas.domain.models import InboxItem

    today = timezone.localdate()
    return InboxItem.objects.filter(owner=user, saved_at__year=today.year, saved_at__month=today.month).count()


def require_shared_import(user) -> None:
    entitlements = resolve_account_entitlements(user)
    if entitlements is None:
        raise CommercialLimitReached("account_plan_unavailable")
    if not entitlements.allows_new(
        "max_shared_imports_monthly", current_count=shared_imports_used_this_month(user)
    ):
        raise CommercialLimitReached("max_shared_imports_monthly_reached")
