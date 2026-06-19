from __future__ import annotations

import json
from dataclasses import asdict

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.mail import send_mail
from django.core.serializers.json import DjangoJSONEncoder
from django.conf import settings
from django.db.models import Q
from django.http import HttpResponse, HttpResponseBadRequest, HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST

from notas.application.services.access.capabilities import get_capabilities
from notas.application.services.commands.program_commands import (
    assign_dailyplan_to_program_slot,
    copy_program as copy_program_command,
    create_weekly_program,
    delete_program,
    fork_program as fork_program_command,
    remove_program_day,
)
from notas.application.services.commands.share_commands import create_program_share
from notas.application.services.nutrition.food_aggregation import (
    build_dailyplan_foods_aggregation,
)
from notas.application.services.nutrition.weight import get_current_weight
from notas.domain.models import DailyPlan, Program, ProgramDay
from notas.interface.forms.forms import ProgramShareForm
from notas.presentation.composition.viewmodel.components.builder_menu import (
    build_dailyplan_menu,
)
from notas.presentation.composition.viewmodel.components.builder_table_items import (
    build_dailyplan_food_aggregation_table_item,
    build_dailyplanmeal_table_item,
)
from notas.presentation.config.icons import CONTENT_ICON_REGISTRY
from notas.presentation.resolvers.title_resolvers import resolve_category_badge
from notas.presentation.composition.viewmodel.components.builder_headers import build_page_header
from notas.presentation.composition.viewmodel.ui_builder import build_ui_vm
from notas.presentation.config.viewmodel_config import (
    PROGRAM_VIEWMODE_CONFIGURE,
    PROGRAM_VIEWMODE_CREATE,
    PROGRAM_VIEWMODE_PERSONAL_DETAIL,
    PROGRAM_VIEWMODE_PERSONAL_LIST,
    PROGRAM_VIEWMODE_SHARE,
)

DAY_LABELS = (
    (1, "Lun"),
    (2, "Mar"),
    (3, "Mié"),
    (4, "Jue"),
    (5, "Vie"),
    (6, "Sáb"),
    (7, "Dom"),
)


# ==================================================
# UI HELPERS
# ==================================================

def _action(
    *,
    key,
    label,
    url,
    method="get",
    icon="chevron-right",
    order=90,
    desktop_position="inline",
    mobile_position="inline",
    is_back=False,
    disabled=False,
    extra_class="",
):
    return {
        "key": key,
        "label": label,
        "url": url,
        "method": method,
        "icon": icon,
        "order": order,
        "desktop_position": desktop_position,
        "mobile_position": mobile_position,
        "is_back": is_back,
        "disabled": disabled,
        "extra_class": extra_class,
    }


def _program_list_actions(list_mode="list"):
    if list_mode == "reorder":
        return [
            _action(
                key="save_list_order",
                label="Guardar Orden",
                url=reverse("program_list_reorder"),
                method="button",
                icon="check",
                order=10,
                extra_class="js-list-reorder-save",
            )
        ]

    if list_mode == "delete":
        return [
            _action(
                key="exit_delete_mode",
                label="Cerrar",
                url=reverse("program_list"),
                icon="check",
                order=10,
            ),
            _action(
                key="bulk_delete",
                label="Eliminar seleccionados",
                url=reverse("program_list_bulk_delete"),
                method="post",
                icon="trash-2",
                order=20,
                disabled=True,
                extra_class="js-list-bulk-delete-submit",
            ),
        ]

    return [
        _action(
            key="create",
            label="Crear",
            url=reverse("program_create"),
            icon="plus",
            order=10,
        ),
        _action(
            key="enter_reorder_mode",
            label="Reordenar Programas",
            url=f"{reverse('program_list')}?mode=reorder",
            icon="list-ordered",
            order=20,
            desktop_position="menu",
            mobile_position="menu",
        ),
        _action(
            key="enter_delete_mode",
            label="Eliminar Programas",
            url=f"{reverse('program_list')}?mode=delete",
            icon="trash-2",
            order=30,
            desktop_position="menu",
            mobile_position="menu",
        ),
    ]


