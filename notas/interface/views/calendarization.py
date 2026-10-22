from __future__ import annotations

import json
import uuid
from dataclasses import asdict
from datetime import date, timedelta

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.http import Http404, HttpResponseBadRequest, HttpResponseRedirect, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_GET, require_POST

from mobile_api.read_cache import invalidate_mobile_read_cache
from notas.application.queries.calendar_foods import calendar_foods_for_period
from notas.application.queries.calendar_metrics import calendar_adherence_summary, calendar_future_schedule_summary
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
from notas.application.services.calendarization.scheduling import local_date_for_timezone
from notas.application.services.commands.calendar_commitment_commands import register_calendar_commitments
from notas.application.services.commands.calendar_day_commands import (
    assign_dailyplan_to_calendar_date,
    move_calendar_date_plan,
    remove_calendar_date_plan,
)
from notas.application.services.commands.calendar_progress_commands import start_new_calendar_progress_period
from notas.application.services.commands.calendarization_commands import (
    activate_program_calendarization,
    cancel_calendarization,
    deactivate_web_push_subscription,
    pause_calendarization,
    register_web_push_subscription,
    rename_calendarized_day_plan,
    rename_calendarized_meal,
    resume_calendarization,
    update_calendarization_preferences,
    update_calendarized_meal_hour,
)
from notas.application.services.commands.calendarization_execution_commands import (
    record_meal_execution,
)
from notas.domain.models import CalendarCommitment, CalendarizedDay, DailyPlan, Program, WebPushSubscription
from notas.interface.forms.calendarization_forms import (
    CalendarizationActivationForm,
    CalendarizationPreferencesForm,
)
from notas.interface.forms.meal_time_forms import MealTimeChangeForm
from notas.presentation.composition.viewmodel.components.builder_headers import build_page_header
from notas.presentation.composition.viewmodel.ui_builder import build_ui_vm
from notas.presentation.config.viewmodel_config import (
    CALENDARIZATION_VIEWMODE_DASHBOARD,
    CALENDARIZATION_VIEWMODE_DAY_DETAIL,
    CALENDARIZATION_VIEWMODE_HISTORY,
)
from notas.presentation.pages.calendarized_dailyplan import (
    build_calendarized_dailyplan_detail,
)
from notas.presentation.pages.calendarized_meal import build_calendarized_meal_detail
from notas.presentation.pages.home_calendarization import build_home_calendarization_vm

ERROR_MESSAGES = {
    "calendarization_incomplete_confirmation_required": "El programa está incompleto. Confirma que deseas calendarizarlo con días vacíos.",
    "calendarization_replacement_confirmation_required": "Ya tienes una calendarización vigente. Confirma que deseas reemplazarla.",
    "calendarization_start_date_past": "La fecha de inicio no puede estar en el pasado para tu zona horaria.",
    "calendarization_program_not_owned": "Solo puedes calendarizar programas propios.",
    "calendarization_current_conflict": "El programa coincide con fechas ocupadas por planes individuales, o el calendario cambió. Revisa esas fechas e inténtalo de nuevo.",
}


def _context(viewmode, content):
    ui = build_ui_vm(viewmode)
    return {"vm": {"ui": asdict(ui), "content": content}}


def _can_check_in_today(day) -> bool:
    calendarization = day.calendarization
    today = (
        today_for_calendarization(calendarization)
        if calendarization else local_date_for_timezone(day.user.profile.timezone_name or "UTC")
    )
    if day.calendar_date != today or day.assignment_state != CalendarizedDay.STATE_CURRENT:
        return False
    if calendarization is None:
        return True
    return calendarization.status in {
        calendarization.STATUS_SCHEDULED,
        calendarization.STATUS_ACTIVE,
    } or (
        calendarization.status == calendarization.STATUS_CANCELLED
        and calendarization.replaced_by_id is not None
        and calendarization.replacement_effective_on is not None
        and day.calendar_date < calendarization.replacement_effective_on
    )


