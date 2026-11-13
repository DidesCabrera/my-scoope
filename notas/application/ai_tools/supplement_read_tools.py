"""Owner-scoped, Pro-gated reads of informational supplement state."""

from notas.application.ai_tools.results import tool_error
from notas.application.ai_tools.runtime import run_ai_tool
from notas.application.services.commands.supplement_commands import require_supplements_pro
from notas.domain.models import DailyPlan, Supplement, SupplementIntakePreset


def query_supplements_tool(user, *, resource: str, object_id: int | None, search: str, limit: int, offset: int):
    try:
        require_supplements_pro(user)
    except PermissionError:
        return tool_error(
            code="supplements_pro_required",
            message="La consulta de suplementos requiere acceso Pro activo.",
        )
    return run_ai_tool(
        _supplement_query_data,
        user,
        resource=resource,
        object_id=object_id,
        search=search,
        limit=limit,
        offset=offset,
        user=user,
    )


def _supplement_query_data(user, *, resource: str, object_id: int | None, search: str, limit: int, offset: int) -> dict:
    if resource not in {"supplements", "supplement_presets", "supplement_intakes"}:
        raise ValueError("invalid_supplement_resource")
    limit = max(1, min(int(limit), 50))
    offset = max(0, int(offset))

    if resource == "supplement_intakes":
        if object_id is None:
            raise ValueError("dailyplan_id_required")
        plan = DailyPlan.objects.filter(pk=object_id, created_by=user).first()
        if plan is None:
            raise ValueError("dailyplan_not_found")
        queryset = plan.supplement_intakes.all()
        total = queryset.count()
        intakes = queryset.prefetch_related("items")[offset:offset + limit]
        items = [
            {
                "id": intake.id,
                "hour": intake.hour.strftime("%H:%M") if intake.hour else None,
                "supplements": [
                    {
                        "name": item.supplement_snapshot.get("name", ""),
                        "quantity": str(item.quantity),
                        "unit": item.unit,
                    }
                    for item in intake.items.all()
                ],
            }
            for intake in intakes
        ]
        return {
            "resource": resource,
            "dailyplan_id": plan.id,
            "items": items,
            "total_count": total,
            "count_for_user_questions": total,
            "returned_count": len(items),
            "offset": offset,
            "has_more": offset + len(items) < total,
            "next_offset": offset + len(items) if offset + len(items) < total else None,
            "nutrition_policy": "informational_only_not_in_plan_totals",
        }

    if resource == "supplement_presets":
        queryset = SupplementIntakePreset.objects.filter(created_by=user)
        if object_id is not None:
            row = queryset.prefetch_related("items").filter(pk=object_id).first()
            if row is None:
                raise ValueError("supplement_preset_not_found")
            return {"resource": resource, "item": _preset_item(row), "nutrition_policy": "informational_only_not_in_plan_totals"}
        if search:
            queryset = queryset.filter(name__icontains=search)
        total = queryset.count()
        items = [_preset_item(row) for row in queryset.prefetch_related("items")[offset:offset + limit]]
    else:
        queryset = Supplement.objects.filter(created_by=user)
        if object_id is not None:
            row = queryset.filter(pk=object_id).first()
            if row is None:
                raise ValueError("supplement_not_found")
            return {"resource": resource, "item": _supplement_item(row, detail=True), "nutrition_policy": "informational_only_not_in_plan_totals"}
        if search:
            queryset = queryset.filter(name__icontains=search)
        total = queryset.count()
        items = [_supplement_item(row) for row in queryset[offset:offset + limit]]

    returned = len(items)
    return {
        "resource": resource,
        "items": items,
        "total_count": total,
        "count_for_user_questions": total,
        "returned_count": returned,
        "offset": offset,
        "has_more": offset + returned < total,
        "next_offset": offset + returned if offset + returned < total else None,
        "nutrition_policy": "informational_only_not_in_plan_totals",
    }


def _supplement_item(row, *, detail: bool = False) -> dict:
    item = {
        "id": row.id,
        "name": row.name,
        "brand": row.brand,
        "form": row.form,
        "default_quantity": str(row.default_quantity) if row.default_quantity is not None else None,
        "default_unit": row.default_unit,
    }
    if detail:
        item.update({
            "description": row.description[:500],
            "components": row.components[:30],
            "label_nutrition": row.nutrition,
        })
    return item


def _preset_item(row) -> dict:
    return {
        "id": row.id,
        "name": row.name,
        "supplements": [
            {
                "name": item.supplement_snapshot.get("name", ""),
                "quantity": str(item.quantity),
                "unit": item.unit,
            }
            for item in row.items.all()
        ],
    }
