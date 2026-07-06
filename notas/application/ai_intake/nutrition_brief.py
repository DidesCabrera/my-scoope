from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field, replace
from typing import Iterable

from notas.application.dto.nutrition_subject_context_dto import (
    PPK_WEIGHT_SOURCE_EXTERNAL,
    PPK_WEIGHT_SOURCE_MANUAL,
    PPK_WEIGHT_SOURCE_PROFILE,
    PPK_WEIGHT_SOURCE_UNKNOWN,
    SUBJECT_SOURCE_EXTERNAL_CHAT_DATA,
    SUBJECT_SOURCE_MANUAL_CHAT_DATA,
    SUBJECT_SOURCE_SELF_PROFILE,
)
from notas.application.queries.user_nutrition_profile import (
    NutritionSubjectContextError,
    build_nutrition_subject_context,
)

from notas.application.ai_intake.iteration_commands import (
    PlanIterationCommandSet,
    parse_dailyplan_iteration_commands,
)


AI_NUTRITION_BRIEF_SESSION_KEY = "ai_nutrition_brief"
AI_NUTRITION_CONVERSATION_SESSION_KEY = "ai_nutrition_conversation"

GOAL_CHOICES = (
    ("", "Pendiente"),
    ("fat_loss", "Bajar grasa"),
    ("muscle_gain", "Ganar masa muscular"),
    ("maintenance", "Mantención"),
    ("performance", "Rendimiento deportivo"),
    ("healthy_eating", "Comer mejor"),
)

REQUESTED_ENTITY_CHOICES = (
    ("daily_plan", "Plan diario"),
    ("program", "Programa semanal"),
)

STYLE_CHOICES = (
    ("simple", "Simple"),
    ("budget", "Económico"),
    ("varied", "Variado"),
    ("low_prep", "Poco tiempo de preparación"),
)

COMPLEXITY_CHOICES = (
    ("", "Pendiente"),
    ("low", "Baja / muy simple"),
    ("medium", "Media"),
    ("high", "Alta / más variedad"),
)

BUDGET_CHOICES = (
    ("", "Pendiente"),
    ("low", "Bajo"),
    ("medium", "Medio"),
    ("high", "Flexible"),
)

SEX_CHOICES = (
    ("", "Pendiente"),
    ("male", "Hombre"),
    ("female", "Mujer"),
)

ACTIVITY_LEVEL_CHOICES = (
    ("", "Pendiente"),
    ("sedentary", "Sedentario"),
    ("light", "Actividad ligera"),
    ("moderate", "Actividad moderada"),
    ("high", "Actividad alta"),
    ("very_high", "Actividad muy alta"),
)

SUBJECT_SOURCE_CHOICES = (
    ("", "Pendiente"),
    (SUBJECT_SOURCE_SELF_PROFILE, "Ficha personal"),
    (SUBJECT_SOURCE_EXTERNAL_CHAT_DATA, "Datos externos"),
    (SUBJECT_SOURCE_MANUAL_CHAT_DATA, "Datos temporales"),
)

PPK_WEIGHT_SOURCE_CHOICES = (
    (PPK_WEIGHT_SOURCE_PROFILE, "Peso de ficha personal"),
    (PPK_WEIGHT_SOURCE_EXTERNAL, "Peso externo"),
    (PPK_WEIGHT_SOURCE_MANUAL, "Peso temporal"),
    (PPK_WEIGHT_SOURCE_UNKNOWN, "Peso pendiente"),
)

DEFAULT_MEALS_FOR_ADJUSTMENT = 4

ENERGY_ADJUSTMENT_CHOICES = (
    ("", "Según objetivo"),
    ("deficit_mild", "Déficit leve"),
    ("deficit_moderate", "Déficit moderado"),
    ("deficit_large", "Déficit grande"),
    ("surplus_mild", "Superávit leve"),
    ("surplus_moderate", "Superávit moderado"),
    ("surplus_large", "Superávit grande"),
    ("maintenance", "Mantención"),
)


@dataclass(frozen=True)
class NutritionBrief:
    """Contrato interno editable para traducir una solicitud libre en intención.

    Este objeto sigue siendo deliberadamente liviano: no llama a modelos externos,
    no genera planes y no crea propuestas. Patch 2 lo convierte en una estructura
    editable y serializable en sesión para que el usuario pueda revisar lo que
    MyScoope entendió antes de avanzar al generador de propuestas.
    """

    raw_prompt: str
    subject_source: str | None = None
    ppk_weight_source: str = PPK_WEIGHT_SOURCE_UNKNOWN
    requires_library_ppk_warning: bool = False
    goal: str | None = None
    requested_entity: str = "daily_plan"
    meals_per_day: int | None = None
    training_frequency: int | None = None
    calorie_target: int | None = None
    protein_target: int | None = None
    carb_target: int | None = None
    fat_target: int | None = None
    weight_kg: float | None = None
    height_cm: int | None = None
    age_years: int | None = None
    sex: str | None = None
    activity_level: str | None = None
    energy_adjustment: str | None = None
    style_preferences: list[str] = field(default_factory=list)
    excluded_foods: list[str] = field(default_factory=list)
    preferred_foods: list[str] = field(default_factory=list)
    complexity_level: str | None = None
    budget_level: str | None = None
    notes: list[str] = field(default_factory=list)

    @property
    def requested_entity_label(self) -> str:
        return _choice_label(REQUESTED_ENTITY_CHOICES, self.requested_entity, "Plan diario")

    @property
    def subject_source_label(self) -> str:
        return _choice_label(SUBJECT_SOURCE_CHOICES, self.subject_source or "", "Pendiente")

    @property
    def ppk_weight_source_label(self) -> str:
        return _choice_label(PPK_WEIGHT_SOURCE_CHOICES, self.ppk_weight_source or "", "Peso pendiente")

    @property
    def is_external_subject(self) -> bool:
        return self.subject_source in {
            SUBJECT_SOURCE_EXTERNAL_CHAT_DATA,
            SUBJECT_SOURCE_MANUAL_CHAT_DATA,
        }

    @property
    def goal_label(self) -> str:
        return _choice_label(GOAL_CHOICES, self.goal or "", "Pendiente")

    @property
    def complexity_label(self) -> str:
        return _choice_label(COMPLEXITY_CHOICES, self.complexity_level or "", "Pendiente")

    @property
    def budget_label(self) -> str:
        return _choice_label(BUDGET_CHOICES, self.budget_level or "", "Pendiente")

    @property
    def sex_label(self) -> str:
        return _choice_label(SEX_CHOICES, self.sex or "", "Pendiente")

    @property
    def activity_level_label(self) -> str:
        return _choice_label(ACTIVITY_LEVEL_CHOICES, self.activity_level or "", "Pendiente")

    @property
    def energy_adjustment_label(self) -> str:
        return _choice_label(ENERGY_ADJUSTMENT_CHOICES, self.energy_adjustment or "", "Según objetivo")

    @property
    def can_estimate_energy_expenditure(self) -> bool:
        return can_estimate_energy_expenditure(self)

    @property
    def excluded_foods_text(self) -> str:
        return ", ".join(self.excluded_foods)

    @property
    def preferred_foods_text(self) -> str:
        return ", ".join(self.preferred_foods)

    @property
    def notes_text(self) -> str:
        return ", ".join(self.notes)

    @property
    def is_ready_for_proposal(self) -> bool:
        return is_brief_ready_for_proposal(self)


