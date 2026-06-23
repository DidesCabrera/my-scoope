from dataclasses import dataclass, field
from typing import Any

from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render
from django.urls import reverse

from notas.application.services.nutrition.weight import get_current_weight
from notas.domain.models import DailyPlan, Food, Meal
from notas.presentation.composition.viewmodel.ui_builder import build_ui_vm
from notas.presentation.config.viewmodel_config import (
    COMPARATOR_VIEWMODE_DAILYPLANS,
    COMPARATOR_VIEWMODE_FOODS,
    COMPARATOR_VIEWMODE_MEALS,
)
from notas.presentation.viewmodels.base_vm import BaseVM


MIN_COMPARATOR_SLOTS = 2


@dataclass
class ComparatorChoice:
    id: int
    name: str


@dataclass
class ComparatorSelection:
    id: int | None = None
    name: str = ""
    quantity: float | None = None
    position: int = 1

    @property
    def label(self) -> str:
        return f"Selector {self.position}"


@dataclass
class ComparatorMetricBar:
    label: str
    value: float
    formatted_value: str
    width: float


@dataclass
class ComparatorMetric:
    key: str
    label: str
    unit: str
    bars: list[ComparatorMetricBar] = field(default_factory=list)


@dataclass
class ComparatorTab:
    label: str
    url: str
    icon: str
    is_active: bool = False


@dataclass
class ComparatorContentVM:
    entity_label: str
    entity_plural_label: str
    entity_icon: str
    entity_scope: str
    selector_label: str
    add_action_label: str
    show_quantity_inputs: bool = False
    quantity_unit: str = "g"
    choices: list[ComparatorChoice] = field(default_factory=list)
    selections: list[ComparatorSelection] = field(default_factory=list)
    metrics: list[ComparatorMetric] = field(default_factory=list)
    tabs: list[ComparatorTab] = field(default_factory=list)
    item_count: int = 0
    is_ready: bool = False
    empty_message: str = "Selecciona al menos dos elementos para compararlos."

    @property
    def can_remove_selection(self) -> bool:
        return len(self.selections) > MIN_COMPARATOR_SLOTS


def _parse_int(value: Any) -> int | None:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return None

    return parsed if parsed > 0 else None


def _parse_zero_based_index(value: Any) -> int | None:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return None

    return parsed if parsed >= 0 else None


def _parse_quantity(value: Any, fallback: float = 100.0) -> float:
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return fallback

    return parsed if parsed > 0 else fallback


def _format_number(value: float, decimals: int = 0) -> str:
    if value is None:
        value = 0

    if decimals == 0:
        return f"{value:.0f}"

    formatted = f"{value:.{decimals}f}"
    return formatted.rstrip("0").rstrip(".")


def _format_metric_value(value: float, unit: str) -> str:
    if unit == "g/kg":
        decimals = 2
    elif unit in {"g", "%"}:
        decimals = 1
    else:
        decimals = 0

    return f"{_format_number(value, decimals)} {unit}"


def _metric_bar(label: str, value: float, unit: str, max_value: float) -> ComparatorMetricBar:
    safe_value = max(float(value or 0), 0)
    width = 0

    if max_value > 0:
        width = max((safe_value / max_value) * 100, 4 if safe_value > 0 else 0)

    return ComparatorMetricBar(
        label=label,
        value=safe_value,
        formatted_value=_format_metric_value(safe_value, unit),
        width=round(width, 2),
    )


def _build_metric(
    key: str,
    label: str,
    unit: str,
    comparable_rows: list[tuple[ComparatorSelection, dict[str, float]]],
) -> ComparatorMetric:
    max_value = max((float(values.get(key, 0) or 0) for _, values in comparable_rows), default=0)

    return ComparatorMetric(
        key=key,
        label=label,
        unit=unit,
        bars=[
            _metric_bar(selection.name, values.get(key, 0), unit, max_value)
            for selection, values in comparable_rows
        ],
    )


def _alloc_from_values(total_kcal: float, kcal_protein: float, kcal_carbs: float, kcal_fat: float) -> dict[str, float]:
    if not total_kcal or total_kcal <= 0:
        return {"protein": 0, "carbs": 0, "fat": 0}

    return {
        "protein": (kcal_protein / total_kcal) * 100,
        "carbs": (kcal_carbs / total_kcal) * 100,
        "fat": (kcal_fat / total_kcal) * 100,
    }


def _food_values(food: Food, quantity: float) -> dict[str, float]:
    factor = quantity / 100
    protein = food.protein * factor
    carbs = food.carbs * factor
    fat = food.fat * factor
    kcal_protein = food.kcal_protein * factor
    kcal_carbs = food.kcal_carbs * factor
    kcal_fat = food.kcal_fat * factor
    total_kcal = kcal_protein + kcal_carbs + kcal_fat
    alloc = _alloc_from_values(total_kcal, kcal_protein, kcal_carbs, kcal_fat)

    return {
        "total_kcal": total_kcal,
        "protein": protein,
        "carbs": carbs,
        "fat": fat,
        "alloc_protein": alloc["protein"],
        "alloc_carbs": alloc["carbs"],
        "alloc_fat": alloc["fat"],
    }


