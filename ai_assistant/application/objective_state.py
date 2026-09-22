from __future__ import annotations

import re
import unicodedata
from collections.abc import Mapping, Sequence
from typing import Any

ACTIVE_WORK_VERSION = "ai_assistant.active_work.v1"

_RESOURCE_PATTERNS: tuple[tuple[str, str], ...] = (
    ("calendarization", r"\b(?:calendari\w*|calendariz\w*)\b"),
    ("saved_comparison", r"\b(?:comparacion\w*|comparison\w*)\b"),
    ("program", r"\b(?:programas?|programs?|semana\w*)\b"),
    ("dailyplan", r"\b(?:dailyplans?|planes?|plan diario|dietas?)\b"),
    ("meal", r"\b(?:comidas?|meals?|colacion\w*|desayuno\w*|almuerzo\w*|cena\w*)\b"),
    ("food", r"\b(?:alimentos?|foods?|ingredientes?)\b"),
    ("proposal", r"\b(?:propuestas?|proposals?)\b"),
    ("profile", r"\b(?:perfil|ficha|peso|altura|edad|sexo|actividad)\b"),
    ("preferences", r"\b(?:preferencias?|alergias?|intolerancias?|evito|prefiero)\b"),
)

_MUTATION_ACTION_PATTERNS: tuple[tuple[str, str], ...] = (
    ("rename", r"\b(?:renombr\w*|nombr\w*)\b"),
    ("delete", r"\b(?:elimin\w*|borr\w*)\b"),
    ("pause", r"\b(?:paus\w*)\b"),
    ("resume", r"\b(?:reanud\w*)\b"),
    ("cancel", r"\b(?:cancel\w*)\b"),
    ("approve", r"\b(?:aprob\w*|aprueb\w*)\b"),
    ("reject", r"\b(?:rechaz\w*)\b"),
    ("apply", r"\b(?:aplic\w*)\b"),
    ("duplicate", r"\b(?:duplic\w*)\b"),
    ("remove", r"\b(?:quit\w*|remov\w*)\b"),
    ("add", r"\b(?:agreg\w*|anad\w*|inclu\w*|incorpor\w*)\b"),
    ("update", r"\b(?:actualiz\w*|cambi\w*|ajust\w*|aument\w*|reduc\w*|modific\w*)\b"),
)

_NEGATED_MUTATION_PREFIX = re.compile(
    r"(?:\bno(?:\s+\w+){0,3}\s+|\bsin(?:\s+(?:mi|tu|su|la|el|un|una))?\s*)$"
)

_CREATE_PATTERN = re.compile(
    r"\b(?:crea\w*|genera\w*|prepara\w*|arm\w*|hagam\w*|dame|quiero|necesito|haz(?:me|lo)?)\b"
)
_QUERY_PATTERN = re.compile(
    r"(?:\?|\b(?:que|cual(?:es)?|cuanto(?:s)?|como|donde|lista\w*|muestra\w*|"
    r"busca\w*|revisa\w*|dime|tengo|hay|existe\w*)\b)"
)
_CONTINUATION_PATTERN = re.compile(
    r"^(?:si|ok|okay|dale|continua|avanza(?:mos)?|hazlo|hagamoslo|"
    r"perfecto|de acuerdo|con eso basta(?:,? avancemos)?|adelante)[.! ]*$"
)
_NUTRITION_GOAL_PATTERN = re.compile(
    r"\b(?:perder|bajar) (?:grasa|peso)|\bganar (?:masa|musculo)|"
    r"\bcomer mejor|\bmejorar mi alimentacion\b"
)
_PROFILE_FACT_PATTERN = re.compile(
    r"\b(?:peso|mido|altura|anos|hombre|mujer|masculino|femenino|"
    r"sedentari\w*|actividad|entreno|entrenamiento)\b|\b\d{2,3}(?:[.,]\d+)?\s*(?:kg|cm)\b"
)
_PREFERENCE_FACT_PATTERN = re.compile(
    r"\b(?:preferencias?|prefiero|evito|alerg\w*|intoler\w*|vegetarian\w*|vegan\w*|"
    r"sin gluten|sin lactosa|presupuesto|cocinar|variedad|simple)\b"
)
_MEALS_PER_DAY_FACT_PATTERN = re.compile(r"\b[1-9]\s+comidas?\b")


def infer_active_work(
    conversation_state: Any | None,
    *,
    current_user_message: str = "",
) -> dict[str, Any]:
    """Infer the unresolved outcome without granting authority to mutate state.

    This is deliberately a small routing signal, not a second assistant or an
    authorization layer. Product tools still resolve ownership, validate exact
    arguments and require trusted UI approval for every persistent change.
    """

    current = _classify_objective(current_user_message)
    if current is not None:
        return _active_payload(current, source="current_message")

    normalized_current = _normalize(current_user_message)
    should_resume = not normalized_current or bool(
        _CONTINUATION_PATTERN.fullmatch(normalized_current)
    ) or bool(_PROFILE_FACT_PATTERN.search(normalized_current)) or bool(
        _PREFERENCE_FACT_PATTERN.search(normalized_current)
    ) or bool(
        _MEALS_PER_DAY_FACT_PATTERN.search(normalized_current)
    )
    if not should_resume:
        return _response_only_payload()

    messages: Sequence[Any] = tuple(getattr(conversation_state, "messages", ()) or ())
    skipped_current_duplicate = False
    for message in reversed(messages):
        if _is_completed_review_artifact(message):
            break
        if str(getattr(message, "role", "")) != "user":
            continue
        text = str(getattr(message, "text", "") or "")
        if (
            not skipped_current_duplicate
            and normalized_current
            and _normalize(text) == normalized_current
        ):
            skipped_current_duplicate = True
            continue
        objective = _classify_objective(text)
        if objective is not None:
            return _active_payload(objective, source="conversation_history")
    return _response_only_payload()


