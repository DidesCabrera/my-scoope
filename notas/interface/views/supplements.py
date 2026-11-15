"""Web session surfaces backed by the supplement domain commands."""

from dataclasses import asdict
from datetime import time
from decimal import Decimal, InvalidOperation

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import IntegrityError, transaction
from django.http import Http404, HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_GET, require_POST

from notas.application.services.commands.supplement_commands import (
    create_supplement_intake,
    create_supplement_intake_from_preset,
    delete_supplement,
    delete_supplement_intake,
    delete_supplement_intake_preset,
    require_supplements_pro,
    save_supplement,
    save_supplement_intake_preset,
    update_supplement_intake,
)
from notas.domain.models import DailyPlan, Supplement, SupplementCatalogEntry, SupplementIntake, SupplementIntakePreset
from notas.presentation.composition.viewmodel.components.builder_headers import build_page_header
from notas.presentation.composition.viewmodel.ui_builder import build_ui_vm
from notas.presentation.config.viewmodel_config import SUPPLEMENT_VIEWMODE_DETAIL, SUPPLEMENT_VIEWMODE_LIST
from notas.presentation.pages.library_entity_cards import supplement_card, supplement_preset_card

UNITS = ("capsule", "tablet", "softgel", "gummy", "sachet", "scoop", "drop", "ml", "g", "mg", "mcg", "iu", "tsp")
FORMS = ("capsule", "tablet", "softgel", "gummy", "sachet", "powder", "liquid", "drop")
COMPONENT_UNITS = ("g", "mg", "mcg", "ml", "iu")
NUTRITION_FIELDS = ("energy_kcal", "protein_g", "carbs_g", "fat_g", "saturated_fat_g", "sugar_g", "fiber_g", "sodium_mg")
FORM_LABELS = {
    "capsule": "Cápsula", "tablet": "Comprimido", "softgel": "Cápsula blanda",
    "gummy": "Gomita", "sachet": "Sobre", "powder": "Polvo",
    "liquid": "Líquido", "drop": "Gota",
}
UNIT_LABELS = {
    "capsule": ("cápsula", "cápsulas"), "tablet": ("comprimido", "comprimidos"),
    "softgel": ("cápsula blanda", "cápsulas blandas"), "gummy": ("gomita", "gomitas"),
    "sachet": ("sobre", "sobres"), "scoop": ("medida", "medidas"),
    "drop": ("gota", "gotas"), "tsp": ("cucharadita", "cucharaditas"),
    "iu": ("UI", "UI"),
}


def _access(user):
    try:
        require_supplements_pro(user)
    except PermissionError:
        return False
    return True


def _context(viewmode, **content):
    return {"vm": {"ui": asdict(build_ui_vm(viewmode)), "content": {
        "header": asdict(build_page_header(actions=[])), **content,
    }}}


def _amount(value):
    try:
        number = Decimal(str(value))
    except (TypeError, InvalidOperation):
        raise ValueError("invalid_amount") from None
    if not number.is_finite() or number <= 0 or number >= 1000000:
        raise ValueError("invalid_amount")
    return number


def _items(post, *, prefix):
    ids = post.getlist(f"{prefix}_id")
    quantities = post.getlist(f"{prefix}_quantity")
    units = post.getlist(f"{prefix}_unit")
    if len(ids) != len(quantities) or len(ids) != len(units):
        raise ValueError("invalid_items")
    if any(not item_id or not quantity or not unit for item_id, quantity, unit in zip(ids, quantities, units)):
        raise ValueError("invalid_items")
    return [
        {"supplement_id": int(item_id), "quantity": _amount(quantity), "unit": unit}
        for item_id, quantity, unit in zip(ids, quantities, units)
    ]


def _hour(value):
    if not value:
        return None
    try:
        return time.fromisoformat(value)
    except ValueError:
        raise ValueError("invalid_hour") from None


@login_required
@require_GET
def supplement_list(request):
    access = _access(request.user)
    search = request.GET.get("q", "").strip()[:100]
    rows = Supplement.objects.none()
    presets = SupplementIntakePreset.objects.none()
    catalog = SupplementCatalogEntry.objects.none()
    saved_catalog_ids = set()
    if access:
        rows = Supplement.objects.filter(created_by=request.user)
        presets = SupplementIntakePreset.objects.filter(created_by=request.user).prefetch_related("items")
        catalog = SupplementCatalogEntry.objects.filter(is_published=True)
        if search:
            rows = rows.filter(name__icontains=search)
            presets = presets.filter(name__icontains=search)
            catalog = catalog.filter(name__icontains=search)
        saved_catalog_ids = set(Supplement.objects.filter(
            created_by=request.user, catalog_entry__isnull=False,
        ).values_list("catalog_entry_id", flat=True))
    rows = list(rows[:100])
    presets = list(presets[:100])
    return render(request, "notas/supplements/list.html", _context(
        SUPPLEMENT_VIEWMODE_LIST, access=access, search=search,
        rows=rows, presets=presets, catalog=catalog[:100],
        supplement_cards=[supplement_card(item) for item in rows],
        preset_cards=[supplement_preset_card(item) for item in presets],
        saved_catalog_ids=saved_catalog_ids, units=UNITS,
    ))


