from __future__ import annotations

from dataclasses import dataclass
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from django.db.models import Q
from django.urls import reverse

from notas.domain.models import DailyPlanMeal, MealFood, ProgramDay
from notas.presentation.viewmodels.base_vm import BreadcrumbItem

PROGRAM_CONTEXT_KEYS = ("program_day", "dpm", "mealfood")


@dataclass(frozen=True)
class ProgramNavigationContext:
    """Serializable navigation context for deep Program routes.

    It keeps the query-string contract in one place instead of rebuilding
    program_day/dpm/mealfood params by hand across pages and action resolvers.
    """

    program_day_id: int | str | None = None
    dpm_id: int | str | None = None
    mealfood_id: int | str | None = None

    def as_params(self, *, include_empty: bool = False) -> dict[str, str]:
        raw_params = {
            "program_day": self.program_day_id,
            "dpm": self.dpm_id,
            "mealfood": self.mealfood_id,
        }
        params = {}
        for key, value in raw_params.items():
            if value in (None, "") and not include_empty:
                continue
            params[key] = "" if value is None else str(value)
        return params

    def as_query(self) -> str:
        return urlencode(self.as_params())

    def is_active(self) -> bool:
        return bool(self.program_day_id)

    def with_dpm(self, dpm: DailyPlanMeal | int | str | None) -> "ProgramNavigationContext":
        dpm_id = getattr(dpm, "id", dpm)
        return ProgramNavigationContext(
            program_day_id=self.program_day_id,
            dpm_id=dpm_id,
            mealfood_id=self.mealfood_id,
        )

    def with_mealfood(self, mealfood: MealFood | int | str | None) -> "ProgramNavigationContext":
        mealfood_id = getattr(mealfood, "id", mealfood)
        return ProgramNavigationContext(
            program_day_id=self.program_day_id,
            dpm_id=self.dpm_id,
            mealfood_id=mealfood_id,
        )


@dataclass(frozen=True)
class ProgramBreadcrumbParent:
    label: str
    url: str | None = None
    kind: str | None = None

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


def parse_context_query(query: str | dict | None) -> dict[str, str]:
    """Return only supported Program context params from a query string/dict."""
    if not query:
        return {}

    if isinstance(query, dict):
        raw_items = query.items()
    else:
        raw_items = parse_qsl(str(query), keep_blank_values=False)

    params = {}
    for key, value in raw_items:
        if key in PROGRAM_CONTEXT_KEYS and value not in (None, ""):
            params[key] = str(value)
    return params


def navigation_context_from_query(query: str | dict | None) -> ProgramNavigationContext:
    params = parse_context_query(query)
    return ProgramNavigationContext(
        program_day_id=params.get("program_day"),
        dpm_id=params.get("dpm"),
        mealfood_id=params.get("mealfood"),
    )


def context_query_dict(context) -> dict[str, str]:
    query = (context or {}).get("query") if isinstance(context, dict) else context
    return parse_context_query(query)


def context_query_string(context) -> str:
    return urlencode(context_query_dict(context))


def contextual_url(url: str, context=None, **params) -> str:
    return append_query(
        url,
        **context_query_dict(context),
        **{key: value for key, value in params.items() if value not in (None, "")},
    )


def program_context_query(
    program_day: ProgramDay | int | str | None = None,
    dpm: DailyPlanMeal | int | str | None = None,
    mealfood: MealFood | int | str | None = None,
) -> str:
    return ProgramNavigationContext(
        program_day_id=getattr(program_day, "id", program_day),
        dpm_id=getattr(dpm, "id", dpm),
        mealfood_id=getattr(mealfood, "id", mealfood),
    ).as_query()


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
    return f"{program_url(program_day)}#week-{program_day.week_number}"


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


def program_parent(program_day: ProgramDay) -> ProgramBreadcrumbParent:
    return ProgramBreadcrumbParent(str(program_day.program), program_url(program_day), kind="program")


def week_parent(program_day: ProgramDay) -> ProgramBreadcrumbParent:
    return ProgramBreadcrumbParent(
        f"Semana {program_day.week_number}",
        week_url(program_day),
        kind="program_week",
    )


def day_plan_parent(program_day: ProgramDay, *, url: str | None = None) -> ProgramBreadcrumbParent:
    return ProgramBreadcrumbParent(
        f"Día {program_day.day_number} - {program_day.dailyplan.name}",
        url,
        kind="program_day_plan",
    )


def dpm_parent(program_day: ProgramDay, dpm: DailyPlanMeal, *, url: str | None = None) -> ProgramBreadcrumbParent:
    return ProgramBreadcrumbParent(
        dpm.meal.name,
        url,
        kind="program_dpm",
    )


def compact_program_breadcrumbs(ui_vm, *, visible_from_kind: str = "program_week", visible_from_prefix: str = "Semana "):
    """Collapse program/list roots into an overflow breadcrumb.

    Prefer semantic item.kind markers so compacting is not coupled to labels.
    The label prefix fallback keeps compatibility with older breadcrumb items.
    """
    breadcrumb = list(getattr(ui_vm, "breadcrumb", []) or [])
    if not breadcrumb:
        return ui_vm

    start_index = None
    for index, item in enumerate(breadcrumb):
        kind = getattr(item, "kind", None)
        label = str(getattr(item, "label", ""))
        if kind == visible_from_kind or label.startswith(visible_from_prefix):
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
            kind="overflow",
        ),
        *visible_items,
    ]
    return ui_vm
