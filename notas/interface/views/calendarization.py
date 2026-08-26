from __future__ import annotations

import json
import uuid
from dataclasses import asdict

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import Http404, HttpResponseBadRequest, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.http import require_GET, require_POST

from notas.application.queries.calendarization_execution_queries import (
    meal_execution_state_for_day,
)
from notas.application.queries.calendarization_queries import (
    calendarization_history_for_user,
    calendarized_day_for_user,
    current_calendarization_for_user,
    owned_programs_for_calendarization,
    today_for_calendarization,
)
from notas.application.services.commands.calendarization_commands import (
    activate_program_calendarization,
    cancel_calendarization,
    deactivate_web_push_subscription,
    pause_calendarization,
    register_web_push_subscription,
    resume_calendarization,
    update_calendarization_preferences,
)
from notas.application.services.commands.calendarization_execution_commands import (
    record_meal_execution,
)
from notas.domain.models import Program, WebPushSubscription
from notas.interface.forms.calendarization_forms import (
    CalendarizationActivationForm,
    CalendarizationPreferencesForm,
)
from notas.presentation.composition.viewmodel.components.builder_headers import build_page_header
from notas.presentation.composition.viewmodel.ui_builder import build_ui_vm
from notas.presentation.config.viewmodel_config import (
    CALENDARIZATION_VIEWMODE_DASHBOARD,
    CALENDARIZATION_VIEWMODE_DAY_DETAIL,
    CALENDARIZATION_VIEWMODE_HISTORY,
)
from notas.presentation.pages.calendarized_meal import build_calendarized_meal_detail
from notas.presentation.pages.home_calendarization import build_home_calendarization_vm

ERROR_MESSAGES = {
    "calendarization_incomplete_confirmation_required": "El programa está incompleto. Confirma que deseas calendarizarlo con días vacíos.",
    "calendarization_replacement_confirmation_required": "Ya tienes una calendarización vigente. Confirma que deseas reemplazarla.",
    "calendarization_start_date_past": "La fecha de inicio no puede estar en el pasado para tu zona horaria.",
    "calendarization_program_not_owned": "Solo puedes calendarizar programas propios.",
    "calendarization_current_conflict": "Otra calendarización quedó vigente al mismo tiempo. Vuelve a intentarlo.",
}


def _context(viewmode, content):
    ui = build_ui_vm(viewmode)
    return {"vm": {"ui": asdict(ui), "content": content}}


def _header(*, history=False):
    action = {
        "key": "calendarization_dashboard" if history else "calendarization_history",
        "label": "Calendarizador" if history else "Historial",
        "method": "get",
        "icon": "calendar-clock" if history else "history",
        "desktop_position": "menu",
        "mobile_position": "menu",
        "url": reverse("calendarization_dashboard" if history else "calendarization_history"),
    }
    return asdict(build_page_header(actions=[action]))


@login_required
@require_GET
def dashboard(request):
    programs = list(owned_programs_for_calendarization(request.user))
    for program in programs:
        program.calendarization_empty_days = max(
            program.duration_days - program.calendarization_filled_days,
            0,
        )
    current = current_calendarization_for_user(request.user)
    today = today_for_calendarization(current) if current else None
    today_day = current.days.filter(calendar_date=today).first() if current and today else None
    content = {
        "header": _header(),
        "programs": programs,
        "current": current,
        "current_program_url": (
            reverse("program_detail", args=[current.source_program_id]) if current and current.source_program_id else ""
        ),
        "current_calendar": build_home_calendarization_vm(
            request.user,
            request_get=request.GET,
            navigation_view_name="calendarization_dashboard",
        ),
        "today": today,
        "today_day": today_day,
        "default_timezone": request.user.profile.timezone_name or "UTC",
        "push_enabled": bool(getattr(settings, "MYSCOOPE_WEB_PUSH_ENABLED", False)),
        "vapid_public_key": getattr(settings, "MYSCOOPE_VAPID_PUBLIC_KEY", ""),
        "has_push_subscription": WebPushSubscription.objects.filter(user=request.user, is_active=True).exists(),
    }
    return render(
        request,
        "notas/calendarization/dashboard.html",
        _context(CALENDARIZATION_VIEWMODE_DASHBOARD, content),
    )


