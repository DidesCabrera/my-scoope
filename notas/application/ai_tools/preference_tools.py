from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from notas.application.ai_tools.runtime import run_ai_tool

PREFERENCE_DRAFT_FIELDS = (
    "dietary_pattern",
    "avoided_foods",
    "preferred_foods",
    "allergies_or_intolerances",
    "preferred_meals_per_day",
    "cooking_time_preference",
    "budget_preference",
    "simplicity_preference",
    "variety_preference",
)

FOOD_PREFERENCE_FIELDS = (
    "dietary_pattern",
    "avoided_foods",
    "preferred_foods",
    "allergies_or_intolerances",
)

MEAL_ORGANIZATION_FIELDS = (
    "preferred_meals_per_day",
    "cooking_time_preference",
    "budget_preference",
    "simplicity_preference",
    "variety_preference",
)

FIELD_LABELS = {
    "dietary_pattern": "Patrón alimentario",
    "avoided_foods": "Alimentos evitados",
    "preferred_foods": "Alimentos preferidos",
    "allergies_or_intolerances": "Alergias o intolerancias",
    "preferred_meals_per_day": "Comidas preferidas",
    "cooking_time_preference": "Tiempo de preparación",
    "budget_preference": "Presupuesto",
    "simplicity_preference": "Simplicidad",
    "variety_preference": "Variedad",
}

SOURCE_LABELS = {
    "profile": "Preferencias guardadas",
    "chat_draft": "Este chat",
    "manual": "Manual",
    "unknown": "Pendiente",
}

DIETARY_PATTERNS = {
    "omnivore",
    "vegetarian",
    "vegan",
    "pescatarian",
    "flexitarian",
}

DIETARY_PATTERN_ALIASES = {
    "omnivore": "omnivore",
    "omnivoro": "omnivore",
    "omnívoro": "omnivore",
    "como de todo": "omnivore",
    "vegetarian": "vegetarian",
    "vegetariano": "vegetarian",
    "vegetariana": "vegetarian",
    "vegan": "vegan",
    "vegano": "vegan",
    "vegana": "vegan",
    "pescatarian": "pescatarian",
    "pescetariano": "pescatarian",
    "pescetariana": "pescatarian",
    "flexitarian": "flexitarian",
    "flexitariano": "flexitarian",
    "flexitariana": "flexitarian",
}

PREFERENCE_LEVELS = {
    "low",
    "medium",
    "high",
    "none",
    "unknown",
}

PREFERENCE_LEVEL_ALIASES = {
    "bajo": "low",
    "baja": "low",
    "poco": "low",
    "medio": "medium",
    "media": "medium",
    "moderado": "medium",
    "moderada": "medium",
    "alto": "high",
    "alta": "high",
    "mucho": "high",
    "sin preferencia": "none",
    "me da igual": "none",
    "no se": "unknown",
    "no sé": "unknown",
}


# DRAFT TOOLS ------------------------------------------------


