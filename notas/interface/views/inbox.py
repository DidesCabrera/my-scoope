from dataclasses import asdict, dataclass

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseBadRequest
from django.shortcuts import redirect, render
from django.urls import reverse
from django.views.decorators.http import require_POST

from notas.application.services.commands.dailyplan_commands import save_dailyplan
from notas.application.services.commands.food_commands import create_food
from notas.application.services.commands.meal_commands import save_dailyplan_meal_to_library, save_meal
from notas.presentation.composition.viewmodel.components.builder_headers import (
    build_page_header,
)
from notas.presentation.composition.viewmodel.dailyplan.detail_dailyplan_builder import (
    build_dailyplan_detail_vm,
)
from notas.presentation.composition.viewmodel.dpm.detail_dpm_builder import (
    build_dpm_detail_vm,
)
from notas.presentation.composition.viewmodel.food.detail_food_builder import (
    build_food_detail_vm,
)
from notas.presentation.composition.viewmodel.meal.detail_meal_builder import (
    build_meal_detail_vm,
)
from notas.presentation.composition.viewmodel.ui_builder import build_ui_vm
from notas.presentation.config.viewmodel_config import (
    DAILYPLAN_MEAL_VIEWMODE_DETAIL,
    DAILYPLAN_VIEWMODE_SHARED_DETAIL,
    FOOD_VIEWMODE_PERSONAL_DETAIL,
    INBOX_VIEWMODE_DETAIL,
    INBOX_VIEWMODE_LIST,
    MEAL_VIEWMODE_SHARED_DETAIL,
)
from notas.presentation.pages.dailyplan_pages import get_dailyplan_detail_page_data
from notas.presentation.pages.dpm_pages import get_dpm_detail_page_data
from notas.presentation.pages.inbox_pages import (
    build_inbox_items,
    get_inbox_item_or_404,
    get_inbox_share_or_404,
    get_sent_inbox_item_or_404,
    get_sent_inbox_share_or_404,
)
from notas.presentation.pages.meal_pages import get_meal_detail_page_data
from notas.presentation.viewmodels.base_vm import BaseVM


@dataclass
class InboxListContentVM:
    header: object
    inbox_items: list[dict]
    list_mode: str = "list"
    favorites_only: bool = False
    scope: str = "received"


@dataclass
class InboxDetailContentVM:
    header: object
    inbox: dict


@dataclass(frozen=True)
class BreadcrumbParent:
    label: str
    url: str

    def __str__(self):
        return self.label

    def get_absolute_url(self):
        return self.url


def _normalize_inbox_scope(request):
    scope = (request.GET.get("scope") or "received").strip()
    return scope if scope in {"received", "sent"} else "received"


def _normalize_inbox_list_mode(request, *, scope: str = "received"):
    mode = (request.GET.get("mode") or "list").strip()
    if scope == "sent":
        return "list"
    return mode if mode in {"list", "delete"} else "list"


def _get_favorites_only(request) -> bool:
    value = (request.GET.get("favorites") or request.POST.get("favorites") or "").strip()
    return value in {"1", "true", "yes"}


def _inbox_list_url(*, mode: str | None = None, favorites_only: bool = False, scope: str = "received"):
    base_url = reverse("inbox_list")
    params = []

    if scope == "sent":
        params.append("scope=sent")

    if mode and mode != "list" and scope != "sent":
        params.append(f"mode={mode}")

    if favorites_only and scope != "sent":
        params.append("favorites=1")

    if not params:
        return base_url

    return f"{base_url}?{'&'.join(params)}"


def _build_inbox_scope_actions(*, scope: str):
    return [
        {
            "key": "received",
            "label": "Recibidos",
            "url": _inbox_list_url(),
            "method": "get",
            "icon": "inbox",
            "order": 10,
            "desktop_position": "menu",
            "mobile_position": "menu",
            "extra_class": "is-active" if scope == "received" else "",
        },
        {
            "key": "sent",
            "label": "Enviados",
            "url": _inbox_list_url(scope="sent"),
            "method": "get",
            "icon": "send",
            "order": 40,
            "desktop_position": "menu",
            "mobile_position": "menu",
            "extra_class": "is-active" if scope == "sent" else "",
        },
    ]


