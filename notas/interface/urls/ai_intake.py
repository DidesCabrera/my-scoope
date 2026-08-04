from django.urls import path

from notas.interface.views.ai_intake import (
    ai_nutrition_async_job_status,
    ai_nutrition_brief_edit,
    ai_nutrition_chat_detail,
    ai_nutrition_chat_list,
    ai_nutrition_chat_new,
    ai_nutrition_intake,
    ai_prepared_action_cancel,
    ai_prepared_action_commit,
)

urlpatterns = [
    path("ai-nutrition/intake/", ai_nutrition_intake, name="ai_nutrition_intake"),
    path(
        "ai-nutrition/jobs/<uuid:job_id>/",
        ai_nutrition_async_job_status,
        name="ai_nutrition_async_job_status",
    ),
    path("ai-nutrition/intake/brief/edit/", ai_nutrition_brief_edit, name="ai_nutrition_brief_edit"),
    path("ai-nutrition/chats/", ai_nutrition_chat_list, name="ai_nutrition_chat_list"),
    path("ai-nutrition/chats/new/", ai_nutrition_chat_new, name="ai_nutrition_chat_new"),
    path("ai-nutrition/chats/<int:chat_id>/", ai_nutrition_chat_detail, name="ai_nutrition_chat_detail"),
    path(
        "ai-nutrition/actions/<uuid:action_id>/commit/",
        ai_prepared_action_commit,
        name="ai_prepared_action_commit",
    ),
    path(
        "ai-nutrition/actions/<uuid:action_id>/cancel/",
        ai_prepared_action_cancel,
        name="ai_prepared_action_cancel",
    ),
]
