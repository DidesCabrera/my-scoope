from django.urls import path

from notas.interface.views import preparations

urlpatterns = [
    path("preparations/", preparations.preparation_list, name="preparation_list"),
    path("preparations/create/", preparations.preparation_create, name="preparation_create"),
    path("preparations/<int:pk>/", preparations.preparation_detail, name="preparation_detail"),
    path("preparations/<int:pk>/edit/", preparations.preparation_edit, name="preparation_edit"),
    path("meals/<int:meal_id>/preparations/", preparations.meal_preparation_add, name="meal_preparation_add"),
    path("meals/<int:meal_id>/preparations/<int:relation_id>/save/", preparations.meal_preparation_update, name="meal_preparation_update"),
    path("meals/<int:meal_id>/preparations/<int:relation_id>/remove/", preparations.meal_preparation_remove, name="meal_preparation_remove"),
]
