from django.urls import path

from notas.interface.views.sharing import (
    share_claim,
    share_invitation_claim,
    share_invitation_preview,
    share_preview,
)

urlpatterns = [
    path("s/<uuid:public_id>/", share_preview, name="share_preview"),
    path("s/<uuid:public_id>/claim/", share_claim, name="share_claim"),
    path("i/<uuid:public_id>/", share_invitation_preview, name="share_invitation_preview"),
    path("i/<uuid:public_id>/claim/", share_invitation_claim, name="share_invitation_claim"),
]