def _program_detail_actions(program, user):
    actions = [
        _action(
            key="back_to_list",
            label="Volver",
            url=reverse("program_list"),
            method="get",
            icon="chevron-left",
            order=10,
            is_back=True,
            mobile_position="hidden",
        ),
    ]

    is_owner = program.created_by_id == user.id

    if is_owner:
        actions.extend([
            _action(
                key="configure",
                label="Configurar",
                url=reverse("configure_program", args=[program.id]),
                icon="settings",
                order=30,
                mobile_position="menu",
            ),
            _action(
                key="share",
                label="Compartir",
                url=reverse("program_share", args=[program.id]),
                icon="send",
                order=40,
                mobile_position="menu",
            ),
        ])

    if is_owner or program.is_forkable:
        actions.append(
            _action(
                key="fork",
                label="Duplicar",
                url=reverse("fork_program", args=[program.id]),
                method="post",
                icon="copy",
                order=50,
                desktop_position="menu",
                mobile_position="menu",
            )
        )

    if is_owner or program.is_copiable:
        actions.append(
            _action(
                key="copy",
                label="Copiar limpio",
                url=reverse("copy_program", args=[program.id]),
                method="post",
                icon="copy-plus",
                order=60,
                desktop_position="menu",
                mobile_position="menu",
            )
        )

    if is_owner:
        actions.append(
            _action(
                key="remove",
                label="Eliminar",
                url=reverse("program_remove", args=[program.id]),
                method="post",
                icon="trash-2",
                order=70,
                desktop_position="menu",
                mobile_position="menu",
            )
        )

    return actions


def _header(actions=None):
    return asdict(build_page_header(actions=actions or []))


def _vm_context(viewmode, *, content, instance=None):
    ui_vm = build_ui_vm(viewmode, instance=instance)
    return {
        "vm": {
            "ui": asdict(ui_vm),
            "content": content,
        }
    }


def _normalize_list_mode(request_get=None):
    mode = (request_get or {}).get("mode", "list")
    return mode if mode in {"list", "reorder", "delete"} else "list"


def _safe_return_to(request, fallback_name, mode=None):
    fallback_url = reverse(fallback_name)
    if mode:
        fallback_url = f"{fallback_url}?mode={mode}"

    return_to = request.POST.get("return_to") or request.GET.get("return_to") or ""
    if return_to and url_has_allowed_host_and_scheme(
        url=return_to,
        allowed_hosts={request.get_host()},
        require_https=request.is_secure(),
    ):
        return return_to

    return fallback_url


# ==================================================
# NUTRITION HELPERS
# ==================================================

def _plan_snapshot(dailyplan):
    total_kcal = dailyplan.total_kcal or 0
    protein = dailyplan.protein or 0
    carbs = dailyplan.carbs or 0
    fat = dailyplan.fat or 0
    kcal_protein = dailyplan.kcal_protein or 0
    kcal_carbs = dailyplan.kcal_carbs or 0
    kcal_fat = dailyplan.kcal_fat or 0

    if total_kcal > 0:
        alloc = {
            "protein": kcal_protein / total_kcal * 100,
            "carbs": kcal_carbs / total_kcal * 100,
            "fat": kcal_fat / total_kcal * 100,
        }
    else:
        alloc = {"protein": 0, "carbs": 0, "fat": 0}

    return {
        "id": dailyplan.id,
        "name": dailyplan.name,
        "total_kcal": total_kcal,
        "protein": protein,
        "carbs": carbs,
        "fat": fat,
        "kcal_protein": kcal_protein,
        "kcal_carbs": kcal_carbs,
        "kcal_fat": kcal_fat,
        "alloc": alloc,
        "meals_count": dailyplan.dailyplan_meals.count(),
    }


def _empty_totals():
    return {
        "total_kcal": 0,
        "protein": 0,
        "carbs": 0,
        "fat": 0,
        "kcal_protein": 0,
        "kcal_carbs": 0,
        "kcal_fat": 0,
        "alloc": {"protein": 0, "carbs": 0, "fat": 0},
    }


def _add_snapshot(totals, snapshot):
    for key in (
        "total_kcal",
        "protein",
        "carbs",
        "fat",
        "kcal_protein",
        "kcal_carbs",
        "kcal_fat",
    ):
        totals[key] += snapshot[key]


def _finalize_totals(totals):
    total_kcal = totals["total_kcal"]
    if total_kcal > 0:
        totals["alloc"] = {
            "protein": totals["kcal_protein"] / total_kcal * 100,
            "carbs": totals["kcal_carbs"] / total_kcal * 100,
            "fat": totals["kcal_fat"] / total_kcal * 100,
        }
    return totals


def _average_totals(totals, divisor=7):
    divisor = divisor or 1
    averaged = _empty_totals()
    for key in (
        "total_kcal",
        "protein",
        "carbs",
        "fat",
        "kcal_protein",
        "kcal_carbs",
        "kcal_fat",
    ):
        averaged[key] = totals[key] / divisor
    return _finalize_totals(averaged)

