from dataclasses import dataclass, field
from typing import Any

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.utils.http import url_has_allowed_host_and_scheme

from notas.application.services.nutrition.weight import get_current_weight
from notas.domain.models import DailyPlan, Food, Meal, SavedComparison
from notas.presentation.composition.viewmodel.components.builder_headers import build_page_header
from notas.presentation.composition.viewmodel.ui_builder import build_ui_vm
from notas.presentation.config.viewmodel_config import (
    COMPARATOR_VIEWMODE_DAILYPLANS,
    COMPARATOR_VIEWMODE_FOODS,
    COMPARATOR_VIEWMODE_MEALS,
)
from notas.presentation.viewmodels.base_vm import BaseVM


MIN_COMPARATOR_SLOTS = 2
COMPARATOR_KINDS = {
    "foods": {
        "entity_label": "alimento",
        "entity_plural_label": "alimentos",
        "selector_label": "Alimento",
        "entity_icon": "carrot",
        "entity_scope": "food",
        "add_action_label": "Agregar Alimento a la comparación",
        "empty_message": "Selecciona al menos dos alimentos y define sus porciones para ver la comparación.",
        "viewmode": COMPARATOR_VIEWMODE_FOODS,
        "comparator_url_name": "food_comparator",
        "include_quantities": True,
        "include_ppk": False,
    },
    "meals": {
        "entity_label": "comida",
        "entity_plural_label": "comidas",
        "selector_label": "Comida",
        "entity_icon": "utensils",
        "entity_scope": "meal",
        "add_action_label": "Agregar Comida a la comparación",
        "empty_message": "Selecciona al menos dos comidas para ver la comparación.",
        "viewmode": COMPARATOR_VIEWMODE_MEALS,
        "comparator_url_name": "meal_comparator",
        "include_quantities": False,
        "include_ppk": True,
    },
    "dailyplans": {
        "entity_label": "plan diario",
        "entity_plural_label": "planes diarios",
        "selector_label": "Plan",
        "entity_icon": "clipboard-list",
        "entity_scope": "dailyplan",
        "add_action_label": "Agregar Plan a la comparación",
        "empty_message": "Selecciona al menos dos planes diarios para ver la comparación.",
        "viewmode": COMPARATOR_VIEWMODE_DAILYPLANS,
        "comparator_url_name": "dailyplan_comparator",
        "include_quantities": False,
        "include_ppk": True,
    },
}


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
    display_name: str = ""

    @property
    def label(self) -> str:
        return f"Selector {self.position}"


@dataclass
class ComparatorMetricBar:
    label: str
    value: float
    formatted_value: str
    width: float
    label_suffix: str = ""


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
    header: Any | None = None
    show_quantity_inputs: bool = False
    quantity_unit: str = "g"
    choices: list[ComparatorChoice] = field(default_factory=list)
    selections: list[ComparatorSelection] = field(default_factory=list)
    metrics: list[ComparatorMetric] = field(default_factory=list)
    tabs: list[ComparatorTab] = field(default_factory=list)
    item_count: int = 0
    selected_count: int = 0
    is_ready: bool = False
    empty_message: str = "Selecciona al menos dos elementos para compararlos."
    is_saved_detail: bool = False
    is_saved_edit_mode: bool = False
    saved_comparison_id: int | None = None
    saved_comparison_name: str = ""
    has_unsaved_changes: bool = False

    @property
    def can_remove_selection(self) -> bool:
        return len(self.selections) > MIN_COMPARATOR_SLOTS

    @property
    def save_action_label(self) -> str:
        if self.is_saved_detail:
            return "Guardar cambios"
        return "Guardar comparacion"


@dataclass
class SavedComparisonCard:
    id: int
    title: str
    subtitle: str
    preview: str
    url: str
    icon: str
    entity_scope: str


@dataclass
class SavedComparisonsContentVM:
    entity_label: str
    entity_plural_label: str
    entity_icon: str
    entity_scope: str
    tabs: list[ComparatorTab] = field(default_factory=list)
    saved_comparisons: list[SavedComparisonCard] = field(default_factory=list)
    header: Any | None = None
    item_count: int = 0
    empty_message: str = "Todavía no tienes comparaciones guardadas para esta sección."


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


