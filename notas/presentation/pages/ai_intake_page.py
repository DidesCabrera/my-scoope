from dataclasses import asdict, dataclass, replace

from django.urls import reverse

from notas.application.dto.proposal_iteration_trace import extract_plan_iteration_trace
from notas.application.ai_intake.nutrition_brief import (
    NutritionConversationMessage,
    NutritionConversationState,
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
    url: str


@dataclass(frozen=True)
class AiNutritionChatListContentVM:
    header: object
    chats: list[AiNutritionChatListItemVM]
    item_count: int


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


def build_chat_list_content(chats) -> AiNutritionChatListContentVM:
    chat_items = [
        AiNutritionChatListItemVM(
            title=chat.title,
            subtitle=chat.updated_at.strftime("%d/%m/%Y %H:%M"),
            preview=chat.last_message_preview or "Sin mensajes guardados.",
            status_label=chat.get_status_display(),
            url=reverse("ai_nutrition_chat_detail", args=[chat.id]),
        )
        for chat in chats
    ]
    return AiNutritionChatListContentVM(
        header=build_page_header(title="Chats"),
        chats=chat_items,
        item_count=len(chat_items),
    )


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
        messages=messages[-16:],
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
        conversation = NutritionConversationState(messages=messages[-16:], result=conversation.result)

    return append_generated_plan_message(
        conversation,
        proposal=proposal,
        text=(
            "Actualicé la propuesta con tu ajuste"
            + (f": {feedback}." if feedback else ".")
            + " Dejo la versión anterior en el historial y marco esta nueva card como versión actual."
        ),
    )


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
