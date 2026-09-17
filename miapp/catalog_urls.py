from django.contrib import admin
from django.urls import path

from food_catalog.interface.views import (
    catalog_healthz,
    catalog_service_info,
    export_authority_snapshot,
    export_catalog_release,
)

urlpatterns = [
    path("", catalog_service_info, name="catalog_service_info"),
    path("healthz/", catalog_healthz, name="catalog_healthz"),
    path("admin/", admin.site.urls),
    path(
        "internal/authority-snapshot/export/",
        export_authority_snapshot,
        name="catalog_authority_snapshot_export",
    ),
    path(
        "internal/releases/<str:version>/export/",
        export_catalog_release,
        name="catalog_release_export",
    ),
]