def _build_inbox_list_actions(*, list_mode: str, favorites_only: bool, scope: str):
    if scope == "sent":
        return _build_inbox_scope_actions(scope=scope)

    if list_mode == "delete":
        return [
            {
                "key": "exit_delete_mode",
                "label": "Cerrar",
                "url": _inbox_list_url(favorites_only=favorites_only, scope=scope),
                "method": "get",
                "icon": "check",
                "order": 10,
                "desktop_position": "inline",
                "mobile_position": "inline",
            },
            {
                "key": "bulk_delete",
                "label": "Eliminar seleccionados",
                "url": (
                    reverse("inbox_bulk_delete")
                    + ("?favorites=1" if favorites_only else "")
                ),
                "method": "post",
                "icon": "trash-2",
                "order": 20,
                "desktop_position": "inline",
                "mobile_position": "inline",
                "disabled": True,
                "extra_class": "js-list-bulk-delete-submit",
            },
        ]

    filter_action = (
        {
            "key": "show_all",
            "label": "Mostrar todos",
            "url": _inbox_list_url(scope="received"),
            "method": "get",
            "icon": "list",
            "order": 30,
            "desktop_position": "menu",
            "mobile_position": "menu",
            "extra_class": "is-active",
        }
        if favorites_only
        else {
            "key": "show_favorites",
            "label": "Mostrar favoritos",
            "url": _inbox_list_url(favorites_only=True, scope=scope),
            "method": "get",
            "icon": "star",
            "order": 30,
            "desktop_position": "menu",
            "mobile_position": "menu",
        }
    )

    return [
        *_build_inbox_scope_actions(scope=scope),
        {
            "key": "enter_delete_mode",
            "label": "Eliminar Inbox",
            "url": _inbox_list_url(mode="delete", favorites_only=favorites_only, scope=scope),
            "method": "get",
            "icon": "trash-2",
            "order": 20,
            "desktop_position": "menu",
            "mobile_position": "menu",
        },
        filter_action,
    ]


def _build_inbox_detail_actions(inbox: dict):
    return [
        {
            "key": "favorite",
            "label": "Quitar favorito" if inbox["is_favorite"] else "Marcar como favorito",
            "url": inbox["favorite_url"],
            "method": "post",
            "icon": "star",
            "order": 10,
            "desktop_position": "inline",
            "mobile_position": "inline",
            "extra_class": "is-active" if inbox["is_favorite"] else "",
        },
        {
            "key": "delete",
            "label": "Eliminar inbox",
            "url": inbox["dismiss_url"],
            "method": "post",
            "icon": "trash-2",
            "order": 20,
            "desktop_position": "menu",
            "mobile_position": "menu",
        },
    ]


def _inbox_parent():
    return BreadcrumbParent(
        label="Inbox",
        url=reverse("inbox_list"),
    )


def _inbox_detail_parent(inbox: dict):
    return BreadcrumbParent(
        label=inbox["title"],
        url=reverse("inbox_detail", args=[inbox["kind"], inbox["share_id"]]),
    )


def _inbox_sent_detail_parent(inbox: dict):
    return BreadcrumbParent(
        label=inbox["title"],
        url=reverse("inbox_sent_detail", args=[inbox["kind"], inbox["share_id"]]),
    )


def _inbox_entity_nav_root(kind: str) -> str:
    if kind == "dpm":
        return "meal"
    return kind


def _mark_share_as_read(share):
    if not hasattr(share, "is_read"):
        return

    if share.is_read:
        return

    share.is_read = True
    share.save(update_fields=["is_read"])


def _build_inbox_entity_ui(*, inbox: dict, instance):
    parents = (
        [
            BreadcrumbParent(label="Enviados", url=_inbox_list_url(scope="sent")),
            _inbox_sent_detail_parent(inbox),
        ]
        if inbox.get("direction") == "sent"
        else [_inbox_detail_parent(inbox)]
    )
    ui_vm = build_ui_vm(
        INBOX_VIEWMODE_DETAIL,
        parents=parents,
        instance=instance,
        back_config={"type": "parent"},
    )
    ui_vm.icon = inbox["attachment"]["icon"]
    ui_vm.page_icon = inbox["attachment"]["icon"]
    ui_vm.nav_root = _inbox_entity_nav_root(inbox["kind"])
    return ui_vm


