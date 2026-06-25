from dataclasses import dataclass, field
from typing import Any

from django.urls import reverse

from notas.application.services.comparisons.constants import MIN_COMPARATOR_SLOTS
from notas.application.services.comparisons.payloads import selection_rows_from_params


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


def format_number(value: float, decimals: int = 0) -> str:
    if value is None:
        value = 0

    if decimals == 0:
        return f"{value:.0f}"

    formatted = f"{value:.{decimals}f}"
    return formatted.rstrip("0").rstrip(".")


def format_selection_name(name: str, quantity: float | None = None) -> str:
    if not name:
        return ""

    if quantity is None:
        return name

    return f"{name} ({format_number(quantity, 0)}g)"


def format_metric_value(value: float, unit: str) -> str:
    if unit == "g/kg":
        decimals = 2
    elif unit in {"g", "%"}:
        decimals = 1
    else:
        decimals = 0

    return f"{format_number(value, decimals)} {unit}"


def metric_bar(
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
        formatted_value=format_metric_value(safe_value, unit),
        width=round(width, 2),
        label_suffix=label_suffix,
    )


def build_metric(
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
            metric_bar(
                selection.name,
                values.get(key, 0),
                unit,
                max_value,
                label_suffix=(
                    f"({format_number(selection.quantity, 0)}g)"
                    if selection.quantity is not None and selection.name
                    else ""
                ),
            )
            for selection, values in comparable_rows
        ],
    )


def build_metrics(
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
        build_metric(
            key=key,
            label=label,
            unit=unit,
            comparable_rows=comparable_rows,
        )
        for key, label, unit in metric_specs
    ]


def build_tabs(active_key: str, *, saved: bool = False) -> list[ComparatorTab]:
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


def choices_from_queryset(queryset) -> list[ComparatorChoice]:
    return [ComparatorChoice(id=item.id, name=item.name) for item in queryset]


def items_by_id(queryset) -> dict[int, Any]:
    return {item.id: item for item in queryset}


def build_selections_from_params(
    params,
    *,
    items_by_id: dict[int, Any],
    include_quantities: bool = False,
    default_rows: list[dict[str, Any]] | None = None,
) -> list[ComparatorSelection]:
    rows = selection_rows_from_params(
        params,
        include_quantities=include_quantities,
        default_rows=default_rows,
    )

    selections: list[ComparatorSelection] = []
    for index, row in enumerate(rows, start=1):
        selected_id = row.get("id")
        selected_item = items_by_id.get(selected_id) if selected_id else None
        name = selected_item.name if selected_item else (row.get("name") or "")
        quantity = row.get("quantity") if include_quantities else None
        selections.append(
            ComparatorSelection(
                id=selected_item.id if selected_item else selected_id,
                name=name,
                quantity=quantity,
                position=index,
                display_name=format_selection_name(name, quantity),
            )
        )

    return selections
