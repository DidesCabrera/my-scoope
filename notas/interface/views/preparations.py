"""Session-based web surfaces for operational preparations."""

from dataclasses import asdict
from decimal import Decimal, InvalidOperation

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Q
from django.http import Http404, HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_GET, require_http_methods, require_POST

from notas.application.queries.food_picker_queries import list_food_picker_page
from notas.application.services.cache.dailyplan_summary import refresh_dailyplans_for_meal
from notas.application.services.commands.meal_commands import next_meal_component_order
from notas.application.services.commands.personal_preparation_commands import (
    PersonalPreparationError,
    add_personal_preparation_food,
    can_use_personal_preparations,
    clear_personal_preparation_ingredients,
    create_personal_preparation_draft,
    remove_personal_preparation,
    rename_personal_preparation_draft,
    save_personal_preparation,
)
from notas.application.services.nutrition.meal_nutrition import rebuild_meal_cached_state
from notas.application.services.nutrition.weight import get_current_weight
from notas.domain.models import Meal, MealPreparation, Preparation
from notas.presentation.composition.viewmodel.components.builder_headers import build_page_header
from notas.presentation.composition.viewmodel.ui_builder import build_ui_vm
from notas.presentation.config.viewmodel_config import PREPARATION_VIEWMODE_DETAIL, PREPARATION_VIEWMODE_LIST
from notas.presentation.pages.library_entity_cards import (
    preparation_card,
    preparation_food_rows,
    preparation_ingredient_cards,
    preparation_kpis,
)


def _context(viewmode, **content):
    return {"vm": {"ui": asdict(build_ui_vm(viewmode)), "content": {
        "header": asdict(build_page_header(actions=[])), **content,
    }}}


def _visible_preparation(user, pk):
    visibility = Q(is_global=True, is_active=True) | Q(is_global=False, created_by=user)
    preparation = get_object_or_404(
        Preparation.objects.select_related("current_version"), visibility, pk=pk,
    )
    if not preparation.is_global and not can_use_personal_preparations(user):
        raise Http404
    return preparation


def _positive_decimal(value):
    try:
        result = Decimal(str(value))
    except (TypeError, InvalidOperation):
        raise ValueError("Cantidad inválida") from None
    if not result.is_finite() or result <= 0 or result > 100000:
        raise ValueError("Cantidad inválida")
    return result


def _portion(version, *, mode, value):
    quantity = _positive_decimal(value)
    if mode == "units":
        if quantity < Decimal("0.5") or quantity > 10 or quantity * 2 != (quantity * 2).to_integral_value():
            raise ValueError("Cantidad inválida")
        return "units", quantity, quantity * version.default_portion_g
    if mode == "grams" and quantity <= version.default_portion_g * 10:
        return "grams", None, quantity
    raise ValueError("Cantidad inválida")


@login_required
@require_GET
def preparation_list(request):
    search = request.GET.get("q", "").strip()[:100]
    global_rows = Preparation.objects.select_related("current_version").filter(
        is_global=True, is_active=True, current_version__isnull=False,
    )
    if search:
        global_rows = global_rows.filter(name__icontains=search)
    personal_access = can_use_personal_preparations(request.user)
    personal_rows = Preparation.objects.none()
    if personal_access:
        personal_rows = Preparation.objects.select_related("current_version").filter(
            is_global=False, is_active=True, created_by=request.user,
        )
        if search:
            personal_rows = personal_rows.filter(name__icontains=search)
    personal_rows = list(personal_rows.order_by("name", "id")[:100])
    global_rows = list(global_rows.order_by("name", "id")[:100])
    weight = get_current_weight(request.user)
    return render(request, "notas/preparations/list.html", _context(
        PREPARATION_VIEWMODE_LIST,
        search=search,
        global_rows=global_rows,
        personal_rows=personal_rows,
        global_cards=[preparation_card(item, weight=weight) for item in global_rows],
        personal_cards=[preparation_card(item, weight=weight) for item in personal_rows],
        personal_access=personal_access,
    ))