def _entity_values(entity, current_weight: float | None = None) -> dict[str, float]:
    alloc = entity.alloc
    protein = entity.protein

    return {
        "total_kcal": entity.total_kcal,
        "ppk": (protein / current_weight) if (current_weight and protein) else 0,
        "protein": protein,
        "carbs": entity.carbs,
        "fat": entity.fat,
        "alloc_protein": alloc.get("protein", 0),
        "alloc_carbs": alloc.get("carbs", 0),
        "alloc_fat": alloc.get("fat", 0),
    }


def _build_metrics(
    comparable_rows: list[tuple[ComparatorSelection, dict[str, float]]],
    *,
    include_ppk: bool = False,
) -> list[ComparatorMetric]:
    metric_specs = [
        ("total_kcal", "Calorías", "kcal"),
    ]

    if include_ppk:
        metric_specs.append(("ppk", "PPK", "g/kg"))

    metric_specs.extend([
        ("protein", "Proteínas", "g"),
        ("carbs", "Carbohidratos", "g"),
        ("fat", "Grasas", "g"),
        ("alloc_protein", "P%", "%"),
        ("alloc_carbs", "C%", "%"),
        ("alloc_fat", "F%", "%"),
    ])

    return [
        _build_metric(
            key=key,
            label=label,
            unit=unit,
            comparable_rows=comparable_rows,
        )
        for key, label, unit in metric_specs
    ]


def _build_tabs(active_key: str) -> list[ComparatorTab]:
    specs = [
        ("foods", "Alimentos", "carrot", "food_comparator"),
        ("meals", "Comidas", "utensils", "meal_comparator"),
        ("dailyplans", "Planes", "clipboard-list", "dailyplan_comparator"),
    ]

    return [
        ComparatorTab(
            label=label,
            icon=icon,
            url=reverse(url_name),
            is_active=key == active_key,
        )
        for key, label, icon, url_name in specs
    ]


def _choices_from_queryset(queryset) -> list[ComparatorChoice]:
    return [ComparatorChoice(id=item.id, name=item.name) for item in queryset]


def _items_by_id(queryset) -> dict[int, Any]:
    return {item.id: item for item in queryset}


def _selection_rows_from_request(request, *, include_quantities: bool = False) -> list[dict[str, Any]]:
    indexed_positions: list[int] = []

    for key in request.GET.keys():
        if key.startswith("item_"):
            parsed = _parse_int(key.removeprefix("item_"))
            if parsed:
                indexed_positions.append(parsed)

    if indexed_positions:
        max_position = max(max(indexed_positions), MIN_COMPARATOR_SLOTS)
        return [
            {
                "id": _parse_int(request.GET.get(f"item_{position}")),
                "quantity": _quantity_from_request(request, position) if include_quantities else None,
            }
            for position in range(1, max_position + 1)
        ]

    return [
        {
            "id": _parse_int(request.GET.get("a")),
            "quantity": _quantity_from_request(request, 1) if include_quantities else None,
        },
        {
            "id": _parse_int(request.GET.get("b")),
            "quantity": _quantity_from_request(request, 2) if include_quantities else None,
        },
    ]


def _quantity_from_request(request, position: int, fallback: float = 100.0) -> float:
    value = request.GET.get(f"qty_{position}")

    if value is None and position == 1:
        value = request.GET.get("qty_a")
    elif value is None and position == 2:
        value = request.GET.get("qty_b")

    return _parse_quantity(value, fallback=fallback)


def _build_selections_from_request(
    request,
    *,
    items_by_id: dict[int, Any],
    include_quantities: bool = False,
) -> list[ComparatorSelection]:
    rows = _selection_rows_from_request(request, include_quantities=include_quantities)
    remove_index = _parse_zero_based_index(request.GET.get("remove_index"))

    if remove_index is not None and len(rows) > MIN_COMPARATOR_SLOTS:
        if remove_index < len(rows):
            rows.pop(remove_index)

    if request.GET.get("comparator_action") == "add":
        rows.append({"id": None, "quantity": 100.0 if include_quantities else None})

    while len(rows) < MIN_COMPARATOR_SLOTS:
        rows.append({"id": None, "quantity": 100.0 if include_quantities else None})

    selections: list[ComparatorSelection] = []
    for index, row in enumerate(rows, start=1):
        selected_id = row.get("id")
        selected_item = items_by_id.get(selected_id) if selected_id else None
        selections.append(
            ComparatorSelection(
                id=selected_item.id if selected_item else selected_id,
                name=selected_item.name if selected_item else "",
                quantity=row.get("quantity") if include_quantities else None,
                position=index,
            )
        )

    return selections


