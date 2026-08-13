from __future__ import annotations

from types import SimpleNamespace

from django.db.models import Q

from notas.application.services.commands.saved_comparison_commands import (
    create_saved_comparison,
    update_saved_comparison,
)
from notas.application.services.comparisons.nutrition import comparable_rows, entity_values, food_values
from notas.application.services.comparisons.payloads import parse_quantity
from notas.application.services.comparisons.snapshots import comparable_rows_from_snapshot
from notas.application.services.nutrition.weight import get_current_weight
from notas.domain.models import DailyPlan, Food, Meal, SavedComparison
from notas.presentation.viewmodels.comparators import build_metrics

COMPARISON_KINDS = {
    SavedComparison.KIND_FOODS: {
        "label": "Alimentos",
        "entity_label": "Alimento",
        "include_quantities": True,
        "include_ppk": False,
    },
    SavedComparison.KIND_MEALS: {
        "label": "Comidas",
        "entity_label": "Comida",
        "include_quantities": False,
        "include_ppk": True,
    },
    SavedComparison.KIND_DAILYPLANS: {
        "label": "Planes diarios",
        "entity_label": "Plan diario",
        "include_quantities": False,
        "include_ppk": True,
    },
}


def comparison_metadata_payload() -> dict:
    return {
        "kinds": [
            {
                "key": key,
                "label": config["label"],
                "entity_label": config["entity_label"],
                "uses_quantity": config["include_quantities"],
                "quantity_unit": "g" if config["include_quantities"] else None,
                "includes_ppk": config["include_ppk"],
            }
            for key, config in COMPARISON_KINDS.items()
        ]
    }


def _queryset_for_kind(kind: str, user):
    if kind == SavedComparison.KIND_FOODS:
        return Food.objects.filter(created_by=user, is_active=True).order_by("list_order", "name", "id")
    if kind == SavedComparison.KIND_MEALS:
        return (
            Meal.objects.filter(created_by=user, is_draft=False, dailyplanmeal__isnull=True)
            .order_by("list_order", "name", "id")
            .distinct()
        )
    if kind == SavedComparison.KIND_DAILYPLANS:
        return (
            DailyPlan.objects.filter(created_by=user, is_draft=False)
            .exclude(source=DailyPlan.SOURCE_PROGRAM)
            .order_by("list_order", "name", "id")
        )
    raise ValueError("comparison_kind_not_supported")


def comparison_options_payload(user, *, kind: str, search=None, offset=0, limit=30) -> dict:
    queryset = _queryset_for_kind(kind, user)
    normalized_search = (search or "").strip()[:100]
    if normalized_search:
        queryset = queryset.filter(Q(name__icontains=normalized_search))
    safe_offset = max(int(offset or 0), 0)
    safe_limit = min(max(int(limit or 30), 1), 100)
    total = queryset.count()
    return {
        "items": [{"id": item.id, "name": item.name} for item in queryset[safe_offset:safe_offset + safe_limit]],
        "total": total,
        "offset": safe_offset,
        "limit": safe_limit,
        "search": normalized_search or None,
    }


def build_comparison(user, *, kind: str, raw_selections: list[dict]):
    config = COMPARISON_KINDS.get(kind)
    if config is None:
        raise ValueError("comparison_kind_not_supported")
    if not isinstance(raw_selections, list) or len(raw_selections) < 2:
        raise ValueError("comparison_requires_two_items")
    normalized = []
    seen = set()
    for position, row in enumerate(raw_selections, start=1):
        try:
            item_id = int(row.get("id"))
        except (AttributeError, TypeError, ValueError) as exc:
            raise ValueError("comparison_selection_invalid") from exc
        if item_id <= 0:
            raise ValueError("comparison_selection_invalid")
        seen.add(item_id)
        quantity = row.get("quantity")
        if config["include_quantities"]:
            quantity = parse_quantity(quantity, fallback=100.0)
        elif quantity is not None:
            raise ValueError("comparison_quantity_not_allowed")
        normalized.append(
            SimpleNamespace(
                id=item_id,
                name="",
                quantity=quantity if config["include_quantities"] else None,
                position=position,
            )
        )

    entities = list(_queryset_for_kind(kind, user).filter(id__in=seen))
    items_by_id = {item.id: item for item in entities}
    if len(items_by_id) != len(seen):
        raise ValueError("comparison_item_not_available")
    for selection in normalized:
        selection.name = items_by_id[selection.id].name

    if config["include_quantities"]:
        rows = comparable_rows(
            normalized,
            items_by_id,
            lambda food, selection: food_values(food, selection.quantity),
        )
    else:
        current_weight = get_current_weight(user)
        rows = comparable_rows(
            normalized,
            items_by_id,
            lambda entity, selection: entity_values(entity, current_weight=current_weight),
        )
    return config, normalized, rows


