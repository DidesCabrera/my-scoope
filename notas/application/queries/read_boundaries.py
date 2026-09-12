from django.db.models import Q
from django.shortcuts import get_object_or_404

from notas.domain.models import (
    DailyPlan,
    Food,
    Meal,
)


def get_owned_food_queryset(user):
    return (
        Food.objects
        .filter(created_by=user)
        .order_by("name", "id")
    )


def get_readable_food_queryset(user):
    """
    Foods legibles para el usuario:
    - alimentos propios;
    - alimentos globales;
    - alimentos legacy de sistema, creados sin usuario.

    Regla de negocio:
    - is_global=True => disponible para todos;
    - created_by=user => disponible solo para ese usuario;
    - created_by=None => tratado como system/legacy global.
    """
    return (
        Food.objects
        .filter(
            Q(created_by=user)
            | Q(is_global=True)
            | Q(created_by__isnull=True)
        )
        .distinct()
        .order_by("name", "id")
    )



def get_readable_food_or_404(user, food_id: int):
    return get_object_or_404(
        get_readable_food_queryset(user),
        pk=food_id,
    )


def get_owned_meal_queryset(user):
    return (
        Meal.objects
        .filter(created_by=user)
        .order_by("name", "id")
    )


def get_readable_meal_queryset(user):
    """
    Meals legibles para el usuario: propias o públicas y no draft.
    Los compartidos se leen desde snapshots de Inbox hasta guardarlos.
    """
    return (
        Meal.objects
        .filter(
            Q(created_by=user)
            | Q(is_public=True, is_draft=False)
        )
        .distinct()
        .order_by("name", "id")
    )


def get_readable_meal_or_404(user, meal_id: int):
    return get_object_or_404(
        get_readable_meal_queryset(user),
        pk=meal_id,
    )


def get_owned_dailyplan_queryset(user):
    return (
        DailyPlan.objects
        .filter(created_by=user)
        .order_by("name", "id")
    )


def get_readable_dailyplan_queryset(user):
    """
    DailyPlans legibles para el usuario: propios o públicos y no draft.
    Los compartidos se leen desde snapshots de Inbox hasta guardarlos.
    """
    return (
        DailyPlan.objects
        .filter(
            Q(created_by=user)
            | Q(is_public=True, is_draft=False)
        )
        .distinct()
        .order_by("name", "id")
    )


def get_readable_dailyplan_or_404(user, dailyplan_id: int):
    return get_object_or_404(
        get_readable_dailyplan_queryset(user),
        pk=dailyplan_id,
    )