@dataclass(frozen=True)
class NutritionConversationMessage:
    role: str
    text: str
    generated_plan_card: dict | None = None


@dataclass(frozen=True)
class NutritionConversationState:
    messages: list[NutritionConversationMessage]
    result: NutritionIntakeResult

    @property
    def is_ready_for_proposal(self) -> bool:
        return self.result.is_ready_for_proposal

    @property
    def required_follow_up_questions(self) -> list[str]:
        return self.result.required_follow_up_questions

    @property
    def visible_follow_up_questions(self) -> list[str]:
        return self.result.follow_up_questions[:4]

    @property
    def last_assistant_message(self) -> str:
        for message in reversed(self.messages):
            if message.role == "assistant":
                return message.text
        return ""


@dataclass(frozen=True)
class NutritionBriefSummaryItem:
    label: str
    value: str
    is_pending: bool = False


@dataclass(frozen=True)
class NutritionBriefFormVM:
    goal_choices: tuple[tuple[str, str], ...] = GOAL_CHOICES
    requested_entity_choices: tuple[tuple[str, str], ...] = REQUESTED_ENTITY_CHOICES
    style_choices: tuple[tuple[str, str], ...] = STYLE_CHOICES
    complexity_choices: tuple[tuple[str, str], ...] = COMPLEXITY_CHOICES
    budget_choices: tuple[tuple[str, str], ...] = BUDGET_CHOICES
    sex_choices: tuple[tuple[str, str], ...] = SEX_CHOICES
    activity_level_choices: tuple[tuple[str, str], ...] = ACTIVITY_LEVEL_CHOICES
    energy_adjustment_choices: tuple[tuple[str, str], ...] = ENERGY_ADJUSTMENT_CHOICES
    subject_source_choices: tuple[tuple[str, str], ...] = SUBJECT_SOURCE_CHOICES


@dataclass(frozen=True)
class NutritionIntakeResult:
    prompt: str
    brief: NutritionBrief
    summary_items: list[NutritionBriefSummaryItem]
    follow_up_questions: list[str]
    required_follow_up_questions: list[str] = field(default_factory=list)
    completed_summary_items: list[NutritionBriefSummaryItem] = field(default_factory=list)
    visible_follow_up_questions: list[str] = field(default_factory=list)
    has_pending_questions: bool = False
    has_required_pending_questions: bool = False
    is_ready_for_proposal: bool = False
    readiness_label: str = ""
    form: NutritionBriefFormVM = field(default_factory=NutritionBriefFormVM)


_GOAL_KEYWORDS = {
    "fat_loss": (
        "bajar grasa",
        "perder grasa",
        "perdida de grasa",
        "pérdida de grasa",
        "quemar grasa",
        "reducir grasa",
        "eliminar grasa",
        "disminuir grasa",
        "definir",
        "definicion",
        "definición",
        "bajar de peso",
        "perder peso",
        "adelgazar",
        "cut",
    ),
    "muscle_gain": (
        "ganar masa",
        "ganar musculo",
        "ganar músculo",
        "subir masa",
        "subir musculo",
        "subir músculo",
        "hipertrofia",
        "volumen",
        "bulk",
    ),
    "maintenance": (
        "mantencion",
        "mantención",
        "mantener",
        "mantenimiento",
        "mantenerme",
    ),
    "performance": (
        "rendimiento",
        "performance",
        "deporte",
        "entreno fuerte",
        "mejorar marcas",
    ),
    "healthy_eating": (
        "comer mejor",
        "saludable",
        "ordenar mi alimentacion",
        "ordenar mi alimentación",
    ),
}

_STYLE_KEYWORDS = {
    "simple": ("simple", "facil", "fácil", "rapido", "rápido", "pocas comidas", "sencillo"),
    "budget": ("barato", "economico", "económico", "presupuesto", "bajo costo", "ahorrar"),
    "varied": ("variado", "variedad", "no repetir", "distinto"),
    "low_prep": ("sin cocinar", "poco tiempo", "meal prep", "preparacion", "preparación", "preparar rapido"),
}

_ACTIVITY_KEYWORDS = {
    "sedentary": ("sedentario", "sedentaria", "actividad baja", "poco activo", "poco activa"),
    "light": ("actividad ligera", "ligera", "camino", "activo leve"),
    "moderate": ("actividad moderada", "moderada", "moderado", "entreno 3", "entreno tres"),
    "high": ("actividad alta", "alta actividad", "muy activo", "muy activa", "entreno 5", "entreno cinco"),
    "very_high": ("actividad muy alta", "muy alta", "doble turno"),
}

_ENERGY_ADJUSTMENT_KEYWORDS = {
    "deficit_mild": ("deficit leve", "déficit leve", "deficit pequeno", "deficit pequeño", "baja lenta"),
    "deficit_moderate": ("deficit moderado", "déficit moderado", "deficit normal"),
    "deficit_large": ("deficit grande", "déficit grande", "deficit agresivo", "agresivo"),
    "surplus_mild": ("superavit leve", "superávit leve", "subida lenta"),
    "surplus_moderate": ("superavit moderado", "superávit moderado"),
    "surplus_large": ("superavit grande", "superávit grande"),
    "maintenance": ("sin deficit", "sin déficit", "mantencion", "mantención", "mantener"),
}

_FOOD_HINTS = (
    "atun",
    "atún",
    "pollo",
    "huevo",
    "huevos",
    "arroz",
    "quinoa",
    "lentejas",
    "pescado",
    "carne",
    "avena",
    "yogur",
    "palta",
)


