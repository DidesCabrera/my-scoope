"""Private supplement library and daily-plan composition commands."""

from copy import deepcopy
from datetime import time
from decimal import Decimal, InvalidOperation

from django.conf import settings
from django.db import transaction

from accounts.services.entitlements import resolve_account_entitlements
from notas.application.services.calendarization.snapshots import snapshot_content_hash
from notas.domain.models import (
    CalendarizedDay,
    DailyPlan,
    Supplement,
    SupplementIntake,
    SupplementIntakeItem,
    SupplementIntakePreset,
    SupplementIntakePresetItem,
)

SUPPLEMENT_FORMS = frozenset({"capsule", "tablet", "softgel", "gummy", "sachet", "powder", "liquid", "drop"})
SUPPLEMENT_UNITS = frozenset({"capsule", "tablet", "softgel", "gummy", "sachet", "scoop", "drop", "ml", "g", "mg", "mcg", "iu", "tsp"})
COMPONENT_UNITS = frozenset({"g", "mg", "mcg", "ml", "iu"})
SUPPLEMENT_NUTRITION_FIELDS = frozenset({"energy_kcal", "protein_g", "carbs_g", "fat_g", "saturated_fat_g", "sugar_g", "fiber_g", "sodium_mg"})


def require_supplements_pro(user):
    entitlements = resolve_account_entitlements(user)
    if not settings.SUPPLEMENTS_FEATURE_ENABLED or entitlements is None or not entitlements.enabled("can_use_supplements"):
        raise PermissionError("supplements_pro_required")


def _clean_components(components):
    if not isinstance(components, list) or len(components) > 100:
        raise ValueError("supplement_components_invalid")
    cleaned = []
    for component in components:
        if not isinstance(component, dict):
            raise ValueError("supplement_components_invalid")
        name = str(component.get("name") or "").strip()
        unit = str(component.get("unit") or "").lower().strip()
        quantity = component.get("quantity")
        if not name or len(name) > 100 or unit not in COMPONENT_UNITS:
            raise ValueError("supplement_components_invalid")
        try:
            amount = Decimal(str(quantity))
        except (TypeError, ValueError, InvalidOperation):
            raise ValueError("supplement_components_invalid") from None
        if not amount.is_finite() or amount <= 0 or amount > 1000000:
            raise ValueError("supplement_components_invalid")
        cleaned.append({"name": name, "quantity": str(amount), "unit": unit})
    return cleaned


def _clean_nutrition(nutrition):
    if nutrition is None:
        return {}
    if not isinstance(nutrition, dict) or set(nutrition) - SUPPLEMENT_NUTRITION_FIELDS:
        raise ValueError("supplement_nutrition_invalid")
    cleaned = {}
    for field in SUPPLEMENT_NUTRITION_FIELDS:
        value = nutrition.get(field)
        if value is None or value == "":
            continue
        try:
            amount = Decimal(str(value))
        except (TypeError, ValueError, InvalidOperation):
            raise ValueError("supplement_nutrition_invalid") from None
        maximum = Decimal("1000000") if field == "sodium_mg" else Decimal("100000")
        if not amount.is_finite() or amount < 0 or amount > maximum:
            raise ValueError("supplement_nutrition_invalid")
        cleaned[field] = str(amount)
    return cleaned


def supplement_snapshot(supplement):
    return {
        "name": supplement.name,
        "brand": supplement.brand,
        "form": supplement.form,
        "description": supplement.description,
        "user_information": supplement.user_information,
        "components": supplement.components,
    }


def save_supplement(*, user, supplement_id=None, name, brand="", form="", description="", user_information="", components=None, nutrition=None, default_quantity=None, default_unit=""):
    require_supplements_pro(user)
    name = (name or "").strip()
    brand = (brand or "").strip()
    form = (form or "").strip().lower()
    default_unit = (default_unit or "").strip().lower()
    if not name or len(name) > 100 or len(brand) > 100 or len(form) > 32:
        raise ValueError("supplement_fields_invalid")
    if form and form not in SUPPLEMENT_FORMS:
        raise ValueError("supplement_form_invalid")
    if (default_quantity is None) != (not default_unit):
        raise ValueError("supplement_default_quantity_invalid")
    if default_unit and default_unit not in SUPPLEMENT_UNITS:
        raise ValueError("supplement_default_quantity_invalid")
    if default_quantity is not None and (not Decimal(str(default_quantity)).is_finite() or Decimal(str(default_quantity)) <= 0 or Decimal(str(default_quantity)) >= 1000000):
        raise ValueError("supplement_default_quantity_invalid")
    values = {
        "name": name, "brand": brand, "form": form,
        "description": (description or "").strip(),
        "user_information": (user_information or "").strip(),
        "components": _clean_components(components or []),
        "default_quantity": default_quantity,
        "default_unit": default_unit,
    }
    if nutrition is not None:
        values["nutrition"] = _clean_nutrition(nutrition)
    if supplement_id is None:
        values.setdefault("nutrition", {})
        return Supplement.objects.create(created_by=user, **values)
    supplement = Supplement.objects.filter(pk=supplement_id, created_by=user).first()
    if supplement is None:
        raise ValueError("supplement_not_found")
    for key, value in values.items():
        setattr(supplement, key, value)
    supplement.save(update_fields=[*values, "updated_at"])
    return supplement


