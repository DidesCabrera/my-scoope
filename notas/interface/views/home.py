import uuid
from dataclasses import dataclass
from datetime import date, timedelta
from typing import List

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import IntegrityError
from django.db.models import Q
from django.http import Http404, HttpResponseBadRequest
from django.shortcuts import redirect, render
from django.urls import reverse
from django.views.decorators.http import require_POST

from notas.application.commercial.limits import CommercialLimitReached
from notas.application.queries.calendar_metrics import calendar_adherence_summary, calendar_future_schedule_summary
from notas.application.queries.calendarization_execution_queries import pinned_dailyplan_execution_state
from notas.application.queries.calendarization_queries import current_calendarization_for_user
from notas.application.services.calendarization.scheduling import local_date_for_timezone
from notas.application.services.commands.personal_preparation_commands import can_use_personal_preparations
from notas.application.services.commands.pinned_dailyplan_commands import (
    create_and_pin_empty_dailyplan,
    pin_dailyplan,
    record_pinned_meal_execution,
    unpin_dailyplan,
)
from notas.application.services.commands.supplement_commands import require_supplements_pro
from notas.domain.models import (
    CalendarCommitment,
    CalendarizedDay,
    DailyPlan,
    Food,
    Meal,
    PinnedDailyPlan,
    PinnedSupplementIntakeExecution,
    Preparation,
    Program,
    Supplement,
    SupplementIntake,
    WeightLog,
)
from notas.presentation.composition.viewmodel.components.builder_headers import build_page_header
from notas.presentation.composition.viewmodel.ui_builder import build_ui_vm
from notas.presentation.config.viewmodel_config import (
    HOME_VIEWMODE,
)
from notas.presentation.pages.home_calendarization import (
    HomeCalendarizationVM,
    build_home_calendarization_vm,
)
from notas.presentation.viewmodels.base_vm import BaseVM
from notas.presentation.viewmodels.components.header_vm import HeaderVM


@dataclass
class HomeHeroVM:
    title: str
    subtitle: str


@dataclass
class HomeStatVM:
    label: str
    value: int
    icon: str
    url: str


@dataclass
class HomeContentVM:
    header: HeaderVM
    hero: HomeHeroVM
    stats: List[HomeStatVM]
    calendarization: HomeCalendarizationVM
    calendar_progress: dict
    today_date: date
    today_commitments: List[CalendarCommitment]
    month_start: date
    previous_month_key: str
    next_month_key: str
    month_days: list[dict]
    future_plans_count: int
    calendar_coverage: int
    meal_coverage: int
    weight_history: list[WeightLog]
    weight_chart_points: str
    can_pin_dailyplan: bool
    pinned_dailyplan: DailyPlan | None
    pinned_meals: list[dict]
    pinned_supplement_intakes: list[dict]
    pinnable_dailyplans: list[DailyPlan]
    preparations_count: int
    supplements_count: int
    personal_preparations_access: bool
    supplements_visible: bool


def _pinned_context(user, *, today_date, has_dated_plan):
    if current_calendarization_for_user(user) is not None or has_dated_plan:
        return None, [], [], []
    pinned = PinnedDailyPlan.objects.select_related("dailyplan").filter(user=user, is_active=True).first()
    plans = list(DailyPlan.objects.filter(created_by=user).exclude(
        source=DailyPlan.SOURCE_PROGRAM,
    ).order_by("-created_at")[:100])
    if pinned is None:
        return None, [], [], plans
    states = {item["meal_key"]: item for item in pinned_dailyplan_execution_state(pinned, today_date)}
    meals = []
    for relation in pinned.dailyplan.dailyplan_meals.select_related("meal").order_by("order", "id"):
        key = f"dailyplan-meal:{relation.id}"
        meals.append({
            "relation": relation, "key": key,
            "status": states.get(key, {}).get("status", "planned"),
            "idempotency_key": f"web-pinned-meal-{uuid.uuid4()}",
        })
    intakes = []
    try:
        require_supplements_pro(user)
    except PermissionError:
        pass
    else:
        states = {}
        for event in PinnedSupplementIntakeExecution.objects.filter(
            pinned_dailyplan=pinned, local_date=today_date,
        ).order_by("created_at", "id"):
            states[event.intake_key] = "planned" if event.action == "reset" else event.action
        for intake in SupplementIntake.objects.filter(dailyplan=pinned.dailyplan).prefetch_related("items"):
            intakes.append({
                "intake": intake, "status": states.get(f"supplement_intake:{intake.id}", "planned"),
                "idempotency_key": f"web-pinned-supplement-{uuid.uuid4()}",
            })
    return pinned.dailyplan, meals, intakes, plans


