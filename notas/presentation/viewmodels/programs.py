from __future__ import annotations

import json

from django.core.serializers.json import DjangoJSONEncoder
from django.urls import reverse

from notas.application.services.cache.program_summary import (
    DAY_LABELS,
    build_dailyplan_snapshot,
    get_program_summary,
)
from notas.application.services.nutrition.food_aggregation import build_dailyplan_foods_aggregation
from notas.application.services.nutrition.weight import get_current_weight
from notas.domain.models import DailyPlan, Program
from notas.presentation.composition.viewmodel.components.builder_menu import build_dailyplan_menu
from notas.presentation.composition.viewmodel.components.builder_table_items import (
    build_dailyplan_food_aggregation_table_item,
    build_dailyplanmeal_table_item,
)
from notas.presentation.navigation.program_context import append_query

FULL_DAY_LABELS = {
    1: "Lunes",
    2: "Martes",
    3: "Miércoles",
    4: "Jueves",
    5: "Viernes",
    6: "Sábado",
    7: "Domingo",
}


def _action(
    *,
    key,
    label,
    url="",
    method="get",
    icon="chevron-right",
    order=90,
    desktop_position="inline",
    mobile_position="inline",
    is_back=False,
    disabled=False,
    extra_class="",
    attrs=None,
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
        "attrs": attrs or {},
    }


def _safe_percentage(part, total):
    if not total or total <= 0:
        return 0.0
    return part / total * 100


def available_dailyplans(user):
    return (
        DailyPlan.objects
        .filter(created_by=user, is_draft=False)
        .exclude(source=DailyPlan.SOURCE_PROGRAM)
        .prefetch_related("dailyplan_meals__meal__meal_food_set__food")
        .order_by("list_order", "-created_at", "-id")
        .distinct()
    )


def minimal_program_list_item(program):
    return {
        "child_id": program.id,
        "title": program.name,
    }


def _format_chart_number(value, decimals=0):
    value = value or 0
    if decimals:
        return f"{value:.{decimals}f}"
    return f"{value:.0f}"


def _program_chart_bar_height(value, max_value):
    value = max(float(value or 0), 0)
    max_value = max(float(max_value or 0), 1)
    return min((value / max_value) * 100, 100)


def _program_chart_value_label(value, unit="", decimals=0):
    number = _format_chart_number(value, decimals)
    return f"{number} {unit}".strip()


def _program_chart_range_label(min_value, max_value, unit, decimals=0):
    display_unit = "cal" if unit == "kcal" else unit
    min_label = _program_chart_value_label(min_value, "", decimals)
    max_label = _program_chart_value_label(max_value, display_unit, decimals)
    return f"{min_label} - {max_label}"


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


def _chart_day_value(point, field):
    if field == "total_kcal":
        return point.get("total_kcal", 0)
    if field == "protein":
        return point.get("protein", 0)
    if field == "carbs":
        return point.get("carbs", 0)
    if field == "fat":
        return point.get("fat", 0)
    if field == "ppk":
        return point.get("ppk", 0)
    return 0


def _chart_metric_range(values, unit, decimals=0):
    if not values:
        return _program_chart_range_label(0, 0, unit, decimals)
    return _program_chart_range_label(min(values), max(values), unit, decimals)


def _chart_bar_payload(point, *, value=None, decimals=0, unit="", title_value=None, segments=None, stack_total=None):
    raw_value = float(value or 0)
    visible_label = _format_chart_number(raw_value, decimals)
    title_value = title_value if title_value is not None else f"{visible_label} {unit}".strip()
    payload = {
        "weekNumber": point["week_number"],
        "dayNumber": point["day_number"],
        "dayLabel": point["day_label"],
        "xLabel": point["x_label"],
        "mobileLabel": point.get("mobile_label") or point["day_label"][:1],
        "isWeekStart": point["is_week_start"],
        "isEmpty": point["is_empty"],
        "dailyplanName": point["dailyplan_name"],
        "value": raw_value,
        "valueLabel": visible_label,
        "unit": unit,
        "titleValue": title_value,
        "title": f"Semana {point['week_number']} · {point['day_label']} · {point['dailyplan_name']} · {title_value}".strip(),
    }
    if segments is not None:
        payload["segments"] = segments
        payload["stackTotal"] = float(stack_total if stack_total is not None else raw_value)
    return payload