def build_intake_result(prompt: str) -> NutritionIntakeResult:
    normalized_prompt = _normalize_prompt(prompt)
    brief = NutritionBrief(
        raw_prompt=prompt.strip(),
        subject_source=_detect_subject_source(normalized_prompt),
        goal=_detect_goal(normalized_prompt),
        requested_entity=_detect_requested_entity(normalized_prompt),
        meals_per_day=_detect_meals_per_day(normalized_prompt),
        training_frequency=_detect_training_frequency(normalized_prompt),
        calorie_target=_detect_numeric_target(normalized_prompt, ("kcal", "calorias", "calorías")),
        protein_target=_detect_numeric_target(normalized_prompt, ("proteina", "proteína", "p ")),
        carb_target=_detect_numeric_target(normalized_prompt, ("carbohidratos", "carbos", "carbo", "c ")),
        fat_target=_detect_numeric_target(normalized_prompt, ("grasa", "grasas", "f ")),
        weight_kg=_detect_weight_kg(normalized_prompt),
        height_cm=_detect_height_cm(normalized_prompt),
        age_years=_detect_age_years(normalized_prompt),
        sex=_detect_sex(normalized_prompt),
        activity_level=_detect_activity_level(normalized_prompt),
        energy_adjustment=_detect_energy_adjustment(normalized_prompt),
        style_preferences=_detect_styles(normalized_prompt),
        excluded_foods=_detect_excluded_foods(normalized_prompt),
        preferred_foods=_detect_preferred_foods(normalized_prompt),
        complexity_level=_detect_complexity(normalized_prompt),
        budget_level=_detect_budget(normalized_prompt),
        notes=_build_notes(normalized_prompt),
    )
    brief = apply_subject_context(brief)
    return build_intake_result_from_brief(brief)


def build_intake_result_from_brief(brief: NutritionBrief) -> NutritionIntakeResult:
    summary_items = build_summary_items(brief)
    follow_up_questions = build_follow_up_questions(brief)
    required_follow_up_questions = build_required_follow_up_questions(brief)
    is_ready_for_proposal = not required_follow_up_questions
    readiness_label = (
        "Listo para crear propuesta"
        if is_ready_for_proposal
        else f"Faltan {len(required_follow_up_questions)} datos mínimos"
    )
    return NutritionIntakeResult(
        prompt=brief.raw_prompt.strip(),
        brief=brief,
        summary_items=summary_items,
        follow_up_questions=follow_up_questions,
        required_follow_up_questions=required_follow_up_questions,
        completed_summary_items=build_completed_summary_items(brief),
        visible_follow_up_questions=follow_up_questions[:4],
        has_pending_questions=bool(follow_up_questions),
        has_required_pending_questions=bool(required_follow_up_questions),
        is_ready_for_proposal=is_ready_for_proposal,
        readiness_label=readiness_label,
    )


def start_or_continue_conversation(
    *,
    message: str,
    existing_payload: dict | None = None,
    user=None,
) -> NutritionConversationState:
    user_message = (message or "").strip()
    if not user_message:
        raise ValueError("conversation_message_required")

    existing_state = deserialize_conversation(existing_payload)
    parsed_brief = build_intake_result(user_message).brief
    brief = _merge_briefs(existing_state.result.brief if existing_state else None, parsed_brief)
    brief = apply_conversation_adjustments(brief, user_message)
    brief = apply_subject_context(brief, user=user)
    result = build_intake_result_from_brief(brief)

    messages = list(existing_state.messages) if existing_state else []
    messages.append(NutritionConversationMessage(role="user", text=user_message))
    messages.append(
        NutritionConversationMessage(
            role="assistant",
            text=build_conversation_reply(result, latest_user_message=user_message),
        )
    )

    return NutritionConversationState(
        messages=messages[-12:],
        result=result,
    )


def build_conversation_from_brief(
    *,
    brief: NutritionBrief,
    existing_payload: dict | None = None,
) -> NutritionConversationState:
    existing_state = deserialize_conversation(existing_payload)
    result = build_intake_result_from_brief(brief)
    messages = list(existing_state.messages) if existing_state else []
    if not messages:
        messages.append(
            NutritionConversationMessage(
                role="assistant",
                text=build_conversation_reply(result),
            )
        )
    return NutritionConversationState(messages=messages[-12:], result=result)


def build_conversation_reply(
    result: NutritionIntakeResult,
    *,
    latest_user_message: str = "",
) -> str:
    brief = result.brief
    required_questions = result.required_follow_up_questions
    acknowledgements = _build_acknowledgements(brief)
    ack_text = " ".join(acknowledgements)
    wants_brief = _is_brief_preview_request(latest_user_message)

    if required_questions:
        questions = " ".join(
            f"{index}. {question}"
            for index, question in enumerate(required_questions[:3], start=1)
        )
        if wants_brief:
            return f"Todavía no tengo el brief mínimo listo. Para poder mostrarte una propuesta revisable, me falta esto: {questions}"
        if ack_text:
            return f"{ack_text} Para preparar una primera propuesta, me falta esto: {questions}"
        return f"Perfecto. Para preparar una primera propuesta, me falta esto: {questions}"

    if result.follow_up_questions:
        questions = " ".join(
            f"{index}. {question}"
            for index, question in enumerate(result.follow_up_questions[:3], start=1)
        )
        if wants_brief:
            return (
                "Listo, te dejo el brief nutricional abajo. "
                f"Ya puedo crear una propuesta revisable. Si quieres afinarla más antes de avanzar, puedes responder: {questions}"
            )
        prefix = ack_text or "Ya tengo suficiente información para crear una propuesta revisable."
        return (
            f"{prefix} Ya puedo crear una propuesta revisable. "
            f"Te dejo el brief abajo. Si quieres afinarla más antes de avanzar, puedes responder: {questions}"
        )

    pieces = _build_brief_pieces(brief)
    if wants_brief:
        return "Listo, te dejo el brief nutricional abajo. Ya puedo crear una propuesta revisable."
    return "Excelente. Con esto ya puedo crear una propuesta revisable: " + ", ".join(pieces) + ". Te dejo el brief abajo."



def apply_conversation_adjustments(brief: NutritionBrief, message: str) -> NutritionBrief:
    """Apply structured chat feedback to the accumulated NutritionBrief.

    Patch 13 promotes common post-generation feedback into deterministic
    commands (macros, food exclusions/preferences, replacements and style). The
    brief is updated before creating a new reviewable proposal revision.
    """
    command_set = parse_dailyplan_iteration_commands(message)
    return apply_iteration_command_set(brief, command_set)


