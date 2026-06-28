from django.urls import path

from notas.interface.views.ai_intake import (
    ai_nutrition_brief_edit,
    ai_nutrition_chat_detail,
    ai_nutrition_chat_list,
    ai_nutrition_intake,
)

urlpatterns = [
    path("ai-nutrition/intake/", ai_nutrition_intake, name="ai_nutrition_intake"),
    path("ai-nutrition/intake/brief/edit/", ai_nutrition_brief_edit, name="ai_nutrition_brief_edit"),
    path("ai-nutrition/chats/", ai_nutrition_chat_list, name="ai_nutrition_chat_list"),
    path("ai-nutrition/chats/<int:chat_id>/", ai_nutrition_chat_detail, name="ai_nutrition_chat_detail"),
]