@login_required
@require_GET
def supplement_detail(request, pk):
    if not _access(request.user):
        raise Http404
    supplement = get_object_or_404(Supplement, pk=pk, created_by=request.user)
    quantity = supplement.default_quantity
    unit = supplement.default_unit
    unit_labels = UNIT_LABELS.get(unit, (unit, unit))
    dose_label = f"{quantity.normalize()} {unit_labels[0] if quantity == 1 else unit_labels[1]}" if quantity and unit else ""
    return render(request, "notas/supplements/detail.html", _context(
        SUPPLEMENT_VIEWMODE_DETAIL, supplement=supplement, units=UNITS,
        forms=FORMS, component_units=COMPONENT_UNITS, nutrition_fields=NUTRITION_FIELDS,
        form_label=FORM_LABELS.get(supplement.form, supplement.form),
        dose_label=dose_label,
        title={"name": supplement.name, "label": "supplement", "icon": "pill"},
    ))


@login_required
@require_GET
def supplement_edit(request, pk):
    if not _access(request.user):
        raise Http404
    supplement = get_object_or_404(Supplement, pk=pk, created_by=request.user)
    return render(request, "notas/supplements/edit.html", _context(
        SUPPLEMENT_VIEWMODE_DETAIL, supplement=supplement, units=UNITS,
        forms=FORMS, component_units=COMPONENT_UNITS, nutrition_fields=NUTRITION_FIELDS,
    ))


@login_required
@require_POST
def supplement_save(request, pk=None):
    if not _access(request.user):
        return HttpResponseForbidden()
    if pk is not None:
        get_object_or_404(Supplement, pk=pk, created_by=request.user)
    try:
        components = []
        names = request.POST.getlist("component_name")
        quantities = request.POST.getlist("component_quantity")
        units = request.POST.getlist("component_unit")
        if len(names) != len(quantities) or len(names) != len(units):
            raise ValueError("invalid_components")
        for name, quantity, unit in zip(names, quantities, units):
            if name or quantity:
                components.append({"name": name, "quantity": _amount(quantity), "unit": unit})
        nutrition = {field: request.POST.get(field) for field in NUTRITION_FIELDS if request.POST.get(field)}
        default_quantity = request.POST.get("default_quantity")
        row = save_supplement(
            user=request.user, supplement_id=pk,
            name=request.POST.get("name", ""), brand=request.POST.get("brand", ""),
            form=request.POST.get("form", ""), description=request.POST.get("description", ""),
            user_information=request.POST.get("user_information", ""),
            components=components, nutrition=nutrition,
            default_quantity=_amount(default_quantity) if default_quantity else None,
            default_unit=request.POST.get("default_unit", ""),
        )
    except (ValueError, TypeError):
        messages.error(request, "Revisa los datos y las unidades del suplemento.")
        return redirect("supplement_detail", pk=pk) if pk else redirect("supplement_list")
    messages.success(request, "Suplemento guardado.")
    return redirect("supplement_detail", pk=row.pk)


@login_required
@require_POST
def supplement_remove(request, pk):
    if not _access(request.user):
        return HttpResponseForbidden()
    get_object_or_404(Supplement, pk=pk, created_by=request.user)
    delete_supplement(user=request.user, supplement_id=pk)
    return redirect("supplement_list")


@login_required
@require_POST
def supplement_catalog_save(request, pk):
    if not _access(request.user):
        return HttpResponseForbidden()
    row = get_object_or_404(SupplementCatalogEntry, pk=pk, is_published=True)
    try:
        with transaction.atomic():
            personal, _ = Supplement.objects.get_or_create(
                created_by=request.user, catalog_entry=row,
                defaults={
                    "name": row.name, "brand": row.brand, "form": row.form,
                    "description": row.description, "components": row.components,
                    "nutrition": row.nutrition, "default_quantity": row.default_quantity,
                    "default_unit": row.default_unit,
                },
            )
    except IntegrityError:
        personal = Supplement.objects.get(created_by=request.user, catalog_entry=row)
    return redirect("supplement_detail", pk=personal.pk)


@login_required
@require_POST
def supplement_preset_save(request, pk=None):
    if not _access(request.user):
        return HttpResponseForbidden()
    if pk is not None:
        get_object_or_404(SupplementIntakePreset, pk=pk, created_by=request.user)
    try:
        preset = save_supplement_intake_preset(
            user=request.user, preset_id=pk, name=request.POST.get("name", ""),
            items=_items(request.POST, prefix="preset"),
        )
    except (ValueError, TypeError):
        messages.error(request, "Revisa la toma, las cantidades y las unidades.")
        return redirect("supplement_list")
    messages.success(request, f"Toma {preset.name} guardada.")
    return redirect("supplement_preset_detail", pk=preset.pk)