def apply_iteration_command_set(
    brief: NutritionBrief,
    command_set: PlanIterationCommandSet,
) -> NutritionBrief:
    if not command_set.has_commands:
        return brief

    updates = {}
    style_preferences = list(brief.style_preferences)
    excluded_foods = list(brief.excluded_foods)
    preferred_foods = list(brief.preferred_foods)
    complexity_level = brief.complexity_level
    budget_level = brief.budget_level

    for command in command_set.commands:
        kind = command.kind
        payload = command.payload

        if kind == "decrease_meals_per_day":
            current = brief.meals_per_day or DEFAULT_MEALS_FOR_ADJUSTMENT
            updates["meals_per_day"] = max(1, current - 1)
        elif kind == "increase_meals_per_day":
            current = brief.meals_per_day or DEFAULT_MEALS_FOR_ADJUSTMENT
            updates["meals_per_day"] = min(6, current + 1)
        elif kind == "increase_protein_target":
            updates["protein_target"] = min(500, int((brief.protein_target or 140) + 20))
        elif kind == "decrease_protein_target":
            updates["protein_target"] = max(0, int((brief.protein_target or 140) - 20))
        elif kind == "decrease_calorie_target":
            updates["calorie_target"] = max(800, int((brief.calorie_target or 2200) - 200))
        elif kind == "increase_calorie_target":
            updates["calorie_target"] = min(6000, int((brief.calorie_target or 2200) + 200))
        elif kind == "set_simple_style":
            _append_unique(style_preferences, "simple")
            complexity_level = str(payload.get("complexity_level") or "low")
        elif kind == "set_budget_style":
            _append_unique(style_preferences, "budget")
            budget_level = str(payload.get("budget_level") or "low")
        elif kind == "set_varied_style":
            _append_unique(style_preferences, "varied")
            complexity_level = str(payload.get("complexity_level") or "high")
        elif kind == "avoid_food":
            _append_unique(excluded_foods, str(payload.get("term") or ""))
        elif kind == "prefer_food":
            _append_unique(preferred_foods, str(payload.get("term") or ""))
        elif kind == "replace_food_preference":
            _append_unique(excluded_foods, str(payload.get("exclude") or ""))
            _append_unique(preferred_foods, str(payload.get("prefer") or ""))

    updates["style_preferences"] = style_preferences
    updates["excluded_foods"] = excluded_foods
    updates["preferred_foods"] = preferred_foods
    updates["complexity_level"] = complexity_level
    updates["budget_level"] = budget_level

    return replace(brief, **updates)


def _append_unique(values: list[str], value: str) -> None:
    cleaned = " ".join(str(value or "").strip().split())
    if not cleaned:
        return
    normalized = _normalize_prompt(cleaned)
    if normalized and normalized not in {_normalize_prompt(item) for item in values}:
        values.append(cleaned)


def serialize_conversation(state: NutritionConversationState) -> dict:
    serialized_messages = []
    for message in state.messages:
        if not message.text and not message.generated_plan_card:
            continue
        item = {"role": message.role, "text": message.text}
        if message.generated_plan_card:
            item["generated_plan_card"] = message.generated_plan_card
        serialized_messages.append(item)

    return {
        "brief": serialize_brief(state.result.brief),
        "messages": serialized_messages,
    }


def deserialize_conversation(payload: dict | None) -> NutritionConversationState | None:
    if not payload:
        return None

    brief = deserialize_brief(payload.get("brief"))
    if not brief:
        return None

    messages = []
    for item in payload.get("messages") or []:
        role = str(item.get("role") or "").strip()
        text = str(item.get("text") or "").strip()
        generated_plan_card = item.get("generated_plan_card")
        if not isinstance(generated_plan_card, dict):
            generated_plan_card = None
        if role in {"user", "assistant"} and (text or generated_plan_card):
            messages.append(
                NutritionConversationMessage(
                    role=role,
                    text=text,
                    generated_plan_card=generated_plan_card,
                )
            )

    return NutritionConversationState(
        messages=messages[-12:],
        result=build_intake_result_from_brief(brief),
    )


def build_brief_from_form(data) -> NutritionBrief:
    return NutritionBrief(
        raw_prompt=(data.get("raw_prompt") or "").strip(),
        goal=_clean_choice(data.get("goal"), GOAL_CHOICES),
        requested_entity=_clean_choice(data.get("requested_entity"), REQUESTED_ENTITY_CHOICES) or "daily_plan",
        meals_per_day=_clean_int(data.get("meals_per_day"), min_value=1, max_value=8),
        training_frequency=_clean_int(data.get("training_frequency"), min_value=0, max_value=7),
        calorie_target=_clean_int(data.get("calorie_target"), min_value=800, max_value=6000),
        protein_target=_clean_int(data.get("protein_target"), min_value=0, max_value=500),
        carb_target=_clean_int(data.get("carb_target"), min_value=0, max_value=800),
        fat_target=_clean_int(data.get("fat_target"), min_value=0, max_value=300),
        weight_kg=_clean_float(data.get("weight_kg"), min_value=25, max_value=350),
        height_cm=_clean_int(data.get("height_cm"), min_value=100, max_value=250),
        age_years=_clean_int(data.get("age_years"), min_value=10, max_value=100),
        sex=_clean_choice(data.get("sex"), SEX_CHOICES),
        activity_level=_clean_choice(data.get("activity_level"), ACTIVITY_LEVEL_CHOICES),
        energy_adjustment=_clean_choice(data.get("energy_adjustment"), ENERGY_ADJUSTMENT_CHOICES),
        style_preferences=_clean_multi_choice(data.getlist("style_preferences"), STYLE_CHOICES),
        excluded_foods=_split_free_text_list(data.get("excluded_foods")),
        preferred_foods=_split_free_text_list(data.get("preferred_foods")),
        complexity_level=_clean_choice(data.get("complexity_level"), COMPLEXITY_CHOICES),
        budget_level=_clean_choice(data.get("budget_level"), BUDGET_CHOICES),
        notes=_split_free_text_list(data.get("notes")),
    )


def serialize_brief(brief: NutritionBrief) -> dict:
    return {
        "raw_prompt": brief.raw_prompt,
        "subject_source": brief.subject_source,
        "ppk_weight_source": brief.ppk_weight_source,
        "requires_library_ppk_warning": brief.requires_library_ppk_warning,
        "goal": brief.goal,
        "requested_entity": brief.requested_entity,
        "meals_per_day": brief.meals_per_day,
        "training_frequency": brief.training_frequency,
        "calorie_target": brief.calorie_target,
        "protein_target": brief.protein_target,
        "carb_target": brief.carb_target,
        "fat_target": brief.fat_target,
        "weight_kg": brief.weight_kg,
        "height_cm": brief.height_cm,
        "age_years": brief.age_years,
        "sex": brief.sex,
        "activity_level": brief.activity_level,
        "energy_adjustment": brief.energy_adjustment,
        "style_preferences": list(brief.style_preferences),
        "excluded_foods": list(brief.excluded_foods),
        "preferred_foods": list(brief.preferred_foods),
        "complexity_level": brief.complexity_level,
        "budget_level": brief.budget_level,
        "notes": list(brief.notes),
    }


