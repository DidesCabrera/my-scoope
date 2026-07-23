from django.urls import path

from admin_knowledge.views import document_detail, overview


urlpatterns = [
    path("", overview, name="admin_knowledge_overview"),
    path(
        "documents/<path:document_path>",
        document_detail,
        name="admin_knowledge_document",
    ),
]