def build_program_metric_chart(
    weeks,
    current_weight=None,
    title="Variación diaria del programa",
    subtitle="Eje X agrupado por semanas, con cortes visuales entre bloques de 7 días.",
    axis_mode="weeks",
):
    """Build a normalized JSON contract for the custom Program chart component.

    The template only mounts the component. The JS renderer owns tabs, bars,
    stacked segments, labels and responsive axis behavior. Keeping this contract
    stable lets program/week charts share one engine without adding a charting
    dependency.
    """
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
            dailyplan = day.get("dailyplan") or {}
            day_label = FULL_DAY_LABELS.get(day["day_number"], day.get("day_label") or "")

            day_points.append({
                "day_index": day_index,
                "x_label": f"w{week['week_number']}",
                "week_number": week["week_number"],
                "day_number": day["day_number"],
                "day_label": day_label,
                "mobile_label": (day.get("day_label") or day_label or "")[:1],
                "is_week_start": day_index > 1 and day["day_number"] == 1,
                "is_empty": not day.get("program_day"),
                "dailyplan_name": dailyplan.get("name") or "Sin plan diario",
                "total_kcal": total_kcal,
                "protein": protein,
                "carbs": carbs,
                "fat": fat,
                "ppk": ppk,
                "kcal_protein": snapshot.get("kcal_protein", 0),
                "kcal_carbs": snapshot.get("kcal_carbs", 0),
                "kcal_fat": snapshot.get("kcal_fat", 0),
                "alloc_protein": alloc.get("protein", 0),
                "alloc_carbs": alloc.get("carbs", 0),
                "alloc_fat": alloc.get("fat", 0),
            })

    simple_specs = [
        {"key": "calories", "label": "Calorías", "unit": "kcal", "field": "total_kcal", "decimals": 0},
        {"key": "ppk", "label": "PPK", "unit": "g/kg", "field": "ppk", "decimals": 2},
        {"key": "protein", "label": "Proteínas", "unit": "g", "field": "protein", "decimals": 0},
        {"key": "carbs", "label": "Carbos", "unit": "g", "field": "carbs", "decimals": 0},
        {"key": "fat", "label": "Grasas", "unit": "g", "field": "fat", "decimals": 0},
    ]

    metrics = []
    for index, spec in enumerate(simple_specs):
        values = [_chart_day_value(point, spec["field"]) for point in day_points]
        metrics.append({
            "key": spec["key"],
            "label": spec["label"],
            "unit": spec["unit"],
            "kind": "bar",
            "decimals": spec["decimals"],
            "isActive": index == 0,
            "rangeLabel": _chart_metric_range(values, spec["unit"], spec["decimals"]),
            "bars": [
                _chart_bar_payload(
                    point,
                    value=_chart_day_value(point, spec["field"]),
                    decimals=spec["decimals"],
                    unit=spec["unit"],
                )
                for point in day_points
            ],
        })

    alloc_bars = []
    for point in day_points:
        alloc_segments = [
            {"key": "protein", "label": "P%", "value": float(point["alloc_protein"] or 0), "valueLabel": _format_chart_number(point["alloc_protein"])},
            {"key": "carbs", "label": "C%", "value": float(point["alloc_carbs"] or 0), "valueLabel": _format_chart_number(point["alloc_carbs"])},
            {"key": "fat", "label": "F%", "value": float(point["alloc_fat"] or 0), "valueLabel": _format_chart_number(point["alloc_fat"])},
        ]
        alloc_label = " · ".join(f"{segment['label']} {segment['valueLabel']}" for segment in alloc_segments)
        alloc_bars.append(_chart_bar_payload(
            point,
            value=100 if any(segment["value"] for segment in alloc_segments) else 0,
            unit="%",
            title_value=alloc_label,
            segments=alloc_segments,
            stack_total=100,
        ))

    metrics.append({
        "key": "alloc",
        "label": "Alloc",
        "unit": "%",
        "kind": "stacked",
        "decimals": 0,
        "isActive": False,
        "rangeLabel": "",
        "rangeLabels": [
            {"key": "protein", "label": "P", "value": _chart_metric_range([point["alloc_protein"] for point in day_points], "%", 0)},
            {"key": "carbs", "label": "C", "value": _chart_metric_range([point["alloc_carbs"] for point in day_points], "%", 0)},
            {"key": "fat", "label": "G", "value": _chart_metric_range([point["alloc_fat"] for point in day_points], "%", 0)},
        ],
        "legendLabel": "Leyenda de alloc",
        "legendItems": [
            {"key": "protein", "label": "P%"},
            {"key": "carbs", "label": "C%"},
            {"key": "fat", "label": "F%"},
        ],
        "bars": alloc_bars,
    })


    week_numbers = [week["week_number"] for week in weeks]
    if axis_mode == "days":
        axis_labels = [
            {
                "label": FULL_DAY_LABELS.get(point["day_number"], point["day_label"]),
                "mobileLabel": point.get("mobile_label") or point["day_label"][:1],
            }
            for point in day_points
        ]
        axis_count = len(axis_labels)
    else:
        axis_labels = [
            {"label": f"Semana {week_number}", "mobileLabel": f"S{week_number}"}
            for week_number in week_numbers
        ]
        axis_count = len(axis_labels)

    scope = "week" if axis_mode == "days" else "program"
    payload = {
        "scope": scope,
        "title": title,
        "subtitle": subtitle,
        "daysCount": len(day_points),
        "weeksCount": len(week_numbers),
        "axisCount": axis_count,
        "axisLabels": axis_labels,
        "metrics": metrics,
    }

    return {
        "scope": scope,
        "title": title,
        "subtitle": subtitle,
        "days_count": len(day_points),
        "weeks_count": len(week_numbers),
        "axis_count": axis_count,
        "axis_labels": axis_labels,
        "metrics": metrics,
        "data_json": json.dumps(payload, cls=DjangoJSONEncoder),
    }