def deserialize_brief(payload: dict | None) -> NutritionBrief | None:
    if not payload:
        return None

    return NutritionBrief(
        raw_prompt=str(payload.get("raw_prompt") or ""),
        subject_source=_clean_choice(payload.get("subject_source"), SUBJECT_SOURCE_CHOICES),
        ppk_weight_source=_clean_ppk_weight_source(payload.get("ppk_weight_source")),
        requires_library_ppk_warning=bool(payload.get("requires_library_ppk_warning")),
        goal=_clean_choice(payload.get("goal"), GOAL_CHOICES),
        requested_entity=_clean_choice(payload.get("requested_entity"), REQUESTED_ENTITY_CHOICES) or "daily_plan",
        meals_per_day=_clean_int(payload.get("meals_per_day"), min_value=1, max_value=8),
        training_frequency=_clean_int(payload.get("training_frequency"), min_value=0, max_value=7),
        calorie_target=_clean_int(payload.get("calorie_target"), min_value=800, max_value=6000),
        protein_target=_clean_int(payload.get("protein_target"), min_value=0, max_value=500),
        carb_target=_clean_int(payload.get("carb_target"), min_value=0, max_value=800),
        fat_target=_clean_int(payload.get("fat_target"), min_value=0, max_value=300),
        weight_kg=_clean_float(payload.get("weight_kg"), min_value=25, max_value=350),
        height_cm=_clean_int(payload.get("height_cm"), min_value=100, max_value=250),
        age_years=_clean_int(payload.get("age_years"), min_value=10, max_value=100),
        sex=_clean_choice(payload.get("sex"), SEX_CHOICES),
        activity_level=_clean_choice(payload.get("activity_level"), ACTIVITY_LEVEL_CHOICES),
        energy_adjustment=_clean_choice(payload.get("energy_adjustment"), ENERGY_ADJUSTMENT_CHOICES),
        style_preferences=_clean_multi_choice(payload.get("style_preferences") or [], STYLE_CHOICES),
        excluded_foods=_clean_text_list(payload.get("excluded_foods") or []),
        preferred_foods=_clean_text_list(payload.get("preferred_foods") or []),
        complexity_level=_clean_choice(payload.get("complexity_level"), COMPLEXITY_CHOICES),
        budget_level=_clean_choice(payload.get("budget_level"), BUDGET_CHOICES),
        notes=_clean_text_list(payload.get("notes") or []),
    )


def _merge_briefs(existing: NutritionBrief | None, incoming: NutritionBrief) -> NutritionBrief:
    if existing is None:
        return incoming

    raw_prompt = "\n".join(
        value for value in (existing.raw_prompt.strip(), incoming.raw_prompt.strip()) if value
    )
    inferred = build_intake_result(raw_prompt).brief if raw_prompt else incoming

    requested_entity = existing.requested_entity
    if incoming.requested_entity == "program" or inferred.requested_entity == "program" or existing.requested_entity not in {"daily_plan", "program"}:
        requested_entity = incoming.requested_entity if incoming.requested_entity == "program" else inferred.requested_entity

    subject_source = incoming.subject_source or existing.subject_source or inferred.subject_source
    ppk_weight_source = (
        incoming.ppk_weight_source
        if incoming.ppk_weight_source != PPK_WEIGHT_SOURCE_UNKNOWN
        else existing.ppk_weight_source
        if existing.ppk_weight_source != PPK_WEIGHT_SOURCE_UNKNOWN
        else inferred.ppk_weight_source
    )

    return NutritionBrief(
        raw_prompt=raw_prompt,
        subject_source=subject_source,
        ppk_weight_source=ppk_weight_source,
        requires_library_ppk_warning=(
            incoming.requires_library_ppk_warning
            or existing.requires_library_ppk_warning
            or inferred.requires_library_ppk_warning
        ),
        goal=incoming.goal or existing.goal or inferred.goal,
        requested_entity=requested_entity or "daily_plan",
        meals_per_day=incoming.meals_per_day or existing.meals_per_day or inferred.meals_per_day,
        training_frequency=(
            incoming.training_frequency
            if incoming.training_frequency is not None
            else existing.training_frequency
            if existing.training_frequency is not None
            else inferred.training_frequency
        ),
        calorie_target=incoming.calorie_target or existing.calorie_target or inferred.calorie_target,
        protein_target=incoming.protein_target or existing.protein_target or inferred.protein_target,
        carb_target=incoming.carb_target or existing.carb_target or inferred.carb_target,
        fat_target=incoming.fat_target or existing.fat_target or inferred.fat_target,
        weight_kg=incoming.weight_kg or existing.weight_kg or inferred.weight_kg,
        height_cm=incoming.height_cm or existing.height_cm or inferred.height_cm,
        age_years=incoming.age_years or existing.age_years or inferred.age_years,
        sex=incoming.sex or existing.sex or inferred.sex,
        activity_level=incoming.activity_level or existing.activity_level or inferred.activity_level,
        energy_adjustment=incoming.energy_adjustment or existing.energy_adjustment or inferred.energy_adjustment,
        style_preferences=_merge_unique(existing.style_preferences, inferred.style_preferences, incoming.style_preferences),
        excluded_foods=_merge_unique(existing.excluded_foods, inferred.excluded_foods, incoming.excluded_foods),
        preferred_foods=_merge_unique(existing.preferred_foods, inferred.preferred_foods, incoming.preferred_foods),
        complexity_level=incoming.complexity_level or existing.complexity_level or inferred.complexity_level,
        budget_level=incoming.budget_level or existing.budget_level or inferred.budget_level,
        notes=_merge_unique(existing.notes, inferred.notes, incoming.notes),
    )


def _merge_unique(*groups: Iterable[str]) -> list[str]:
    merged = []
    for group in groups:
        for value in group:
            cleaned = str(value or "").strip()
            if cleaned and cleaned not in merged:
                merged.append(cleaned)
    return merged


def _normalize_prompt(prompt: str) -> str:
    text = " ".join((prompt or "").strip().lower().split())
    return "".join(
        char
        for char in unicodedata.normalize("NFD", text)
        if unicodedata.category(char) != "Mn"
    )


def _detect_goal(prompt: str) -> str | None:
    if "grasa" in prompt and _contains_any(prompt, ("bajar", "perder", "reducir", "quemar", "definir", "definicion")):
        return "fat_loss"

    for goal, keywords in _GOAL_KEYWORDS.items():
        if _contains_any(prompt, keywords):
            return goal
    return None


def _detect_requested_entity(prompt: str) -> str:
    if _contains_any(prompt, ("semana", "semanal", "programa", "7 dias", "7 días")):
        return "program"
    return "daily_plan"


