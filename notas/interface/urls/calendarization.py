from django.urls import path

from notas.interface.views import calendarization, calendarization_review

urlpatterns = [
    path("calendar/preview/", calendarization.calendar_preview, name="calendar_preview"),
    path("calendar/days/<str:day_date>/", calendarization.calendar_date_detail, name="calendar_date_detail"),
    path("calendar/preview/action/", calendarization.calendar_preview_action, name="calendar_preview_action"),
    path("calendar/commitments/foods/", calendarization.calendar_commitment_foods, name="calendar_commitment_foods"),
    path("calendar/commitments/<str:kind>/", calendarization.calendar_commitments, name="calendar_commitments"),
    path("calendarization/", calendarization.dashboard, name="calendarization_dashboard"),
    path("calendarization/review/", calendarization_review.review_detail, name="calendarization_review"),
    path("calendarization/reviews/create/", calendarization_review.review_create, name="calendarization_review_create"),
    path("calendarization/revisions/<int:revision_id>/decision/", calendarization_review.revision_decide, name="calendarization_revision_decide"),
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
    path("calendarization/days/<int:day_id>/supplement-intakes/from-preset/", calendarization.supplement_intake_from_preset, name="calendarization_supplement_intake_from_preset"),
    path("calendarization/days/<int:day_id>/supplement-intakes/<str:intake_key>/check-in/", calendarization.supplement_intake_check_in, name="calendarization_supplement_intake_check_in"),
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
    path("calendarization/days/<int:day_id>/meals/<str:meal_snapshot_key>/preparations/", calendarization.calendarized_preparation_save, name="calendarized_preparation_add"),
    path("calendarization/days/<int:day_id>/meals/<str:meal_snapshot_key>/preparations/<str:component_snapshot_key>/save/", calendarization.calendarized_preparation_save, name="calendarized_preparation_save"),
    path("calendarization/days/<int:day_id>/meals/<str:meal_snapshot_key>/preparations/<str:component_snapshot_key>/remove/", calendarization.calendarized_preparation_remove, name="calendarized_preparation_remove"),
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
