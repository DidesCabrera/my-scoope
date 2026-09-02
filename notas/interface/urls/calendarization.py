from django.urls import path

from notas.interface.views import calendarization

urlpatterns = [
    path("calendarization/", calendarization.dashboard, name="calendarization_dashboard"),
    path("calendarization/history/", calendarization.history, name="calendarization_history"),
    path("calendarization/activate/", calendarization.activate, name="calendarization_activate"),
    path("calendarization/<int:calendarization_id>/pause/", calendarization.pause, name="calendarization_pause"),
    path("calendarization/<int:calendarization_id>/resume/", calendarization.resume, name="calendarization_resume"),
    path("calendarization/<int:calendarization_id>/cancel/", calendarization.cancel, name="calendarization_cancel"),
    path(
        "calendarization/<int:calendarization_id>/preferences/",
        calendarization.preferences,
        name="calendarization_preferences",
    ),
    path("calendarization/days/<int:day_id>/", calendarization.day_detail, name="calendarization_day_detail"),
    path(
        "calendarization/days/<int:day_id>/rename/",
        calendarization.day_rename,
        name="calendarization_day_rename",
    ),
    path(
        "calendarization/days/<int:day_id>/meals/<str:meal_snapshot_key>/",
        calendarization.meal_detail,
        name="calendarization_meal_detail",
    ),
    path(
        "calendarization/days/<int:day_id>/meals/<str:meal_snapshot_key>/check-in/",
        calendarization.meal_check_in,
        name="calendarization_meal_check_in",
    ),
    path(
        "calendarization/days/<int:day_id>/meals/<str:meal_snapshot_key>/change-time/",
        calendarization.meal_change_time,
        name="calendarization_meal_change_time",
    ),
    path(
        "calendarization/days/<int:day_id>/meals/<str:meal_snapshot_key>/rename/",
        calendarization.meal_rename,
        name="calendarization_meal_rename",
    ),
    path("calendarization/push/subscriptions/", calendarization.push_subscribe, name="calendarization_push_subscribe"),
    path(
        "calendarization/push/subscriptions/deactivate/",
        calendarization.push_unsubscribe,
        name="calendarization_push_unsubscribe",
    ),
]
