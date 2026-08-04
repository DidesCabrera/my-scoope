from dataclasses import dataclass

from django.urls import reverse
from django.utils import timezone

from notas.application.ai_intake.chat_engine import build_ai_nutrition_intake_engine_status
from notas.application.ai_intake.generated_plan_messages import (
    AiGeneratedPlanCardVM,
    AiGeneratedPlanMealVM,
    append_ai_assistant_structured_response,
    append_generated_plan_message,
    append_iterated_plan_message,
    append_target_item,
    build_generated_plan_card,
    build_generated_plan_card_for_chat,
    build_generated_plan_cards_for_ai_response,
    conversation_has_generated_plan_cards,
    deactivate_generated_plan_cards,
    serialize_generated_plan_card,
)
from notas.application.ai_intake.nutrition_brief import (
    deserialize_conversation,
)
from notas.presentation.composition.viewmodel.components.builder_headers import build_page_header


@dataclass
class AiNutritionIntakeContentVM:
    header: object
    result: object | None
    conversation: object | None
    generated_proposal_card: AiGeneratedPlanCardVM | None = None
    has_historical_generated_plan_cards: bool = False
    prompt: str = ""
    engine_status: dict | None = None


@dataclass
class AiNutritionBriefEditContentVM:
    header: object
    result: object
    conversation: object | None
    prompt: str = ""


@dataclass(frozen=True)
class AiNutritionChatListItemVM:
    title: str
    subtitle: str
    preview: str
    status_label: str
    status_key: str
    url: str
    is_active: bool = False
    message_count: int = 0
    generated_plan_count: int = 0
    readiness_label: str = "Brief en progreso"
    goal_label: str = "Pendiente"
    meals_label: str = "Comidas pendientes"
    proposal_url: str | None = None
    proposal_status_label: str = ""
    proposal_status_key: str = ""


@dataclass(frozen=True)
class AiNutritionChatListContentVM:
    header: object
    chats: list[AiNutritionChatListItemVM]
    item_count: int
    active_chat_id: int | None = None


def build_intake_content(
    *,
    result,
    conversation,
    prompt: str = "",
    active_chat=None,
    generated_proposal_card: AiGeneratedPlanCardVM | None = None,
) -> AiNutritionIntakeContentVM:
    return AiNutritionIntakeContentVM(
        header=build_intake_header(has_result=result is not None),
        result=result,
        conversation=conversation,
        generated_proposal_card=(
            generated_proposal_card
            if generated_proposal_card is not None
            else build_generated_plan_card_for_chat(active_chat)
        ),
        has_historical_generated_plan_cards=conversation_has_generated_plan_cards(conversation),
        prompt=prompt,
        engine_status=build_ai_nutrition_intake_engine_status(),
    )


def build_brief_edit_content(*, result, conversation, prompt: str) -> AiNutritionBriefEditContentVM:
    return AiNutritionBriefEditContentVM(
        header=build_page_header(
            title="Editar Brief Nutricional",
            actions=[
                {
                    "key": "back_ai_intake",
                    "label": "Volver al chat",
                    "url": reverse("ai_nutrition_intake"),
                    "method": "get",
                    "icon": "arrow-left",
                    "order": 10,
                    "desktop_position": "inline",
                    "mobile_position": "inline",
                }
            ],
        ),
        result=result,
        conversation=conversation,
        prompt=prompt,
    )


def build_chat_list_content(chats, *, active_chat_id: int | None = None) -> AiNutritionChatListContentVM:
    chat_items = [
        build_chat_list_item(chat, active_chat_id=active_chat_id)
        for chat in chats
    ]
    return AiNutritionChatListContentVM(
        header=build_page_header(
            title="Chats",
            actions=[
                {
                    "key": "new_ai_chat",
                    "label": "Nuevo chat",
                    "url": reverse("ai_nutrition_chat_new"),
                    "method": "get",
                    "icon": "plus",
                    "order": 10,
                    "desktop_position": "inline",
                    "mobile_position": "inline",
                }
            ],
        ),
        chats=chat_items,
        item_count=len(chat_items),
        active_chat_id=active_chat_id,
    )


def build_chat_list_item(chat, *, active_chat_id: int | None = None) -> AiNutritionChatListItemVM:
    conversation = deserialize_conversation(chat.conversation_payload)
    brief = conversation.result.brief if conversation else None
    messages = conversation.messages if conversation else []
    generated_plan_count = sum(1 for message in messages if message.generated_plan_card)

    proposal = getattr(chat, "proposal", None)
    proposal_url = reverse("proposal_detail", args=[proposal.id]) if proposal else None
    proposal_status_key = getattr(proposal, "status", "") or ""
    proposal_status_label = proposal.get_status_display() if proposal else ""

    return AiNutritionChatListItemVM(
        title=chat.title or "Chat nutricional",
        subtitle=f"Actualizado {timezone.localtime(chat.updated_at).strftime('%d/%m/%Y %H:%M')}",
        preview=chat.last_message_preview or "Sin mensajes guardados.",
        status_label=chat.get_status_display(),
        status_key=(chat.status or "active").replace("_", "-"),
        url=reverse("ai_nutrition_chat_detail", args=[chat.id]),
        is_active=bool(active_chat_id and int(chat.id) == int(active_chat_id)),
        message_count=len(messages),
        generated_plan_count=generated_plan_count,
        readiness_label="Brief listo" if conversation and conversation.is_ready_for_proposal else "Brief en progreso",
        goal_label=(brief.goal_label if brief else "Pendiente"),
        meals_label=build_chat_meals_label(brief),
        proposal_url=proposal_url,
        proposal_status_label=proposal_status_label,
        proposal_status_key=proposal_status_key,
    )


def build_chat_meals_label(brief) -> str:
    meals_per_day = getattr(brief, "meals_per_day", None)
    if not meals_per_day:
        return "Comidas pendientes"
    if int(meals_per_day) == 1:
        return "1 comida/día"
    return f"{int(meals_per_day)} comidas/día"


def build_intake_header(*, has_result: bool):
    actions = []

    if has_result:
        actions.append(
            {
                "key": "edit_nutrition_brief",
                "label": "Editar Brief Nutricional Manualmente",
                "url": reverse("ai_nutrition_brief_edit"),
                "method": "get",
                "icon": "sliders-horizontal",
                "order": 20,
                "desktop_position": "menu",
                "mobile_position": "menu",
            }
        )

    return build_page_header(title="Asistente nutricional", actions=actions)