def _kpi_from_totals(totals):
    return {
        "ppk": None,
        "tot_kcal": totals["total_kcal"],
        "g_protein": totals["protein"],
        "g_carbs": totals["carbs"],
        "g_fat": totals["fat"],
        "kcal_protein": totals["kcal_protein"],
        "kcal_carbs": totals["kcal_carbs"],
        "kcal_fat": totals["kcal_fat"],
        "alloc_protein": totals["alloc"]["protein"],
        "alloc_carbs": totals["alloc"]["carbs"],
        "alloc_fat": totals["alloc"]["fat"],
    }


def _dailyplan_meals_for_card(dailyplan):
    prefetched = getattr(dailyplan, "_prefetched_objects_cache", {}).get(
        "dailyplan_meals"
    )

    if prefetched is not None:
        return list(prefetched)

    return list(dailyplan.meals_with_foods())


def _program_slot_dailyplan_card(dailyplan, user):
    dailyplan_meals = _dailyplan_meals_for_card(dailyplan)
    snapshot = _plan_snapshot(dailyplan)
    current_weight = get_current_weight(user)
    foods_aggregation = build_dailyplan_foods_aggregation(dailyplan_meals)

    return {
        "id": f"program-slot-{dailyplan.id}",
        "child_id": dailyplan.id,
        "titulo": {
            "name": dailyplan.name,
            "label": "DailyPlan",
            "icon": CONTENT_ICON_REGISTRY.get("dailyplan"),
            "category": dailyplan.category,
            "category_badge": resolve_category_badge(dailyplan.category),
            "structural_indicators": {
                "meals_count": len(dailyplan_meals),
                "foods_count": len(foods_aggregation),
            },
            "url": None,
        },
        "kpis": {
            "ppk": (snapshot["protein"] / current_weight)
            if (current_weight and snapshot["protein"])
            else None,
            "tot_kcal": snapshot["total_kcal"],
            "g_protein": snapshot["protein"],
            "g_carbs": snapshot["carbs"],
            "g_fat": snapshot["fat"],
            "kcal_protein": snapshot["kcal_protein"],
            "kcal_carbs": snapshot["kcal_carbs"],
            "kcal_fat": snapshot["kcal_fat"],
            "alloc_protein": snapshot["alloc"]["protein"],
            "alloc_carbs": snapshot["alloc"]["carbs"],
            "alloc_fat": snapshot["alloc"]["fat"],
        },
        "table": {
            "items": [
                build_dailyplanmeal_table_item(
                    dailyplan_meal,
                    dailyplan_snapshot=snapshot,
                )
                for dailyplan_meal in dailyplan_meals
            ],
        },
        "menu": build_dailyplan_menu(dailyplan_meals),
        "foods_aggregation": foods_aggregation,
        "metadata": {
            "owner": str(dailyplan.created_by),
            "author": str(dailyplan.original_author),
            "fork_from": str(dailyplan.forked_from) if dailyplan.forked_from else None,
        },
        "actions": [
            _action(
                key="detail",
                label="Ir a detalle",
                url=reverse("dailyplan_detail", args=[dailyplan.id]),
                icon="pencil",
            ),
        ],
    }


def _available_dailyplans(user):
    return (
        DailyPlan.objects
        .filter(
            created_by=user,
            is_draft=False,
        )
        .exclude(source=DailyPlan.SOURCE_PROGRAM)
        .prefetch_related("dailyplan_meals__meal__meal_food_set__food")
        .order_by("list_order", "-created_at", "-id")
        .distinct()
    )


def _program_days_queryset(program):
    return (
        program.program_dailyplan
        .select_related("dailyplan")
        .prefetch_related("dailyplan__dailyplan_meals__meal__meal_food_set__food")
        .all()
        .order_by("week_number", "day_number", "id")
    )


