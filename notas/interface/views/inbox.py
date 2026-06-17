from dataclasses import asdict, dataclass

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseBadRequest
from django.shortcuts import redirect, render
from django.urls import reverse
from django.views.decorators.http import require_POST

from notas.application.services.commands.dailyplan_commands import save_dailyplan
from notas.application.services.commands.meal_commands import save_meal
from notas.application.use_cases.inbox_pages import (
    build_inbox_items,
    get_inbox_item_or_404,
    get_inbox_share_or_404,
)
from notas.presentation.composition.viewmodel.components.builder_headers import (
    build_page_header,
)
from notas.presentation.composition.viewmodel.ui_builder import build_ui_vm
from notas.presentation.config.viewmodel_config import (
    INBOX_VIEWMODE_DETAIL,
    INBOX_VIEWMODE_LIST,
)
from notas.presentation.viewmodels.base_vm import BaseVM


@dataclass
class InboxListContentVM:
    header: object
    inbox_items: list[dict]
    list_mode: str = "list"
    favorites_only: bool = False


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


def _normalize_inbox_list_mode(request):
    mode = (request.GET.get("mode") or "list").strip()
    return mode if mode in {"list", "delete"} else "list"


def _get_favorites_only(request) -> bool:
    value = (request.GET.get("favorites") or request.POST.get("favorites") or "").strip()
    return value in {"1", "true", "yes"}


def _inbox_list_url(*, mode: str | None = None, favorites_only: bool = False):
    base_url = reverse("inbox_list")
    params = []

    if mode and mode != "list":
        params.append(f"mode={mode}")

    if favorites_only:
        params.append("favorites=1")

    if not params:
        return base_url

    return f"{base_url}?{'&'.join(params)}"


def _build_inbox_list_actions(*, list_mode: str, favorites_only: bool):
    if list_mode == "delete":
        return [
            {
                "key": "exit_delete_mode",
                "label": "Cerrar",
                "url": _inbox_list_url(favorites_only=favorites_only),
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
            "url": reverse("inbox_list"),
            "method": "get",
            "icon": "list",
            "order": 20,
            "desktop_position": "menu",
            "mobile_position": "menu",
            "extra_class": "is-active",
        }
        if favorites_only
        else {
            "key": "show_favorites",
            "label": "Mostrar favoritos",
            "url": _inbox_list_url(favorites_only=True),
            "method": "get",
            "icon": "star",
            "order": 20,
            "desktop_position": "menu",
            "mobile_position": "menu",
        }
    )

    return [
        {
            "key": "enter_delete_mode",
            "label": "Eliminar Inbox",
            "url": _inbox_list_url(mode="delete", favorites_only=favorites_only),
            "method": "get",
            "icon": "trash-2",
            "order": 10,
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
        label="Compartir / Inbox",
        url=reverse("inbox_list"),
    )


@login_required
def inbox_list(request):
    list_mode = _normalize_inbox_list_mode(request)
    favorites_only = _get_favorites_only(request)
    items = [
        asdict(item)
        for item in build_inbox_items(
            request.user,
            favorites_only=favorites_only,
        )
    ]

    content_vm = InboxListContentVM(
        header=build_page_header(
            title="Compartir / Inbox",
            actions=_build_inbox_list_actions(
                list_mode=list_mode,
                favorites_only=favorites_only,
            ),
        ),
        inbox_items=items,
        list_mode=list_mode,
        favorites_only=favorites_only,
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
        parents=[_inbox_parent()],
        instance=inbox["title"],
        back_config={"type": "parent"},
    )

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

    return HttpResponseBadRequest("Tipo de inbox no soportado.")
