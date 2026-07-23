from django.urls import include, path

from notas.interface.views.home import home_view

urlpatterns = [
    path("", home_view, name="home_view"),
    path("", include("notas.interface.urls.pwa")),
    path("", include("notas.interface.urls.inbox")),
    path("", include("notas.interface.urls.ai_intake")),
    path("", include("notas.interface.urls.comparators")),
    path("", include("notas.interface.urls.elemental")),
    path("", include("notas.interface.urls.dailyplans")),
    path("", include("notas.interface.urls.meals")),
    path("", include("notas.interface.urls.foods")),
    path("", include("notas.interface.urls.programs")),
    path("", include("notas.interface.urls.calendarization")),
    path("", include("notas.interface.urls.profiles")),
    path("", include("notas.interface.urls.admin_tools")),
    path("", include("notas.interface.urls.proposals")),
    path("", include("notas.interface.urls.ai_tools")),
]
