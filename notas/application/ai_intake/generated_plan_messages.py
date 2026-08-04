from dataclasses import asdict, dataclass, replace
from typing import Iterable

from ai_assistant.domain import AssistantStructuredResponse
from notas.application.ai_intake.nutrition_brief import (
    AI_NUTRITION_CONVERSATION_MESSAGE_LIMIT,
    NutritionConversationMessage,
    NutritionConversationState,
)
from notas.application.dto.proposal_iteration_trace import extract_plan_iteration_trace


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
        conversation = NutritionConversationState(
            messages=messages[-AI_NUTRITION_CONVERSATION_MESSAGE_LIMIT:],
            result=conversation.result,
        )

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
    """Append an assistant turn and cards scoped by the authenticated caller."""

    cards = build_generated_plan_cards_for_ai_response(
        structured_response=structured_response,
        visible_proposals=visible_proposals,
    )
    messages = deactivate_generated_plan_cards(conversation.messages) if cards else list(conversation.messages)
    assistant_text = (structured_response.assistant_text or "").strip()
    if assistant_text:
        messages.append(NutritionConversationMessage(role="assistant", text=assistant_text))
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
    return NutritionConversationState(
        messages=messages[-AI_NUTRITION_CONVERSATION_MESSAGE_LIMIT:],
        result=conversation.result,
    )


def build_generated_plan_cards_for_ai_response(
    *,
    structured_response: AssistantStructuredResponse,
    visible_proposals: Iterable = (),
) -> list[AiGeneratedPlanCardVM]:
    requested_ids = [int(proposal_id) for proposal_id in structured_response.proposal_ids or ()]
    if not requested_ids:
        return []
    proposals_by_id = {
        int(proposal.id): proposal
        for proposal in visible_proposals
        if getattr(proposal, "id", None)
    }
    cards = []
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
    meals = [
        AiGeneratedPlanMealVM(
            hour=meal.get("hour") or "",
            name=((meal.get("meal") or {}).get("name") or "Comida IA"),
            food_count=len(((meal.get("meal") or {}).get("foods") or [])),
        )
        for meal in dailyplan.get("meals") or []
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
        url=_proposal_detail_path(proposal.id),
        summary=proposal.summary or "Propuesta generada desde el brief nutricional.",
        target_items=target_items,
        meals=meals,
        iteration_trace=iteration_trace.as_dict() if iteration_trace else None,
        previous_proposal_url=(
            _proposal_detail_path(previous_proposal_id)
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
    formatted = f"{int(number)} {suffix}" if number.is_integer() else f"{number:.1f} {suffix}"
    items.append({"label": label, "value": formatted})


def _proposal_detail_path(proposal_id: int) -> str:
    """Return the stable public path without importing HTTP concerns."""

    return f"/app/proposals/{int(proposal_id)}/"