def delete_supplement(*, user, supplement_id):
    require_supplements_pro(user)
    deleted, _ = Supplement.objects.filter(pk=supplement_id, created_by=user).delete()
    if not deleted:
        raise ValueError("supplement_not_found")


def _prepare_preset_items(*, user, items):
    if not items or len(items) > 30:
        raise ValueError("supplement_intake_preset_items_invalid")
    supplement_ids = [item.get("supplement_id") for item in items]
    if any(supplement_id is None for supplement_id in supplement_ids) or len(set(supplement_ids)) != len(supplement_ids):
        raise ValueError("supplement_intake_preset_items_invalid")
    supplements = {row.id: row for row in Supplement.objects.filter(created_by=user, id__in=supplement_ids)}
    if len(supplements) != len(supplement_ids):
        raise ValueError("supplement_not_found")
    prepared = []
    for order, item in enumerate(items, 1):
        try:
            quantity = Decimal(str(item["quantity"]))
        except (KeyError, TypeError, ValueError, InvalidOperation):
            raise ValueError("supplement_intake_quantity_invalid") from None
        unit = str(item.get("unit") or "").lower()
        if not quantity.is_finite() or quantity <= 0 or quantity >= 1000000 or unit not in SUPPLEMENT_UNITS:
            raise ValueError("supplement_intake_quantity_invalid")
        supplement = supplements[item["supplement_id"]]
        prepared.append({
            "order": order,
            "quantity": quantity,
            "supplement": supplement,
            "supplement_snapshot": supplement_snapshot(supplement),
            "unit": unit,
        })
    return prepared


@transaction.atomic
def save_supplement_intake_preset(*, user, name, items, preset_id=None):
    require_supplements_pro(user)
    name = (name or "").strip()
    if not name or len(name) > 100:
        raise ValueError("supplement_intake_preset_name_invalid")
    prepared = _prepare_preset_items(user=user, items=items)
    if preset_id is None:
        preset = SupplementIntakePreset.objects.create(created_by=user, name=name)
    else:
        preset = SupplementIntakePreset.objects.filter(pk=preset_id, created_by=user).first()
        if preset is None:
            raise ValueError("supplement_intake_preset_not_found")
        preset.name = name
        preset.save(update_fields=["name", "updated_at"])
        preset.items.all().delete()
    SupplementIntakePresetItem.objects.bulk_create([
        SupplementIntakePresetItem(preset=preset, **item) for item in prepared
    ])
    return preset


def delete_supplement_intake_preset(*, user, preset_id):
    require_supplements_pro(user)
    deleted, _ = SupplementIntakePreset.objects.filter(pk=preset_id, created_by=user).delete()
    if not deleted:
        raise ValueError("supplement_intake_preset_not_found")


def _owned_dailyplan(user, dailyplan_id):
    dailyplan = DailyPlan.objects.filter(pk=dailyplan_id, created_by=user).first()
    if dailyplan is None:
        raise ValueError("dailyplan_not_found")
    return dailyplan


def _replace_intake_items(*, user, intake, items):
    if not items or len(items) > 30:
        raise ValueError("supplement_intake_items_invalid")
    supplement_ids = [item.get("supplement_id") for item in items if item.get("supplement_id") is not None]
    preserved_ids = [item.get("item_id") for item in items if item.get("item_id") is not None]
    if len(set(supplement_ids)) != len(supplement_ids) or len(set(preserved_ids)) != len(preserved_ids):
        raise ValueError("supplement_intake_duplicate_item")
    supplements = {row.id: row for row in Supplement.objects.filter(created_by=user, id__in=supplement_ids)}
    preserved = {row.id: row for row in intake.items.filter(id__in=preserved_ids)}
    if len(supplements) != len(supplement_ids) or len(preserved) != len(preserved_ids):
        raise ValueError("supplement_not_found")
    prepared = []
    for order, item in enumerate(items, 1):
        quantity = Decimal(str(item["quantity"]))
        unit = str(item["unit"]).lower()
        if not quantity.is_finite() or quantity <= 0 or quantity >= 1000000 or unit not in SUPPLEMENT_UNITS:
            raise ValueError("supplement_intake_quantity_invalid")
        preserved_item = preserved.get(item.get("item_id"))
        if preserved_item is not None:
            if item.get("supplement_id") is not None and item["supplement_id"] != preserved_item.supplement_id:
                raise ValueError("supplement_intake_item_invalid")
            supplement = preserved_item.supplement
            snapshot = preserved_item.supplement_snapshot
        else:
            if item.get("supplement_id") is None:
                raise ValueError("supplement_intake_item_invalid")
            supplement = supplements[item["supplement_id"]]
            snapshot = supplement_snapshot(supplement)
        prepared.append(SupplementIntakeItem(
            intake=intake, supplement=supplement, supplement_snapshot=snapshot,
            quantity=quantity, unit=unit, order=order,
        ))
    intake.items.all().delete()
    SupplementIntakeItem.objects.bulk_create(prepared)


