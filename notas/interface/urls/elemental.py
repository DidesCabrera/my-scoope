from django.urls import path

from notas.interface.views.nutrition import elemental_context, elemental_nutrition, elemental_platform

urlpatterns = [
    path("elemental/context/", elemental_context, name="elemental_context"),
    path("elemental/nutrition/", elemental_nutrition, name="elemental_nutrition"),
    path("elemental/platform/", elemental_platform, name="elemental_platform"),
]