def build_weekly_grid(program, program_days, user=None, include_dailyplan_cards=False):
    slots = {
        (program_day.week_number, program_day.day_number): program_day
        for program_day in program_days
    }
    weeks = []
    program_totals = _empty_totals()
    week_totals_for_variance = []
    program_dailyplan_meals = []

    for week_number in range(1, program.normalized_duration_weeks + 1):
        week_totals = _empty_totals()
        week_dailyplan_meals = []
        days = []

        for day_number, day_label in DAY_LABELS:
            program_day = slots.get((week_number, day_number))
            snapshot = None

            dailyplan_card = None

            if program_day:
                snapshot = _plan_snapshot(program_day.dailyplan)
                dailyplan_meals = _dailyplan_meals_for_card(program_day.dailyplan)
                week_dailyplan_meals.extend(dailyplan_meals)
                program_dailyplan_meals.extend(dailyplan_meals)
                if include_dailyplan_cards and user is not None:
                    dailyplan_card = _program_slot_dailyplan_card(
                        program_day.dailyplan,
                        user,
                    )
                _add_snapshot(week_totals, snapshot)
                _add_snapshot(program_totals, snapshot)

            days.append({
                "day_number": day_number,
                "day_label": day_label,
                "program_day": program_day,
                "dailyplan": program_day.dailyplan if program_day else None,
                "snapshot": snapshot,
                "dailyplan_card": dailyplan_card,
            })

        week_totals = _finalize_totals(week_totals)
        week_totals_for_variance.append(week_totals["total_kcal"])
        week_averages = _average_totals(week_totals, divisor=len(DAY_LABELS))
        week_foods_aggregation = build_dailyplan_foods_aggregation(week_dailyplan_meals)
        week_foods_aggregation_table = [
            build_dailyplan_food_aggregation_table_item(
                food_aggregation,
                dailyplan_snapshot=week_totals,
            )
            for food_aggregation in week_foods_aggregation
        ]
        weeks.append({
            "week_number": week_number,
            "days": days,
            "totals": week_totals,
            "averages": week_averages,
            "kpis": _kpi_from_totals(week_totals),
            "average_kpis": _kpi_from_totals(week_averages),
            "filled_days_count": sum(1 for day in days if day["program_day"]),
            "meals_count": len(week_dailyplan_meals),
            "foods_count": len(week_foods_aggregation),
            "foods_aggregation": week_foods_aggregation,
            "foods_aggregation_table": week_foods_aggregation_table,
            "foods_panel_id": f"program-week-{week_number}",
        })

    program_totals = _finalize_totals(program_totals)
    program_foods_aggregation = build_dailyplan_foods_aggregation(program_dailyplan_meals)
    program_foods_aggregation_table = [
        build_dailyplan_food_aggregation_table_item(
            food_aggregation,
            dailyplan_snapshot=program_totals,
        )
        for food_aggregation in program_foods_aggregation
    ]
    non_zero_weeks = [value for value in week_totals_for_variance if value > 0]
    avg_week_kcal = (sum(non_zero_weeks) / len(non_zero_weeks)) if non_zero_weeks else 0

    for week in weeks:
        week["kcal_delta_vs_avg"] = week["totals"]["total_kcal"] - avg_week_kcal if avg_week_kcal else 0

    return {
        "weeks": weeks,
        "program_totals": program_totals,
        "program_kpis": _kpi_from_totals(program_totals),
        "average_week_kcal": avg_week_kcal,
        "filled_days_count": sum(week["filled_days_count"] for week in weeks),
        "program_meals_count": len(program_dailyplan_meals),
        "program_foods_count": len(program_foods_aggregation),
        "program_foods_aggregation": program_foods_aggregation,
        "program_foods_aggregation_table": program_foods_aggregation_table,
    }


def _format_chart_number(value, decimals=0):
    value = value or 0
    if decimals:
        return f"{value:.{decimals}f}"
    return f"{value:.0f}"


def _program_chart_axis_ticks(max_value, unit, decimals=0):
    max_value = max(float(max_value or 0), 1)
    ticks = (max_value, max_value / 2, 0)
    return [
        {"label": f"{_format_chart_number(tick, decimals)} {unit}".strip()}
        for tick in ticks
    ]


def _program_chart_bar_height(value, max_value):
    value = max(float(value or 0), 0)
    max_value = max(float(max_value or 0), 1)
    return min((value / max_value) * 100, 100)


def _program_chart_value_label(value, unit, decimals=0):
    number = _format_chart_number(value, decimals)
    return f"{number} {unit}".strip()


def _program_chart_range_label(min_value, max_value, unit, decimals=0):
    min_label = _program_chart_value_label(min_value, unit, decimals)
    max_label = _program_chart_value_label(max_value, unit, decimals)
    return f"Min: {min_label} - Max: {max_label}"


