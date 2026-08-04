from __future__ import annotations

from collections import defaultdict
from datetime import timedelta

from django.db.models import Avg, Count, Q
from django.utils import timezone

from admin_analytics.filters import AdminAnalyticsFilters
from notas.domain.model_modules.comparisons import SavedComparison
from notas.domain.model_modules.proposals import NutritionProposal
from notas.domain.model_modules.sharing import (
    DailyPlanMealShare,
    DailyPlanShare,
    FoodShare,
    MealShare,
    ProgramShare,
)
from notas.domain.models import DailyPlan, DailyPlanMeal, Food, Meal, MealFood, Program, ProgramDay

SHARE_MODELS = (
    ("foods", "Foods", FoodShare),
    ("meals", "Meals", MealShare),
    ("dailyplans", "DailyPlans", DailyPlanShare),
    ("dailyplan_meals", "DailyPlanMeals", DailyPlanMealShare),
    ("programs", "Programs", ProgramShare),
)


def _safe_ratio(numerator: int | float, denominator: int | float) -> float:
    denominator = denominator or 0
    if denominator <= 0:
        return 0.0
    return float(numerator or 0) / float(denominator)


def _count_since(model, field: str, since) -> int:
    return model.objects.filter(**{f"{field}__gte": since}).count()


def _add_user_score(scores: dict[int, dict], *, user_id, email: str, username: str, key: str, weight: int = 1) -> None:
    if not user_id:
        return
    row = scores[user_id]
    row["email"] = email or username or "—"
    row["username"] = username or email or "—"
    row[key] += 1
    row["score"] += weight


def _top_builder_rows(*, since_7d, top_limit: int) -> list[dict]:
    scores: dict[int, dict] = defaultdict(
        lambda: {
            "email": "—",
            "username": "—",
            "meals": 0,
            "dailyplans": 0,
            "programs": 0,
            "shares": 0,
            "comparisons": 0,
            "applied_proposals": 0,
            "score": 0,
        }
    )

    for row in Meal.objects.filter(created_at__gte=since_7d).values("created_by_id", "created_by__email", "created_by__username"):
        _add_user_score(
            scores,
            user_id=row["created_by_id"],
            email=row["created_by__email"],
            username=row["created_by__username"],
            key="meals",
        )

    for row in DailyPlan.objects.filter(created_at__gte=since_7d).values("created_by_id", "created_by__email", "created_by__username"):
        _add_user_score(
            scores,
            user_id=row["created_by_id"],
            email=row["created_by__email"],
            username=row["created_by__username"],
            key="dailyplans",
            weight=2,
        )

    for row in Program.objects.filter(created_at__gte=since_7d).values("created_by_id", "created_by__email", "created_by__username"):
        _add_user_score(
            scores,
            user_id=row["created_by_id"],
            email=row["created_by__email"],
            username=row["created_by__username"],
            key="programs",
            weight=3,
        )

    for _, _, share_model in SHARE_MODELS:
        for row in share_model.objects.filter(created_at__gte=since_7d).values("sender_id", "sender__email", "sender__username"):
            _add_user_score(
                scores,
                user_id=row["sender_id"],
                email=row["sender__email"],
                username=row["sender__username"],
                key="shares",
            )

    for row in SavedComparison.objects.filter(updated_at__gte=since_7d).values("owner_id", "owner__email", "owner__username"):
        _add_user_score(
            scores,
            user_id=row["owner_id"],
            email=row["owner__email"],
            username=row["owner__username"],
            key="comparisons",
            weight=2,
        )

    for row in NutritionProposal.objects.filter(applied_at__gte=since_7d).values("applied_by_id", "applied_by__email", "applied_by__username"):
        _add_user_score(
            scores,
            user_id=row["applied_by_id"],
            email=row["applied_by__email"],
            username=row["applied_by__username"],
            key="applied_proposals",
            weight=3,
        )

    rows = list(scores.values())
    rows.sort(key=lambda row: (row["score"], row["programs"], row["dailyplans"], row["meals"]), reverse=True)
    return rows[:top_limit]


