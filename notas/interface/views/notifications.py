from dataclasses import dataclass

from django.contrib.auth.decorators import login_required
from django.http import Http404
from django.shortcuts import redirect, render
from django.views.decorators.http import require_POST

from notas.application.services.notifications.center import list_notifications, mark_notification_read
from notas.presentation.composition.viewmodel.components.builder_headers import build_page_header
from notas.presentation.composition.viewmodel.ui_builder import build_ui_vm
from notas.presentation.config.viewmodel_config import HOME_VIEWMODE
from notas.presentation.notifications import present_notifications
from notas.presentation.viewmodels.base_vm import BaseVM


@dataclass
class NotificationContentVM:
    header: object
    items: list[dict]


@login_required
def notifications_list(request):
    ui = build_ui_vm(HOME_VIEWMODE)
    ui.icon = "bell"
    ui.nav_root = "notifications"
    ui.title = "Notificaciones"
    ui.breadcrumb = []
    for section in ui.sidebar_sections:
        for group in section["groups"]:
            group["is_active"] = False
            group["is_open"] = False
            for item in group["items"]:
                item["is_active"] = False
    vm = BaseVM(
        ui=ui,
        content=NotificationContentVM(
            header=build_page_header(title="Notificaciones"),
            items=present_notifications(list_notifications(request.user)),
        ),
    )
    return render(request, "notas/notifications/list.html", vm.as_context())


@login_required
@require_POST
def notification_read(request, kind, item_id):
    target = next((item for item in present_notifications(list_notifications(request.user)) if item["kind"] == kind and item["id"] == item_id), None)
    if target is None:
        raise Http404
    if not mark_notification_read(request.user, kind, item_id):
        raise Http404
    if kind == "announcement":
        return redirect("notifications_list")
    return redirect(target["web_url"])
