"""Mobile projection of the centralized commercial entitlements."""

from accounts.services.entitlements import resolve_account_entitlements
from accounts.services.profile import build_account_credit_display
from notas.application.commercial.limits import shared_imports_used_this_month, workspace_usage


def entitlements_payload(user) -> dict:
    account = build_account_credit_display(user)
    entitlements = resolve_account_entitlements(user)
    limit_keys = (
        "max_meals",
        "max_dailyplans",
        "max_programs",
        "max_program_duration_days",
        "max_active_programs",
        "max_shared_imports_monthly",
        "max_saved_comparisons",
    )
    usage = workspace_usage(user)
    usage["shared_imports_monthly"] = shared_imports_used_this_month(user)
    return {
        "plan_name": account.plan_name,
        "plan_slug": account.plan_slug,
        "subscription_status": account.subscription_status,
        "period": account.period,
        "available_credits": account.available_credits,
        "reserved_credits": account.reserved_credits,
        "monthly_credit_limit": account.monthly_credit_limit,
        "daily_credit_limit": account.daily_credit_limit,
        "included_monthly_credits": account.included_monthly_credits,
        "purchased_credits": account.purchased_credits,
        "workspace_limits": {key: entitlements.limit(key) for key in limit_keys} if entitlements else {},
        "workspace_usage": usage,
    }