def _range_values(values):
    values = [float(value or 0) for value in values if value is not None]
    if not values:
        return 0, 0
    return min(values), max(values)


def _format_range_value(value, decimals=0):
    value = float(value or 0)
    if decimals:
        return f"{value:.{decimals}f}"
    return f"{value:.0f}"


def _format_range_label(min_value, max_value, *, unit="", decimals=0, suffix=""):
    min_label = _format_range_value(min_value, decimals)
    max_label = _format_range_value(max_value, decimals)
    return f"{min_label}/{max_label}{unit}{suffix}"


def build_program_kpi_ranges(weeks, current_weight=None):
    snapshots = [
        day["snapshot"]
        for week in weeks
        for day in week["days"]
        if day.get("snapshot")
    ]
    kcal_min, kcal_max = _range_values(snapshot["total_kcal"] for snapshot in snapshots)
    protein_min, protein_max = _range_values(snapshot["protein"] for snapshot in snapshots)
    carbs_min, carbs_max = _range_values(snapshot["carbs"] for snapshot in snapshots)
    fat_min, fat_max = _range_values(snapshot["fat"] for snapshot in snapshots)
    ppk_values = [snapshot["protein"] / current_weight for snapshot in snapshots] if current_weight else []
    ppk_min, ppk_max = _range_values(ppk_values)
    alloc_protein_min, alloc_protein_max = _range_values(snapshot["alloc"].get("protein", 0) for snapshot in snapshots)
    alloc_carbs_min, alloc_carbs_max = _range_values(snapshot["alloc"].get("carbs", 0) for snapshot in snapshots)
    alloc_fat_min, alloc_fat_max = _range_values(snapshot["alloc"].get("fat", 0) for snapshot in snapshots)

    return {
        "tot_kcal": {"min": _format_range_value(kcal_min), "max": _format_range_value(kcal_max)},
        "ppk": {"label": _format_range_label(ppk_min, ppk_max, unit="g/kg", decimals=1)},
        "protein": {"label": _format_range_label(protein_min, protein_max, unit="g")},
        "carbs": {"label": _format_range_label(carbs_min, carbs_max, unit="g")},
        "fat": {"label": _format_range_label(fat_min, fat_max, unit="g")},
        "alloc_protein": {"label": _format_range_label(alloc_protein_min, alloc_protein_max, unit="%"), "bar_value": alloc_protein_max},
        "alloc_carbs": {"label": _format_range_label(alloc_carbs_min, alloc_carbs_max, unit="%"), "bar_value": alloc_carbs_max},
        "alloc_fat": {"label": _format_range_label(alloc_fat_min, alloc_fat_max, unit="%"), "bar_value": alloc_fat_max},
    }