def _comparable_rows(
    selections: list[ComparatorSelection],
    items_by_id: dict[int, Any],
    value_builder,
) -> list[tuple[ComparatorSelection, dict[str, float]]]:
    rows: list[tuple[ComparatorSelection, dict[str, float]]] = []

    for selection in selections:
        if not selection.id:
            continue

        item = items_by_id.get(selection.id)
        if not item:
            continue

        rows.append((selection, value_builder(item, selection)))

    return rows


@login_required
def comparator_index(request):
    return redirect("food_comparator")


@login_required
def food_comparator(request):
    foods = list(
        Food.objects
        .filter(
            created_by=request.user,
            is_active=True,
        )
        .order_by("list_order", "name", "id")
    )
    foods_by_id = _items_by_id(foods)
    selections = _build_selections_from_request(
        request,
        items_by_id=foods_by_id,
        include_quantities=True,
    )
    comparable_rows = _comparable_rows(
        selections,
        foods_by_id,
        lambda food, selection: _food_values(food, selection.quantity or 100.0),
    )
    metrics = _build_metrics(comparable_rows) if len(comparable_rows) >= 2 else []

    content_vm = ComparatorContentVM(
        entity_label="alimento",
        entity_plural_label="alimentos",
        entity_icon="carrot",
        entity_scope="food",
        selector_label="Alimento",
        add_action_label="Agregar Alimento a la comparación",
        show_quantity_inputs=True,
        choices=_choices_from_queryset(foods),
        selections=selections,
        metrics=metrics,
        tabs=_build_tabs("foods"),
        item_count=len(foods),
        is_ready=bool(metrics),
        empty_message="Selecciona al menos dos alimentos y define sus porciones para ver la comparación.",
    )

    return _render_comparator(
        request=request,
        viewmode=COMPARATOR_VIEWMODE_FOODS,
        content_vm=content_vm,
    )


@login_required
def meal_comparator(request):
    meals = list(
        Meal.objects
        .filter(
            created_by=request.user,
            is_draft=False,
            dailyplanmeal__isnull=True,
        )
        .order_by("list_order", "name", "id")
        .distinct()
    )
    meals_by_id = _items_by_id(meals)
    selections = _build_selections_from_request(request, items_by_id=meals_by_id)
    current_weight = get_current_weight(request.user)
    comparable_rows = _comparable_rows(
        selections,
        meals_by_id,
        lambda meal, selection: _entity_values(meal, current_weight=current_weight),
    )
    metrics = _build_metrics(comparable_rows, include_ppk=True) if len(comparable_rows) >= 2 else []

    content_vm = ComparatorContentVM(
        entity_label="comida",
        entity_plural_label="comidas",
        entity_icon="utensils",
        entity_scope="meal",
        selector_label="Comida",
        add_action_label="Agregar Comida a la comparación",
        choices=_choices_from_queryset(meals),
        selections=selections,
        metrics=metrics,
        tabs=_build_tabs("meals"),
        item_count=len(meals),
        is_ready=bool(metrics),
        empty_message="Selecciona al menos dos comidas para ver la comparación.",
    )

    return _render_comparator(
        request=request,
        viewmode=COMPARATOR_VIEWMODE_MEALS,
        content_vm=content_vm,
    )


@login_required
def dailyplan_comparator(request):
    dailyplans = list(
        DailyPlan.objects
        .filter(
            created_by=request.user,
            is_draft=False,
        )
        .exclude(source=DailyPlan.SOURCE_PROGRAM)
        .order_by("list_order", "name", "id")
    )
    dailyplans_by_id = _items_by_id(dailyplans)
    selections = _build_selections_from_request(request, items_by_id=dailyplans_by_id)
    current_weight = get_current_weight(request.user)
    comparable_rows = _comparable_rows(
        selections,
        dailyplans_by_id,
        lambda dailyplan, selection: _entity_values(dailyplan, current_weight=current_weight),
    )
    metrics = _build_metrics(comparable_rows, include_ppk=True) if len(comparable_rows) >= 2 else []

    content_vm = ComparatorContentVM(
        entity_label="plan diario",
        entity_plural_label="planes diarios",
        entity_icon="clipboard-list",
        entity_scope="dailyplan",
        selector_label="Plan",
        add_action_label="Agregar Plan a la comparación",
        choices=_choices_from_queryset(dailyplans),
        selections=selections,
        metrics=metrics,
        tabs=_build_tabs("dailyplans"),
        item_count=len(dailyplans),
        is_ready=bool(metrics),
        empty_message="Selecciona al menos dos planes diarios para ver la comparación.",
    )

    return _render_comparator(
        request=request,
        viewmode=COMPARATOR_VIEWMODE_DAILYPLANS,
        content_vm=content_vm,
    )


def _render_comparator(request, viewmode, content_vm: ComparatorContentVM):
    ui_vm = build_ui_vm(viewmode)
    base_vm = BaseVM(ui=ui_vm, content=content_vm)

    return render(
        request,
        "notas/comparators/detail.html",
        base_vm.as_context(),
    )