@login_required
@require_GET
def supplement_preset_detail(request, pk):
    if not _access(request.user):
        raise Http404
    preset = get_object_or_404(
        SupplementIntakePreset.objects.prefetch_related("items"), pk=pk, created_by=request.user,
    )
    items = []
    for item in preset.items.all():
        labels = UNIT_LABELS.get(item.unit, (item.unit, item.unit))
        unit = labels[0] if item.quantity == 1 else labels[1]
        snapshot = item.supplement_snapshot or {}
        items.append({
            "supplement_id": item.supplement_id,
            "name": snapshot.get("name") or "Suplemento guardado",
            "brand": snapshot.get("brand") or "",
            "quantity_label": f"{item.quantity.normalize()} {unit}",
        })
    return render(request, "notas/supplements/preset_detail.html", _context(
        SUPPLEMENT_VIEWMODE_DETAIL, preset=preset, items=items,
        title={"name": preset.name, "label": "supplement", "eyebrow": "Ingesta de suplementos", "icon": "pill-bottle"},
        supplements=Supplement.objects.filter(created_by=request.user)[:100], units=UNITS,
    ))


@login_required
@require_GET
def supplement_preset_edit(request, pk):
    if not _access(request.user):
        raise Http404
    preset = get_object_or_404(
        SupplementIntakePreset.objects.prefetch_related("items"), pk=pk, created_by=request.user,
    )
    return render(request, "notas/supplements/preset_edit.html", _context(
        SUPPLEMENT_VIEWMODE_DETAIL, preset=preset,
        supplements=Supplement.objects.filter(created_by=request.user)[:100], units=UNITS,
    ))


@login_required
@require_POST
def supplement_preset_remove(request, pk):
    if not _access(request.user):
        return HttpResponseForbidden()
    get_object_or_404(SupplementIntakePreset, pk=pk, created_by=request.user)
    delete_supplement_intake_preset(user=request.user, preset_id=pk)
    return redirect("supplement_list")


@login_required
@require_POST
def dailyplan_intake_add(request, plan_id):
    if not _access(request.user):
        return HttpResponseForbidden()
    get_object_or_404(DailyPlan, pk=plan_id, created_by=request.user)
    try:
        hour = _hour(request.POST.get("hour"))
        if request.POST.get("preset_id"):
            if hour is None:
                raise ValueError("hour_required")
            create_supplement_intake_from_preset(
                user=request.user, dailyplan_id=plan_id,
                preset_id=int(request.POST["preset_id"]), hour=hour,
            )
        else:
            create_supplement_intake(
                user=request.user, dailyplan_id=plan_id,
                items=_items(request.POST, prefix="intake"), hour=hour,
            )
    except (ValueError, TypeError):
        messages.error(request, "Revisa la hora y las cantidades de la toma.")
    return redirect("dailyplan_detail", pk=plan_id)


@login_required
@require_POST
def dailyplan_intake_remove(request, plan_id, intake_id):
    if not _access(request.user):
        return HttpResponseForbidden()
    get_object_or_404(DailyPlan, pk=plan_id, created_by=request.user)
    get_object_or_404(SupplementIntake, pk=intake_id, dailyplan_id=plan_id)
    delete_supplement_intake(user=request.user, dailyplan_id=plan_id, intake_id=intake_id)
    return redirect("dailyplan_detail", pk=plan_id)


@login_required
@require_POST
def dailyplan_intake_update(request, plan_id, intake_id):
    if not _access(request.user):
        return HttpResponseForbidden()
    get_object_or_404(DailyPlan, pk=plan_id, created_by=request.user)
    intake = get_object_or_404(SupplementIntake.objects.prefetch_related("items"), pk=intake_id, dailyplan_id=plan_id)
    ids = request.POST.getlist("item_id")
    quantities = request.POST.getlist("quantity")
    units = request.POST.getlist("unit")
    if len(ids) != len(quantities) or len(ids) != len(units):
        messages.error(request, "Revisa las cantidades de la toma.")
        return redirect("dailyplan_detail", pk=plan_id)
    owned_ids = set(intake.items.values_list("id", flat=True))
    try:
        if set(map(int, ids)) != owned_ids:
            raise ValueError("invalid_items")
        items = [
            {"item_id": int(item_id), "quantity": _amount(quantity), "unit": unit}
            for item_id, quantity, unit in zip(ids, quantities, units)
        ]
        update_supplement_intake(
            user=request.user, dailyplan_id=plan_id, intake_id=intake_id,
            items=items, hour=_hour(request.POST.get("hour")),
        )
    except (ValueError, TypeError):
        messages.error(request, "Revisa las cantidades y la hora de la toma.")
    return redirect("dailyplan_detail", pk=plan_id)