@login_required
def inbox_list(request):
    scope = _normalize_inbox_scope(request)
    list_mode = _normalize_inbox_list_mode(request, scope=scope)
    favorites_only = _get_favorites_only(request) if scope == "received" else False
    items = [
        asdict(item)
        for item in build_inbox_items(
            request.user,
            favorites_only=favorites_only,
            scope=scope,
        )
    ]
    if scope == "received":
        request.session["inbox_notification_seen_count"] = sum(
            1 for item in items if not item.get("is_read")
        )

    content_vm = InboxListContentVM(
        header=build_page_header(
            title="Inbox",
            actions=_build_inbox_list_actions(
                list_mode=list_mode,
                favorites_only=favorites_only,
                scope=scope,
            ),
        ),
        inbox_items=items,
        list_mode=list_mode,
        favorites_only=favorites_only,
        scope=scope,
    )

    ui_vm = build_ui_vm(INBOX_VIEWMODE_LIST)

    base_vm = BaseVM(
        ui=ui_vm,
        content=content_vm,
    )

    return render(
        request,
        "notas/inbox/list.html",
        base_vm.as_context(),
    )


@login_required
def inbox_detail(request, kind, share_id):
    try:
        share = get_inbox_share_or_404(
            request.user,
            kind=kind,
            share_id=share_id,
        )
    except ValueError:
        return HttpResponseBadRequest("Tipo de inbox no soportado.")

    if not share.is_read:
        share.is_read = True
        share.save(update_fields=["is_read"])

    try:
        item = get_inbox_item_or_404(
            request.user,
            kind=kind,
            share_id=share_id,
        )
    except ValueError:
        return HttpResponseBadRequest("Tipo de inbox no soportado.")

    inbox = asdict(item)

    content_vm = InboxDetailContentVM(
        header=build_page_header(
            title=inbox["title"],
            actions=_build_inbox_detail_actions(inbox),
        ),
        inbox=inbox,
    )

    ui_vm = build_ui_vm(
        INBOX_VIEWMODE_DETAIL,
        instance=inbox["title"],
        back_config={"type": "nav_item"},
    )
    ui_vm.icon = inbox["attachment"]["icon"]

    base_vm = BaseVM(
        ui=ui_vm,
        content=content_vm,
    )

    return render(
        request,
        "notas/inbox/detail.html",
        base_vm.as_context(),
    )


@login_required
def inbox_sent_detail(request, kind, share_id):
    try:
        item = get_sent_inbox_item_or_404(
            request.user,
            kind=kind,
            share_id=share_id,
        )
    except ValueError:
        return HttpResponseBadRequest("Tipo de inbox no soportado.")

    inbox = asdict(item)

    content_vm = InboxDetailContentVM(
        header=build_page_header(
            title=inbox["title"],
            actions=[],
        ),
        inbox=inbox,
    )

    ui_vm = build_ui_vm(
        INBOX_VIEWMODE_DETAIL,
        parents=[BreadcrumbParent(label="Enviados", url=_inbox_list_url(scope="sent"))],
        instance=inbox["title"],
        back_config={"type": "parent"},
    )
    ui_vm.icon = inbox["attachment"]["icon"]

    base_vm = BaseVM(
        ui=ui_vm,
        content=content_vm,
    )

    return render(
        request,
        "notas/inbox/detail.html",
        base_vm.as_context(),
    )


