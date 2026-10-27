from django.urls import path

from notas.interface.views.notifications import notification_read, notifications_list

urlpatterns = [
    path("notifications/", notifications_list, name="notifications_list"),
    path("notifications/<str:kind>/<int:item_id>/read/", notification_read, name="notification_read"),
]