def _update_preference_draft_data(
    user,
    updates: Mapping[str, Any],
    current_draft: Mapping[str, Any] | None = None,
    field_sources: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    if not isinstance(updates, Mapping) or not updates:
        raise ValueError("preference_draft_updates_required")

    draft = _normalize_preference_draft(current_draft or {})
    incoming_sources = _clean_source_map(field_sources or {})
    changed_fields: list[str] = []
    rejected_fields: dict[str, str] = {}

    for raw_field_name, raw_value in updates.items():
        field_name = _normalize_field_name(raw_field_name)
        if field_name not in PREFERENCE_DRAFT_FIELDS:
            rejected_fields[str(raw_field_name)] = "unsupported_preference_draft_field"
            continue
        value = _normalize_field_value(field_name, raw_value)
        if _is_empty_value(value):
            rejected_fields[field_name] = "invalid_or_empty_value"
            continue
        draft[field_name] = value
        draft["field_sources"][field_name] = incoming_sources.get(field_name) or "chat_draft"
        changed_fields.append(field_name)

    preference_draft = _with_preference_draft_metadata(draft)
    return {
        "preference_draft": preference_draft,
        "changed_fields": _dedupe(changed_fields),
        "rejected_fields": rejected_fields,
        "field_definitions": _field_definitions(),
        "source_boundary": {
            "object": "preference_draft",
            "persistent_preferences_updated": False,
            "writes_allowed": False,
            "renderable_in_chat_thread": False,
            "presentation_mode": "silent_state_update",
            "share_tool": "share_preference_draft_card",
            "persistence_requires_user_approval": True,
            "commit_tool_planned": "commit_preference_update",
        },
    }


def update_preference_draft_tool(
    user,
    *,
    updates: Mapping[str, Any],
    current_draft: Mapping[str, Any] | None = None,
    field_sources: Mapping[str, Any] | None = None,
):
    """Update a non-persistent preference draft from LLM-interpreted user facts."""

    return run_ai_tool(
        _update_preference_draft_data,
        user,
        updates=updates,
        current_draft=current_draft,
        field_sources=field_sources,
        user=user,
    )


def _share_preference_draft_card_data(user, preference_draft: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(preference_draft, Mapping):
        raise ValueError("preference_draft_required")
    draft = _with_preference_draft_metadata(_normalize_preference_draft(preference_draft))
    return {
        "preference_draft_card": _build_preference_draft_card(draft),
        "preference_draft": draft,
        "source_boundary": {
            "object": "preference_draft_card",
            "persistent_preferences_updated": False,
            "writes_allowed": False,
            "renderable_in_chat_thread": True,
            "persistence_requires_user_approval": True,
        },
    }


def share_preference_draft_card_tool(user, *, preference_draft: Mapping[str, Any]):
    """Return a chat-renderable card payload for a preference draft."""

    return run_ai_tool(
        _share_preference_draft_card_data,
        user,
        preference_draft=preference_draft,
        user=user,
    )


# NORMALIZATION ---------------------------------------------


def _normalize_preference_draft(value: Mapping[str, Any]) -> dict[str, Any]:
    payload = dict(value or {})
    draft: dict[str, Any] = {field: None for field in PREFERENCE_DRAFT_FIELDS}
    field_sources = _clean_source_map(payload.get("field_sources") or {})
    for field_name in PREFERENCE_DRAFT_FIELDS:
        normalized = _normalize_field_value(field_name, payload.get(field_name))
        draft[field_name] = normalized
        if not _is_empty_value(normalized) and field_name not in field_sources:
            field_sources[field_name] = "unknown"
    draft["field_sources"] = field_sources
    return draft


def _with_preference_draft_metadata(draft: Mapping[str, Any]) -> dict[str, Any]:
    payload = _normalize_preference_draft(draft)
    known_fields = [
        field_name
        for field_name in PREFERENCE_DRAFT_FIELDS
        if not _is_empty_value(payload.get(field_name))
    ]
    chat_draft_fields = [
        field_name
        for field_name, source in payload.get("field_sources", {}).items()
        if source == "chat_draft" and not _is_empty_value(payload.get(field_name))
    ]
    payload["known_fields"] = known_fields
    payload["chat_draft_fields"] = chat_draft_fields
    payload["has_food_preferences"] = any(field in known_fields for field in FOOD_PREFERENCE_FIELDS)
    payload["has_meal_organization_preferences"] = any(field in known_fields for field in MEAL_ORGANIZATION_FIELDS)
    payload["requires_approval_for_persistence"] = bool(chat_draft_fields)
    return payload


def _build_preference_draft_card(preference_draft: Mapping[str, Any]) -> dict[str, Any]:
    sections = [
        {
            "title": "Preferencias alimentarias",
            "items": [_build_item(preference_draft, field_name) for field_name in FOOD_PREFERENCE_FIELDS],
        },
        {
            "title": "Organización de comidas",
            "items": [_build_item(preference_draft, field_name) for field_name in MEAL_ORGANIZATION_FIELDS],
        },
    ]
    known_count = sum(1 for section in sections for item in section["items"] if not item["is_pending"])
    return {
        "title": "Preferencias para esta propuesta",
        "subtitle": "Información que ayuda a adaptar alimentos y estructura. No cambia tus preferencias guardadas sin aprobación.",
        "sections": sections,
        "known_count": known_count,
        "has_chat_draft_updates": bool(preference_draft.get("chat_draft_fields")),
        "can_update_preferences": False,
        "status": "has_data" if known_count else "empty",
    }


def _build_item(preference_draft: Mapping[str, Any], field_name: str) -> dict[str, Any]:
    value = preference_draft.get(field_name)
    source = (preference_draft.get("field_sources") or {}).get(field_name) or "unknown"
    return {
        "key": field_name,
        "label": FIELD_LABELS[field_name],
        "value": _format_preference_value(field_name, value),
        "is_pending": _is_empty_value(value),
        "source": source,
        "source_label": SOURCE_LABELS.get(source, SOURCE_LABELS["unknown"]),
    }


def _field_definitions() -> dict[str, dict[str, Any]]:
    return {
        "dietary_pattern": {
            "label": FIELD_LABELS["dietary_pattern"],
            "description": "Patrón alimentario declarado por el usuario. Diferencia restricciones fuertes de preferencias suaves.",
            "allowed_values": sorted(DIETARY_PATTERNS),
            "examples": ["soy vegano", "vegetariana", "como de todo"],
            "persistence": "future preference profile after explicit approval",
        },
        "avoided_foods": {
            "label": FIELD_LABELS["avoided_foods"],
            "description": "Alimentos que el usuario evita o no quiere en propuestas. Pueden ser restricciones fuertes o preferencias según contexto.",
            "examples": ["evito pescado", "no me gusta el atún", "sin lácteos"],
            "persistence": "future preference profile after explicit approval",
        },
        "preferred_foods": {
            "label": FIELD_LABELS["preferred_foods"],
            "description": "Alimentos que el usuario prefiere y que pueden mejorar adherencia.",
            "examples": ["prefiero pollo", "me gustan huevos y arroz"],
            "persistence": "future preference profile after explicit approval",
        },
        "allergies_or_intolerances": {
            "label": FIELD_LABELS["allergies_or_intolerances"],
            "description": "Alergias o intolerancias declaradas. Deben tratarse como restricciones fuertes cuando el usuario lo indique.",
            "examples": ["soy intolerante a la lactosa", "alergia al maní"],
            "persistence": "future preference profile after explicit approval",
        },
        "preferred_meals_per_day": {
            "label": FIELD_LABELS["preferred_meals_per_day"],
            "description": "Número habitual o preferido de comidas. No pertenece a la ficha personal base y puede cambiar por propuesta.",
            "examples": ["3 comidas", "prefiero cinco comidas al día"],
            "persistence": "proposal/preference draft, not personal base profile",
        },
        "cooking_time_preference": {
            "label": FIELD_LABELS["cooking_time_preference"],
            "description": "Preferencia de tiempo de preparación.",
            "allowed_values": sorted(PREFERENCE_LEVELS),
            "examples": ["poco tiempo", "puedo cocinar más"],
            "persistence": "future preference profile after explicit approval",
        },
        "budget_preference": {
            "label": FIELD_LABELS["budget_preference"],
            "description": "Sensibilidad del usuario al presupuesto.",
            "allowed_values": sorted(PREFERENCE_LEVELS),
            "examples": ["económico", "presupuesto bajo"],
            "persistence": "future preference profile after explicit approval",
        },
        "simplicity_preference": {
            "label": FIELD_LABELS["simplicity_preference"],
            "description": "Preferencia por recetas simples o más elaboradas.",
            "allowed_values": sorted(PREFERENCE_LEVELS),
            "examples": ["simple", "no muy elaborado"],
            "persistence": "future preference profile after explicit approval",
        },
        "variety_preference": {
            "label": FIELD_LABELS["variety_preference"],
            "description": "Preferencia por variedad versus repetición.",
            "allowed_values": sorted(PREFERENCE_LEVELS),
            "examples": ["variado", "puedo repetir comidas"],
            "persistence": "future preference profile after explicit approval",
        },
    }


def _normalize_field_name(value: Any) -> str:
    normalized = str(value or "").strip().lower().replace("-", "_").replace(" ", "_")
    aliases = {
        "pattern": "dietary_pattern",
        "patron": "dietary_pattern",
        "patrón": "dietary_pattern",
        "tipo_alimentacion": "dietary_pattern",
        "diet": "dietary_pattern",
        "dieta": "dietary_pattern",
        "avoid": "avoided_foods",
        "avoid_foods": "avoided_foods",
        "excluded_foods": "avoided_foods",
        "excluir": "avoided_foods",
        "evitar": "avoided_foods",
        "preferred": "preferred_foods",
        "prefer": "preferred_foods",
        "preferidos": "preferred_foods",
        "allergies": "allergies_or_intolerances",
        "allergy": "allergies_or_intolerances",
        "intolerances": "allergies_or_intolerances",
        "alergias": "allergies_or_intolerances",
        "intolerancias": "allergies_or_intolerances",
        "meals_per_day": "preferred_meals_per_day",
        "comidas_por_dia": "preferred_meals_per_day",
        "comidas_al_dia": "preferred_meals_per_day",
        "cooking_time": "cooking_time_preference",
        "tiempo_cocina": "cooking_time_preference",
        "budget": "budget_preference",
        "presupuesto": "budget_preference",
        "simple": "simplicity_preference",
        "simplicity": "simplicity_preference",
        "variety": "variety_preference",
        "variedad": "variety_preference",
    }
    return aliases.get(normalized, normalized)


def _normalize_field_value(field_name: str, value: Any) -> Any:
    if _is_empty_value(value):
        return None
    if field_name in {"avoided_foods", "preferred_foods", "allergies_or_intolerances"}:
        return _clean_term_list(value)
    if field_name == "dietary_pattern":
        normalized = _normalize_text(value)
        return DIETARY_PATTERN_ALIASES.get(normalized, normalized if normalized in DIETARY_PATTERNS else None)
    if field_name == "preferred_meals_per_day":
        number = _int_or_none(value)
        if number is None or not 1 <= number <= 10:
            return None
        return number
    if field_name in {"cooking_time_preference", "budget_preference", "simplicity_preference", "variety_preference"}:
        normalized = _normalize_text(value)
        return PREFERENCE_LEVEL_ALIASES.get(normalized, normalized if normalized in PREFERENCE_LEVELS else None)
    return None


def _format_preference_value(field_name: str, value: Any) -> str:
    if _is_empty_value(value):
        return "Pendiente"
    if isinstance(value, list):
        return ", ".join(str(item) for item in value if item) or "Pendiente"
    if field_name == "dietary_pattern":
        return {
            "omnivore": "Omnívoro",
            "vegetarian": "Vegetariano",
            "vegan": "Vegano",
            "pescatarian": "Pescetariano",
            "flexitarian": "Flexitariano",
        }.get(str(value), str(value))
    if field_name == "preferred_meals_per_day":
        return f"{int(value)} comidas"
    if field_name in {"cooking_time_preference", "budget_preference", "simplicity_preference", "variety_preference"}:
        return {
            "low": "Baja",
            "medium": "Media",
            "high": "Alta",
            "none": "Sin preferencia",
            "unknown": "Pendiente",
        }.get(str(value), str(value))
    return str(value)


def _clean_term_list(value: Any) -> list[str]:
    if isinstance(value, str):
        raw_values = value.replace(";", ",").split(",")
    elif isinstance(value, (list, tuple, set)):
        raw_values = list(value)
    else:
        raw_values = [value]
    result: list[str] = []
    seen: set[str] = set()
    for raw_item in raw_values:
        item = " ".join(str(raw_item or "").strip().split())
        if not item:
            continue
        key = _normalize_text(item)
        if key in seen:
            continue
        seen.add(key)
        result.append(item)
    return result[:20]


def _clean_source_map(value: Mapping[str, Any]) -> dict[str, str]:
    if not isinstance(value, Mapping):
        return {}
    cleaned = {}
    for key, raw_source in value.items():
        field_name = _normalize_field_name(key)
        if field_name not in PREFERENCE_DRAFT_FIELDS:
            continue
        source = str(raw_source or "").strip().lower()
        cleaned[field_name] = source if source in SOURCE_LABELS else "unknown"
    return cleaned


def _normalize_text(value: Any) -> str:
    return " ".join(str(value or "").strip().lower().split())


def _is_empty_value(value: Any) -> bool:
    if value is None:
        return True
    if isinstance(value, str):
        return not value.strip()
    if isinstance(value, (list, tuple, set, dict)):
        return len(value) == 0
    return False


def _int_or_none(value: Any) -> int | None:
    try:
        return int(float(str(value).replace(",", ".").strip()))
    except (TypeError, ValueError):
        return None


def _dedupe(values: list[str]) -> list[str]:
    result = []
    for value in values:
        if value and value not in result:
            result.append(value)
    return result