def build_program_metric_chart(
    weeks,
    current_weight=None,
    title="Variación diaria del programa",
    subtitle="Eje X agrupado por semanas, con cortes visuales entre bloques de 7 días.",
):
    """Build a tabbed, CSS-rendered chart with one bar per program day."""
    day_points = []
    day_index = 0

    for week in weeks:
        for day in week["days"]:
            day_index += 1
            snapshot = day.get("snapshot") or _empty_totals()
            total_kcal = snapshot["total_kcal"]
            protein = snapshot["protein"]
            carbs = snapshot["carbs"]
            fat = snapshot["fat"]
            ppk = (protein / current_weight) if (current_weight and protein) else 0
            alloc = snapshot.get("alloc") or {"protein": 0, "carbs": 0, "fat": 0}

            day_points.append({
                "day_index": day_index,
                "x_label": f"w{week['week_number']}",
                "week_number": week["week_number"],
                "day_number": day["day_number"],
                "day_label": day["day_label"],
                "is_week_start": day_index > 1 and day["day_number"] == 1,
                "is_empty": not day.get("program_day"),
                "dailyplan_name": day["dailyplan"].name if day.get("dailyplan") else "Sin plan diario",
                "total_kcal": total_kcal,
                "protein": protein,
                "carbs": carbs,
                "fat": fat,
                "ppk": ppk,
                "alloc_protein": alloc.get("protein", 0),
                "alloc_carbs": alloc.get("carbs", 0),
                "alloc_fat": alloc.get("fat", 0),
            })

    simple_metrics = [
        {"key": "calories", "label": "Calorías", "unit": "kcal", "field": "total_kcal", "decimals": 0},
        {"key": "protein", "label": "Proteínas", "unit": "g", "field": "protein", "decimals": 0},
        {"key": "carbs", "label": "Carbos", "unit": "g", "field": "carbs", "decimals": 0},
        {"key": "fat", "label": "Grasas", "unit": "g", "field": "fat", "decimals": 0},
        {"key": "ppk", "label": "PPK", "unit": "g/kg", "field": "ppk", "decimals": 2},
    ]

    metrics = []
    for index, spec in enumerate(simple_metrics):
        values = [point[spec["field"]] for point in day_points]
        min_value = min(values, default=0)
        max_metric_value = max(values, default=0)
        max_value = max_metric_value or 1
        bars = []
        for point in day_points:
            value = point[spec["field"]]
            value_label = _format_chart_number(value, spec["decimals"])
            bars.append({
                "x_label": point["x_label"],
                "week_number": point["week_number"],
                "day_number": point["day_number"],
                "day_label": point["day_label"],
                "is_week_start": point["is_week_start"],
                "is_empty": point["is_empty"],
                "height_percent": _program_chart_bar_height(value, max_value),
                "value_label": f"{value_label} {spec['unit']}",
                "title": f"Semana {point['week_number']} · {point['day_label']} · {point['dailyplan_name']} · {value_label} {spec['unit']}",
            })

        metrics.append({
            "key": spec["key"],
            "label": spec["label"],
            "unit": spec["unit"],
            "kind": "bar",
            "is_active": index == 0,
            "bars": bars,
            "range_label": _program_chart_range_label(
                min_value,
                max_metric_value,
                spec["unit"],
                spec["decimals"],
            ),
        })

    alloc_bars = []
    for point in day_points:
        total_alloc = point["alloc_protein"] + point["alloc_carbs"] + point["alloc_fat"]
        alloc_label = (
            f"P {_format_chart_number(point['alloc_protein'])}% · "
            f"C {_format_chart_number(point['alloc_carbs'])}% · "
            f"F {_format_chart_number(point['alloc_fat'])}%"
        )
        alloc_bars.append({
            "x_label": point["x_label"],
            "week_number": point["week_number"],
            "day_number": point["day_number"],
            "day_label": point["day_label"],
            "is_week_start": point["is_week_start"],
            "is_empty": point["is_empty"],
            "height_percent": 100 if total_alloc else 0,
            "value_label": alloc_label,
            "title": f"Semana {point['week_number']} · {point['day_label']} · {point['dailyplan_name']} · {alloc_label}",
            "segments": [
                {"key": "protein", "label": "P", "height_percent": point["alloc_protein"]},
                {"key": "carbs", "label": "C", "height_percent": point["alloc_carbs"]},
                {"key": "fat", "label": "F", "height_percent": point["alloc_fat"]},
            ],
        })

    metrics.insert(4, {
        "key": "alloc",
        "label": "Alloc",
        "unit": "%",
        "kind": "stacked",
        "is_active": False,
        "bars": alloc_bars,
        "range_label": "Min: 0% - Max: 100%",
    })

    week_numbers = [week["week_number"] for week in weeks]

    return {
        "title": title,
        "subtitle": subtitle,
        "days_count": len(day_points),
        "weeks_count": len(week_numbers),
        "week_labels": [f"w{week_number}" for week_number in week_numbers],
        "metrics": metrics,
    }


