from django.urls import path

from notas.interface.views.admin_tools import (
    admin_home,
    admin_food_catalog,
    admin_foods_export_csv,
    admin_foods_template,
)

urlpatterns = [
    path("admin-tools/", admin_home, name="admin_home"),
    path("admin-tools/foods/", admin_food_catalog, name="admin_food_catalog"),
    path("admin-tools/foods/export/", admin_foods_export_csv, name="admin_foods_export_csv"),
    path("admin-tools/foods/template/", admin_foods_template, name="admin_foods_template"),
]