def build_week_kpi_ranges(week, current_weight=None):
    snapshots = [day["snapshot"] for day in week.get("days", []) if day.get("snapshot")]
    kcal_min, kcal_max = _range_values(snapshot["total_kcal"] for snapshot in snapshots)
    protein_min, protein_max = _range_values(snapshot["protein"] for snapshot in snapshots)
    carbs_min, carbs_max = _range_values(snapshot["carbs"] for snapshot in snapshots)
    fat_min, fat_max = _range_values(snapshot["fat"] for snapshot in snapshots)
    ppk_values = [snapshot["protein"] / current_weight for snapshot in snapshots] if current_weight else []
    ppk_min, ppk_max = _range_values(ppk_values)
    alloc_protein_min, alloc_protein_max = _range_values(snapshot["alloc"].get("protein", 0) for snapshot in snapshots)
    alloc_carbs_min, alloc_carbs_max = _range_values(snapshot["alloc"].get("carbs", 0) for snapshot in snapshots)
    alloc_fat_min, alloc_fat_max = _range_values(snapshot["alloc"].get("fat", 0) for snapshot in snapshots)

    return {
        "tot_kcal": {"min": _format_range_value(kcal_min), "max": _format_range_value(kcal_max)},
        "ppk": {"label": _format_range_label(ppk_min, ppk_max, unit="g/kg", decimals=1)},
        "protein": {"label": _format_range_label(protein_min, protein_max, unit="g")},
        "carbs": {"label": _format_range_label(carbs_min, carbs_max, unit="g")},
        "fat": {"label": _format_range_label(fat_min, fat_max, unit="g")},
        "alloc_protein": {"label": _format_range_label(alloc_protein_min, alloc_protein_max, unit="%"), "bar_value": alloc_protein_max},
        "alloc_carbs": {"label": _format_range_label(alloc_carbs_min, alloc_carbs_max, unit="%"), "bar_value": alloc_carbs_max},
        "alloc_fat": {"label": _format_range_label(alloc_fat_min, alloc_fat_max, unit="%"), "bar_value": alloc_fat_max},
    }


def build_week_day_nutrition_rows(week, current_weight=None, program=None):
    rows = []
    week_totals = week.get("totals") or _empty_totals()
    for day in week.get("days", []):
        snapshot = day.get("snapshot") or _empty_totals()
        protein = float(snapshot.get("protein") or 0)
        macro_distribution = snapshot.get("alloc") or {"protein": 0, "carbs": 0, "fat": 0}
        dailyplan = day.get("dailyplan") or {}
        program_day = day.get("program_day") or {}
        day_name = FULL_DAY_LABELS.get(day["day_number"], day.get("day_label") or "")
        has_plan = bool(program_day)
        remove_url = ""
        if has_plan and program is not None:
            remove_url = reverse("remove_dailyplan_from_program", args=[program.id, program_day["id"]])
        rows.append({
            "day_number": day["day_number"],
            "day_name": day_name,
            "dailyplan_id": dailyplan.get("id"),
            "dailyplan_name": dailyplan.get("name") or "Sin plan asignado",
            "program_day_id": program_day.get("id"),
            "has_plan": has_plan,
            "remove_url": remove_url,
            "is_empty": not has_plan,
            "total_kcal": snapshot.get("total_kcal", 0),
            "kcal_share": _safe_percentage(snapshot.get("total_kcal", 0), week_totals.get("total_kcal", 0)),
            "kcal_distribution": {
                "protein": macro_distribution.get("protein", 0),
                "carbs": macro_distribution.get("carbs", 0),
                "fat": macro_distribution.get("fat", 0),
            },
            "ppk": (protein / current_weight) if (current_weight and protein) else 0,
            "protein": protein,
            "carbs": snapshot.get("carbs", 0),
            "fat": snapshot.get("fat", 0),
            "alloc": {
                "protein": _safe_percentage(snapshot.get("kcal_protein", 0), week_totals.get("kcal_protein", 0)),
                "carbs": _safe_percentage(snapshot.get("kcal_carbs", 0), week_totals.get("kcal_carbs", 0)),
                "fat": _safe_percentage(snapshot.get("kcal_fat", 0), week_totals.get("kcal_fat", 0)),
            },
        })
    return rows