def _metrics_payload(rows, *, include_ppk: bool) -> list[dict]:
    metrics = build_metrics(rows, include_ppk=include_ppk)
    return [
        {
            "key": metric.key,
            "label": metric.label,
            "unit": metric.unit,
            "bars": [
                {
                    "position": selection.position,
                    "id": selection.id,
                    "label": bar.label,
                    "quantity": selection.quantity,
                    "value": round(float(bar.value), 2),
                    "formatted_value": bar.formatted_value,
                    "relative_percentage": bar.width,
                }
                for (selection, _values), bar in zip(rows, metric.bars, strict=True)
            ],
        }
        for metric in metrics
    ]


def comparison_result_payload(*, kind: str, rows, historical=False, saved_comparison=None) -> dict:
    config = COMPARISON_KINDS[kind]
    return {
        "kind": kind,
        "kind_label": config["label"],
        "historical_snapshot": bool(historical),
        "saved_comparison_id": saved_comparison.id if saved_comparison else None,
        "saved_comparison_name": saved_comparison.name if saved_comparison else "",
        "metrics": _metrics_payload(rows, include_ppk=config["include_ppk"]),
        "items": [
            {
                "position": selection.position,
                "id": selection.id,
                "name": selection.name,
                "quantity": selection.quantity if config["include_quantities"] else None,
                "values": {
                    "calories": round(float(values.get("total_kcal", 0) or 0), 1),
                    "protein_g": round(float(values.get("protein", 0) or 0), 1),
                    "carbs_g": round(float(values.get("carbs", 0) or 0), 1),
                    "fat_g": round(float(values.get("fat", 0) or 0), 1),
                    "protein_per_kilogram": (
                        round(float(values.get("ppk", 0) or 0), 2)
                        if config["include_ppk"]
                        else None
                    ),
                },
            }
            for selection, values in rows
        ],
    }


def dynamic_comparison_payload(user, *, kind: str, selections: list[dict]) -> dict:
    _config, _normalized, rows = build_comparison(user, kind=kind, raw_selections=selections)
    return comparison_result_payload(kind=kind, rows=rows)


def save_comparison(user, *, kind: str, selections: list[dict]):
    config, normalized, rows = build_comparison(user, kind=kind, raw_selections=selections)
    result = create_saved_comparison(
        owner=user,
        kind=kind,
        entity_plural_label=config["label"],
        selections=normalized,
        comparable_rows=rows,
        include_quantities=config["include_quantities"],
    )
    return result.comparison


def update_comparison(user, *, comparison_id: int, kind: str, selections: list[dict]):
    comparison = SavedComparison.objects.filter(pk=comparison_id, owner=user).first()
    if comparison is None:
        raise ValueError("saved_comparison_not_found")
    if comparison.kind != kind:
        raise ValueError("saved_comparison_kind_mismatch")
    config, normalized, rows = build_comparison(user, kind=kind, raw_selections=selections)
    result = update_saved_comparison(
        comparison=comparison,
        selections=normalized,
        comparable_rows=rows,
        include_quantities=config["include_quantities"],
    )
    return result.comparison


def saved_comparison_list_payload(user, *, kind=None, offset=0, limit=30) -> dict:
    queryset = SavedComparison.objects.filter(owner=user)
    if kind:
        if kind not in COMPARISON_KINDS:
            raise ValueError("comparison_kind_not_supported")
        queryset = queryset.filter(kind=kind)
    safe_offset = max(int(offset or 0), 0)
    safe_limit = min(max(int(limit or 30), 1), 50)
    total = queryset.count()
    return {
        "items": [
            {
                "id": comparison.id,
                "name": comparison.name,
                "kind": comparison.kind,
                "kind_label": COMPARISON_KINDS[comparison.kind]["label"],
                "item_count": len(comparison.snapshot_payload or comparison.payload or []),
                "updated_at": comparison.updated_at,
            }
            for comparison in queryset[safe_offset:safe_offset + safe_limit]
        ],
        "total": total,
        "offset": safe_offset,
        "limit": safe_limit,
    }


def saved_comparison_detail_payload(user, comparison_id: int) -> dict | None:
    comparison = SavedComparison.objects.filter(pk=comparison_id, owner=user).first()
    if comparison is None:
        return None
    config = COMPARISON_KINDS[comparison.kind]
    rows = comparable_rows_from_snapshot(
        comparison.snapshot_payload,
        include_quantities=config["include_quantities"],
    )
    return {
        **comparison_result_payload(
            kind=comparison.kind,
            rows=rows,
            historical=True,
            saved_comparison=comparison,
        ),
        "editable_selections": [
            {
                "id": row.get("id"),
                "quantity": row.get("quantity") if config["include_quantities"] else None,
            }
            for row in comparison.payload
            if isinstance(row, dict)
        ],
        "updated_at": comparison.updated_at,
    }