def build_program_child_card(program, user, current_weight=None):
    program_days = list(_program_days_queryset(program))
    grid_data = build_weekly_grid(program, program_days)
    current_weight = current_weight or get_current_weight(user)
    primary_week = grid_data["weeks"][0] if grid_data["weeks"] else None
    owner_label = "Tú" if program.created_by_id == user.id else str(program.created_by)

    actions = [
        _action(
            key="detail",
            label="Ver programa",
            url=reverse("program_detail", args=[program.id]),
            icon="chevron-right",
        )
    ]

    if program.created_by_id == user.id or program.is_forkable:
        actions.append(
            _action(
                key="duplicate",
                label="Duplicar",
                url=reverse("fork_program", args=[program.id]),
                method="post",
                icon="copy",
                desktop_position="menu",
                mobile_position="menu",
            )
        )

    if program.created_by_id == user.id:
        actions.append(
            _action(
                key="delete",
                label="Eliminar",
                url=reverse("program_remove", args=[program.id]),
                method="post",
                icon="trash-2",
                desktop_position="menu",
                mobile_position="menu",
            )
        )

    return {
        "child_id": program.id,
        "title": program.name,
        "icon": "calendar",
        "weeks_count": program.normalized_duration_weeks,
        "filled_days_count": grid_data["filled_days_count"],
        "duration_days": program.duration_days,
        "foods_count": grid_data["program_foods_count"],
        "primary_week": primary_week,
        "weeks": grid_data["weeks"],
        "chart": build_program_metric_chart(grid_data["weeks"], current_weight=current_weight),
        "owner": owner_label,
        "is_shared": program.created_by_id != user.id,
        "actions": actions,
    }


# ==================================================
# LIST
# ==================================================

@login_required
def program_list(request):
    list_mode = _normalize_list_mode(request.GET)

    programs = (
        Program.objects
        .filter(
            Q(created_by=request.user)
            | Q(shares__accepted_by=request.user, shares__removed=False)
        )
        .select_related("created_by", "original_author", "forked_from")
        .prefetch_related(
            "shares",
            "program_dailyplan__dailyplan__dailyplan_meals__meal__meal_food_set__food",
        )
        .distinct()
        .order_by("list_order", "-created_at", "-id")
    )

    current_weight = get_current_weight(request.user)
    child_cards = [
        build_program_child_card(program, request.user, current_weight=current_weight)
        for program in programs
    ]
    content = {
        "header": _header(_program_list_actions(list_mode)),
        "child_cards": child_cards,
        "list_mode": list_mode,
    }

    context = _vm_context(
        PROGRAM_VIEWMODE_PERSONAL_LIST,
        content=content,
    )

    return render(request, "notas/programs/list.html", context)


@login_required
@require_POST
def program_list_reorder(request):
    ordered_ids = request.POST.getlist("order[]")

    if not ordered_ids:
        return HttpResponseBadRequest("No order received.")

    programs = {
        program.id: program
        for program in Program.objects.filter(
            created_by=request.user,
            id__in=ordered_ids,
        )
    }

    for index, raw_id in enumerate(ordered_ids):
        try:
            program_id = int(raw_id)
        except (TypeError, ValueError):
            continue

        program = programs.get(program_id)
        if not program:
            continue

        if program.list_order != index:
            program.list_order = index
            program.save(update_fields=["list_order"])

    return HttpResponse(status=204)


@login_required
@require_POST
def program_list_bulk_delete(request):
    selected_ids = request.POST.getlist("selected_ids[]")

    if not selected_ids:
        messages.info(request, "No seleccionaste programas para eliminar.")
        return redirect(_safe_return_to(request, "program_list", mode="delete"))

    programs = Program.objects.filter(
        created_by=request.user,
        id__in=selected_ids,
    )

    deleted_count = 0
    for program in programs:
        delete_program(program=program)
        deleted_count += 1

    if deleted_count:
        messages.success(request, f"{deleted_count} programa(s) eliminado(s).")
    else:
        messages.info(request, "No se eliminaron programas.")

    return redirect(_safe_return_to(request, "program_list", mode="delete"))


# ==================================================
# CREATE / DETAIL / CONFIGURE
# ==================================================

@login_required
def program_create(request):
    viewmode = PROGRAM_VIEWMODE_CREATE
    content = {"header": _header([])}

    if request.method == "POST":
        name = request.POST.get("name")
        duration_weeks = request.POST.get("duration_weeks")

        try:
            result = create_weekly_program(
                user=request.user,
                name=name,
                duration_weeks=duration_weeks,
            )
        except ValueError as exc:
            if str(exc) == "program_name_required":
                messages.error(request, "El nombre es obligatorio.")
            else:
                messages.error(request, "El número de semanas debe ser 1 o superior.")
            return redirect("program_create")

        return redirect("program_detail", pk=result.program.pk)

    context = _vm_context(viewmode, content=content)
    return render(request, "notas/programs/create.html", context)