@login_required
def inbox_sent_attachment_detail(request, kind, share_id):
    try:
        share = get_sent_inbox_share_or_404(
            request.user,
            kind=kind,
            share_id=share_id,
        )
    except ValueError:
        return HttpResponseBadRequest("Tipo de inbox no soportado.")

    try:
        item = get_sent_inbox_item_or_404(
            request.user,
            kind=kind,
            share_id=share_id,
        )
    except ValueError:
        return HttpResponseBadRequest("Tipo de inbox no soportado.")

    inbox = asdict(item)

    if kind == "dailyplan":
        page = get_dailyplan_detail_page_data(
            user=request.user,
            dailyplan_id=share.dailyplan_id,
            viewmode=DAILYPLAN_VIEWMODE_SHARED_DETAIL,
        )
        content_vm = build_dailyplan_detail_vm(page.detail_content_data)
        content_vm.header = build_page_header(title=page.dailyplan.name, actions=[])
        ui_vm = _build_inbox_entity_ui(inbox=inbox, instance=page.dailyplan)

        base_vm = BaseVM(ui=ui_vm, content=content_vm)
        return render(request, "notas/dailyplans/detail.html", base_vm.as_context())

    if kind == "meal":
        page = get_meal_detail_page_data(
            user=request.user,
            meal_id=share.meal_id,
            viewmode=MEAL_VIEWMODE_SHARED_DETAIL,
        )
        content_vm = build_meal_detail_vm(page.detail_content_data)
        content_vm.header = build_page_header(title=page.meal.name, actions=[])
        ui_vm = _build_inbox_entity_ui(inbox=inbox, instance=page.meal)

        base_vm = BaseVM(ui=ui_vm, content=content_vm)
        context = base_vm.as_context()
        context["show_return_to_dailyplan"] = False
        context["foods_json"] = "[]"
        context["food_picker_context"] = "{}"
        context["can_edit_foods"] = False
        context["editing_mealfood_id"] = None
        context["selected_food_id"] = None
        return render(request, "notas/meals/detail.html", context)

    if kind == "food":
        food = share.food
        content_vm = build_food_detail_vm(
            food,
            request.user,
            FOOD_VIEWMODE_PERSONAL_DETAIL,
        )
        content_vm.header = build_page_header(title=food.name, actions=[])
        ui_vm = _build_inbox_entity_ui(inbox=inbox, instance=food)

        base_vm = BaseVM(ui=ui_vm, content=content_vm)
        return render(request, "notas/foods/detail.html", base_vm.as_context())

    if kind == "dpm":
        dpm = share.dailyplan_meal
        page = get_dpm_detail_page_data(
            user=request.user,
            dailyplan_id=dpm.dailyplan_id,
            dpm_id=dpm.id,
            viewmode=DAILYPLAN_MEAL_VIEWMODE_DETAIL,
            request_get=request.GET,
        )
        content_vm = build_dpm_detail_vm(page.detail_content_data)
        content_vm.header = build_page_header(title=page.meal.name, actions=[])
        ui_vm = _build_inbox_entity_ui(inbox=inbox, instance=page.meal)

        base_vm = BaseVM(ui=ui_vm, content=content_vm)
        context = base_vm.as_context()
        context["foods_json"] = "[]"
        context["food_picker_json"] = "{}"
        context["can_edit_foods"] = False
        context["selected_food_id"] = None
        context["editing_mealfood_id"] = None
        return render(request, "notas/dailyplan_meals/detail.html", context)

    return HttpResponseBadRequest("Tipo de inbox no soportado.")


@login_required
def inbox_attachment_detail(request, kind, share_id):
    try:
        share = get_inbox_share_or_404(
            request.user,
            kind=kind,
            share_id=share_id,
        )
    except ValueError:
        return HttpResponseBadRequest("Tipo de inbox no soportado.")

    _mark_share_as_read(share)

    try:
        item = get_inbox_item_or_404(
            request.user,
            kind=kind,
            share_id=share_id,
        )
    except ValueError:
        return HttpResponseBadRequest("Tipo de inbox no soportado.")

    inbox = asdict(item)

    if kind == "dailyplan":
        page = get_dailyplan_detail_page_data(
            user=request.user,
            dailyplan_id=share.dailyplan_id,
            viewmode=DAILYPLAN_VIEWMODE_SHARED_DETAIL,
        )
        content_vm = build_dailyplan_detail_vm(page.detail_content_data)
        content_vm.header = build_page_header(title=page.dailyplan.name, actions=[])
        ui_vm = _build_inbox_entity_ui(inbox=inbox, instance=page.dailyplan)

        base_vm = BaseVM(ui=ui_vm, content=content_vm)
        return render(request, "notas/dailyplans/detail.html", base_vm.as_context())

    if kind == "meal":
        page = get_meal_detail_page_data(
            user=request.user,
            meal_id=share.meal_id,
            viewmode=MEAL_VIEWMODE_SHARED_DETAIL,
        )
        content_vm = build_meal_detail_vm(page.detail_content_data)
        content_vm.header = build_page_header(title=page.meal.name, actions=[])
        ui_vm = _build_inbox_entity_ui(inbox=inbox, instance=page.meal)

        base_vm = BaseVM(ui=ui_vm, content=content_vm)
        context = base_vm.as_context()
        context["show_return_to_dailyplan"] = False
        context["foods_json"] = "[]"
        context["food_picker_context"] = "{}"
        context["can_edit_foods"] = False
        context["editing_mealfood_id"] = None
        context["selected_food_id"] = None
        return render(request, "notas/meals/detail.html", context)

    if kind == "food":
        food = share.food
        content_vm = build_food_detail_vm(
            food,
            request.user,
            FOOD_VIEWMODE_PERSONAL_DETAIL,
        )
        content_vm.header = build_page_header(title=food.name, actions=[])
        ui_vm = _build_inbox_entity_ui(inbox=inbox, instance=food)

        base_vm = BaseVM(ui=ui_vm, content=content_vm)
        return render(request, "notas/foods/detail.html", base_vm.as_context())

    if kind == "dpm":
        dpm = share.dailyplan_meal
        page = get_dpm_detail_page_data(
            user=share.sender,
            dailyplan_id=dpm.dailyplan_id,
            dpm_id=dpm.id,
            viewmode=DAILYPLAN_MEAL_VIEWMODE_DETAIL,
            request_get=request.GET,
        )
        content_vm = build_dpm_detail_vm(page.detail_content_data)
        content_vm.header = build_page_header(title=page.meal.name, actions=[])
        ui_vm = _build_inbox_entity_ui(inbox=inbox, instance=page.meal)

        base_vm = BaseVM(ui=ui_vm, content=content_vm)
        context = base_vm.as_context()
        context["foods_json"] = "[]"
        context["food_picker_json"] = "{}"
        context["can_edit_foods"] = False
        context["selected_food_id"] = None
        context["editing_mealfood_id"] = None
        return render(request, "notas/dailyplan_meals/detail.html", context)

    return HttpResponseBadRequest("Tipo de inbox no soportado.")