def _detect_subject_source(prompt: str) -> str | None:
    if _contains_any(
        prompt,
        (
            "mi ficha",
            "mis datos",
            "datos de mi ficha",
            "usa mi perfil",
            "usar mi perfil",
            "usa mi ficha",
            "usar mi ficha",
            "para mi",
            "para mí",
        ),
    ):
        return SUBJECT_SOURCE_SELF_PROFILE

    if _contains_any(
        prompt,
        (
            "otra persona",
            "alguien mas",
            "alguien más",
            "un cliente",
            "una clienta",
            "mi cliente",
            "mi clienta",
            "para el",
            "para él",
            "para ella",
            "mi hermano",
            "mi hermana",
            "mi amigo",
            "mi amiga",
        ),
    ):
        return SUBJECT_SOURCE_EXTERNAL_CHAT_DATA

    return None


def _detect_meals_per_day(prompt: str) -> int | None:
    match = re.search(r"\b([2-6])\s*(comidas|comida|meals?)\b", prompt)
    if match:
        return int(match.group(1))
    return None


def _detect_training_frequency(prompt: str) -> int | None:
    match = re.search(r"\b(?:entreno|entrenar|entrenamiento|gym|gimnasio)\D{0,18}([1-7])\s*(?:veces|dias|días)?\b", prompt)
    if match:
        return int(match.group(1))

    match = re.search(r"\b([1-7])\s*(?:veces|dias|días)\D{0,18}(?:entreno|entrenar|entrenamiento|gym|gimnasio)\b", prompt)
    if match:
        return int(match.group(1))

    return None


def _detect_numeric_target(prompt: str, keywords: Iterable[str]) -> int | None:
    for keyword in keywords:
        cleaned_keyword = keyword.strip()
        if len(cleaned_keyword) <= 1:
            continue
        escaped_keyword = re.escape(cleaned_keyword)
        patterns = (
            rf"\b(\d{{2,4}})\s*(?:g\s*)?{escaped_keyword}\b",
            rf"\b{escaped_keyword}\D{{0,12}}(\d{{2,4}})\s*(?:g|kcal|calorias|calorías)\b",
        )
        for pattern in patterns:
            match = re.search(pattern, prompt)
            if match:
                return int(match.group(1))
    return None


def _detect_weight_kg(prompt: str) -> float | None:
    patterns = (
        r"\b(?:peso|peso actual|peso corporal)\D{0,12}(\d{2,3}(?:[\.,]\d{1,2})?)\s*(?:kg|kilos)?\b",
        r"\b(\d{2,3}(?:[\.,]\d{1,2})?)\s*(?:kg|kilos)\b",
    )
    for pattern in patterns:
        match = re.search(pattern, prompt)
        if match:
            value = _parse_float(match.group(1))
            if value and 25 <= value <= 350:
                return value
    return None


def _detect_height_cm(prompt: str) -> int | None:
    patterns = (
        r"\b(?:mido|altura|estatura)\D{0,12}(\d(?:[\.,]\d{1,2}))\s*(?:m|metros)?\b",
        r"\b(?:mido|altura|estatura)\D{0,12}(\d{3})\s*(?:cm|centimetros|centímetros)?\b",
        r"\b(\d(?:[\.,]\d{1,2}))\s*(?:m|metros)\b",
        r"\b(\d{3})\s*(?:cm|centimetros|centímetros)\b",
    )
    for pattern in patterns:
        match = re.search(pattern, prompt)
        if match:
            raw = match.group(1)
            if "." in raw or "," in raw:
                value = _parse_float(raw)
                if value and 1.0 <= value <= 2.5:
                    return int(round(value * 100))
            elif raw.isdigit():
                value = int(raw)
                if 100 <= value <= 250:
                    return value
    return None


def _detect_age_years(prompt: str) -> int | None:
    patterns = (
        r"\b(?:tengo|edad)\D{0,10}(\d{2})\s*(?:anos|años)?\b",
        r"\b(\d{2})\s*(?:anos|años)\b",
    )
    for pattern in patterns:
        match = re.search(pattern, prompt)
        if match:
            value = int(match.group(1))
            if 10 <= value <= 100:
                return value
    return None


def _detect_sex(prompt: str) -> str | None:
    if _contains_any(prompt, ("hombre", "masculino", "varon", "varón")):
        return "male"
    if _contains_any(prompt, ("mujer", "femenino")):
        return "female"
    return None


def _detect_activity_level(prompt: str) -> str | None:
    for level, keywords in _ACTIVITY_KEYWORDS.items():
        if _contains_any(prompt, keywords):
            return level
    return None


def _detect_energy_adjustment(prompt: str) -> str | None:
    for adjustment, keywords in _ENERGY_ADJUSTMENT_KEYWORDS.items():
        if _contains_any(prompt, keywords):
            return adjustment
    return None


def _detect_styles(prompt: str) -> list[str]:
    styles: list[str] = []
    for style, keywords in _STYLE_KEYWORDS.items():
        if _contains_any(prompt, keywords):
            styles.append(style)
    return styles


def _detect_complexity(prompt: str) -> str | None:
    if _contains_any(prompt, ("simple", "facil", "fácil", "pocas cosas", "pocos alimentos")):
        return "low"
    if _contains_any(prompt, ("variado", "variedad", "no repetir")):
        return "high"
    return None


def _detect_budget(prompt: str) -> str | None:
    if _contains_any(prompt, ("barato", "economico", "económico", "bajo presupuesto")):
        return "low"
    return None


def _detect_excluded_foods(prompt: str) -> list[str]:
    excluded = []
    exclusion_patterns = (
        r"(?:no como|no consumo|no me gusta|sin|evitar|excluir|no quiero)\s+([^,.]+)",
        r"\bno\s+((?:atun|pollo|huevo|huevos|arroz|quinoa|lentejas|pescado|carne|avena|yogur|palta)(?:\s+y\s+)?[^,.]*)",
    )
    for pattern in exclusion_patterns:
        for match in re.finditer(pattern, prompt):
            fragment = match.group(1)
            for food in _FOOD_HINTS:
                normalized_food = _normalize_food_hint(food)
                if normalized_food in fragment and normalized_food not in excluded:
                    excluded.append(normalized_food)
    return excluded


def _detect_preferred_foods(prompt: str) -> list[str]:
    preferred = []
    preference_patterns = (
        r"(?:me gusta|prefiero|tengo|usar|incluye|incluir)\s+([^,.]+)",
    )
    for pattern in preference_patterns:
        for match in re.finditer(pattern, prompt):
            fragment = match.group(1)
            for food in _FOOD_HINTS:
                normalized_food = _normalize_food_hint(food)
                if normalized_food in fragment and normalized_food not in preferred:
                    preferred.append(normalized_food)
    return preferred


def _build_notes(prompt: str) -> list[str]:
    notes = []
    if "a medida" in prompt or "personalizada" in prompt or "personalizado" in prompt:
        notes.append("El usuario pidió una solución personalizada.")
    return notes