@transaction.atomic
def create_supplement_intake(*, user, dailyplan_id, items, hour=None):
    require_supplements_pro(user)
    dailyplan = _owned_dailyplan(user, dailyplan_id)
    existing = SupplementIntake.objects.select_for_update().filter(dailyplan=dailyplan)
    next_order = max((row.order for row in existing), default=0) + 1
    intake = SupplementIntake.objects.create(dailyplan=dailyplan, hour=hour, order=next_order)
    _replace_intake_items(user=user, intake=intake, items=items)
    dailyplan.update_draft_status()
    return intake


@transaction.atomic
def create_supplement_intake_from_preset(*, user, dailyplan_id, preset_id, hour):
    require_supplements_pro(user)
    dailyplan = _owned_dailyplan(user, dailyplan_id)
    preset = SupplementIntakePreset.objects.prefetch_related("items__supplement").filter(pk=preset_id, created_by=user).first()
    if preset is None:
        raise ValueError("supplement_intake_preset_not_found")
    preset_items = list(preset.items.all())
    if not preset_items:
        raise ValueError("supplement_intake_preset_items_invalid")
    next_order = max((row.order for row in SupplementIntake.objects.filter(dailyplan=dailyplan)), default=0) + 1
    intake = SupplementIntake.objects.create(dailyplan=dailyplan, hour=hour, order=next_order)
    SupplementIntakeItem.objects.bulk_create([
        SupplementIntakeItem(
            intake=intake,
            supplement=item.supplement if item.supplement and item.supplement.created_by_id == user.id else None,
            supplement_snapshot=item.supplement_snapshot,
            quantity=item.quantity,
            unit=item.unit,
            order=item.order,
        )
        for item in preset_items
    ])
    dailyplan.update_draft_status()
    return intake


@transaction.atomic
def update_supplement_intake(*, user, dailyplan_id, intake_id, items, hour=None):
    require_supplements_pro(user)
    dailyplan = _owned_dailyplan(user, dailyplan_id)
    intake = SupplementIntake.objects.select_for_update().filter(pk=intake_id, dailyplan=dailyplan).first()
    if intake is None:
        raise ValueError("supplement_intake_not_found")
    _replace_intake_items(user=user, intake=intake, items=items)
    intake.hour = hour
    intake.save(update_fields=["hour"])
    return intake


@transaction.atomic
def reorder_supplement_intakes(*, user, dailyplan_id, intake_ids):
    require_supplements_pro(user)
    dailyplan = _owned_dailyplan(user, dailyplan_id)
    rows = list(SupplementIntake.objects.select_for_update().filter(dailyplan=dailyplan))
    if len(intake_ids) != len(rows) or set(intake_ids) != {row.id for row in rows}:
        raise ValueError("supplement_intake_order_invalid")
    by_id = {row.id: row for row in rows}
    for order, intake_id in enumerate(intake_ids, 1):
        row = by_id[intake_id]
        if row.order != order:
            row.order = order
            row.save(update_fields=["order"])


@transaction.atomic
def delete_supplement_intake(*, user, dailyplan_id, intake_id):
    require_supplements_pro(user)
    dailyplan = _owned_dailyplan(user, dailyplan_id)
    intake = SupplementIntake.objects.filter(pk=intake_id, dailyplan=dailyplan).first()
    if intake is None:
        raise ValueError("supplement_intake_not_found")
    intake.delete()
    for order, row in enumerate(SupplementIntake.objects.filter(dailyplan=dailyplan), 1):
        if row.order != order:
            row.order = order
            row.save(update_fields=["order"])


def _calendarized_supplement_context(*, user, day_id):
    require_supplements_pro(user)
    day = CalendarizedDay.objects.select_for_update().filter(
        pk=day_id,
        user=user,
        assignment_state=CalendarizedDay.STATE_CURRENT,
    ).first()
    if day is None:
        raise ValueError("calendarized_day_not_found")
    snapshot = deepcopy(day.plan_snapshot) if isinstance(day.plan_snapshot, dict) else None
    if snapshot is None or not isinstance(snapshot.get("supplement_intakes"), list):
        raise ValueError("calendarized_plan_snapshot_invalid")
    return day, snapshot, snapshot["supplement_intakes"]


