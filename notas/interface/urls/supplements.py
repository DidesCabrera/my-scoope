from django.urls import path

from notas.interface.views import supplements

urlpatterns = [
    path("supplements/", supplements.supplement_list, name="supplement_list"),
    path("supplements/create/", supplements.supplement_save, name="supplement_create"),
    path("supplements/catalog/<int:pk>/save/", supplements.supplement_catalog_save, name="supplement_catalog_save"),
    path("supplements/presets/create/", supplements.supplement_preset_save, name="supplement_preset_create"),
    path("supplements/presets/<int:pk>/save/", supplements.supplement_preset_save, name="supplement_preset_save"),
    path("supplements/presets/<int:pk>/remove/", supplements.supplement_preset_remove, name="supplement_preset_remove"),
    path("supplements/presets/<int:pk>/", supplements.supplement_preset_detail, name="supplement_preset_detail"),
    path("supplements/presets/<int:pk>/edit/", supplements.supplement_preset_edit, name="supplement_preset_edit"),
    path("supplements/<int:pk>/", supplements.supplement_detail, name="supplement_detail"),
    path("supplements/<int:pk>/edit/", supplements.supplement_edit, name="supplement_edit"),
    path("supplements/<int:pk>/save/", supplements.supplement_save, name="supplement_save"),
    path("supplements/<int:pk>/remove/", supplements.supplement_remove, name="supplement_remove"),
    path("dailyplans/<int:plan_id>/supplement-intakes/", supplements.dailyplan_intake_add, name="dailyplan_intake_add"),
    path("dailyplans/<int:plan_id>/supplement-intakes/<int:intake_id>/remove/", supplements.dailyplan_intake_remove, name="dailyplan_intake_remove"),
    path("dailyplans/<int:plan_id>/supplement-intakes/<int:intake_id>/save/", supplements.dailyplan_intake_update, name="dailyplan_intake_update"),
]
