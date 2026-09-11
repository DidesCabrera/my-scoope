from django.urls import path

from notas.interface.views.sharing import share_claim, share_preview

urlpatterns = [
    path("s/<uuid:public_id>/", share_preview, name="share_preview"),
    path("s/<uuid:public_id>/claim/", share_claim, name="share_claim"),
]
