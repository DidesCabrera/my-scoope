from __future__ import annotations

from datetime import timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.db.models import Sum
from django.utils import timezone

from accounts.models import AccountSubscription, CreditLedger, CreditWallet
from admin_analytics.filters import AdminAnalyticsFilters
from ai_assistant.models import AIUsageEvent
from notas.domain.model_modules.comparisons import SavedComparison
from notas.domain.model_modules.identity import Profile
from notas.domain.model_modules.proposals import NutritionProposal
from notas.domain.models import DailyPlan, DailyPlanShare, Meal, MealShare, Program, ProgramShare


def get_overview_metrics(*, now=None, analytics_filters: AdminAnalyticsFilters | None = None) -> dict:
    """Return ADM02 read-only aggregate metrics for the executive overview.

    This selector intentionally uses existing operational tables. It does not
    create analytical snapshots, background jobs or denormalized reporting data.
    """

    now = now or timezone.now()
    analytics_filters = analytics_filters or AdminAnalyticsFilters()
    since_7d = analytics_filters.since(now=now)
    since_30d = now - timedelta(days=30)

    users = analytics_filters.user_queryset()

    total_users = users.count()
    new_users_7d = users.filter(date_joined__gte=since_7d).count()
    new_users_30d = users.filter(date_joined__gte=since_30d).count()

    onboarding_completed = analytics_filters.apply_user_segment(
        Profile.objects.filter(onboarding_completed_at__isnull=False),
        "user",
    ).count()

    meals = analytics_filters.apply_user_segment(Meal.objects.all(), "created_by")
    dailyplans = analytics_filters.apply_user_segment(DailyPlan.objects.all(), "created_by")
    programs = analytics_filters.apply_user_segment(Program.objects.all(), "created_by")
    meal_activity_7d = meals.filter(created_at__gte=since_7d)
    dailyplan_activity_7d = dailyplans.filter(created_at__gte=since_7d)
    program_activity_7d = programs.filter(created_at__gte=since_7d)

    saved_comparison_users_7d = set(
        analytics_filters.apply_user_segment(SavedComparison.objects.filter(updated_at__gte=since_7d), "owner")
        .values_list("owner_id", flat=True)
        .distinct()
    )
    applied_proposal_users_7d = set(
        analytics_filters.apply_user_segment(NutritionProposal.objects.filter(applied_at__gte=since_7d), "applied_by")
        .values_list("applied_by_id", flat=True)
        .distinct()
    )
    share_user_ids_7d = set(
        analytics_filters.apply_user_segment(MealShare.objects.filter(created_at__gte=since_7d), "sender").values_list("sender_id", flat=True)
    ) | set(
        analytics_filters.apply_user_segment(DailyPlanShare.objects.filter(created_at__gte=since_7d), "sender").values_list("sender_id", flat=True)
    ) | set(
        analytics_filters.apply_user_segment(ProgramShare.objects.filter(created_at__gte=since_7d), "sender").values_list("sender_id", flat=True)
    )

    active_nutrition_builder_user_ids = (
        set(meal_activity_7d.values_list("created_by_id", flat=True))
        | set(dailyplan_activity_7d.values_list("created_by_id", flat=True))
        | set(program_activity_7d.values_list("created_by_id", flat=True))
        | saved_comparison_users_7d
        | applied_proposal_users_7d
        | share_user_ids_7d
    )
    active_nutrition_builders_7d = len(active_nutrition_builder_user_ids - {None})

    ai_usage = analytics_filters.apply_user_segment(AIUsageEvent.objects.all(), "user")
    ai_usage_7d = ai_usage.filter(created_at__gte=since_7d)
    ai_aggregates_7d = ai_usage_7d.aggregate(
        total_tokens=Sum("total_tokens"),
        input_tokens=Sum("input_tokens"),
        output_tokens=Sum("output_tokens"),
        estimated_cost_usd=Sum("estimated_cost_usd"),
        charged_credits=Sum("charged_credits"),
    )

    credit_ledger_7d = analytics_filters.apply_user_segment(CreditLedger.objects.filter(created_at__gte=since_7d), "user")
    consumed_credits_7d = abs(
        credit_ledger_7d.filter(kind=CreditLedger.Kind.CONSUME).aggregate(total=Sum("credits_delta"))["total"] or 0
    )
    reserved_credit_movements_7d = abs(
        credit_ledger_7d.filter(kind=CreditLedger.Kind.RESERVE).aggregate(total=Sum("reserved_delta"))["total"] or 0
    )

    wallets = analytics_filters.apply_user_segment(CreditWallet.objects.all(), "user")
    wallet_totals = wallets.aggregate(
        balance=Sum("balance"),
        reserved_balance=Sum("reserved_balance"),
    )

    return {
        "generated_at": now,
        "period_label": analytics_filters.period_label,
        "users": {
            "total": total_users,
            "new_7d": new_users_7d,
            "new_30d": new_users_30d,
            "onboarding_completed": onboarding_completed,
        },
        "product_activity": {
            "weekly_active_nutrition_builders": active_nutrition_builders_7d,
            "meals_total": meals.count(),
            "meals_7d": meal_activity_7d.count(),
            "dailyplans_total": dailyplans.count(),
            "dailyplans_7d": dailyplan_activity_7d.count(),
            "programs_total": programs.count(),
            "programs_7d": program_activity_7d.count(),
            "saved_comparisons_total": analytics_filters.apply_user_segment(SavedComparison.objects.all(), "owner").count(),
            "shares_7d": (
                analytics_filters.apply_user_segment(MealShare.objects.filter(created_at__gte=since_7d), "sender").count()
                + analytics_filters.apply_user_segment(DailyPlanShare.objects.filter(created_at__gte=since_7d), "sender").count()
                + analytics_filters.apply_user_segment(ProgramShare.objects.filter(created_at__gte=since_7d), "sender").count()
            ),
        },
        "ai": {
            "turns_total": ai_usage.count(),
            "turns_7d": ai_usage_7d.count(),
            "completed_7d": ai_usage_7d.filter(status=AIUsageEvent.Status.COMPLETED).count(),
            "error_7d": ai_usage_7d.filter(status=AIUsageEvent.Status.ERROR).count(),
            "blocked_7d": ai_usage_7d.filter(status=AIUsageEvent.Status.BLOCKED).count(),
            "total_tokens_7d": ai_aggregates_7d["total_tokens"] or 0,
            "input_tokens_7d": ai_aggregates_7d["input_tokens"] or 0,
            "output_tokens_7d": ai_aggregates_7d["output_tokens"] or 0,
            "estimated_cost_usd_7d": ai_aggregates_7d["estimated_cost_usd"] or Decimal("0"),
            "charged_credits_7d": ai_aggregates_7d["charged_credits"] or 0,
        },
        "accounts": {
            "active_subscriptions": analytics_filters.apply_user_segment(AccountSubscription.objects.filter(
                status__in=[AccountSubscription.Status.TRIALING, AccountSubscription.Status.ACTIVE]
            ), "user").count(),
            "wallets_total": wallets.count(),
            "wallet_balance_total": wallet_totals["balance"] or 0,
            "wallet_reserved_total": wallet_totals["reserved_balance"] or 0,
            "credits_consumed_7d": consumed_credits_7d,
            "credits_reserved_7d": reserved_credit_movements_7d,
        },
        "proposals": {
            "ai_proposals_total": analytics_filters.apply_user_segment(NutritionProposal.objects.filter(source=NutritionProposal.SOURCE_AI), "created_by").count(),
            "ai_proposals_7d": analytics_filters.apply_user_segment(NutritionProposal.objects.filter(
                source=NutritionProposal.SOURCE_AI,
                created_at__gte=since_7d,
            ), "created_by").count(),
            "applied_7d": analytics_filters.apply_user_segment(NutritionProposal.objects.filter(
                source=NutritionProposal.SOURCE_AI,
                status=NutritionProposal.STATUS_APPLIED,
                applied_at__gte=since_7d,
            ), "applied_by").count(),
        },
    }
