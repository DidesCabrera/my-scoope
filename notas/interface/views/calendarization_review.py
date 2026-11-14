"""Web review and prospective revision decisions for a calendarized program."""

import uuid
from dataclasses import asdict
from datetime import timedelta

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import Http404
from django.shortcuts import redirect, render
from django.views.decorators.http import require_GET, require_POST

from notas.application.queries.calendarization_execution_queries import pending_revision_for_calendarization
from notas.application.queries.calendarization_queries import (
    current_calendarization_for_user,
    today_for_calendarization,
)
from notas.application.services.commands.calendarization_execution_commands import (
    create_calendarization_review,
    decide_calendarization_revision,
)
from notas.domain.models import CalendarizationReview
from notas.presentation.composition.viewmodel.components.builder_headers import build_page_header
from notas.presentation.composition.viewmodel.ui_builder import build_ui_vm
from notas.presentation.config.viewmodel_config import CALENDARIZATION_VIEWMODE_DASHBOARD


def _comparison_days(revision):
    if revision is None:
        return []
    before = {row.get("calendar_date"): row for row in revision.before_snapshot.get("days", [])}
    rows = []
    for proposed in revision.after_snapshot.get("days", []):
        date_key = proposed.get("calendar_date")
        current = before.get(date_key, {})
        current_plan = current.get("plan_snapshot") or {}
        proposed_plan = proposed.get("plan_snapshot") or {}
        rows.append({
            "date": date_key,
            "before_name": current_plan.get("name", "Plan actual"),
            "after_name": proposed_plan.get("name", "Plan propuesto"),
            "before_kcal": (current_plan.get("totals") or {}).get("total_kcal", 0),
            "after_kcal": (proposed_plan.get("totals") or {}).get("total_kcal", 0),
        })
    return rows


@login_required
@require_GET
def review_detail(request):
    current = current_calendarization_for_user(request.user)
    today = today_for_calendarization(current) if current else None
    review_start = max(current.start_date, today - timedelta(days=6)) if current else None
    pending = pending_revision_for_calendarization(current) if current else None
    reviews = CalendarizationReview.objects.filter(calendarization__user=request.user).order_by(
        "-period_end", "-created_at", "-id",
    )[:12]
    content = {
        "header": asdict(build_page_header(actions=[])),
        "current": current,
        "today": today,
        "review_start": review_start,
        "can_review": bool(current and today >= current.start_date),
        "review_idempotency_key": str(uuid.uuid4()),
        "pending": pending,
        "comparison_days": _comparison_days(pending),
        "reviews": reviews,
    }
    return render(request, "notas/calendarization/review.html", {
        "vm": {"ui": asdict(build_ui_vm(CALENDARIZATION_VIEWMODE_DASHBOARD)), "content": content},
    })


@login_required
@require_POST
def review_create(request):
    current = current_calendarization_for_user(request.user)
    if current is None:
        raise Http404("Programa vigente no encontrado")
    today = today_for_calendarization(current)
    if today < current.start_date:
        messages.error(request, "La revisión estará disponible cuando comience el programa.")
        return redirect("calendarization_review")
    period_start = max(current.start_date, today - timedelta(days=6))
    try:
        create_calendarization_review(
            user=request.user, period_start=period_start, period_end=today,
            idempotency_key=request.POST.get("idempotency_key", ""),
            energy_score=int(request.POST.get("energy_score", "")),
            hunger_score=int(request.POST.get("hunger_score", "")),
            training_performance_score=int(request.POST.get("training_performance_score", "")),
            note=request.POST.get("note", ""),
        )
    except (ValueError, TypeError):
        messages.error(request, "Revisa las puntuaciones y el periodo de tu programa.")
    else:
        messages.success(request, "Revisión registrada. No cambió tu programa automáticamente.")
    return redirect("calendarization_review")


@login_required
@require_POST
def revision_decide(request, revision_id):
    decision = request.POST.get("decision")
    if decision not in {"approve", "reject"}:
        messages.error(request, "Elige aprobar o rechazar el ajuste.")
        return redirect("calendarization_review")
    try:
        decide_calendarization_revision(
            user=request.user, revision_id=revision_id, decision=decision,
        )
    except ValueError as exc:
        if str(exc) == "calendarization_revision_not_found":
            raise Http404("Ajuste no encontrado") from exc
        messages.error(request, "El ajuste ya cambió o no puede aplicarse. Revisa el programa vigente.")
    else:
        if decision == "approve":
            messages.success(request, "Ajuste aplicado a las fechas futuras.")
        else:
            messages.success(request, "Ajuste rechazado. El programa continúa sin cambios.")
    return redirect("calendarization_review")