def build_program_child_card(program: Program, user, current_weight=None):
    summary = get_program_summary(program)
    weeks = summary["weeks"]
    current_weight = current_weight or get_current_weight(user)
    primary_week = weeks[0] if weeks else None
    owner_label = "Tú" if program.created_by_id == user.id else str(program.created_by)

    actions = [_action(key="detail", label="Ver programa", url=reverse("program_detail", args=[program.id]), icon="chevron-right")]
    if program.created_by_id == user.id or program.is_forkable:
        actions.append(_action(key="duplicate", label="Duplicar", url=reverse("fork_program", args=[program.id]), method="post", icon="copy", desktop_position="menu", mobile_position="menu"))
    if program.created_by_id == user.id:
        actions.append(_action(key="delete", label="Eliminar", url=reverse("program_remove", args=[program.id]), method="post", icon="trash-2", desktop_position="menu", mobile_position="menu"))

    return {
        "child_id": program.id,
        "title": program.name,
        "icon": "calendar",
        "weeks_count": program.normalized_duration_weeks,
        "filled_days_count": summary["filled_days_count"],
        "duration_days": program.duration_days,
        "foods_count": summary["program_foods_count"],
        "primary_week": primary_week,
        "weeks": weeks,
        "chart": build_program_metric_chart(weeks, current_weight=current_weight),
        "kpi_ranges": build_program_kpi_ranges(weeks, current_weight=current_weight),
        "owner": owner_label,
        "metadata": {
            "owner": owner_label,
            "author": str(program.original_author),
            "fork_from": str(program.forked_from) if program.forked_from else None,
        },
        "is_shared": program.created_by_id != user.id,
        "actions": actions,
    }


def build_program_list_cards(programs, user, list_mode="list", current_weight=None):
    if list_mode in {"reorder", "delete"}:
        return [minimal_program_list_item(program) for program in programs]
    current_weight = current_weight or get_current_weight(user)
    return [build_program_child_card(program, user, current_weight=current_weight) for program in programs]


def _dailyplan_options(user):
    return [build_dailyplan_snapshot(dailyplan) for dailyplan in list(available_dailyplans(user))]


def build_program_week_summary_metrics(weeks):
    previous_average_kcal = None
    for week in weeks:
        assigned_dailyplans_count = int(week.get("filled_days_count") or 0)
        total_kcal = float((week.get("totals") or {}).get("total_kcal") or 0)
        average_kcal = total_kcal / assigned_dailyplans_count if assigned_dailyplans_count else 0.0
        previous_ratio = (
            (average_kcal - previous_average_kcal) / previous_average_kcal * 100
            if previous_average_kcal is not None and previous_average_kcal > 0
            else None
        )
        week["assigned_dailyplans_count"] = assigned_dailyplans_count
        week["average_kcal_per_assigned_day"] = average_kcal
        week["previous_week_average_ratio"] = previous_ratio
        previous_average_kcal = average_kcal
    return weeks


