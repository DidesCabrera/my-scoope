from django.urls import path

from notas.interface.views.inbox import (
    inbox_attachment_detail,
    inbox_sent_attachment_detail,
    inbox_bulk_delete,
    inbox_delete,
    inbox_detail,
    inbox_sent_detail,
    inbox_list,
    inbox_save_attachment,
    inbox_toggle_favorite,
)
from notas.interface.views.project import project_view

urlpatterns = [
    path("inbox/", inbox_list, name="inbox_list"),
    path("inbox/bulk-delete/", inbox_bulk_delete, name="inbox_bulk_delete"),
    path("inbox/<str:kind>/<int:share_id>/", inbox_detail, name="inbox_detail"),
    path("inbox/<str:kind>/<int:share_id>/attachment/", inbox_attachment_detail, name="inbox_attachment_detail"),
    path("inbox/sent/<str:kind>/<int:share_id>/", inbox_sent_detail, name="inbox_sent_detail"),
    path("inbox/sent/<str:kind>/<int:share_id>/attachment/", inbox_sent_attachment_detail, name="inbox_sent_attachment_detail"),
    path("inbox/<str:kind>/<int:share_id>/delete/", inbox_delete, name="inbox_delete"),
    path("inbox/<str:kind>/<int:share_id>/favorite/", inbox_toggle_favorite, name="inbox_toggle_favorite"),
    path("inbox/<str:kind>/<int:share_id>/save/", inbox_save_attachment, name="inbox_save_attachment"),
    path("project/", project_view, name="project_view"),
]
