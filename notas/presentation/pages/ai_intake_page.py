from dataclasses import asdict, dataclass, replace
from typing import Iterable

from django.urls import reverse
from django.utils import timezone

from ai_assistant.domain import AssistantStructuredResponse
from notas.application.ai_intake.chat_engine import build_ai_nutrition_intake_engine_status
from notas.application.dto.proposal_iteration_trace import extract_plan_iteration_trace
from notas.application.ai_intake.nutrition_brief import (
    AI_NUTRITION_CONVERSATION_MESSAGE_LIMIT,
    NutritionConversationMessage,
    NutritionConversationState,
    deserialize_conversation,
)
from notas.presentation.composition.viewmodel.components.builder_headers import build_page_header


@dataclass
class AiGeneratedPlanMealVM:
    hour: str
    name: str
    food_count: int


@dataclass
class AiGeneratedPlanCardVM:
    title: str
    url: str
    summary: str
    target_items: list[dict]
    meals: list[AiGeneratedPlanMealVM]
    iteration_trace: dict | None = None
    previous_proposal_url: str | None = None


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


def append_generated_plan_message(
    conversation,
    *,
    proposal,
    text: str | None = None,
) -> NutritionConversationState:
    messages = deactivate_generated_plan_cards(conversation.messages)
    card = build_generated_plan_card(proposal)
    messages.append(
        NutritionConversationMessage(
            role="assistant",
            text=(
                text
                or "Listo. Generé una primera propuesta de DailyPlan dentro del chat. "
                "Puedes revisar la card y pedirme ajustes antes de aplicarla."
            ),
            generated_plan_card=serialize_generated_plan_card(card, is_current=True),
        )
    )
    return NutritionConversationState(
        messages=messages[-AI_NUTRITION_CONVERSATION_MESSAGE_LIMIT:],
        result=conversation.result,
    )


def append_iterated_plan_message(
    conversation,
    *,
    user_message: str,
    previous_proposal,
    proposal,
) -> NutritionConversationState:
    feedback = " ".join((user_message or "").strip().split())
    if not conversation_has_generated_plan_cards(conversation):
        previous_card = build_generated_plan_card(previous_proposal)
        messages = list(conversation.messages)
        messages.append(
            NutritionConversationMessage(
                role="assistant",
                text="",
                generated_plan_card=serialize_generated_plan_card(previous_card, is_current=False),
            )
        )
        conversation = NutritionConversationState(messages=messages[-AI_NUTRITION_CONVERSATION_MESSAGE_LIMIT:], result=conversation.result)

    return append_generated_plan_message(
        conversation,
        proposal=proposal,
        text=(
            "Actualicé la propuesta con tu ajuste"
            + (f": {feedback}." if feedback else ".")
            + " Dejo la versión anterior en el historial y marco esta nueva card como versión actual."
        ),
    )


def append_ai_assistant_structured_response(
    conversation,
    *,
    structured_response: AssistantStructuredResponse,
    visible_proposals: Iterable = (),
) -> NutritionConversationState:
    """Append an AI Assistant turn and safe proposal cards to the chat history.

    The structured response may contain proposal ids only after My Scoope tools
    have created real `NutritionProposal` records. This renderer does not fetch
    by ids and does not trust provider-supplied ids; callers must pass proposal
    objects already scoped to the authenticated user.
    """

    cards = build_generated_plan_cards_for_ai_response(
        structured_response=structured_response,
        visible_proposals=visible_proposals,
    )
    messages = deactivate_generated_plan_cards(conversation.messages) if cards else list(conversation.messages)

    assistant_text = (structured_response.assistant_text or "").strip()
    if assistant_text:
        messages.append(
            NutritionConversationMessage(
                role="assistant",
                text=assistant_text,
            )
        )

    for index, card in enumerate(cards):
        messages.append(
            NutritionConversationMessage(
                role="assistant",
                text="",
                generated_plan_card=serialize_generated_plan_card(
                    card,
                    is_current=index == len(cards) - 1,
                ),
            )
        )

    return NutritionConversationState(messages=messages[-AI_NUTRITION_CONVERSATION_MESSAGE_LIMIT:], result=conversation.result)