@login_required
def program_detail(request, pk):
    program = get_object_or_404(
        Program.objects.select_related("created_by", "original_author", "forked_from"),
        pk=pk,
    )

    if program.created_by_id != request.user.id and not program.shares.filter(
        accepted_by=request.user,
        removed=False,
    ).exists():
        return HttpResponseForbidden()

    program_days = list(_program_days_queryset(program))
    grid_data = build_weekly_grid(
        program,
        program_days,
        user=request.user,
        include_dailyplan_cards=True,
    )
    current_weight = get_current_weight(request.user)
    for week in grid_data["weeks"]:
        week["chart"] = build_program_metric_chart(
            [week],
            current_weight=current_weight,
            title=f"Variación diaria · Semana {week['week_number']}",
            subtitle="Detalle diario de calorías, macros, alloc y PPK de esta semana.",
        )

    dailyplans = list(_available_dailyplans(request.user))
    dailyplan_options = [_plan_snapshot(dailyplan) for dailyplan in dailyplans]

    content = {
        "header": _header(_program_detail_actions(program, request.user)),
        "program": program,
        "weeks": grid_data["weeks"],
        "program_kpis": grid_data["program_kpis"],
        "program_totals": grid_data["program_totals"],
        "program_meals_count": grid_data["program_meals_count"],
        "program_foods_count": grid_data["program_foods_count"],
        "program_foods_aggregation_table": grid_data["program_foods_aggregation_table"],
        "program_chart": build_program_metric_chart(
            grid_data["weeks"],
            current_weight=current_weight,
        ),
        "average_week_kcal": grid_data["average_week_kcal"],
        "filled_days_count": grid_data["filled_days_count"],
        "empty_days_count": max(program.duration_days - grid_data["filled_days_count"], 0),
        "available_dailyplans": dailyplan_options,
        "available_dailyplans_json": json.dumps(dailyplan_options, cls=DjangoJSONEncoder),
        "day_labels": DAY_LABELS,
    }

    context = _vm_context(
        PROGRAM_VIEWMODE_PERSONAL_DETAIL,
        content=content,
        instance=program,
    )

    return render(request, "notas/programs/detail.html", context)


@login_required
def configure_program(request, pk):
    program = get_object_or_404(
        Program.objects.prefetch_related("program_dailyplan"),
        pk=pk,
        created_by=request.user,
    )

    caps = get_capabilities(request.user)

    if request.method == "POST":
        is_public = bool(request.POST.get("is_public"))
        is_forkable = bool(request.POST.get("is_forkable"))
        is_copiable = bool(request.POST.get("is_copiable"))
        duration_weeks = request.POST.get("duration_weeks")

        if is_public and not caps.can_publish():
            messages.error(request, "No puedes publicar este programa.")
            return redirect("configure_program", pk=pk)

        if is_copiable and not caps.can_copy():
            messages.error(request, "Tu plan no permite copias.")
            return redirect("configure_program", pk=pk)

        try:
            duration_weeks = int(duration_weeks)
        except (TypeError, ValueError):
            messages.error(request, "La duración debe ser un número de semanas válido.")
            return redirect("configure_program", pk=pk)

        if duration_weeks < 1:
            messages.error(request, "La duración debe ser de al menos 1 semana.")
            return redirect("configure_program", pk=pk)

        max_filled_week = (
            program.program_dailyplan.order_by("-week_number").values_list("week_number", flat=True).first()
            or 1
        )
        if duration_weeks < max_filled_week:
            messages.error(request, "No puedes reducir la duración por debajo de la última semana con planes asignados.")
            return redirect("configure_program", pk=pk)

        program.is_public = is_public
        program.is_forkable = is_forkable
        program.is_copiable = is_copiable
        program.duration_weeks = duration_weeks

        if program.is_draft and program.program_dailyplan.exists():
            program.is_draft = False

        program.save(
            update_fields=[
                "is_public",
                "is_forkable",
                "is_copiable",
                "is_draft",
                "duration_weeks",
            ]
        )
        messages.success(request, "Programa guardado.")
        return redirect("program_detail", pk=pk)

    content = {
        "header": _header([
            _action(
                key="back_detail",
                label="Volver",
                url=reverse("program_detail", args=[program.id]),
                icon="chevron-left",
                order=10,
                is_back=True,
            )
        ]),
        "program": program,
        "caps": caps,
    }
    context = _vm_context(
        PROGRAM_VIEWMODE_CONFIGURE,
        content=content,
        instance=program,
    )
    return render(request, "notas/programs/configure.html", context)