def _require_unprogrammed_home(user):
    if current_calendarization_for_user(user) is not None:
        raise Http404("El programa vigente tiene prioridad sobre una Minuta fijada")


@login_required
def home_view(request):
    user = request.user
    today_date = local_date_for_timezone(user.profile.timezone_name or "UTC")
    requested_month = request.GET.get("month", "")
    try:
        month_start = date.fromisoformat(f"{requested_month}-01") if requested_month else today_date.replace(day=1)
    except ValueError:
        month_start = today_date.replace(day=1)
    month_start = month_start.replace(day=1)
    if month_start.year <= 1 or month_start.year >= 9999:
        month_start = today_date.replace(day=1)
    month_grid_start = month_start - timedelta(days=month_start.weekday())
    month_grid_end = month_grid_start + timedelta(days=41)
    month_plans = {
        day.calendar_date: day for day in CalendarizedDay.objects.filter(
            Q(user=user) | Q(user__isnull=True, calendarization__user=user),
            assignment_state=CalendarizedDay.STATE_CURRENT,
            calendar_date__range=(month_grid_start, month_grid_end),
        )
    }
    month_commitments = {}
    for commitment in CalendarCommitment.objects.filter(user=user, calendar_date__range=(month_grid_start, month_grid_end)):
        month_commitments.setdefault(commitment.calendar_date, []).append(commitment)
    month_days = []
    for offset in range(42):
        current_date = month_grid_start + timedelta(days=offset)
        day = month_plans.get(current_date)
        month_days.append({
            "date": current_date,
            "is_current_month": current_date.month == month_start.month,
            "is_today": current_date == today_date,
            "has_plan": bool(day and day.has_plan),
            "commitments": month_commitments.get(current_date, []),
        })
    progress = calendar_adherence_summary(user)
    schedule_summary = calendar_future_schedule_summary(user, today=today_date)
    future_plans_count = schedule_summary["future_plans_count"] or 0
    weight_history = list(WeightLog.objects.filter(user=user).order_by("-date", "-created_at")[:12])
    weight_values = [float(item.weight_kg) for item in reversed(weight_history)]
    weight_min = min(weight_values) if weight_values else 0
    weight_span = max(max(weight_values) - weight_min, 1) if weight_values else 1
    weight_chart_points = " ".join(
        f"{10 + index * 280 / max(len(weight_values) - 1, 1):.1f},{100 - (value - weight_min) * 80 / weight_span:.1f}"
        for index, value in enumerate(weight_values)
    )

    dailyplans_qs = (
        DailyPlan.objects.filter(
            created_by=user,
            is_draft=False,
        )
        .exclude(source=DailyPlan.SOURCE_PROGRAM)
        .order_by("-created_at")
    )

    meals_qs = Meal.objects.library().filter(
        created_by=user,
        is_draft=False,
    )

    foods_qs = Food.objects.filter(
        created_by=user,
        is_active=True,
    ).order_by("list_order", "name", "id")

    programs_count = Program.objects.filter(created_by=user).count()
    dailyplans_count = dailyplans_qs.count()
    meals_count = meals_qs.count()
    foods_count = foods_qs.count()
    personal_preparations_access = can_use_personal_preparations(user)
    preparations_count = Preparation.objects.filter(created_by=user, is_active=True).count() if personal_preparations_access else 0
    supplements_visible = bool(settings.SUPPLEMENTS_FEATURE_ENABLED)
    supplements_count = Supplement.objects.filter(created_by=user).count() if supplements_visible else 0
    today_plan = month_plans.get(today_date)
    pinned_dailyplan, pinned_meals, pinned_supplement_intakes, pinnable_dailyplans = _pinned_context(
        user, today_date=today_date, has_dated_plan=bool(today_plan and today_plan.has_plan),
    )

    content_vm = HomeContentVM(
        header=build_page_header(title="", actions=[]),
        hero=HomeHeroVM(
            title=f"Bienvenido {user.username}!",
            subtitle=(
                "Consulta tu planificación de hoy y organiza tus próximas fechas."
            ),
        ),
        stats=[
            HomeStatVM(
                label="Mis Programas",
                value=programs_count,
                icon="calendar",
                url=reverse("program_list"),
            ),
            HomeStatVM(
                label="Mis Minutas",
                value=dailyplans_count,
                icon="clipboard-list",
                url=reverse("dailyplan_list"),
            ),
            HomeStatVM(
                label="Comidas",
                value=meals_count,
                icon="utensils",
                url=reverse("meal_list"),
            ),
            HomeStatVM(
                label="Alimentos",
                value=foods_count,
                icon="carrot",
                url=reverse("food_list"),
            ),
        ],
        calendarization=build_home_calendarization_vm(user),
        calendar_progress=progress,
        today_date=today_date,
        today_commitments=list(CalendarCommitment.objects.filter(user=user, calendar_date=today_date)),
        month_start=month_start,
        previous_month_key=(month_start - timedelta(days=1)).strftime("%Y-%m"),
        next_month_key=(month_start + timedelta(days=32)).replace(day=1).strftime("%Y-%m"),
        month_days=month_days,
        future_plans_count=future_plans_count,
        calendar_coverage=min(100, round(progress["days_with_plan"] / progress["scheduled_days_with_plan"] * 100)) if progress["scheduled_days_with_plan"] else 0,
        meal_coverage=min(100, round(progress["completed_meals"] / progress["due_meals"] * 100)) if progress["due_meals"] else 0,
        weight_history=weight_history,
        weight_chart_points=weight_chart_points,
        can_pin_dailyplan=not bool(today_plan and today_plan.has_plan) and current_calendarization_for_user(user) is None,
        pinned_dailyplan=pinned_dailyplan,
        pinned_meals=pinned_meals,
        pinned_supplement_intakes=pinned_supplement_intakes,
        pinnable_dailyplans=pinnable_dailyplans,
        preparations_count=preparations_count,
        supplements_count=supplements_count,
        personal_preparations_access=personal_preparations_access,
        supplements_visible=supplements_visible,
    )

    ui_vm = build_ui_vm(HOME_VIEWMODE)

    base_vm = BaseVM(
        ui=ui_vm,
        content=content_vm,
    )

    return render(
        request,
        "notas/home.html",
        base_vm.as_context(),
    )