def build_generated_plan_cards_for_ai_response(
    *,
    structured_response: AssistantStructuredResponse,
    visible_proposals: Iterable = (),
) -> list[AiGeneratedPlanCardVM]:
    """Build chat cards for proposal ids that were created by My Scoope.

    The function is deliberately conservative: ids in the structured response are
    only used to match the already-visible proposal objects supplied by the
    caller. A provider cannot make a card appear by returning an arbitrary id.
    """

    requested_ids = [int(proposal_id) for proposal_id in structured_response.proposal_ids or ()]
    if not requested_ids:
        return []

    proposals_by_id = {int(proposal.id): proposal for proposal in visible_proposals if getattr(proposal, "id", None)}
    cards: list[AiGeneratedPlanCardVM] = []
    for proposal_id in requested_ids:
        proposal = proposals_by_id.get(proposal_id)
        if proposal is None:
            continue
        card = build_generated_plan_card(proposal)
        if card is not None:
            cards.append(card)
    return cards


def deactivate_generated_plan_cards(messages):
    updated = []
    for message in messages:
        card = message.generated_plan_card
        if isinstance(card, dict) and card:
            card = {**card, "is_current": False}
            updated.append(replace(message, generated_plan_card=card))
        else:
            updated.append(message)
    return updated


def serialize_generated_plan_card(card: AiGeneratedPlanCardVM | None, *, is_current: bool) -> dict | None:
    if card is None:
        return None
    payload = asdict(card)
    payload["is_current"] = is_current
    return payload


def conversation_has_generated_plan_cards(conversation) -> bool:
    if not conversation:
        return False
    return any(bool(message.generated_plan_card) for message in conversation.messages)


def build_generated_plan_card_for_chat(chat) -> AiGeneratedPlanCardVM | None:
    if not chat or not chat.proposal_id:
        return None
    return build_generated_plan_card(chat.proposal)


def build_generated_plan_card(proposal) -> AiGeneratedPlanCardVM | None:
    payload = proposal.proposed_payload or {}
    if payload.get("intent") != "create_dailyplan":
        return None

    dailyplan = payload.get("dailyplan") or {}
    meals_payload = dailyplan.get("meals") or []
    meals = [
        AiGeneratedPlanMealVM(
            hour=meal.get("hour") or "",
            name=((meal.get("meal") or {}).get("name") or "Comida IA"),
            food_count=len(((meal.get("meal") or {}).get("foods") or [])),
        )
        for meal in meals_payload
    ]

    targets = proposal.targets or {}
    target_items = []
    append_target_item(target_items, "Kcal objetivo", targets.get("total_kcal"), "kcal")
    append_target_item(target_items, "Proteína", targets.get("protein"), "g")
    append_target_item(target_items, "Carbohidratos", targets.get("carbs"), "g")
    append_target_item(target_items, "Grasas", targets.get("fat"), "g")
    append_target_item(target_items, "Gasto estimado", targets.get("estimated_tdee"), "kcal")

    iteration_trace = extract_plan_iteration_trace(proposal)
    previous_proposal_id = iteration_trace.previous_proposal_id if iteration_trace else None

    return AiGeneratedPlanCardVM(
        title=dailyplan.get("name") or proposal.title,
        url=reverse("proposal_detail", args=[proposal.id]),
        summary=proposal.summary or "Propuesta generada desde el brief nutricional.",
        target_items=target_items,
        meals=meals,
        iteration_trace=iteration_trace.as_dict() if iteration_trace else None,
        previous_proposal_url=(
            reverse("proposal_detail", args=[previous_proposal_id])
            if previous_proposal_id
            else None
        ),
    )


def append_target_item(items: list[dict], label: str, value, suffix: str) -> None:
    if value in (None, ""):
        return
    try:
        number = float(value)
    except (TypeError, ValueError):
        items.append({"label": label, "value": str(value)})
        return

    if number.is_integer():
        formatted = f"{int(number)} {suffix}"
    else:
        formatted = f"{number:.1f} {suffix}"
    items.append({"label": label, "value": formatted})


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