def _classify_objective(value: Any) -> dict[str, str] | None:
    text = _normalize(value)
    if not text or _CONTINUATION_PATTERN.fullmatch(text):
        return None

    resource = _resource(text)
    mutation_action = _mutation_action(text)
    if resource and mutation_action:
        return {
            "objective": "prepare_reviewable_workspace_patch",
            "expected_outcome": "prepared_patch",
            "resource": resource,
            "action": mutation_action,
        }

    if (
        resource == "program"
        and "mejor" in text
        and _NUTRITION_GOAL_PATTERN.search(text)
    ):
        return {
            "objective": "record_conversation_facts",
            "expected_outcome": "workspace_advanced",
            "resource": resource,
            "action": "update_draft",
        }

    has_preference_fact = bool(
        _PREFERENCE_FACT_PATTERN.search(text)
        or _MEALS_PER_DAY_FACT_PATTERN.search(text)
    )
    if has_preference_fact and "?" not in text and (
        resource in {"", "preferences"}
        or (
            resource == "meal"
            and not _CREATE_PATTERN.search(text)
        )
        or re.search(r"\b(?:mas variedad|poco presupuesto|cocinar rapido)\b", text)
    ):
        return {
            "objective": "record_conversation_facts",
            "expected_outcome": "workspace_advanced",
            "resource": "preferences",
            "action": "update_draft",
        }

    if resource and _CREATE_PATTERN.search(text):
        if resource == "dailyplan":
            return {
                "objective": "create_reviewable_dailyplan_proposal",
                "expected_outcome": "nutrition_proposal",
                "resource": resource,
                "action": "create",
            }
        if resource == "meal":
            return {
                "objective": "create_reviewable_meal_proposal",
                "expected_outcome": "nutrition_proposal",
                "resource": resource,
                "action": "create",
            }
        return {
            "objective": "prepare_reviewable_workspace_patch",
            "expected_outcome": "prepared_patch",
            "resource": resource,
            "action": "create",
        }

    if _PROFILE_FACT_PATTERN.search(text) and "?" not in text:
        return {
            "objective": "record_conversation_facts",
            "expected_outcome": "workspace_advanced",
            "resource": "profile",
            "action": "update_draft",
        }

    if _NUTRITION_GOAL_PATTERN.search(text):
        return {
            "objective": "create_reviewable_dailyplan_proposal",
            "expected_outcome": "nutrition_proposal",
            "resource": "dailyplan",
            "action": "create",
        }

    if resource and _QUERY_PATTERN.search(text):
        return {
            "objective": "query_workspace",
            "expected_outcome": "workspace_query",
            "resource": resource,
            "action": "read",
        }

    if _PREFERENCE_FACT_PATTERN.search(text):
        return {
            "objective": "record_conversation_facts",
            "expected_outcome": "workspace_advanced",
            "resource": "preferences",
            "action": "update_draft",
        }
    return None


def _active_payload(objective: Mapping[str, str], *, source: str) -> dict[str, Any]:
    return {
        "version": ACTIVE_WORK_VERSION,
        "status": "active",
        "objective": objective["objective"],
        "expected_outcome": objective["expected_outcome"],
        "resource": objective["resource"],
        "action": objective["action"],
        "source": source,
        "inference_grants_write_authority": False,
    }


def _response_only_payload() -> dict[str, Any]:
    return {
        "version": ACTIVE_WORK_VERSION,
        "status": "response_only",
        "objective": "respond_to_current_message",
        "expected_outcome": "response_only",
        "resource": "none",
        "action": "respond",
        "source": "default",
        "inference_grants_write_authority": False,
    }


def _resource(text: str) -> str:
    matches = [
        (match.start(), index, value)
        for index, (value, pattern) in enumerate(_RESOURCE_PATTERNS)
        if (match := re.search(pattern, text)) is not None
    ]
    concrete_matches = [item for item in matches if item[2] != "proposal"]
    create_match = _CREATE_PATTERN.search(text)
    if create_match:
        created_resource_matches = [
            item for item in concrete_matches if item[0] >= create_match.end()
        ]
        if created_resource_matches:
            return min(created_resource_matches)[2]
    if concrete_matches:
        return min(concrete_matches)[2]
    return min(matches, default=(0, 0, ""))[2]


def _mutation_action(text: str) -> str:
    for value, pattern in _MUTATION_ACTION_PATTERNS:
        for match in re.finditer(pattern, text):
            prefix = text[max(0, match.start() - 48) : match.start()]
            if _NEGATED_MUTATION_PREFIX.search(prefix):
                continue
            return value
    return ""


def _matched_value(text: str, patterns: Sequence[tuple[str, str]]) -> str:
    for value, pattern in patterns:
        if re.search(pattern, text):
            return value
    return ""


def _is_completed_review_artifact(message: Any) -> bool:
    return any(
        isinstance(getattr(message, field_name, None), Mapping)
        for field_name in ("proposal_review_card", "prepared_action_card")
    )


def _normalize(value: Any) -> str:
    text = unicodedata.normalize("NFKD", str(value or "").strip().lower())
    text = "".join(char for char in text if not unicodedata.combining(char))
    return " ".join(text.split())
