from __future__ import annotations

from dataclasses import dataclass
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from django.db.models import Q
from django.urls import reverse

from notas.domain.models import DailyPlanMeal, MealFood, ProgramDay
from notas.presentation.viewmodels.base_vm import BreadcrumbItem


@dataclass(frozen=True)
class ProgramBreadcrumbParent:
    label: str
    url: str | None = None

    def __str__(self):
        return self.label

    def get_absolute_url(self):
        return self.url


def append_query(url: str, **params) -> str:
    """Append non-empty query params while preserving any existing query string."""
    if not url:
        return url

    clean_params = {
        key: value
        for key, value in params.items()
        if value not in (None, "")
    }
    if not clean_params:
        return url

    parts = urlsplit(url)
    query = dict(parse_qsl(parts.query, keep_blank_values=True))
    query.update({key: str(value) for key, value in clean_params.items()})
    return urlunsplit((parts.scheme, parts.netloc, parts.path, urlencode(query), parts.fragment))


def get_program_day_for_user(user, program_day_id) -> ProgramDay | None:
    try:
        program_day_id = int(program_day_id)
    except (TypeError, ValueError):
        return None

    return (
        ProgramDay.objects
        .select_related("program", "dailyplan")
        .filter(pk=program_day_id)
        .filter(
            Q(program__created_by=user)
            | Q(program__shares__accepted_by=user, program__shares__removed=False)
        )
        .distinct()
        .first()
    )


def get_context_dailyplan_meal(program_day: ProgramDay | None, dpm_id) -> DailyPlanMeal | None:
    if program_day is None:
        return None

    try:
        dpm_id = int(dpm_id)
    except (TypeError, ValueError):
        return None

    return (
        DailyPlanMeal.objects
        .select_related("dailyplan", "meal")
        .filter(pk=dpm_id, dailyplan_id=program_day.dailyplan_id)
        .first()
    )


def get_context_meal_food(dpm: DailyPlanMeal | None, mealfood_id) -> MealFood | None:
    if dpm is None:
        return None

    try:
        mealfood_id = int(mealfood_id)
    except (TypeError, ValueError):
        return None

    return (
        MealFood.objects
        .select_related("meal", "food")
        .filter(pk=mealfood_id, meal_id=dpm.meal_id)
        .first()
    )


def program_url(program_day: ProgramDay) -> str:
    return reverse("program_detail", args=[program_day.program_id])


def week_url(program_day: ProgramDay) -> str:
    return reverse(
        "program_week_detail",
        args=[program_day.program_id, program_day.week_number],
    )


def dailyplan_context_url(program_day: ProgramDay) -> str:
    return append_query(
        reverse("dailyplan_detail", args=[program_day.dailyplan_id]),
        program_day=program_day.id,
    )


def dpm_context_url(program_day: ProgramDay, dpm: DailyPlanMeal) -> str:
    return append_query(
        reverse("dailyplan_meal_detail", args=[dpm.dailyplan_id, dpm.id]),
        program_day=program_day.id,
    )


def program_context_query(program_day: ProgramDay | None = None, dpm: DailyPlanMeal | None = None, mealfood: MealFood | None = None) -> str:
    params = {}
    if program_day is not None:
        params["program_day"] = program_day.id
    if dpm is not None:
        params["dpm"] = dpm.id
    if mealfood is not None:
        params["mealfood"] = mealfood.id
    return urlencode(params)


def program_parent(program_day: ProgramDay) -> ProgramBreadcrumbParent:
    return ProgramBreadcrumbParent(str(program_day.program), program_url(program_day))


def week_parent(program_day: ProgramDay) -> ProgramBreadcrumbParent:
    return ProgramBreadcrumbParent(
        f"Semana {program_day.week_number}",
        week_url(program_day),
    )


def day_plan_parent(program_day: ProgramDay, *, url: str | None = None) -> ProgramBreadcrumbParent:
    return ProgramBreadcrumbParent(
        f"Día {program_day.day_number} - {program_day.dailyplan.name}",
        url,
    )


def dpm_parent(program_day: ProgramDay, dpm: DailyPlanMeal, *, url: str | None = None) -> ProgramBreadcrumbParent:
    return ProgramBreadcrumbParent(
        dpm.meal.name,
        url,
    )


def compact_program_breadcrumbs(ui_vm, *, visible_from_prefix: str = "Semana "):
    """Collapse the program/list roots into an overflow breadcrumb.

    Program context breadcrumbs can become deep:
    Mis Programas / Programa / Semana / Plan / Meal / Food.
    In the header we keep the useful nested segment visible from Semana onward
    and move the previous ancestors into a clickable ellipsis.
    """
    breadcrumb = list(getattr(ui_vm, "breadcrumb", []) or [])
    if not breadcrumb:
        return ui_vm

    start_index = None
    for index, item in enumerate(breadcrumb):
        label = str(getattr(item, "label", ""))
        if label.startswith(visible_from_prefix):
            start_index = index
            break

    if start_index is None or start_index <= 0:
        return ui_vm

    hidden_items = breadcrumb[:start_index]
    visible_items = breadcrumb[start_index:]

    ui_vm.breadcrumb = [
        BreadcrumbItem(
            label="...",
            is_overflow=True,
            overflow_items=hidden_items,
        ),
        *visible_items,
    ]
    return ui_vm