def _save_calendarized_supplements(day, snapshot):
    day.plan_snapshot = snapshot
    day.snapshot_hash = snapshot_content_hash(snapshot)
    day.save(update_fields=["plan_snapshot", "snapshot_hash"])


@transaction.atomic
def create_calendarized_supplement_intake_from_preset(*, user, day_id, preset_id, hour):
    day, snapshot, rows = _calendarized_supplement_context(user=user, day_id=day_id)
    preset = SupplementIntakePreset.objects.prefetch_related("items__supplement").filter(
        pk=preset_id,
        created_by=user,
    ).first()
    if preset is None:
        raise ValueError("supplement_intake_preset_not_found")
    preset_items = list(preset.items.all())
    if not preset_items:
        raise ValueError("supplement_intake_preset_items_invalid")
    try:
        parsed_hour = time.fromisoformat(hour) if isinstance(hour, str) else hour
    except ValueError as exc:
        raise ValueError("supplement_intake_hour_invalid") from exc
    if not isinstance(parsed_hour, time):
        raise ValueError("supplement_intake_hour_invalid")

    intake_ids = [row.get("id") for row in rows if isinstance(row, dict) and isinstance(row.get("id"), int)]
    item_ids = [
        item.get("id")
        for row in rows if isinstance(row, dict)
        for item in row.get("items", []) if isinstance(item, dict) and isinstance(item.get("id"), int)
    ]
    intake_id = max(intake_ids, default=0) + 1
    next_item_id = max(item_ids, default=0) + 1
    order = len(rows) + 1
    rows.append({
        "id": intake_id,
        "key": f"supplement_intake:{intake_id}",
        "label": f"Ingesta {order}",
        "order": order,
        "hour": parsed_hour.strftime("%H:%M"),
        "items": [
            {
                "id": next_item_id + index,
                "key": f"supplement_intake_item:{next_item_id + index}",
                "supplement_id": item.supplement_id if item.supplement and item.supplement.created_by_id == user.id else None,
                "supplement": deepcopy(item.supplement_snapshot),
                "quantity": str(item.quantity),
                "unit": item.unit,
            }
            for index, item in enumerate(preset_items)
        ],
    })
    _save_calendarized_supplements(day, snapshot)
    return intake_id


@transaction.atomic
def update_calendarized_supplement_intake_hour(*, user, day_id, intake_key, hour):
    day, snapshot, rows = _calendarized_supplement_context(user=user, day_id=day_id)
    intake = next((row for row in rows if isinstance(row, dict) and row.get("key") == intake_key), None)
    if intake is None:
        raise ValueError("supplement_intake_not_found")
    try:
        parsed_hour = time.fromisoformat(hour) if isinstance(hour, str) else hour
    except ValueError as exc:
        raise ValueError("supplement_intake_hour_invalid") from exc
    if not isinstance(parsed_hour, time):
        raise ValueError("supplement_intake_hour_invalid")
    intake["hour"] = parsed_hour.strftime("%H:%M")
    _save_calendarized_supplements(day, snapshot)


@transaction.atomic
def reorder_calendarized_supplement_intakes(*, user, day_id, intake_keys):
    day, snapshot, rows = _calendarized_supplement_context(user=user, day_id=day_id)
    current_keys = [row.get("key") for row in rows if isinstance(row, dict)]
    if len(current_keys) != len(rows) or len(intake_keys) != len(rows) or set(intake_keys) != set(current_keys):
        raise ValueError("supplement_intake_order_invalid")
    by_key = {row["key"]: row for row in rows}
    ordered = [by_key[key] for key in intake_keys]
    for order, row in enumerate(ordered, 1):
        row["order"] = order
        row["label"] = f"Ingesta {order}"
    snapshot["supplement_intakes"] = ordered
    _save_calendarized_supplements(day, snapshot)


@transaction.atomic
def delete_calendarized_supplement_intake(*, user, day_id, intake_key):
    day, snapshot, rows = _calendarized_supplement_context(user=user, day_id=day_id)
    if intake_key not in {row.get("key") for row in rows if isinstance(row, dict)}:
        raise ValueError("supplement_intake_not_found")
    remaining = [row for row in rows if not (isinstance(row, dict) and row.get("key") == intake_key)]
    for order, row in enumerate(remaining, 1):
        row["order"] = order
        row["label"] = f"Ingesta {order}"
    snapshot["supplement_intakes"] = remaining
    _save_calendarized_supplements(day, snapshot)
