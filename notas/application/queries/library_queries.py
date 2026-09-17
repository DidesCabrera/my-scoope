"""Canonical user-library projections shared by UI and assistant reads."""

from django.db.models import Q

from notas.domain.models import DailyPlan, Food, Meal, Program


def food_library_queryset(user):
    return Food.objects.filter(
        created_by=user,
        is_active=True,
    ).order_by("list_order", "name", "id")


def meal_library_queryset(user):
    return (
        Meal.objects
        .filter(
            created_by=user,
            is_draft=False,
            dailyplanmeal__isnull=True,
        )
        .distinct()
        .order_by("list_order", "-created_at", "-id")
    )


def dailyplan_library_queryset(user):
    return (
        DailyPlan.objects
        .filter(
            created_by=user,
            is_draft=False,
        )
        .exclude(source=DailyPlan.SOURCE_PROGRAM)
        .order_by("list_order", "-created_at", "-id")
    )


def program_library_queryset(user):
    return (
        Program.objects
        .filter(
            Q(created_by=user)
            | Q(shares__accepted_by=user, shares__removed=False)
        )
        .distinct()
        .order_by("list_order", "-created_at", "-id")
    )