@login_required
@require_POST
def inbox_toggle_favorite(request, kind, share_id):
    try:
        share = get_inbox_share_or_404(
            request.user,
            kind=kind,
            share_id=share_id,
        )
    except ValueError:
        return HttpResponseBadRequest("Tipo de inbox no soportado.")

    share.is_favorite = not share.is_favorite
    share.save(update_fields=["is_favorite"])

    return redirect(request.META.get("HTTP_REFERER") or reverse("inbox_list"))


@login_required
@require_POST
def inbox_delete(request, kind, share_id):
    try:
        share = get_inbox_share_or_404(
            request.user,
            kind=kind,
            share_id=share_id,
        )
    except ValueError:
        return HttpResponseBadRequest("Tipo de inbox no soportado.")

    share.dismissed = True
    share.save(update_fields=["dismissed"])

    messages.success(request, "Inbox eliminado.")
    return redirect("inbox_list")


@login_required
@require_POST
def inbox_bulk_delete(request):
    selected_ids = request.POST.getlist("selected_ids[]")

    if not selected_ids:
        messages.info(request, "No seleccionaste inbox para eliminar.")
        return redirect(_inbox_list_url(mode="delete", favorites_only=_get_favorites_only(request)))

    deleted_count = 0

    for item_id in selected_ids:
        try:
            kind, raw_share_id = item_id.split("-", 1)
            share_id = int(raw_share_id)
            share = get_inbox_share_or_404(
                request.user,
                kind=kind,
                share_id=share_id,
            )
        except (ValueError, TypeError):
            continue

        share.dismissed = True
        share.save(update_fields=["dismissed"])
        deleted_count += 1

    if deleted_count:
        messages.success(request, f"{deleted_count} inbox eliminado(s).")
    else:
        messages.info(request, "No se eliminaron inbox.")

    return redirect(_inbox_list_url(mode="delete", favorites_only=_get_favorites_only(request)))


@login_required
@require_POST
def inbox_save_attachment(request, kind, share_id):
    try:
        share = get_inbox_share_or_404(
            request.user,
            kind=kind,
            share_id=share_id,
        )
    except ValueError:
        return HttpResponseBadRequest("Tipo de inbox no soportado.")

    if kind == "dailyplan":
        saved = save_dailyplan(share.dailyplan, request.user)
        messages.success(request, "Plan diario guardado en Mi librería.")
        return redirect("dailyplan_detail", pk=saved.pk)

    if kind == "meal":
        saved = save_meal(share.meal, request.user)
        messages.success(request, "Comida guardada en Mi librería.")
        return redirect("meal_detail", pk=saved.pk)

    if kind == "food":
        result = create_food(
            user=request.user,
            name=share.food.name,
            protein=share.food.protein,
            carbs=share.food.carbs,
            fat=share.food.fat,
        )
        messages.success(request, "Alimento guardado en Mi librería.")
        return redirect("food_detail", pk=result.food.pk)

    if kind == "dpm":
        saved = save_dailyplan_meal_to_library(share.dailyplan_meal, request.user)
        messages.success(request, "Comida guardada en Mi librería.")
        return redirect("meal_detail", pk=saved.pk)

    return HttpResponseBadRequest("Tipo de inbox no soportado.")