@login_required
@require_POST
def home_create_pinned_dailyplan(request):
    _require_unprogrammed_home(request.user)
    today = local_date_for_timezone(request.user.profile.timezone_name or "UTC")
    try:
        pinned = create_and_pin_empty_dailyplan(user=request.user, local_date=today)
    except CommercialLimitReached:
        messages.error(request, "Llegaste al límite de Minutas de tu plan.")
        return redirect("home_view")
    return redirect("dailyplan_detail", pk=pinned.dailyplan_id)


@login_required
@require_POST
def home_pin_dailyplan(request):
    _require_unprogrammed_home(request.user)
    try:
        pin_dailyplan(user=request.user, dailyplan_id=int(request.POST.get("dailyplan_id", "")))
    except (ValueError, TypeError):
        messages.error(request, "Elige una Minuta propia para fijarla en Inicio.")
    return redirect("home_view")


@login_required
@require_POST
def home_unpin_dailyplan(request):
    unpin_dailyplan(user=request.user)
    return redirect("home_view")


@login_required
@require_POST
def home_pinned_meal_check_in(request, relation_id):
    _require_unprogrammed_home(request.user)
    action = request.POST.get("action")
    if action not in {"completed", "skipped", "reset"}:
        return HttpResponseBadRequest("Estado inválido")
    try:
        record_pinned_meal_execution(
            user=request.user,
            local_date=local_date_for_timezone(request.user.profile.timezone_name or "UTC"),
            meal_key=f"dailyplan-meal:{relation_id}", action=action,
            idempotency_key=request.POST.get("idempotency_key", ""),
        )
    except ValueError:
        messages.error(request, "No se pudo registrar esa Comida.")
    return redirect("home_view")


@login_required
@require_POST
def home_pinned_supplement_check_in(request, intake_id):
    _require_unprogrammed_home(request.user)
    try:
        require_supplements_pro(request.user)
    except PermissionError:
        raise Http404("Suplementos no disponibles") from None
    pinned = PinnedDailyPlan.objects.filter(user=request.user, is_active=True).first()
    if pinned is None or not SupplementIntake.objects.filter(pk=intake_id, dailyplan_id=pinned.dailyplan_id).exists():
        raise Http404("Toma no encontrada")
    action = request.POST.get("action")
    if action not in {"completed", "skipped", "reset"}:
        return HttpResponseBadRequest("Estado inválido")
    key = request.POST.get("idempotency_key", "")
    if not 8 <= len(key) <= 120:
        return HttpResponseBadRequest("Solicitud inválida")
    try:
        PinnedSupplementIntakeExecution.objects.create(
            pinned_dailyplan=pinned,
            local_date=local_date_for_timezone(request.user.profile.timezone_name or "UTC"),
            intake_key=f"supplement_intake:{intake_id}", action=action, idempotency_key=key,
        )
    except IntegrityError:
        messages.error(request, "La toma ya fue registrada.")
    return redirect("home_view")