def build_summary_items(brief: NutritionBrief) -> list[NutritionBriefSummaryItem]:
    return [
        NutritionBriefSummaryItem(
            "Sujeto nutricional",
            brief.subject_source_label,
            brief.subject_source is None,
        ),
        NutritionBriefSummaryItem(
            "Peso para PPK",
            brief.ppk_weight_source_label,
            brief.ppk_weight_source == PPK_WEIGHT_SOURCE_UNKNOWN,
        ),
        NutritionBriefSummaryItem("Objetivo", brief.goal_label, brief.goal is None),
        NutritionBriefSummaryItem("Tipo de solución", brief.requested_entity_label),
        NutritionBriefSummaryItem(
            "Comidas por día",
            str(brief.meals_per_day) if brief.meals_per_day else "Pendiente",
            brief.meals_per_day is None,
        ),
        NutritionBriefSummaryItem(
            "Entrenamiento",
            f"{brief.training_frequency} veces/semana" if brief.training_frequency is not None else "Pendiente",
            brief.training_frequency is None,
        ),
        NutritionBriefSummaryItem(
            "Kcal objetivo",
            f"{brief.calorie_target} kcal" if brief.calorie_target else "Pendiente",
            brief.calorie_target is None,
        ),
        NutritionBriefSummaryItem(
            "Proteína objetivo",
            f"{brief.protein_target} g" if brief.protein_target else "Pendiente",
            brief.protein_target is None,
        ),
        NutritionBriefSummaryItem(
            "Carbohidratos objetivo",
            f"{brief.carb_target} g" if brief.carb_target else "Pendiente",
            brief.carb_target is None,
        ),
        NutritionBriefSummaryItem(
            "Grasas objetivo",
            f"{brief.fat_target} g" if brief.fat_target else "Pendiente",
            brief.fat_target is None,
        ),
        NutritionBriefSummaryItem(
            "Peso",
            f"{_format_number(brief.weight_kg)} kg" if brief.weight_kg else "Pendiente",
            brief.weight_kg is None,
        ),
        NutritionBriefSummaryItem(
            "Altura",
            f"{brief.height_cm} cm" if brief.height_cm else "Pendiente",
            brief.height_cm is None,
        ),
        NutritionBriefSummaryItem(
            "Edad",
            f"{brief.age_years} años" if brief.age_years else "Pendiente",
            brief.age_years is None,
        ),
        NutritionBriefSummaryItem(
            "Sexo",
            brief.sex_label,
            brief.sex is None,
        ),
        NutritionBriefSummaryItem(
            "Actividad",
            brief.activity_level_label,
            brief.activity_level is None,
        ),
        NutritionBriefSummaryItem(
            "Ajuste energético",
            brief.energy_adjustment_label,
            brief.energy_adjustment is None,
        ),
        NutritionBriefSummaryItem(
            "Complejidad",
            brief.complexity_label,
            brief.complexity_level is None,
        ),
        NutritionBriefSummaryItem(
            "Presupuesto",
            brief.budget_label,
            brief.budget_level is None,
        ),
        NutritionBriefSummaryItem(
            "Preferencias",
            _format_style_and_foods(brief),
            not bool(brief.style_preferences or brief.preferred_foods),
        ),
        NutritionBriefSummaryItem(
            "Exclusiones",
            _format_list(brief.excluded_foods, fallback="Sin exclusiones detectadas"),
        ),
    ]


def build_completed_summary_items(brief: NutritionBrief) -> list[NutritionBriefSummaryItem]:
    return [
        item
        for item in build_summary_items(brief)
        if not item.is_pending
        and item.value
        and item.value not in {"Pendiente", "Sin exclusiones detectadas"}
    ]


def is_brief_ready_for_proposal(brief: NutritionBrief) -> bool:
    return not build_required_follow_up_questions(brief)


def can_estimate_energy_expenditure(brief: NutritionBrief) -> bool:
    return all((
        brief.weight_kg,
        brief.height_cm,
        brief.age_years,
        brief.sex,
        brief.activity_level,
    ))


def _missing_energy_inputs(brief: NutritionBrief) -> list[str]:
    missing = []
    if not brief.weight_kg:
        missing.append("peso")
    if not brief.height_cm:
        missing.append("altura")
    if not brief.age_years:
        missing.append("edad")
    if not brief.sex:
        missing.append("sexo")
    if not brief.activity_level:
        missing.append("nivel de actividad")
    return missing


def build_required_follow_up_questions(brief: NutritionBrief) -> list[str]:
    questions = []

    if brief.subject_source is None:
        questions.append(
            "¿Usamos los datos de tu ficha personal para calcular esta propuesta o quieres entregar datos nuevos para otra persona?"
        )

    if brief.goal is None:
        questions.append("¿Cuál es tu objetivo principal: bajar grasa, ganar masa, mantenerte o mejorar rendimiento?")

    if brief.meals_per_day is None:
        questions.append("¿Cuántas comidas quieres tener al día?")

    if not brief.style_preferences and brief.complexity_level is None and brief.budget_level is None:
        questions.append("¿Prefieres algo simple, económico, variado o con poco tiempo de preparación?")

    if brief.calorie_target is None and not can_estimate_energy_expenditure(brief):
        missing = _missing_energy_inputs(brief)
        questions.append(
            "Para estimar tu gasto calórico y definir un objetivo calórico necesito "
            + ", ".join(missing)
            + ". Puedes responder todo junto, por ejemplo: peso 80 kg, altura 175 cm, 30 años, hombre, actividad moderada."
        )

    return questions


def build_follow_up_questions(brief: NutritionBrief) -> list[str]:
    questions = build_required_follow_up_questions(brief)

    if brief.training_frequency is None:
        questions.append("¿Entrenas actualmente? ¿Cuántos días por semana?")

    if brief.protein_target is None:
        questions.append("¿Tienes una meta de proteína diaria o prefieres que MyScoope la estime más adelante?")

    if brief.complexity_level is None:
        questions.append("¿Qué nivel de complejidad te acomoda: muy simple, medio o más variado?")

    if brief.budget_level is None:
        questions.append("¿Quieres priorizar bajo presupuesto, presupuesto medio o flexibilidad?")

    if not brief.excluded_foods:
        questions.append("¿Hay alimentos que quieras evitar o que no te gusten?")

    return questions[:6]


def _format_style_and_foods(brief: NutritionBrief) -> str:
    style_labels = [_choice_label(STYLE_CHOICES, style, style) for style in brief.style_preferences]
    return _format_list(style_labels + brief.preferred_foods)


