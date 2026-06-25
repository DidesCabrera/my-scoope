from typing import Any

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.utils.http import url_has_allowed_host_and_scheme

from notas.application.services.commands.saved_comparison_commands import (
    SavedComparisonCommandError,
    create_saved_comparison,
    rename_saved_comparison,
    update_saved_comparison,
)
from notas.application.services.comparisons.constants import MIN_COMPARATOR_SLOTS
from notas.application.services.comparisons.nutrition import (
    comparable_rows as _comparable_rows,
    entity_values as _entity_values,
    food_values as _food_values,
)
from notas.application.services.comparisons.payloads import (
    normalize_payload as _normalize_payload,
    selected_payload_from_selections as _selected_payload_from_selections,
    selection_rows_from_payload as _selection_rows_from_payload,
)
from notas.application.services.comparisons.snapshots import (
    comparable_rows_from_snapshot as _comparable_rows_from_snapshot,
    normalize_snapshot_payload as _normalize_snapshot_payload,
    selection_rows_from_snapshot as _selection_rows_from_snapshot,
)
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
from notas.presentation.viewmodels.comparators import (
    ComparatorContentVM,
    ComparatorSelection,
    SavedComparisonCard,
    SavedComparisonsContentVM,
    build_metrics as _build_metrics,
    build_selections_from_params as _build_selections_from_params,
    build_tabs as _build_tabs,
    choices_from_queryset as _choices_from_queryset,
    format_number as _format_number,
    items_by_id as _items_by_id,
)


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


def _redirect_with_params(request, fallback_url: str):
    querydict = request.POST.copy()
    for key in ("csrfmiddlewaretoken", "comparator_action"):
        querydict.pop(key, None)

    query_string = querydict.urlencode()
    if query_string:
        return redirect(f"{fallback_url}?{query_string}")

    return redirect(fallback_url)


def _save_new_comparison(
    request,
    kind: str,
    selections: list[ComparatorSelection],
    comparable_rows,
    *,
    include_quantities: bool,
):
    try:
        result = create_saved_comparison(
            owner=request.user,
            kind=kind,
            entity_plural_label=_get_kind_config(kind)["entity_plural_label"],
            selections=selections,
            comparable_rows=comparable_rows,
            include_quantities=include_quantities,
        )
    except SavedComparisonCommandError:
        messages.error(request, "Selecciona al menos dos elementos antes de guardar la comparación.")
        return _redirect_with_params(request, request.path)

    messages.success(request, "Comparación guardada.")

    return redirect("saved_comparison_detail", kind=kind, pk=result.comparison.pk)


def _update_saved_comparison(
    request,
    comparison: SavedComparison,
    selections: list[ComparatorSelection],
    comparable_rows,
    *,
    include_quantities: bool,
):
    try:
        update_saved_comparison(
            comparison=comparison,
            selections=selections,
            comparable_rows=comparable_rows,
            include_quantities=include_quantities,
        )
    except SavedComparisonCommandError:
        messages.error(request, "Mantén al menos dos elementos para guardar los cambios.")
        return _redirect_with_params(
            request,
            reverse("saved_comparison_detail", kwargs={"kind": comparison.kind, "pk": comparison.pk}),
        )

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
    params = request.POST if request.method == "POST" else request.GET
    is_saved_edit_mode = bool(saved_comparison and params.get("edit") == "1")
    default_rows = None

    if saved_comparison:
        if not is_saved_edit_mode and saved_comparison.snapshot_payload:
            default_rows = _selection_rows_from_snapshot(
                saved_comparison.snapshot_payload,
                include_quantities=include_quantities,
            )
        else:
            default_rows = _selection_rows_from_payload(
                saved_comparison.payload,
                include_quantities=include_quantities,
            )

    selections = _build_selections_from_params(
        params,
        items_by_id=items_by_id,
        include_quantities=include_quantities,
        default_rows=default_rows,
    )

    comparable_rows_current = _build_comparable_rows_for_kind(kind, selections, items_by_id, request.user)

    if request.method == "POST":
        action = request.POST.get("comparator_action")
        if action == "save_comparison" and not saved_comparison:
            return _save_new_comparison(
                request,
                kind,
                selections,
                comparable_rows_current,
                include_quantities=include_quantities,
            )
        if action == "save_changes" and saved_comparison:
            return _update_saved_comparison(
                request,
                saved_comparison,
                selections,
                comparable_rows_current,
                include_quantities=include_quantities,
            )

    comparable_rows = comparable_rows_current
    if saved_comparison and not is_saved_edit_mode and saved_comparison.snapshot_payload:
        snapshot_rows = _comparable_rows_from_snapshot(
            saved_comparison.snapshot_payload,
            include_quantities=include_quantities,
        )
        if len(snapshot_rows) >= MIN_COMPARATOR_SLOTS:
            comparable_rows = snapshot_rows

    metrics = (
        _build_metrics(comparable_rows, include_ppk=config["include_ppk"])
        if len(comparable_rows) >= MIN_COMPARATOR_SLOTS
        else []
    )
    current_payload = _selected_payload_from_selections(selections, include_quantities=include_quantities)
    saved_payload = _normalize_payload(saved_comparison.payload, include_quantities=include_quantities) if saved_comparison else []

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
    snapshot_rows = _normalize_snapshot_payload(
        comparison.snapshot_payload,
        include_quantities=include_quantities,
    )
    rows = snapshot_rows or _normalize_payload(comparison.payload, include_quantities=include_quantities)

    for row in rows[:4]:
        item = items_by_id.get(row.get("id"))
        name = row.get("name") or (item.name if item else "")
        if not name:
            continue

        if include_quantities:
            pieces.append(f"{name} ({_format_number(row.get('quantity') or 100, 0)} g)")
        else:
            pieces.append(name)

    if not pieces:
        return "Sin elementos disponibles"

    suffix = f" + {len(rows) - 4}" if len(rows) > 4 else ""
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

        try:
            rename_saved_comparison(comparison=saved_comparison, name=name)
        except SavedComparisonCommandError:
            messages.error(request, "El nombre no puede estar vacío.")
            rename_url = reverse(
                "saved_comparison_rename",
                kwargs={"kind": kind, "pk": saved_comparison.pk},
            )
            if return_to:
                rename_url = f"{rename_url}?return_to={return_to}"
            return redirect(rename_url)

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