@login_required
@require_GET
def history(request):
    content = {
        "header": _header(history=True),
        "history": calendarization_history_for_user(request.user, limit=None),
    }
    return render(
        request,
        "notas/calendarization/history.html",
        _context(CALENDARIZATION_VIEWMODE_HISTORY, content),
    )


@login_required
@require_POST
def activate(request):
    form = CalendarizationActivationForm(request.POST)
    if not form.is_valid():
        messages.error(request, "Revisa el programa, la fecha y la hora seleccionadas.")
        return redirect("calendarization_dashboard")

    program = get_object_or_404(Program, id=form.cleaned_data["program_id"], created_by=request.user)
    try:
        result = activate_program_calendarization(
            user=request.user,
            program=program,
            start_date=form.cleaned_data["start_date"],
            timezone_name=form.cleaned_data["timezone_name"],
            daily_notification_time=form.cleaned_data["notification_time"],
            daily_notifications_enabled=form.cleaned_data["daily_notifications_enabled"],
            meal_notifications_enabled=form.cleaned_data["meal_notifications_enabled"],
            confirm_incomplete=form.cleaned_data["confirm_incomplete"],
            replace_current=form.cleaned_data["replace_current"],
        )
    except ValueError as exc:
        messages.error(request, ERROR_MESSAGES.get(str(exc), "No fue posible activar la calendarización."))
    else:
        suffix = f" ({len(result.empty_dates)} días vacíos)" if result.empty_dates else ""
        messages.success(request, f"Calendarización activada{suffix}.")
    return redirect("calendarization_dashboard")


def _state_action(request, calendarization_id, command, success_message):
    try:
        command(user=request.user, calendarization_id=calendarization_id)
    except ValueError:
        messages.error(request, "La calendarización no admite esa acción.")
    else:
        messages.success(request, success_message)
    return redirect("calendarization_dashboard")


@login_required
@require_POST
def pause(request, calendarization_id):
    return _state_action(request, calendarization_id, pause_calendarization, "Calendarización pausada.")


@login_required
@require_POST
def resume(request, calendarization_id):
    return _state_action(request, calendarization_id, resume_calendarization, "Calendarización reanudada.")


@login_required
@require_POST
def cancel(request, calendarization_id):
    return _state_action(request, calendarization_id, cancel_calendarization, "Calendarización cancelada.")


@login_required
@require_POST
def preferences(request, calendarization_id):
    form = CalendarizationPreferencesForm(request.POST)
    if not form.is_valid():
        messages.error(request, "Revisa la hora seleccionada.")
        return redirect("calendarization_dashboard")
    try:
        update_calendarization_preferences(
            user=request.user,
            calendarization_id=calendarization_id,
            timezone_name=form.cleaned_data["timezone_name"],
            daily_notification_time=form.cleaned_data["notification_time"],
            daily_notifications_enabled=form.cleaned_data["daily_notifications_enabled"],
            meal_notifications_enabled=form.cleaned_data["meal_notifications_enabled"],
        )
    except ValueError:
        messages.error(request, "No fue posible guardar las preferencias.")
    else:
        messages.success(request, "Preferencias actualizadas.")
    return redirect("calendarization_dashboard")