def _format_selection_name(name: str, quantity: float | None = None) -> str:
    if not name:
        return ""

    if quantity is None:
        return name

    return f"{name} ({_format_number(quantity, 0)}g)"


def _format_metric_value(value: float, unit: str) -> str:
    if unit == "g/kg":
        decimals = 2
    elif unit in {"g", "%"}:
        decimals = 1
    else:
        decimals = 0

    return f"{_format_number(value, decimals)} {unit}"


def _metric_bar(
    label: str,
    value: float,
    unit: str,
    max_value: float,
    *,
    label_suffix: str = "",
) -> ComparatorMetricBar:
    safe_value = max(float(value or 0), 0)
    width = 0

    if max_value > 0:
        width = max((safe_value / max_value) * 100, 4 if safe_value > 0 else 0)

    return ComparatorMetricBar(
        label=label,
        value=safe_value,
        formatted_value=_format_metric_value(safe_value, unit),
        width=round(width, 2),
        label_suffix=label_suffix,
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
            _metric_bar(
                selection.name,
                values.get(key, 0),
                unit,
                max_value,
                label_suffix=(
                    f"({_format_number(selection.quantity, 0)}g)"
                    if selection.quantity is not None and selection.name
                    else ""
                ),
            )
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


def _build_tabs(active_key: str, *, saved: bool = False) -> list[ComparatorTab]:
    specs = [
        ("foods", "Alimentos", "carrot", "food_comparator"),
        ("meals", "Comidas", "utensils", "meal_comparator"),
        ("dailyplans", "Planes", "clipboard-list", "dailyplan_comparator"),
    ]

    return [
        ComparatorTab(
            label=label,
            icon=icon,
            url=(reverse("saved_comparisons_list", kwargs={"kind": key}) if saved else reverse(url_name)),
            is_active=key == active_key,
        )
        for key, label, icon, url_name in specs
    ]


def _choices_from_queryset(queryset) -> list[ComparatorChoice]:
    return [ComparatorChoice(id=item.id, name=item.name) for item in queryset]


def _items_by_id(queryset) -> dict[int, Any]:
    return {item.id: item for item in queryset}


def _quantity_from_params(params, position: int, fallback: float = 100.0) -> float:
    value = params.get(f"qty_{position}")

    if value is None and position == 1:
        value = params.get("qty_a")
    elif value is None and position == 2:
        value = params.get("qty_b")

    return _parse_quantity(value, fallback=fallback)


def _normalize_payload(payload: Any, *, include_quantities: bool = False) -> list[dict[str, Any]]:
    if not isinstance(payload, list):
        return []

    normalized: list[dict[str, Any]] = []
    for row in payload:
        if not isinstance(row, dict):
            continue

        selected_id = _parse_int(row.get("id"))
        if not selected_id:
            continue

        normalized_row = {"id": selected_id}
        if include_quantities:
            normalized_row["quantity"] = _parse_quantity(row.get("quantity"), fallback=100.0)
        normalized.append(normalized_row)

    return normalized


def _selection_rows_from_payload(payload: Any, *, include_quantities: bool = False) -> list[dict[str, Any]]:
    rows = _normalize_payload(payload, include_quantities=include_quantities)

    while len(rows) < MIN_COMPARATOR_SLOTS:
        rows.append({"id": None, "quantity": 100.0 if include_quantities else None})

    return rows


def _selection_rows_from_params(
    params,
    *,
    include_quantities: bool = False,
    default_rows: list[dict[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    indexed_positions: list[int] = []

    for key in params.keys():
        if key.startswith("item_"):
            parsed = _parse_int(key.removeprefix("item_"))
            if parsed:
                indexed_positions.append(parsed)

    if indexed_positions:
        max_position = max(max(indexed_positions), MIN_COMPARATOR_SLOTS)
        rows = [
            {
                "id": _parse_int(params.get(f"item_{position}")),
                "quantity": _quantity_from_params(params, position) if include_quantities else None,
            }
            for position in range(1, max_position + 1)
        ]
    elif default_rows is not None:
        rows = [dict(row) for row in default_rows]
    else:
        rows = [
            {
                "id": _parse_int(params.get("a")),
                "quantity": _quantity_from_params(params, 1) if include_quantities else None,
            },
            {
                "id": _parse_int(params.get("b")),
                "quantity": _quantity_from_params(params, 2) if include_quantities else None,
            },
        ]

    remove_index = _parse_zero_based_index(params.get("remove_index"))

    if remove_index is not None and len(rows) > MIN_COMPARATOR_SLOTS:
        if remove_index < len(rows):
            rows.pop(remove_index)

    if params.get("comparator_action") == "add":
        rows.append({"id": None, "quantity": 100.0 if include_quantities else None})

    while len(rows) < MIN_COMPARATOR_SLOTS:
        rows.append({"id": None, "quantity": 100.0 if include_quantities else None})

    return rows


def _build_selections_from_params(
    params,
    *,
    items_by_id: dict[int, Any],
    include_quantities: bool = False,
    default_rows: list[dict[str, Any]] | None = None,
) -> list[ComparatorSelection]:
    rows = _selection_rows_from_params(
        params,
        include_quantities=include_quantities,
        default_rows=default_rows,
    )

    selections: list[ComparatorSelection] = []
    for index, row in enumerate(rows, start=1):
        selected_id = row.get("id")
        selected_item = items_by_id.get(selected_id) if selected_id else None
        name = selected_item.name if selected_item else ""
        quantity = row.get("quantity") if include_quantities else None
        selections.append(
            ComparatorSelection(
                id=selected_item.id if selected_item else selected_id,
                name=name,
                quantity=quantity,
                position=index,
                display_name=_format_selection_name(name, quantity),
            )
        )

    return selections


def _selected_payload_from_selections(
    selections: list[ComparatorSelection],
    *,
    include_quantities: bool = False,
) -> list[dict[str, Any]]:
    payload: list[dict[str, Any]] = []

    for selection in selections:
        if not selection.id:
            continue

        row = {"id": int(selection.id)}
        if include_quantities:
            row["quantity"] = float(selection.quantity or 100.0)
        payload.append(row)

    return payload


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


def _get_kind_config(kind: str) -> dict[str, Any]:
    config = COMPARATOR_KINDS.get(kind)
    if not config:
        raise Http404("Comparador no encontrado.")
    return config


def _build_comparator_header(kind: str, *, saved_comparison: SavedComparison | None = None):
    actions = [
        {
            "key": "saved_comparisons",
            "label": "Ver comparaciones guardadas",
            "method": "get",
            "icon": "pin",
            "order": 10,
            "desktop_position": "menu",
            "mobile_position": "menu",
            "url": reverse("saved_comparisons_list", kwargs={"kind": kind}),
        }
    ]

    if saved_comparison:
        actions.extend([
            {
                "key": "rename",
                "label": "Renombrar",
                "method": "get",
                "icon": "pencil",
                "order": 20,
                "desktop_position": "menu",
                "mobile_position": "menu",
                "url": reverse(
                    "saved_comparison_rename",
                    kwargs={"kind": kind, "pk": saved_comparison.pk},
                ),
            },
            {
                "key": "new_comparison",
                "label": "Nueva comparación",
                "method": "get",
                "icon": "columns-3",
                "order": 30,
                "desktop_position": "menu",
                "mobile_position": "menu",
                "url": reverse(COMPARATOR_KINDS[kind]["comparator_url_name"]),
            },
        ])

    return build_page_header(actions=actions)


def _build_saved_list_header(kind: str):
    return build_page_header(
        actions=[
            {
                "key": "new_comparison",
                "label": "Nueva comparación",
                "method": "get",
                "icon": "columns-3",
                "order": 10,
                "desktop_position": "menu",
                "mobile_position": "menu",
                "url": reverse(COMPARATOR_KINDS[kind]["comparator_url_name"]),
            }
        ]
    )


def _get_foods(user):
    return list(
        Food.objects
        .filter(
            created_by=user,
            is_active=True,
        )
        .order_by("list_order", "name", "id")
    )


def _get_meals(user):
    return list(
        Meal.objects
        .filter(
            created_by=user,
            is_draft=False,
            dailyplanmeal__isnull=True,
        )
        .order_by("list_order", "name", "id")
        .distinct()
    )


def _get_dailyplans(user):
    return list(
        DailyPlan.objects
        .filter(
            created_by=user,
            is_draft=False,
        )
        .exclude(source=DailyPlan.SOURCE_PROGRAM)
        .order_by("list_order", "name", "id")
    )


def _queryset_for_kind(kind: str, user):
    if kind == "foods":
        return _get_foods(user)
    if kind == "meals":
        return _get_meals(user)
    if kind == "dailyplans":
        return _get_dailyplans(user)
    raise Http404("Comparador no encontrado.")


def _build_comparable_rows_for_kind(kind: str, selections, items_by_id, user):
    if kind == "foods":
        return _comparable_rows(
            selections,
            items_by_id,
            lambda food, selection: _food_values(food, selection.quantity or 100.0),
        )

    current_weight = get_current_weight(user)
    return _comparable_rows(
        selections,
        items_by_id,
        lambda entity, selection: _entity_values(entity, current_weight=current_weight),
    )


def _build_saved_comparison_name(kind: str, selections: list[ComparatorSelection]) -> str:
    config = _get_kind_config(kind)
    selected_names = [selection.name for selection in selections if selection.id and selection.name]

    if not selected_names:
        timestamp = timezone.localtime().strftime("%d/%m/%Y %H:%M")
        return f"Comparación de {config['entity_plural_label']} · {timestamp}"

    visible_names = " vs ".join(selected_names[:2])
    extra_count = max(len(selected_names) - 2, 0)
    suffix = f" + {extra_count}" if extra_count else ""

    return f"{visible_names}{suffix}"


def _payload_has_enough_items(payload: list[dict[str, Any]]) -> bool:
    return len([row for row in payload if row.get("id")]) >= MIN_COMPARATOR_SLOTS


def _redirect_with_params(request, fallback_url: str):
    querydict = request.POST.copy()
    for key in ("csrfmiddlewaretoken", "comparator_action"):
        querydict.pop(key, None)

    query_string = querydict.urlencode()
    if query_string:
        return redirect(f"{fallback_url}?{query_string}")

    return redirect(fallback_url)


def _save_new_comparison(request, kind: str, selections: list[ComparatorSelection], *, include_quantities: bool):
    payload = _selected_payload_from_selections(selections, include_quantities=include_quantities)

    if not _payload_has_enough_items(payload):
        messages.error(request, "Selecciona al menos dos elementos antes de guardar la comparación.")
        return _redirect_with_params(request, request.path)

    comparison = SavedComparison.objects.create(
        owner=request.user,
        kind=kind,
        name=_build_saved_comparison_name(kind, selections),
        payload=payload,
    )
    messages.success(request, "Comparación guardada.")

    return redirect("saved_comparison_detail", kind=kind, pk=comparison.pk)


def _update_saved_comparison(request, comparison: SavedComparison, selections: list[ComparatorSelection], *, include_quantities: bool):
    payload = _selected_payload_from_selections(selections, include_quantities=include_quantities)

    if not _payload_has_enough_items(payload):
        messages.error(request, "Mantén al menos dos elementos para guardar los cambios.")
        return _redirect_with_params(
            request,
            reverse("saved_comparison_detail", kwargs={"kind": comparison.kind, "pk": comparison.pk}),
        )

    comparison.payload = payload
    comparison.save(update_fields=["payload", "updated_at"])
    messages.success(request, "Cambios guardados.")

    return redirect("saved_comparison_detail", kind=comparison.kind, pk=comparison.pk)


def _render_kind_comparator(
    request,
    *,
    kind: str,
    saved_comparison: SavedComparison | None = None,
):
    config = _get_kind_config(kind)
    include_quantities = config["include_quantities"]
    items = _queryset_for_kind(kind, request.user)
    items_by_id = _items_by_id(items)
    default_rows = None

    if saved_comparison:
        default_rows = _selection_rows_from_payload(
            saved_comparison.payload,
            include_quantities=include_quantities,
        )

    params = request.POST if request.method == "POST" else request.GET
    selections = _build_selections_from_params(
        params,
        items_by_id=items_by_id,
        include_quantities=include_quantities,
        default_rows=default_rows,
    )

    if request.method == "POST":
        action = request.POST.get("comparator_action")
        if action == "save_comparison" and not saved_comparison:
            return _save_new_comparison(
                request,
                kind,
                selections,
                include_quantities=include_quantities,
            )
        if action == "save_changes" and saved_comparison:
            return _update_saved_comparison(
                request,
                saved_comparison,
                selections,
                include_quantities=include_quantities,
            )

    comparable_rows = _build_comparable_rows_for_kind(kind, selections, items_by_id, request.user)
    metrics = (
        _build_metrics(comparable_rows, include_ppk=config["include_ppk"])
        if len(comparable_rows) >= MIN_COMPARATOR_SLOTS
        else []
    )
    current_payload = _selected_payload_from_selections(selections, include_quantities=include_quantities)
    saved_payload = _normalize_payload(saved_comparison.payload, include_quantities=include_quantities) if saved_comparison else []

    is_saved_edit_mode = bool(saved_comparison and params.get("edit") == "1")

    content_vm = ComparatorContentVM(
        entity_label=config["entity_label"],
        entity_plural_label=config["entity_plural_label"],
        entity_icon=config["entity_icon"],
        entity_scope=config["entity_scope"],
        selector_label=config["selector_label"],
        add_action_label=config["add_action_label"],
        header=_build_comparator_header(kind, saved_comparison=saved_comparison),
        show_quantity_inputs=include_quantities,
        choices=_choices_from_queryset(items),
        selections=selections,
        metrics=metrics,
        tabs=_build_tabs(kind),
        item_count=len(items),
        selected_count=len(current_payload),
        is_ready=bool(metrics),
        empty_message=config["empty_message"],
        is_saved_detail=bool(saved_comparison),
        is_saved_edit_mode=is_saved_edit_mode,
        saved_comparison_id=saved_comparison.id if saved_comparison else None,
        saved_comparison_name=saved_comparison.name if saved_comparison else "",
        has_unsaved_changes=bool(saved_comparison and current_payload != saved_payload),
    )

    return _render_comparator(
        request=request,
        viewmode=config["viewmode"],
        content_vm=content_vm,
        saved_comparison=saved_comparison,
    )


def _saved_comparison_preview(comparison: SavedComparison, items_by_id: dict[int, Any], *, include_quantities: bool) -> str:
    pieces: list[str] = []

    for row in _normalize_payload(comparison.payload, include_quantities=include_quantities)[:4]:
        item = items_by_id.get(row.get("id"))
        if not item:
            continue

        if include_quantities:
            pieces.append(f"{item.name} ({_format_number(row.get('quantity') or 100, 0)} g)")
        else:
            pieces.append(item.name)

    if not pieces:
        return "Sin elementos disponibles"

    total_items = len(_normalize_payload(comparison.payload, include_quantities=include_quantities))
    suffix = f" + {total_items - 4}" if total_items > 4 else ""
    return ", ".join(pieces) + suffix


def _build_saved_comparison_cards(kind: str, comparisons, user) -> list[SavedComparisonCard]:
    config = _get_kind_config(kind)
    items_by_id = _items_by_id(_queryset_for_kind(kind, user))
    cards: list[SavedComparisonCard] = []

    for comparison in comparisons:
        payload = _normalize_payload(comparison.payload, include_quantities=config["include_quantities"])
        updated_at = timezone.localtime(comparison.updated_at).strftime("%d/%m/%Y %H:%M")
        item_count = len(payload)
        cards.append(
            SavedComparisonCard(
                id=comparison.id,
                title=comparison.name,
                subtitle=f"{item_count} elementos · Actualizada {updated_at}",
                preview=_saved_comparison_preview(
                    comparison,
                    items_by_id,
                    include_quantities=config["include_quantities"],
                ),
                url=reverse("saved_comparison_detail", kwargs={"kind": kind, "pk": comparison.pk}),
                icon=config["entity_icon"],
                entity_scope=config["entity_scope"],
            )
        )

    return cards


@login_required
def comparator_index(request):
    return redirect("food_comparator")


@login_required
def food_comparator(request):
    return _render_kind_comparator(request, kind="foods")


@login_required
def meal_comparator(request):
    return _render_kind_comparator(request, kind="meals")


@login_required
def dailyplan_comparator(request):
    return _render_kind_comparator(request, kind="dailyplans")


@login_required
def saved_comparisons_index(request):
    return redirect("saved_comparisons_list", kind="foods")


@login_required
def saved_comparisons_list(request, kind: str):
    config = _get_kind_config(kind)
    comparisons = SavedComparison.objects.filter(
        owner=request.user,
        kind=kind,
    )
    cards = _build_saved_comparison_cards(kind, comparisons, request.user)

    content_vm = SavedComparisonsContentVM(
        entity_label=config["entity_label"],
        entity_plural_label=config["entity_plural_label"],
        entity_icon=config["entity_icon"],
        entity_scope=config["entity_scope"],
        tabs=_build_tabs(kind, saved=True),
        saved_comparisons=cards,
        header=_build_saved_list_header(kind),
        item_count=len(cards),
        empty_message=f"Todavía no tienes comparaciones guardadas de {config['entity_plural_label']}.",
    )

    ui_vm = build_ui_vm(config["viewmode"])
    ui_vm.title = "Comparaciones guardadas"
    ui_vm.page_icon = "pin"
    ui_vm.nav_root = config["entity_scope"]

    base_vm = BaseVM(ui=ui_vm, content=content_vm)

    return render(
        request,
        "notas/comparators/saved_list.html",
        base_vm.as_context(),
    )


@login_required
def saved_comparison_detail(request, kind: str, pk: int):
    _get_kind_config(kind)
    saved_comparison = get_object_or_404(
        SavedComparison,
        pk=pk,
        owner=request.user,
        kind=kind,
    )

    return _render_kind_comparator(
        request,
        kind=kind,
        saved_comparison=saved_comparison,
    )


@login_required
def saved_comparison_rename(request, kind: str, pk: int):
    config = _get_kind_config(kind)
    saved_comparison = get_object_or_404(
        SavedComparison,
        pk=pk,
        owner=request.user,
        kind=kind,
    )

    return_to = request.POST.get("return_to") or request.GET.get("return_to") or ""
    fallback_url = reverse(
        "saved_comparison_detail",
        kwargs={"kind": kind, "pk": saved_comparison.pk},
    )

    if return_to and not url_has_allowed_host_and_scheme(
        url=return_to,
        allowed_hosts={request.get_host()},
        require_https=request.is_secure(),
    ):
        return_to = ""

    redirect_url = return_to or fallback_url

    if request.method == "POST":
        name = request.POST.get("name", "").strip()

        if not name:
            messages.error(request, "El nombre no puede estar vacío.")
            rename_url = reverse(
                "saved_comparison_rename",
                kwargs={"kind": kind, "pk": saved_comparison.pk},
            )
            if return_to:
                rename_url = f"{rename_url}?return_to={return_to}"
            return redirect(rename_url)

        saved_comparison.name = name
        saved_comparison.save(update_fields=["name", "updated_at"])
        messages.success(request, "Nombre actualizado correctamente.")
        return redirect(redirect_url)

    ui_vm = build_ui_vm(config["viewmode"])
    ui_vm.mode = "detail"
    ui_vm.title = "Renombrar comparación"
    ui_vm.root = saved_comparison.name
    ui_vm.icon = "pin"
    ui_vm.page_icon = "pin"
    ui_vm.is_inside = True
    ui_vm.back_url = redirect_url

    content = {
        "header": build_page_header(
            actions=[
                {
                    "key": "back_detail",
                    "label": "Volver",
                    "method": "get",
                    "icon": "chevron-left",
                    "order": 10,
                    "is_back": True,
                    "desktop_position": "inline",
                    "mobile_position": "hidden",
                    "url": redirect_url,
                }
            ]
        ),
        "comparison": saved_comparison,
        "entity_icon": config["entity_icon"],
        "entity_scope": config["entity_scope"],
        "return_to": return_to,
        "fallback_url": fallback_url,
    }

    base_vm = BaseVM(ui=ui_vm, content=content)

    return render(
        request,
        "notas/comparators/rename.html",
        base_vm.as_context(),
    )


def _render_comparator(request, viewmode, content_vm: ComparatorContentVM, saved_comparison: SavedComparison | None = None):
    ui_vm = build_ui_vm(viewmode, instance=saved_comparison if saved_comparison else None)
    ui_vm.nav_root = content_vm.entity_scope

    if saved_comparison:
        ui_vm.mode = "detail"
        ui_vm.title = saved_comparison.name
        ui_vm.root = "Comparaciones guardadas"
        ui_vm.icon = "pin"
        ui_vm.page_icon = "pin"
        ui_vm.is_inside = True
        ui_vm.back_url = reverse("saved_comparisons_list", kwargs={"kind": saved_comparison.kind})

    base_vm = BaseVM(ui=ui_vm, content=content_vm)

    return render(
        request,
        "notas/comparators/detail.html",
        base_vm.as_context(),
    )
