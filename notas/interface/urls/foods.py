from django.urls import path

from notas.interface.views.foods import (
    download_food_template,
    food_create,
    food_delete,
    food_detail,
    food_edit,
    food_list,
    food_list_bulk_delete,
    food_list_reorder,
    food_share,
    food_share_accept,
    foods_json,
    import_foods,
)

urlpatterns = [
    path("foods/import/", import_foods, name="import_foods"),
    path("foods/template/", download_food_template, name="download_food_template"),
    path("foods/", food_list, name="food_list"),
    path("foods/reorder/", food_list_reorder, name="food_list_reorder"),
    path("foods/bulk-delete/", food_list_bulk_delete, name="food_list_bulk_delete"),
    path("foods/<int:pk>/share/", food_share, name="food_share"),
    path("foods/shared/<uuid:token>/", food_share_accept, name="food_share_accept"),
    path("foods/<int:pk>/", food_detail, name="food_detail"),
    path("foods/create/", food_create, name="food_create"),
    path("foods/<int:pk>/edit/", food_edit, name="food_edit"),
    path("foods/<int:pk>/delete/", food_delete, name="food_delete"),
    path("api/foods/", foods_json, name="foods_json"),
]