@login_required
@require_GET
def day_detail(request, day_id):
    day = calendarized_day_for_user(request.user, day_id)
    if day is None:
        raise Http404("Día calendarizado no encontrado")
    execution = meal_execution_state_for_day(day) if day.has_plan else []
    state_by_key = {item["meal_key"]: item for item in execution}
    meals = []
    for meal in (day.plan_snapshot or {}).get("meals", []):
        if not isinstance(meal, dict):
            continue
        meal_key = meal.get("key") or ""
        meal_state = state_by_key.get(meal_key, {"status": "planned", "note": ""})
        meals.append(
            {
                **meal,
                "detail_url": reverse(
                    "calendarization_meal_detail",
                    args=[day.id, meal_key],
                )
                if meal_key
                else None,
                "completed": meal_state["status"] == "completed",
                "has_note": bool(meal_state["note"].strip()),
            }
        )
    return render(
        request,
        "notas/calendarization/day_detail.html",
        _context(
            CALENDARIZATION_VIEWMODE_DAY_DETAIL,
            {
                "header": _header(),
                "day": day,
                "meals": meals,
                "completed_meals_count": sum(item["completed"] for item in meals),
                "noted_meals_count": sum(item["has_note"] for item in meals),
            },
        ),
    )


@login_required
@require_GET
def meal_detail(request, day_id, meal_snapshot_key):
    day = calendarized_day_for_user(request.user, day_id)
    if day is None:
        raise Http404("Día calendarizado no encontrado")
    detail = build_calendarized_meal_detail(
        day=day,
        meal_snapshot_key=meal_snapshot_key,
        user=request.user,
    )
    if detail is None:
        raise Http404("Comida calendarizada no encontrada")
    detail["can_check_in"] = (
        day.calendarization.status == day.calendarization.STATUS_ACTIVE
        and day.calendar_date == today_for_calendarization(day.calendarization)
    )
    detail["status_idempotency_key"] = f"web-meal-status-{uuid.uuid4()}"
    detail["note_idempotency_key"] = f"web-meal-note-{uuid.uuid4()}"
    return render(
        request,
        "notas/calendarization/meal_detail.html",
        _context(
            CALENDARIZATION_VIEWMODE_DAY_DETAIL,
            {"header": _header(), "meal_detail": detail},
        ),
    )


@login_required
@require_POST
def meal_check_in(request, day_id, meal_snapshot_key):
    action = request.POST.get("action", "")
    note = request.POST.get("note", "")
    try:
        record_meal_execution(
            user=request.user,
            day_id=day_id,
            meal_snapshot_key=meal_snapshot_key,
            action=action,
            idempotency_key=request.POST.get("idempotency_key") or f"web-meal-{uuid.uuid4()}",
            note=note,
        )
    except ValueError as exc:
        code = str(exc)
        if code in {"calendarized_day_not_found", "meal_snapshot_key_invalid"}:
            raise Http404("Comida calendarizada no encontrada") from exc
        messages.error(
            request,
            "No fue posible actualizar el cumplimiento de esta comida.",
        )
    return redirect(
        "calendarization_meal_detail",
        day_id=day_id,
        meal_snapshot_key=meal_snapshot_key,
    )


def _json_body(request):
    try:
        return json.loads(request.body.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        raise ValueError("invalid_json")


@login_required
@require_POST
def push_subscribe(request):
    try:
        body = _json_body(request)
        keys = body.get("keys") or {}
        subscription = register_web_push_subscription(
            user=request.user,
            endpoint=body.get("endpoint", ""),
            p256dh_key=keys.get("p256dh", ""),
            auth_key=keys.get("auth", ""),
            user_agent=request.headers.get("User-Agent", ""),
            device_label=body.get("device_label", ""),
        )
    except (AttributeError, TypeError, ValueError):
        return HttpResponseBadRequest("Suscripción inválida")
    return JsonResponse({"ok": True, "subscription_id": subscription.id})


@login_required
@require_POST
def push_unsubscribe(request):
    try:
        body = _json_body(request)
        deactivated = deactivate_web_push_subscription(user=request.user, endpoint=body.get("endpoint", ""))
    except (AttributeError, TypeError, ValueError):
        return HttpResponseBadRequest("Suscripción inválida")
    return JsonResponse({"ok": True, "deactivated": deactivated})