def build_program_detail_content(*, program: Program, user, header):
    summary = get_program_summary(program)
    weeks = build_program_week_summary_metrics(summary["weeks"])
    current_weight = get_current_weight(user)
    for week in weeks:
        week["chart"] = build_program_metric_chart(
            [week],
            current_weight=current_weight,
            title=f"Variación diaria · Semana {week['week_number']}",
            subtitle="Detalle diario de calorías, macros, alloc y PPK de esta semana.",
            axis_mode="days",
        )
        week["kpi_ranges"] = build_week_kpi_ranges(week, current_weight=current_weight)
        week["day_nutrition_rows"] = build_week_day_nutrition_rows(
            week,
            current_weight=current_weight,
            program=program,
        )
    dailyplan_options = _dailyplan_options(user)
    return {
        "header": header,
        "program": program,
        "weeks": weeks,
        "program_kpis": summary["program_kpis"],
        "program_totals": summary["program_totals"],
        "program_meals_count": summary["program_meals_count"],
        "program_foods_count": summary["program_foods_count"],
        "program_foods_aggregation_table": summary["program_foods_aggregation_table"],
        "program_chart": build_program_metric_chart(weeks, current_weight=current_weight),
        "program_kpi_ranges": build_program_kpi_ranges(weeks, current_weight=current_weight),
        "average_week_kcal": summary["average_week_kcal"],
        "filled_days_count": summary["filled_days_count"],
        "empty_days_count": max(program.duration_days - summary["filled_days_count"], 0),
        "available_dailyplans": dailyplan_options,
        "available_dailyplans_json": json.dumps(dailyplan_options, cls=DjangoJSONEncoder),
        "day_labels": DAY_LABELS,
        "can_edit": program.created_by_id == user.id,
    }


def _dailyplan_meals_for_card(dailyplan):
    prefetched = getattr(dailyplan, "_prefetched_objects_cache", {}).get("dailyplan_meals")
    if prefetched is not None:
        return sorted(prefetched, key=lambda dpm: (dpm.order, dpm.id))
    return list(dailyplan.dailyplan_meals.all().order_by("order", "id"))


def build_program_day_child_card(dailyplan, user, program_day=None):
    snapshot = build_dailyplan_snapshot(dailyplan)
    dailyplan_meals = _dailyplan_meals_for_card(dailyplan)
    foods_aggregation = build_dailyplan_foods_aggregation(dailyplan_meals)
    foods_aggregation_table = [
        build_dailyplan_food_aggregation_table_item(food_aggregation, dailyplan_snapshot=snapshot)
        for food_aggregation in foods_aggregation
    ]
    owner_label = "Tú" if dailyplan.created_by_id == user.id else str(dailyplan.created_by)
    current_weight = get_current_weight(user)
    ppk = (snapshot["protein"] / current_weight) if (current_weight and snapshot["protein"]) else None
    return {
        "id": dailyplan.id,
        "child_id": dailyplan.id,
        "titulo": {
            "name": dailyplan.name,
            "label": "DailyPlan",
            "icon": "clipboard-list",
            "category": dailyplan.category,
            "category_badge": None,
            "structural_indicators": {
                "meals_count": len(dailyplan_meals),
                "foods_count": len(foods_aggregation),
            },
            "classes": [],
            "badges": [],
        },
        "kpis": {
            "ppk": ppk,
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
                build_dailyplanmeal_table_item(dailyplan_meal, dailyplan_snapshot=snapshot)
                for dailyplan_meal in dailyplan_meals
            ]
        },
        "menu": build_dailyplan_menu(dailyplan_meals),
        "foods_aggregation": foods_aggregation,
        "foods_aggregation_table": foods_aggregation_table,
        "metadata": {
            "owner": owner_label,
            "author": str(dailyplan.original_author),
            "fork_from": str(dailyplan.forked_from) if dailyplan.forked_from else None,
        },
        "actions": build_program_day_card_actions(
            dailyplan,
            program_day,
        ),
    }


def build_program_day_card_actions(dailyplan, program_day=None):
    if program_day is None:
        return []

    actions = [
        _action(
            key="replace",
            label="Reemplazar",
            method="button",
            icon="refresh-cw",
            extra_class="program-day-selected-card__replace js-program-slot-open-from-card",
            attrs={
                "data-week-number": program_day.week_number,
                "data-day-number": program_day.day_number,
            },
        ),
        _action(
            key="remove",
            label="Quitar",
            url=reverse("remove_dailyplan_from_program", args=[program_day.program_id, program_day.id]),
            method="post",
            icon="trash-2",
            extra_class="program-day-selected-card__remove action-icon-btn--danger",
        ),
    ]

    actions.append(
        _action(
            key="detail",
            label="Ir a detalle",
            url=append_query(
                reverse("dailyplan_detail", args=[dailyplan.id]),
                program_day=program_day.id,
            ),
            icon="chevron-right",
            extra_class="program-day-selected-card__detail",
        )
    )

    return actions