# ==================================================
# SLOT ACTIONS
# ==================================================

@login_required
@require_POST
def add_dailyplan_to_program(request, pk):
    program = get_object_or_404(Program, pk=pk, created_by=request.user)

    dailyplan_id = request.POST.get("dailyplan_id")
    week_number = request.POST.get("week_number")
    day_number = request.POST.get("day_number")

    source_dailyplan = get_object_or_404(
        _available_dailyplans(request.user),
        pk=dailyplan_id,
    )

    try:
        assign_dailyplan_to_program_slot(
            program=program,
            source_dailyplan=source_dailyplan,
            user=request.user,
            week_number=week_number,
            day_number=day_number,
        )
    except ValueError:
        messages.error(request, "La semana o el día seleccionado no es válido.")
        return redirect("program_detail", pk=program.pk)

    messages.success(request, "Plan diario asignado al programa.")
    return redirect(f"{reverse('program_detail', args=[program.pk])}#week-{week_number}")


@login_required
@require_POST
def remove_dailyplan_from_program(request, pk, program_day_id):
    program_day = get_object_or_404(
        ProgramDay.objects.select_related("program", "dailyplan"),
        pk=program_day_id,
        program_id=pk,
        program__created_by=request.user,
    )
    week_number = program_day.week_number
    program = program_day.program

    remove_program_day(program_day=program_day)
    messages.success(request, "Día removido del programa.")
    return redirect(f"{reverse('program_detail', args=[program.pk])}#week-{week_number}")


# ==================================================
# COPY / SHARE / DELETE
# ==================================================

@login_required
@require_POST
def fork_program(request, program_id):
    original = get_object_or_404(
        Program.objects.prefetch_related("program_dailyplan__dailyplan"),
        id=program_id,
    )

    if original.created_by_id != request.user.id and not original.is_forkable:
        return HttpResponseForbidden()

    forked = fork_program_command(original, request.user)
    messages.success(request, "Programa duplicado.")
    return redirect("program_detail", pk=forked.id)


@login_required
@require_POST
def copy_program(request, pk):
    program = get_object_or_404(
        Program.objects.prefetch_related("program_dailyplan__dailyplan"),
        pk=pk,
    )

    if program.created_by_id != request.user.id and not program.is_copiable:
        return HttpResponseForbidden()

    copied = copy_program_command(program, request.user)
    messages.success(request, "Programa copiado.")
    return redirect("program_detail", pk=copied.pk)


@login_required
@require_POST
def program_remove(request, pk):
    program = get_object_or_404(Program, pk=pk, created_by=request.user)
    delete_program(program=program)
    messages.success(request, "Programa eliminado.")
    return redirect(_safe_return_to(request, "program_list"))


@login_required
def program_share(request, pk):
    program = get_object_or_404(Program, pk=pk, created_by=request.user)
    form = ProgramShareForm(request.POST or None, initial={"subject": program.name})

    if request.method == "POST" and form.is_valid():
        email = form.cleaned_data["recipient_email"]
        share_subject = form.cleaned_data.get("subject", program.name)
        message = form.cleaned_data.get("message", "")

        result = create_program_share(
            sender=request.user,
            recipient_email=email,
            program=program,
            subject=share_subject,
            message=message,
        )

        email_sent = False
        try:
            email_sent = bool(send_mail(
                subject=share_subject,
                message=message or f"Te compartieron el programa semanal {program.name} en My Scoope.",
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[email],
                fail_silently=False,
            ))
        except Exception:
            email_sent = False

        if result.share.accepted_by_id:
            messages.success(request, "Compartiste este programa. Ya está disponible para el usuario asociado a ese correo.")
        elif email_sent:
            messages.success(request, "Compartiste este programa y se envió el correo de invitación.")
        else:
            messages.warning(request, "Se creó la invitación, pero no se pudo enviar el correo.")

        return redirect("program_detail", pk=program.pk)

    if request.method == "POST":
        messages.error(request, "No se pudo compartir. Revisa el correo ingresado.")

    content = {
        "header": _header([
            _action(
                key="back_detail",
                label="Volver",
                url=reverse("program_detail", args=[program.id]),
                icon="chevron-left",
                order=10,
                is_back=True,
            )
        ]),
        "program": program,
        "form": form,
    }

    context = _vm_context(PROGRAM_VIEWMODE_SHARE, content=content, instance=program)
    return render(request, "notas/programs/share.html", context)