def get_product_activity_metrics(*, now=None, analytics_filters: AdminAnalyticsFilters | None = None, top_limit: int = 10) -> dict:
    """Return ADM05 read-only product activity metrics from the `notas` app.

    This selector observes operational nutrition-building activity. It does not
    mutate `notas` entities and intentionally avoids analytical snapshot tables.
    """

    now = now or timezone.now()
    analytics_filters = analytics_filters or AdminAnalyticsFilters()
    since_7d = analytics_filters.since(now=now)
    since_30d = now - timedelta(days=30)

    foods_total = Food.objects.count()
    meals_total = Meal.objects.count()
    dailyplans_total = DailyPlan.objects.count()
    programs_total = Program.objects.count()
    meal_foods_total = MealFood.objects.count()
    dailyplan_meals_total = DailyPlanMeal.objects.count()
    program_days_total = ProgramDay.objects.count()

    share_rows = []
    total_shares_7d = 0
    accepted_shares_total = 0
    unread_shares_total = 0
    favorite_shares_total = 0
    removed_shares_total = 0
    for key, label, share_model in SHARE_MODELS:
        sent_7d = share_model.objects.filter(created_at__gte=since_7d).count()
        total_shares_7d += sent_7d
        accepted_total = share_model.objects.filter(accepted_by__isnull=False).count()
        unread_total = share_model.objects.filter(is_read=False, removed=False, dismissed=False).count()
        favorite_total = share_model.objects.filter(is_favorite=True).count()
        removed_total = share_model.objects.filter(removed=True).count()
        accepted_shares_total += accepted_total
        unread_shares_total += unread_total
        favorite_shares_total += favorite_total
        removed_shares_total += removed_total
        share_rows.append(
            {
                "key": key,
                "label": label,
                "sent_total": share_model.objects.count(),
                "sent_7d": sent_7d,
                "sent_30d": share_model.objects.filter(created_at__gte=since_30d).count(),
                "accepted_total": accepted_total,
                "unread_total": unread_total,
                "favorite_total": favorite_total,
                "removed_total": removed_total,
            }
        )

    dailyplan_source_rows = list(
        DailyPlan.objects.values("source")
        .annotate(total=Count("id"), created_7d=Count("id", filter=Q(created_at__gte=since_7d)))
        .order_by("source")
    )

    comparison_rows = list(
        SavedComparison.objects.values("kind")
        .annotate(
            total=Count("id"),
            updated_7d=Count("id", filter=Q(updated_at__gte=since_7d)),
            owners=Count("owner", distinct=True),
        )
        .order_by("kind")
    )

    program_week_rows = list(
        ProgramDay.objects.values("week_number")
        .annotate(slots=Count("id"), programs=Count("program", distinct=True))
        .order_by("week_number")
    )[:top_limit]

    programs_with_slots = Program.objects.filter(program_dailyplan__isnull=False).distinct().count()
    programs_with_multiple_weeks = Program.objects.annotate(weeks=Count("program_dailyplan__week_number", distinct=True)).filter(weeks__gt=1).count()

    top_builder_rows = _top_builder_rows(since_7d=since_7d, top_limit=top_limit)

    active_builder_user_ids = {
        row["created_by_id"]
        for row in Meal.objects.filter(created_at__gte=since_7d).values("created_by_id")
        if row["created_by_id"]
    } | {
        row["created_by_id"]
        for row in DailyPlan.objects.filter(created_at__gte=since_7d).values("created_by_id")
        if row["created_by_id"]
    } | {
        row["created_by_id"]
        for row in Program.objects.filter(created_at__gte=since_7d).values("created_by_id")
        if row["created_by_id"]
    } | {
        row["owner_id"]
        for row in SavedComparison.objects.filter(updated_at__gte=since_7d).values("owner_id")
        if row["owner_id"]
    } | {
        row["applied_by_id"]
        for row in NutritionProposal.objects.filter(applied_at__gte=since_7d).values("applied_by_id")
        if row["applied_by_id"]
    }

    for _, _, share_model in SHARE_MODELS:
        active_builder_user_ids |= {
            row["sender_id"]
            for row in share_model.objects.filter(created_at__gte=since_7d).values("sender_id")
            if row["sender_id"]
        }

    return {
        "generated_at": now,
        "period_label": analytics_filters.period_label,
        "north_star": {
            "weekly_active_nutrition_builders": len(active_builder_user_ids),
            "top_builder_rows": top_builder_rows,
        },
        "entities": {
            "foods": {
                "total": foods_total,
                "created_7d": _count_since(Food, "created_at", since_7d),
                "created_30d": _count_since(Food, "created_at", since_30d),
                "global": Food.objects.filter(is_global=True).count(),
                "active": Food.objects.filter(is_active=True).count(),
                "verified": Food.objects.filter(is_verified=True).count(),
            },
            "meals": {
                "total": meals_total,
                "created_7d": _count_since(Meal, "created_at", since_7d),
                "created_30d": _count_since(Meal, "created_at", since_30d),
                "draft": Meal.objects.filter(is_draft=True).count(),
                "public": Meal.objects.filter(is_public=True).count(),
                "forked": Meal.objects.filter(forked_from__isnull=False).count(),
                "with_foods": Meal.objects.filter(meal_food_set__isnull=False).distinct().count(),
                "avg_foods_per_meal": _safe_ratio(meal_foods_total, meals_total),
            },
            "dailyplans": {
                "total": dailyplans_total,
                "created_7d": _count_since(DailyPlan, "created_at", since_7d),
                "created_30d": _count_since(DailyPlan, "created_at", since_30d),
                "draft": DailyPlan.objects.filter(is_draft=True).count(),
                "public": DailyPlan.objects.filter(is_public=True).count(),
                "forked": DailyPlan.objects.filter(forked_from__isnull=False).count(),
                "with_meals": DailyPlan.objects.filter(dailyplan_meals__isnull=False).distinct().count(),
                "avg_meals_per_dailyplan": _safe_ratio(dailyplan_meals_total, dailyplans_total),
            },
            "programs": {
                "total": programs_total,
                "created_7d": _count_since(Program, "created_at", since_7d),
                "created_30d": _count_since(Program, "created_at", since_30d),
                "draft": Program.objects.filter(is_draft=True).count(),
                "public": Program.objects.filter(is_public=True).count(),
                "forked": Program.objects.filter(forked_from__isnull=False).count(),
                "with_slots": programs_with_slots,
                "with_multiple_weeks": programs_with_multiple_weeks,
                "avg_filled_days_per_program": _safe_ratio(program_days_total, programs_total),
            },
        },
        "composition": {
            "meal_foods_total": meal_foods_total,
            "dailyplan_meals_total": dailyplan_meals_total,
            "program_days_total": program_days_total,
            "dailyplan_source_rows": dailyplan_source_rows,
            "program_week_rows": program_week_rows,
        },
        "comparisons": {
            "total": SavedComparison.objects.count(),
            "updated_7d": SavedComparison.objects.filter(updated_at__gte=since_7d).count(),
            "updated_30d": SavedComparison.objects.filter(updated_at__gte=since_30d).count(),
            "owners_total": SavedComparison.objects.values("owner").distinct().count(),
            "rows": comparison_rows,
        },
        "shares": {
            "total": sum(share_model.objects.count() for _, _, share_model in SHARE_MODELS),
            "sent_7d": total_shares_7d,
            "accepted_total": accepted_shares_total,
            "unread_total": unread_shares_total,
            "favorite_total": favorite_shares_total,
            "removed_total": removed_shares_total,
            "rows": share_rows,
        },
        "proposals": {
            "total": NutritionProposal.objects.count(),
            "created_7d": NutritionProposal.objects.filter(created_at__gte=since_7d).count(),
            "applied_7d": NutritionProposal.objects.filter(applied_at__gte=since_7d).count(),
            "ai_created_7d": NutritionProposal.objects.filter(source=NutritionProposal.SOURCE_AI, created_at__gte=since_7d).count(),
        },
    }
