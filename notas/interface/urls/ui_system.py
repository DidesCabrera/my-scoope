from django.urls import path

from notas.interface.views.ui_system import ui_system_auth_preview, ui_system_gallery

urlpatterns = [
    path("dev/ui-system/", ui_system_gallery, name="ui_system_gallery"),
    path(
        "dev/ui-system/auth/<slug:screen>/",
        ui_system_auth_preview,
        name="ui_system_auth_preview",
    ),
]
