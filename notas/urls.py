from django.urls import include, path

from notas.interface.views.home import (
    home_create_pinned_dailyplan,
    home_pin_dailyplan,
    home_pinned_meal_check_in,
    home_pinned_supplement_check_in,
    home_unpin_dailyplan,
    home_view,
)

urlpatterns = [
    path("", home_view, name="home_view"),
    path("today/pinned-plan/create/", home_create_pinned_dailyplan, name="home_create_pinned_dailyplan"),
    path("today/pinned-plan/pin/", home_pin_dailyplan, name="home_pin_dailyplan"),
    path("today/pinned-plan/unpin/", home_unpin_dailyplan, name="home_unpin_dailyplan"),
    path("today/pinned-plan/meals/<int:relation_id>/check-in/", home_pinned_meal_check_in, name="home_pinned_meal_check_in"),
    path("today/pinned-plan/supplements/<int:intake_id>/check-in/", home_pinned_supplement_check_in, name="home_pinned_supplement_check_in"),
    path("", include("notas.interface.urls.pwa")),
    path("", include("notas.interface.urls.inbox")),
    path("", include("notas.interface.urls.notifications")),
    path("", include("notas.interface.urls.ai_intake")),
    path("", include("notas.interface.urls.comparators")),
    path("", include("notas.interface.urls.elemental")),
    path("", include("notas.interface.urls.dailyplans")),
    path("", include("notas.interface.urls.meals")),
    path("", include("notas.interface.urls.preparations")),
    path("", include("notas.interface.urls.supplements")),
    path("", include("notas.interface.urls.foods")),
    path("", include("notas.interface.urls.programs")),
    path("", include("notas.interface.urls.calendarization")),
    path("", include("notas.interface.urls.profiles")),
    path("", include("notas.interface.urls.learning")),
    path("", include("notas.interface.urls.admin_tools")),
    path("", include("notas.interface.urls.proposals")),
    path("", include("notas.interface.urls.ai_tools")),
    path("", include("notas.interface.urls.ui_system")),
]