@login_required
@require_GET
def _preparation_page_context(request, pk):
    preparation = _visible_preparation(request.user, pk)
    version = preparation.current_version
    food_search = request.GET.get("food", "").strip()[:100]
    food_results = None
    if food_search and not preparation.is_global and preparation.is_active:
        food_results = list_food_picker_page(user=request.user, search=food_search, limit=20).foods
    ingredients = []
    if version:
        for row, snapshot in zip(
            version.ingredients.select_related("food").order_by("order", "id"),
            version.ingredients_snapshot,
        ):
            quantity = Decimal(str(snapshot.get("quantity_g", row.quantity_g)))
            base = snapshot.get("nutrition_per_100g") or {}
            ingredient = {
                "food_id": row.food_id, "name": snapshot.get("name", row.food.name),
                "quantity_g": quantity,
            }
            if all(base.get(key) is not None for key in ("protein_g", "carbs_g", "fat_g")):
                factor = quantity / 100
                ingredient["protein"] = Decimal(str(base["protein_g"])) * factor
                ingredient["carbs"] = Decimal(str(base["carbs_g"])) * factor
                ingredient["fat"] = Decimal(str(base["fat_g"])) * factor
                ingredient["calories"] = (
                    ingredient["protein"] * 4 + ingredient["carbs"] * 4 + ingredient["fat"] * 9
                )
            ingredients.append(ingredient)
    weight = get_current_weight(request.user)
    kpis = {"recipe": preparation_kpis(version, weight=weight), "portion": preparation_kpis(version, portion=True, weight=weight)} if version else None
    return _context(
        PREPARATION_VIEWMODE_DETAIL,
        preparation=preparation, version=version, ingredients=ingredients,
        food_search=food_search, food_results=food_results,
        can_edit=not preparation.is_global and preparation.is_active,
        kpis=kpis,
        food_rows=preparation_food_rows(ingredients, kpis["recipe"], weight=weight) if version else [],
        ingredient_cards=preparation_ingredient_cards(ingredients, weight=weight) if version else [],
        title={"name": preparation.name, "label": "preparation", "icon": "cooking-pot"},
        portion_count=version.yield_g / version.default_portion_g if version else None,
    )


@login_required
@require_GET
def preparation_detail(request, pk):
    return render(request, "notas/preparations/detail.html", _preparation_page_context(request, pk))


@login_required
@require_GET
def _preparation_edit_page(request, pk):
    if not can_use_personal_preparations(request.user):
        raise Http404
    context = _preparation_page_context(request, pk)
    if not context["vm"]["content"]["can_edit"]:
        raise Http404
    return render(request, "notas/preparations/edit.html", context)


@login_required
@require_POST
def preparation_create(request):
    if not can_use_personal_preparations(request.user):
        return HttpResponseForbidden()
    try:
        preparation = create_personal_preparation_draft(user=request.user, name=request.POST.get("name", ""))
    except PersonalPreparationError:
        messages.error(request, "Ingresa un nombre válido para la preparación.")
        return redirect("preparation_list")
    return redirect("preparation_detail", pk=preparation.pk)


