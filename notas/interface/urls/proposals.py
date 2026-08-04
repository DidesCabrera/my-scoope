from django.urls import path

from notas.interface.views.proposals import (
    proposal_apply,
    proposal_approve,
    proposal_cancel,
    proposal_delete,
    proposal_detail,
    proposal_entity_detail,
    proposal_generate_dailyplan,
    proposal_list,
    proposal_list_bulk_delete,
    proposal_list_reorder,
    proposal_reject,
)

urlpatterns = [
    path("proposals/", proposal_list, name="proposal_list"),
    path("proposals/reorder/", proposal_list_reorder, name="proposal_list_reorder"),
    path("proposals/bulk-delete/", proposal_list_bulk_delete, name="proposal_list_bulk_delete"),
    path("proposals/<int:proposal_id>/", proposal_detail, name="proposal_detail"),
    path("proposals/<int:proposal_id>/entity/", proposal_entity_detail, name="proposal_entity_detail"),
    path("proposals/<int:proposal_id>/generate-dailyplan/", proposal_generate_dailyplan, name="proposal_generate_dailyplan"),
    path("proposals/<int:proposal_id>/approve/", proposal_approve, name="proposal_approve"),
    path("proposals/<int:proposal_id>/reject/", proposal_reject, name="proposal_reject"),
    path("proposals/<int:proposal_id>/cancel/", proposal_cancel, name="proposal_cancel"),
    path("proposals/<int:proposal_id>/delete/", proposal_delete, name="proposal_delete"),
    path("proposals/<int:proposal_id>/apply/", proposal_apply, name="proposal_apply"),
]