def _header(*, history=False, extra_actions=None):
    action = {
        "key": "calendarization_dashboard" if history else "calendarization_history",
        "label": "Calendarizador" if history else "Historial",
        "method": "get",
        "icon": "calendar-clock" if history else "history",
        "desktop_position": "menu",
        "mobile_position": "menu",
        "url": reverse("calendarization_dashboard" if history else "calendarization_history"),
    }
    return asdict(build_page_header(actions=[action, *(extra_actions or [])]))


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
    current_program_url = (
        reverse("program_detail", args=[current.source_program_id]) if current and current.source_program_id else ""
    )
    original_program_action = {
        "key": "view_original_program",
        "label": "Ver programa original",
        "method": "get",
        "icon": "external-link",
        "desktop_position": "menu",
        "mobile_position": "menu",
        "url": current_program_url,
    } if current_program_url else None
    today = today_for_calendarization(current) if current else None
    today_day = current.days.filter(calendar_date=today).first() if current and today else None
    content = {
        "header": _header(extra_actions=[original_program_action] if original_program_action else []),
        "programs": programs,
        "current": current,
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
def calendar_preview(request):
    today = local_date_for_timezone(request.user.profile.timezone_name or "UTC")
    monday = today - timedelta(days=today.weekday())
    end_date = monday + timedelta(days=34)
    extended = request.GET.get("extended") == "1"
    requested = request.GET.get("date", "")
    try:
        selected_date = date.fromisoformat(requested) if requested else today
    except ValueError:
        selected_date = today
    if not monday <= selected_date <= end_date:
        selected_date = today
    rows = CalendarizedDay.objects.filter(
        Q(user=request.user) | Q(user__isnull=True, calendarization__user=request.user),
        assignment_state=CalendarizedDay.STATE_CURRENT,
        calendar_date__range=(monday, end_date),
    ).select_related("calendarization", "origin_calendarization")
    by_date = {day.calendar_date: day for day in rows}
    commitments_by_date = {}
    for commitment in CalendarCommitment.objects.filter(
        user=request.user, calendar_date__range=(monday, end_date)
    ):
        commitments_by_date.setdefault(commitment.calendar_date, []).append(commitment)
    dates = []
    for offset in range(35):
        current_date = monday + timedelta(days=offset)
        day = by_date.get(current_date)
        dates.append({
            "date": current_date,
            "weekday": ("L", "M", "M", "J", "V", "S", "D")[current_date.weekday()],
            "has_plan": bool(day and day.has_plan),
            "plan_name": (day.plan_snapshot or {}).get("name", "") if day else "",
            "program_name": (day.origin_calendarization or day.calendarization).program_name_snapshot if day and (day.origin_calendarization or day.calendarization) else "",
            "is_today": current_date == today,
            "is_selected": current_date == selected_date,
            "detail_url": reverse("calendarization_day_detail", args=[day.id]) if day and day.has_plan else "",
            "commitments": commitments_by_date.get(current_date, []),
        })
    selected_day = by_date.get(selected_date)
    return render(request, "notas/calendarization/calendar_preview.html", _context(
        CALENDARIZATION_VIEWMODE_DASHBOARD,
        {
            "header": _header(),
            "today": today,
            "selected_date": selected_date,
            "selected_day": selected_day,
            "selected_commitments": commitments_by_date.get(selected_date, []),
            "selected_day_has_execution": bool(selected_day and selected_day.meal_execution_events.exists()),
            "selected_history": CalendarizedDay.objects.filter(
                user=request.user, calendar_date=selected_date
            ).select_related("origin_calendarization", "calendarization").order_by("created_at", "id"),
            "week": dates[:7],
            "grid": dates[7:35],
            "upcoming": [day for day in dates if day["date"] >= today][:7],
            "extended_days": dates,
            "extended": extended,
            "plans": DailyPlan.objects.filter(created_by=request.user).exclude(
                source=DailyPlan.SOURCE_PROGRAM
            ).order_by("name", "id"),
            "progress": calendar_adherence_summary(request.user),
            "schedule_summary": calendar_future_schedule_summary(request.user, today=today),
        },
    ))


@login_required
def calendar_commitments(request, kind):
    labels = dict(CalendarCommitment.KIND_CHOICES)
    if kind not in labels:
        raise Http404
    today = local_date_for_timezone(request.user.profile.timezone_name or "UTC")
    if request.method == "POST":
        try:
            dates = [date.fromisoformat(value) for value in request.POST.getlist("dates")]
            raw_attachments = json.loads(request.POST.get("food_attachments", "[]"))
            if not isinstance(raw_attachments, list):
                raise ValueError("calendar_food_attachment_dates_invalid")
            food_attachments = [
                (
                    date.fromisoformat(item["calendar_date"]),
                    date.fromisoformat(item["food_period_start"]),
                    date.fromisoformat(item["food_period_end"]),
                )
                for item in raw_attachments
            ]
            raw_notes = json.loads(request.POST.get("notes_by_date", "[]"))
            if not isinstance(raw_notes, list):
                raise ValueError("calendar_commitment_note_dates_invalid")
            note_dates = [date.fromisoformat(item["calendar_date"]) for item in raw_notes]
            if len(set(note_dates)) != len(note_dates):
                raise ValueError("calendar_commitment_note_dates_invalid")
            register_calendar_commitments(
                user=request.user,
                kind=kind,
                dates=dates,
                note=request.POST.get("note", ""),
                food_period_start=(
                    date.fromisoformat(request.POST["food_period_start"])
                    if request.POST.get("food_period_start") else None
                ),
                food_period_end=(
                    date.fromisoformat(request.POST["food_period_end"])
                    if request.POST.get("food_period_end") else None
                ),
                food_attachments=food_attachments,
                notes_by_date={date.fromisoformat(item["calendar_date"]): item["note"] for item in raw_notes},
            )
        except (ValueError, TypeError, KeyError) as exc:
            errors = {
                "calendar_commitment_kind_invalid": "Elige un tipo de compromiso válido.",
                "calendar_commitment_dates_invalid": "Elige entre 1 y 62 fechas distintas.",
                "calendar_commitment_date_in_past": "No puedes registrar compromisos en fechas pasadas.",
                "calendar_commitment_note_too_long": "La nota no puede superar los 500 caracteres.",
                "calendar_commitment_note_dates_invalid": "Cada nota debe corresponder a una fecha seleccionada y distinta.",
                "calendar_commitment_already_exists": "Una de las fechas ya tiene ese compromiso. Revisa tu selección.",
                "calendar_food_period_invalid": "Elige un periodo válido de hasta 366 días.",
                "calendar_food_period_incomplete": "Elige ambas fechas del periodo o deja ambas vacías.",
                "calendar_food_period_wrong_kind": "La lista de alimentos corresponde a Hacer compras o Cocinar.",
                "calendar_food_period_multiple_dates": "Adjunta cada lista a una sola fecha del compromiso.",
                "calendar_food_attachment_dates_invalid": "Cada lista debe corresponder a una fecha seleccionada y distinta.",
            }
            messages.error(request, errors.get(str(exc), "No pudimos registrar los compromisos."))
        else:
            invalidate_mobile_read_cache(request.user.id)
            messages.success(request, "Compromisos registrados en el calendario.")
            return redirect("calendar_preview")
        return redirect("calendar_commitments", kind=kind)
    if request.method != "GET":
        return HttpResponseBadRequest()
    existing_dates = list(
        CalendarCommitment.objects.filter(user=request.user, kind=kind, calendar_date__gte=today)
        .values_list("calendar_date", flat=True)
    )
    return render(request, "notas/calendarization/calendar_commitments.html", {
        "kind": kind,
        "kind_label": {"shopping": "Registrar días de compras", "cooking": "Registrar días de cocinar", "training": "Registrar días de entrenamiento"}[kind],
        "today": today,
        "existing_dates": [value.isoformat() for value in existing_dates],
    })


@login_required
@require_GET
def calendar_commitment_foods(request):
    try:
        start_date = date.fromisoformat(request.GET.get("start_date", ""))
        end_date = date.fromisoformat(request.GET.get("end_date", ""))
        period = calendar_foods_for_period(request.user, start_date=start_date, end_date=end_date)
    except ValueError:
        return JsonResponse({"error": "Elige un periodo válido de hasta 366 días."}, status=422)
    return JsonResponse({
        "plans_count": period["plans_count"],
        "meals_count": period["meals_count"],
        "foods": [
            {
                "name": row["rel"]["name"],
                "quantity": row["rel"]["quantity"],
                "quantity_unit": row["rel"]["quantity_unit"],
            }
            for row in period["foods_aggregation_table"]
        ],
    })


@login_required
@require_POST
def calendar_preview_action(request):
    action = request.POST.get("action", "")
    extended = request.POST.get("extended") == "1"
    try:
        local_date = date.fromisoformat(request.POST.get("date", ""))
    except ValueError:
        messages.error(request, "Selecciona una fecha válida.")
        return redirect("calendar_preview")
    target = f"{reverse('calendar_preview')}?date={local_date.isoformat()}"
    if extended:
        target += "&extended=1"
    try:
        if action == "assign":
            assign_dailyplan_to_calendar_date(
                user=request.user,
                dailyplan_id=int(request.POST.get("dailyplan_id", "0")),
                local_date=local_date,
                assignment_key=str(uuid.uuid4()),
                replace_existing=request.POST.get("confirm_replace") == "1",
            )
        elif action == "remove":
            remove_calendar_date_plan(user=request.user, local_date=local_date)
        elif action == "move":
            target_date = date.fromisoformat(request.POST.get("target_date", ""))
            move_calendar_date_plan(
                user=request.user,
                source_date=local_date,
                target_date=target_date,
                assignment_key=str(uuid.uuid4()),
                replace_existing=request.POST.get("confirm_replace") == "1",
            )
            target = f"{reverse('calendar_preview')}?date={target_date.isoformat()}"
            if extended:
                target += "&extended=1"
        elif action == "reset_progress":
            start_new_calendar_progress_period(user=request.user)
        else:
            raise ValueError("calendar_action_invalid")
    except (ValueError, TypeError) as exc:
        errors = {
            "calendar_replacement_confirmation_required": "Confirma que quieres reemplazar el plan que ya ocupa esa fecha.",
            "calendar_day_has_execution": "No se puede cambiar un día pasado o con cumplimiento registrado.",
            "calendar_move_program_day_unsupported": "Por ahora, mueve desde el calendario solo planes asignados individualmente.",
            "calendar_date_in_past": "No se puede modificar una fecha pasada.",
            "calendar_dailyplan_not_owned": "Selecciona un plan de tu biblioteca.",
        }
        messages.error(request, errors.get(str(exc), "No pudimos actualizar esa fecha. Revisa los datos e inténtalo de nuevo."))
    else:
        invalidate_mobile_read_cache(request.user.id)
        messages.success(request, "Calendario actualizado sin borrar el historial.")
    return HttpResponseRedirect(target)


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
    rename_action = {
        "key": "rename",
        "label": "Renombrar",
        "method": "get",
        "icon": "pencil",
        "desktop_position": "menu",
        "mobile_position": "menu",
        "url": reverse("calendarization_day_rename", args=[day.id]),
    }
    header = _header(extra_actions=[rename_action])
    content = {
        "header": header,
        "day": day,
    }
    if day.has_plan:
        detail = build_calendarized_dailyplan_detail(
            day=day,
            user=request.user,
            header=header,
        )
        execution = meal_execution_state_for_day(day)
        state_by_key = {item["meal_key"]: item for item in execution}
        completion_items = [
            {
                "name": meal["name"],
                "completed": state_by_key.get(meal["key"], {}).get("status") == "completed",
            }
            for meal in detail["calendarized_meals"]
            if meal["key"]
        ]
        can_check_in = _can_check_in_today(day)
        return_to = reverse("calendarization_day_detail", args=[day.id])
        meal_entries = []
        for index, (meal, child_card) in enumerate(
            zip(detail["calendarized_meals"], detail["child_cards"]),
            start=1,
        ):
            meal_key = meal["key"]
            state = state_by_key.get(
                meal_key,
                {"status": "planned", "note": "", "recorded_at": None},
            )
            note = str(state.get("note") or "")
            meal_entries.append(
                {
                    "card": child_card,
                    "checkin": {
                        "day": day,
                        "meal": meal,
                        "execution": {**state, "note": note},
                        "completed": state.get("status") == "completed",
                        "has_note": bool(note.strip()),
                        "instance_id": f"{day.id}-{index}",
                        "status_idempotency_key": f"web-day-meal-status-{uuid.uuid4()}",
                        "note_idempotency_key": f"web-day-meal-note-{uuid.uuid4()}",
                        "return_to": return_to,
                    }
                    if can_check_in and meal_key
                    else None,
                }
            )
        content.update(detail)
        content["day"] = day
        content["can_check_in"] = can_check_in
        content["meal_entries"] = meal_entries
        content["meal_completion"] = {
            "completed_count": sum(item["completed"] for item in completion_items),
            "total_count": len(completion_items),
            "items": completion_items,
        }

    return render(
        request,
        "notas/calendarization/day_detail.html",
        _context(
            CALENDARIZATION_VIEWMODE_DAY_DETAIL,
            content,
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
    detail["can_check_in"] = _can_check_in_today(day)
    detail["status_idempotency_key"] = f"web-meal-status-{uuid.uuid4()}"
    detail["note_idempotency_key"] = f"web-meal-note-{uuid.uuid4()}"
    detail["instance_id"] = f"{day.id}-detail"
    change_time_action = {
        "key": "change_time",
        "label": "Cambiar hora",
        "method": "get",
        "icon": "clock-3",
        "desktop_position": "inline",
        "mobile_position": "inline",
        "url": reverse(
            "calendarization_meal_change_time",
            args=[day.id, meal_snapshot_key],
        ),
    }
    rename_action = {
        "key": "rename",
        "label": "Renombrar",
        "method": "get",
        "icon": "pencil",
        "desktop_position": "menu",
        "mobile_position": "menu",
        "url": reverse(
            "calendarization_meal_rename",
            args=[day.id, meal_snapshot_key],
        ),
    }
    return render(
        request,
        "notas/calendarization/meal_detail.html",
        _context(
            CALENDARIZATION_VIEWMODE_DAY_DETAIL,
            {
                "header": _header(extra_actions=[rename_action, change_time_action]),
                "meal_detail": detail,
            },
        ),
    )


@login_required
def day_rename(request, day_id):
    day = calendarized_day_for_user(request.user, day_id)
    if day is None or not day.has_plan:
        raise Http404("Día calendarizado no encontrado")
    detail_url = reverse("calendarization_day_detail", args=[day.id])
    current_name = (day.plan_snapshot or {}).get("name", "")

    if request.method == "POST":
        try:
            rename_calendarized_day_plan(
                user=request.user,
                day_id=day.id,
                name=request.POST.get("name", ""),
            )
        except ValueError as exc:
            if str(exc) == "calendarized_day_not_found":
                raise Http404("Día calendarizado no encontrado") from exc
            messages.error(request, "El nombre no puede estar vacío.")
        else:
            messages.success(request, "Nombre del plan activo actualizado.")
            return redirect(detail_url)

    return render(
        request,
        "notas/calendarization/snapshot_rename.html",
        {
            "title": "Renombrar plan activo",
            "current_name": current_name,
            "cancel_url": detail_url,
            "entity_icon": "clipboard-list",
            "entity_class": "dailyplan",
        },
    )


@login_required
def meal_rename(request, day_id, meal_snapshot_key):
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
    detail_url = reverse(
        "calendarization_meal_detail",
        args=[day.id, meal_snapshot_key],
    )

    if request.method == "POST":
        try:
            rename_calendarized_meal(
                user=request.user,
                day_id=day.id,
                meal_snapshot_key=meal_snapshot_key,
                name=request.POST.get("name", ""),
            )
        except ValueError as exc:
            if str(exc) in {"calendarized_day_not_found", "meal_snapshot_key_invalid"}:
                raise Http404("Comida calendarizada no encontrada") from exc
            messages.error(request, "El nombre no puede estar vacío.")
        else:
            messages.success(request, "Nombre de la comida activa actualizado.")
            return redirect(detail_url)

    return render(
        request,
        "notas/calendarization/snapshot_rename.html",
        {
            "title": "Renombrar comida activa",
            "current_name": detail["meal"].get("name", ""),
            "cancel_url": detail_url,
            "entity_icon": "utensils",
            "entity_class": "meal",
        },
    )


@login_required
def meal_change_time(request, day_id, meal_snapshot_key):
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
    detail_url = reverse(
        "calendarization_meal_detail",
        args=[day_id, meal_snapshot_key],
    )
    form = MealTimeChangeForm(
        request.POST or None,
        initial={"hour": detail["meal"].get("hour") or None},
    )

    if request.method == "POST" and form.is_valid():
        try:
            update_calendarized_meal_hour(
                user=request.user,
                day_id=day_id,
                meal_snapshot_key=meal_snapshot_key,
                hour=form.cleaned_data["hour"],
            )
        except ValueError as exc:
            if str(exc) in {"calendarized_day_not_found", "meal_snapshot_key_invalid"}:
                raise Http404("Comida calendarizada no encontrada") from exc
            messages.error(request, "No fue posible guardar la nueva hora.")
        else:
            messages.success(request, "Hora de la comida actualizada.")
            return redirect(detail_url)

    context = _context(
        CALENDARIZATION_VIEWMODE_DAY_DETAIL,
        {
            "header": asdict(build_page_header()),
            "title": "Cambiar hora",
            "description": "El cambio se aplicará a esta comida del plan activo y actualizará su recordatorio.",
            "cancel_url": detail_url,
        },
    )
    context["vm"]["ui"]["back_url"] = detail_url
    context["vm"]["ui"]["title"] = "Cambiar hora"
    context["form"] = form
    return render(request, "notas/time_change.html", context)


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
    else:
        invalidate_mobile_read_cache(request.user.id)
    return_to = request.POST.get("return_to", "").strip()
    if return_to and url_has_allowed_host_and_scheme(
        return_to,
        allowed_hosts={request.get_host()},
        require_https=request.is_secure(),
    ):
        return redirect(return_to)
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