@login_required
@require_http_methods(["GET", "POST"])
def preparation_edit(request, pk):
    if request.method == "GET":
        return _preparation_edit_page(request, pk)
    if not can_use_personal_preparations(request.user):
        return HttpResponseForbidden()
    preparation = get_object_or_404(
        Preparation.objects.select_related("current_version"), pk=pk, is_global=False,
        created_by=request.user, is_active=True,
    )
    action = request.POST.get("action")
    try:
        if action == "delete":
            remove_personal_preparation(user=request.user, preparation_id=pk)
            messages.success(request, "Preparación retirada de tu biblioteca.")
            return redirect("preparation_list")
        if action in {"add_food", "update_food"}:
            add_personal_preparation_food(
                user=request.user, preparation_id=pk,
                food_id=int(request.POST.get("food_id", "")),
                quantity_g=_positive_decimal(request.POST.get("quantity_g")),
                replace_food_id=int(request.POST.get("food_id", "")) if action == "update_food" else None,
            )
        elif action in {"save", "remove_food"}:
            version = preparation.current_version
            ingredients = [
                {"food_id": row.food_id, "quantity_g": row.quantity_g}
                for row in version.ingredients.all()
            ] if version else []
            if action == "remove_food":
                food_id = int(request.POST.get("food_id", ""))
                ingredients = [item for item in ingredients if item["food_id"] != food_id]
                if version and len(ingredients) == version.ingredients.count():
                    raise ValueError("Alimento no encontrado")
            if not ingredients:
                clear_personal_preparation_ingredients(user=request.user, preparation_id=pk)
                if action == "save":
                    rename_personal_preparation_draft(
                        user=request.user, preparation_id=pk, name=request.POST.get("name", ""),
                    )
            else:
                save_personal_preparation(
                    user=request.user, preparation_id=pk,
                    name=request.POST.get("name", preparation.name) if action == "save" else preparation.name,
                    ingredients=ingredients,
                    yield_g=(
                        _positive_decimal(request.POST.get("yield_g")) if request.POST.get("manual_yield") == "1" else None
                    ) if action == "save" else (
                        version.yield_g if version and version.evidence.get("yield_is_manual") else None
                    ),
                    default_portion_g=_positive_decimal(request.POST.get("default_portion_g")) if action == "save" else (
                        version.default_portion_g if version else 100
                    ),
                )
        else:
            raise ValueError("Acción inválida")
    except (PersonalPreparationError, ValueError, TypeError):
        messages.error(request, "Revisa el nombre, los alimentos y las cantidades de la preparación.")
        return redirect("preparation_detail", pk=pk)
    messages.success(request, "Preparación actualizada.")
    return redirect("preparation_detail", pk=pk)


@login_required
@require_POST
@transaction.atomic
def meal_preparation_add(request, meal_id):
    meal = get_object_or_404(Meal, pk=meal_id, created_by=request.user)
    try:
        preparation = _visible_preparation(request.user, int(request.POST.get("preparation_id", "")))
        if not preparation.is_active or not preparation.current_version_id:
            raise ValueError
        mode, units, quantity = _portion(
            preparation.current_version,
            mode=request.POST.get("mode", "units"), value=request.POST.get("quantity", request.POST.get("units")),
        )
    except (ValueError, TypeError, Http404):
        messages.error(request, "Elige una preparación disponible y una porción válida.")
        return redirect("meal_detail", pk=meal_id)
    MealPreparation.objects.create(
        meal=meal, preparation=preparation, version=preparation.current_version,
        selection_mode=mode, selected_units=units, quantity_g=quantity,
        order=next_meal_component_order(meal),
    )
    meal.update_draft_status()
    rebuild_meal_cached_state(meal)
    refresh_dailyplans_for_meal(meal)
    return redirect("meal_detail", pk=meal_id)


@login_required
@require_POST
@transaction.atomic
def meal_preparation_update(request, meal_id, relation_id):
    meal = get_object_or_404(Meal, pk=meal_id, created_by=request.user)
    relation = get_object_or_404(MealPreparation.objects.select_related("preparation", "version"), pk=relation_id, meal=meal)
    try:
        if not relation.preparation.is_global and not can_use_personal_preparations(request.user):
            return HttpResponseForbidden()
        mode, units, quantity = _portion(
            relation.version, mode=request.POST.get("mode", "units"),
            value=request.POST.get("quantity"),
        )
    except ValueError:
        messages.error(request, "La porción no es válida.")
        return redirect("meal_detail", pk=meal_id)
    relation.selection_mode = mode
    relation.selected_units = units
    relation.quantity_g = quantity
    relation.save(update_fields=["selection_mode", "selected_units", "quantity_g"])
    rebuild_meal_cached_state(meal)
    refresh_dailyplans_for_meal(meal)
    return redirect("meal_detail", pk=meal_id)


@login_required
@require_POST
@transaction.atomic
def meal_preparation_remove(request, meal_id, relation_id):
    meal = get_object_or_404(Meal, pk=meal_id, created_by=request.user)
    relation = get_object_or_404(MealPreparation, pk=relation_id, meal=meal)
    relation.delete()
    rebuild_meal_cached_state(meal)
    refresh_dailyplans_for_meal(meal)
    return redirect("meal_detail", pk=meal_id)