def _build_acknowledgements(brief: NutritionBrief) -> list[str]:
    acknowledgements = []
    if brief.subject_source == SUBJECT_SOURCE_SELF_PROFILE:
        acknowledgements.append("Usaré tu ficha personal como base de cálculo.")
    elif brief.subject_source == SUBJECT_SOURCE_EXTERNAL_CHAT_DATA:
        acknowledgements.append("Usaré datos externos para esta propuesta.")
    elif brief.subject_source == SUBJECT_SOURCE_MANUAL_CHAT_DATA:
        acknowledgements.append("Usaré datos temporales entregados en el chat para esta propuesta.")
    if brief.goal:
        acknowledgements.append(f"Tomé como objetivo: {brief.goal_label.lower()}.")
    if brief.meals_per_day:
        acknowledgements.append(f"Registré {brief.meals_per_day} comidas al día.")
    if brief.training_frequency is not None:
        acknowledgements.append(f"Consideraré {brief.training_frequency} entrenamientos por semana.")
    if brief.style_preferences or brief.complexity_level or brief.budget_level:
        preferences = []
        if brief.style_preferences:
            preferences.append(_format_style_and_foods(brief).lower())
        if brief.complexity_level:
            preferences.append(brief.complexity_label.lower())
        if brief.budget_level:
            preferences.append(f"presupuesto {brief.budget_label.lower()}")
        acknowledgements.append(f"Preferencia registrada: {_format_list(preferences).lower()}.")
    if brief.excluded_foods:
        acknowledgements.append(f"Excluiré {_format_list(brief.excluded_foods).lower()}.")
    return acknowledgements[-3:]


def _build_brief_pieces(brief: NutritionBrief) -> list[str]:
    pieces = [
        f"objetivo {brief.goal_label.lower()}",
        f"{brief.meals_per_day} comidas" if brief.meals_per_day else "comidas por definir",
    ]
    if brief.training_frequency is not None:
        pieces.append(f"{brief.training_frequency} entrenamientos por semana")
    if brief.style_preferences:
        pieces.append(f"estilo {_format_style_and_foods(brief).lower()}")
    if brief.excluded_foods:
        pieces.append(f"sin {_format_list(brief.excluded_foods).lower()}")
    return pieces


def _normalize_food_hint(food: str) -> str:
    return _normalize_prompt(food)


def _format_list(values: Iterable[str], fallback: str = "Pendiente") -> str:
    cleaned = [value.replace("_", " ").capitalize() for value in values if value]
    return ", ".join(cleaned) if cleaned else fallback


def _is_brief_preview_request(message: str) -> bool:
    prompt = _normalize_prompt(message)
    return "brief" in prompt and _contains_any(
        prompt,
        ("ver", "mostrar", "revisar", "ensena", "enseña", "dame", "muestrame", "muéstrame"),
    )


def _contains_any(prompt: str, keywords: Iterable[str]) -> bool:
    return any(_normalize_prompt(keyword) in prompt for keyword in keywords)


def _choice_label(choices: Iterable[tuple[str, str]], value: str | None, fallback: str) -> str:
    for option_value, label in choices:
        if option_value == (value or ""):
            return label
    return fallback



def _clean_ppk_weight_source(value: str | None) -> str:
    value = str(value or "").strip()
    allowed = {key for key, _label in PPK_WEIGHT_SOURCE_CHOICES}
    return value if value in allowed else PPK_WEIGHT_SOURCE_UNKNOWN


def apply_subject_context(brief: NutritionBrief, *, user=None) -> NutritionBrief:
    """Attach the explicit nutrition subject used by AI Intake.

    The user's ficha is only used when the conversation selects it. If the
    prompt includes body data but no explicit subject, the values are treated as
    temporary chat data for this proposal instead of silently falling back to the
    authenticated user's profile.
    """

    source = brief.subject_source or _infer_subject_source_from_brief(brief)
    if not source:
        return brief

    chat_context = _chat_context_from_brief(brief)
    try:
        subject = build_nutrition_subject_context(
            user=user,
            source=source,
            chat_context=chat_context,
        )
    except (AttributeError, NutritionSubjectContextError):
        return replace(brief, subject_source=source)

    return replace(
        brief,
        subject_source=subject.source,
        ppk_weight_source=subject.ppk_weight_source,
        requires_library_ppk_warning=subject.requires_library_ppk_warning,
        weight_kg=brief.weight_kg if brief.weight_kg is not None else subject.weight_kg,
        height_cm=brief.height_cm if brief.height_cm is not None else subject.height_cm,
        age_years=brief.age_years if brief.age_years is not None else subject.age_years,
        sex=brief.sex or subject.sex,
        activity_level=brief.activity_level or subject.activity_level,
        training_frequency=(
            brief.training_frequency
            if brief.training_frequency is not None
            else subject.training_frequency
        ),
    )


def _infer_subject_source_from_brief(brief: NutritionBrief) -> str | None:
    if any((brief.weight_kg, brief.height_cm, brief.age_years, brief.sex)):
        return SUBJECT_SOURCE_MANUAL_CHAT_DATA
    return None


def _chat_context_from_brief(brief: NutritionBrief) -> dict:
    return {
        "weight_kg": brief.weight_kg,
        "height_cm": brief.height_cm,
        "age_years": brief.age_years,
        "sex": brief.sex,
        "activity_level": brief.activity_level,
        "training_frequency": brief.training_frequency,
    }

def _clean_choice(value: object, choices: Iterable[tuple[str, str]]) -> str | None:
    value = str(value or "").strip()
    allowed_values = {option_value for option_value, _ in choices}
    return value if value in allowed_values and value else None


def _clean_multi_choice(values: Iterable[object], choices: Iterable[tuple[str, str]]) -> list[str]:
    allowed_values = {option_value for option_value, _ in choices if option_value}
    cleaned = []
    for value in values:
        value = str(value or "").strip()
        if value in allowed_values and value not in cleaned:
            cleaned.append(value)
    return cleaned


def _parse_float(value) -> float | None:
    try:
        return float(str(value).replace(",", "."))
    except (TypeError, ValueError):
        return None


def _clean_float(value, *, min_value: float, max_value: float) -> float | None:
    parsed = _parse_float(value)
    if parsed is None or parsed < min_value or parsed > max_value:
        return None
    return round(parsed, 2)


def _format_number(value: float | None) -> str:
    if value is None:
        return ""
    if float(value).is_integer():
        return str(int(value))
    return f"{value:.1f}"


def _clean_int(value: object, *, min_value: int, max_value: int) -> int | None:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return None
    if min_value <= parsed <= max_value:
        return parsed
    return None


def _split_free_text_list(value: object) -> list[str]:
    text = str(value or "").strip()
    if not text:
        return []
    return _clean_text_list(re.split(r"[,\n]", text))


def _clean_text_list(values: Iterable[object]) -> list[str]:
    cleaned = []
    for value in values:
        text = " ".join(str(value or "").strip().split())
        if text and text not in cleaned:
            cleaned.append(text)
    return cleaned
