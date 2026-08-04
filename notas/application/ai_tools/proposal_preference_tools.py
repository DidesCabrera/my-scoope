from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from notas.application.ai_tools.runtime import run_ai_tool

PROPOSAL_PREFERENCE_FIELDS = (
    "goal",
    "requested_entity",
    "meals_per_day",
    "energy_adjustment",
    "complexity_level",
    "calorie_target",
    "protein_target",
    "carb_target",
    "fat_target",
    "notes",
)

TARGET_FIELDS = (
    "calorie_target",
    "protein_target",
    "carb_target",
    "fat_target",
)

FIELD_LABELS = {
    "goal": "Objetivo",
    "requested_entity": "Tipo de propuesta",
    "meals_per_day": "Comidas para esta propuesta",
    "energy_adjustment": "Ajuste energético",
    "complexity_level": "Complejidad de la propuesta",
    "calorie_target": "Calorías objetivo",
    "protein_target": "Proteína objetivo",
    "carb_target": "Carbohidratos objetivo",
    "fat_target": "Grasa objetivo",
    "notes": "Notas de propuesta",
}

SOURCE_LABELS = {
    "chat_draft": "Este chat",
    "manual": "Manual",
    "tool": "Tool",
    "unknown": "Pendiente",
}

GOAL_LABELS = {
    "fat_loss": "Bajar grasa",
    "muscle_gain": "Ganar masa muscular",
    "maintenance": "Mantención",
    "performance": "Rendimiento deportivo",
    "healthy_eating": "Comer mejor",
}

REQUESTED_ENTITY_LABELS = {
    "daily_plan": "Plan diario",
    "program": "Programa semanal",
}

COMPLEXITY_LABELS = {
    "low": "Simple",
    "medium": "Intermedia",
    "high": "Más elaborada",
}

COMPLEXITY_ALIASES = {
    "low": "low",
    "simple": "low",
    "sencillo": "low",
    "sencilla": "low",
    "algo simple": "low",
    "facil": "low",
    "fácil": "low",
    "medium": "medium",
    "intermedio": "medium",
    "intermedia": "medium",
    "moderado": "medium",
    "moderada": "medium",
    "high": "high",
    "complejo": "high",
    "compleja": "high",
    "elaborado": "high",
    "elaborada": "high",
    "variado": "high",
    "variada": "high",
}

ENERGY_ADJUSTMENT_LABELS = {
    "deficit_mild": "Déficit leve",
    "deficit_moderate": "Déficit moderado",
    "deficit_large": "Déficit grande",
    "surplus_mild": "Superávit leve",
    "surplus_moderate": "Superávit moderado",
    "surplus_large": "Superávit grande",
    "maintenance": "Mantención",
}


GOAL_ALIASES = {
    "fat_loss": "fat_loss",
    "bajar grasa": "fat_loss",
    "bajar de grasa": "fat_loss",
    "perder grasa": "fat_loss",
    "definir": "fat_loss",
    "muscle_gain": "muscle_gain",
    "ganar masa": "muscle_gain",
    "ganar musculo": "muscle_gain",
    "ganar músculo": "muscle_gain",
    "ganar musculos": "muscle_gain",
    "ganar músculos": "muscle_gain",
    "gamar musculo": "muscle_gain",
    "gamar musculos": "muscle_gain",
    "gamar músculo": "muscle_gain",
    "gamar músculos": "muscle_gain",
    "ganra masa": "muscle_gain",
    "ganra musculo": "muscle_gain",
    "aumentar masa": "muscle_gain",
    "aumentar de masa": "muscle_gain",
    "aumentar musculo": "muscle_gain",
    "aumentar músculo": "muscle_gain",
    "aumentar de musculo": "muscle_gain",
    "aumentar de músculo": "muscle_gain",
    "aumentar de musculos": "muscle_gain",
    "aumentar de músculos": "muscle_gain",
    "aumentar de muscilo": "muscle_gain",
    "aumennter de muscilo": "muscle_gain",
    "aumenter de musculo": "muscle_gain",
    "aumentar muscilo": "muscle_gain",
    "hipertrofia": "muscle_gain",
    "volumen": "muscle_gain",
    "maintenance": "maintenance",
    "mantener": "maintenance",
    "mantencion": "maintenance",
    "mantención": "maintenance",
    "performance": "performance",
    "rendimiento": "performance",
    "healthy_eating": "healthy_eating",
    "comer mejor": "healthy_eating",
}

ENERGY_ALIASES = {
    "deficit_mild": "deficit_mild",
    "deficit leve": "deficit_mild",
    "leve deficit": "deficit_mild",
    "deficit_moderate": "deficit_moderate",
    "deficit moderado": "deficit_moderate",
    "deficit_large": "deficit_large",
    "deficit grande": "deficit_large",
    "agresivo": "deficit_large",
    "surplus_mild": "surplus_mild",
    "superavit leve": "surplus_mild",
    "superávit leve": "surplus_mild",
    "surplus_moderate": "surplus_moderate",
    "superavit moderado": "surplus_moderate",
    "superávit moderado": "surplus_moderate",
    "surplus_large": "surplus_large",
    "superavit grande": "surplus_large",
    "maintenance": "maintenance",
    "mantencion": "maintenance",
    "mantención": "maintenance",
}

ENTITY_ALIASES = {
    "daily_plan": "daily_plan",
    "plan diario": "daily_plan",
    "día": "daily_plan",
    "dia": "daily_plan",
    "program": "program",
    "programa": "program",
    "programa semanal": "program",
    "semana": "program",
}


def _update_proposal_preferences_data(
    user,
    updates: Mapping[str, Any],
    current_preferences: Mapping[str, Any] | None = None,
    field_sources: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    if not isinstance(updates, Mapping) or not updates:
        raise ValueError("proposal_preferences_updates_required")

    draft = _normalize_proposal_preferences(current_preferences or {})
    incoming_sources = _clean_source_map(field_sources or {})
    changed_fields: list[str] = []
    rejected_fields: dict[str, str] = {}

    for raw_field_name, raw_value in updates.items():
        field_name = _normalize_field_name(raw_field_name)
        if field_name not in PROPOSAL_PREFERENCE_FIELDS:
            rejected_fields[str(raw_field_name)] = "unsupported_proposal_preference_field"
            continue
        value = _normalize_field_value(field_name, raw_value)
        if value is None:
            rejected_fields[field_name] = "invalid_or_empty_value"
            continue
        draft[field_name] = value
        draft["field_sources"][field_name] = incoming_sources.get(field_name) or "chat_draft"
        changed_fields.append(field_name)

    proposal_preferences = _with_proposal_preferences_metadata(draft)
    return {
        "proposal_preferences": proposal_preferences,
        "changed_fields": changed_fields,
        "rejected_fields": rejected_fields,
        "field_definitions": _field_definitions(),
        "nutrition_brief_patch": _build_nutrition_brief_patch(proposal_preferences),
        "source_boundary": {
            "object": "proposal_preferences",
            "persistent_profile_updated": False,
            "persistent_preferences_updated": False,
            "writes_allowed": False,
            "proposal_scoped_only": True,
            "renderable_in_chat_thread": False,
            "presentation_mode": "silent_state_update",
            "share_tool": "share_proposal_preferences_card",
            "used_by_proposal_tools": True,
        },
    }


def update_proposal_preferences_tool(
    user,
    *,
    updates: Mapping[str, Any],
    current_preferences: Mapping[str, Any] | None = None,
    field_sources: Mapping[str, Any] | None = None,
):
    """Update non-persistent preferences for the current proposal only."""

    return run_ai_tool(
        _update_proposal_preferences_data,
        user,
        updates=updates,
        current_preferences=current_preferences,
        field_sources=field_sources,
        user=user,
    )


def _share_proposal_preferences_card_data(user, proposal_preferences: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(proposal_preferences, Mapping):
        raise ValueError("proposal_preferences_required")
    draft = _with_proposal_preferences_metadata(_normalize_proposal_preferences(proposal_preferences))
    return {
        "proposal_preferences": draft,
        "proposal_preferences_card": _build_proposal_preferences_card(draft),
        "nutrition_brief_patch": _build_nutrition_brief_patch(draft),
        "source_boundary": {
            "object": "proposal_preferences_card",
            "persistent_profile_updated": False,
            "persistent_preferences_updated": False,
            "writes_allowed": False,
            "proposal_scoped_only": True,
            "renderable_in_chat_thread": True,
        },
    }


def share_proposal_preferences_card_tool(user, *, proposal_preferences: Mapping[str, Any]):
    """Return a chat-renderable card for proposal-scoped preferences."""

    return run_ai_tool(
        _share_proposal_preferences_card_data,
        user,
        proposal_preferences=proposal_preferences,
        user=user,
    )


def _normalize_proposal_preferences(value: Mapping[str, Any]) -> dict[str, Any]:
    draft: dict[str, Any] = {"field_sources": _clean_source_map(value.get("field_sources") or {})}
    for field_name in PROPOSAL_PREFERENCE_FIELDS:
        normalized = _normalize_field_value(field_name, value.get(field_name))
        if normalized is not None:
            draft[field_name] = normalized
    for field_name in list(draft):
        if field_name != "field_sources" and field_name not in draft["field_sources"]:
            draft["field_sources"][field_name] = "chat_draft"
    return draft


def _with_proposal_preferences_metadata(value: Mapping[str, Any]) -> dict[str, Any]:
    draft = _normalize_proposal_preferences(value)
    known_fields = [field for field in PROPOSAL_PREFERENCE_FIELDS if not _is_missing(draft.get(field))]
    target_fields = [field for field in TARGET_FIELDS if not _is_missing(draft.get(field))]
    draft.update(
        {
            "object_type": "proposal_preferences",
            "known_fields": known_fields,
            "known_count": len(known_fields),
            "target_fields": target_fields,
            "has_targets": bool(target_fields),
            "chat_draft_fields": [
                field
                for field in known_fields
                if draft.get("field_sources", {}).get(field) == "chat_draft"
            ],
            "proposal_scoped_only": True,
            "persistent_profile_updated": False,
            "persistent_preferences_updated": False,
        }
    )
    return draft


def _build_proposal_preferences_card(proposal_preferences: Mapping[str, Any]) -> dict[str, Any]:
    draft = _with_proposal_preferences_metadata(proposal_preferences)
    direction_items = [
        _card_item(draft, field)
        for field in (
            "goal",
            "requested_entity",
            "meals_per_day",
            "complexity_level",
            "energy_adjustment",
        )
    ]
    target_items = [_card_item(draft, field) for field in TARGET_FIELDS]
    note_items = [_card_item(draft, "notes")]
    sections = [
        {"title": "Dirección de la propuesta", "items": direction_items},
        {"title": "Targets opcionales", "items": target_items},
    ]
    if not _is_missing(draft.get("notes")):
        sections.append({"title": "Notas", "items": note_items})
    known_count = int(draft.get("known_count") or 0)
    return {
        "title": "Preferencias de propuesta",
        "subtitle": "Parámetros usados solo para esta propuesta. No modifican tu ficha personal.",
        "sections": sections,
        "known_count": known_count,
        "status": "has_data" if known_count else "empty",
        "has_chat_draft_updates": bool(draft.get("chat_draft_fields")),
        "can_create_proposal": _can_create_proposal_from_preferences(draft),
        "proposal_scoped_only": True,
    }


def _card_item(draft: Mapping[str, Any], field_name: str) -> dict[str, Any]:
    raw_value = draft.get(field_name)
    source = str(draft.get("field_sources", {}).get(field_name) or "unknown")
    is_pending = _is_missing(raw_value)
    return {
        "key": field_name,
        "label": FIELD_LABELS.get(field_name, field_name),
        "value": "Pendiente" if is_pending else _format_value(field_name, raw_value),
        "is_pending": is_pending,
        "source": source if not is_pending else "unknown",
        "source_label": SOURCE_LABELS.get(source if not is_pending else "unknown", "Pendiente"),
    }


def _build_nutrition_brief_patch(proposal_preferences: Mapping[str, Any]) -> dict[str, Any]:
    draft = _with_proposal_preferences_metadata(proposal_preferences)
    patch = {}
    for field_name in PROPOSAL_PREFERENCE_FIELDS:
        if field_name == "notes":
            if not _is_missing(draft.get(field_name)):
                patch[field_name] = list(draft.get(field_name) or [])
            continue
        if not _is_missing(draft.get(field_name)):
            patch[field_name] = draft.get(field_name)
    return patch


def _can_create_proposal_from_preferences(draft: Mapping[str, Any]) -> bool:
    return bool(draft.get("goal") and draft.get("meals_per_day"))


def _normalize_field_name(value: Any) -> str:
    return "_".join(str(value or "").replace("-", "_").split()).lower()


def _normalize_field_value(field_name: str, value: Any) -> Any:
    if _is_missing(value):
        return None
    if field_name == "goal":
        return _normalize_goal(value)
    if field_name == "requested_entity":
        return _normalize_entity(value)
    if field_name == "meals_per_day":
        return _clean_int(value, min_value=1, max_value=8)
    if field_name in TARGET_FIELDS:
        return _clean_int(value, min_value=0, max_value=6000)
    if field_name == "energy_adjustment":
        return _normalize_energy_adjustment(value)
    if field_name == "complexity_level":
        return _normalize_complexity_level(value)
    if field_name == "notes":
        return _clean_text_list(value)
    return str(value or "").strip() or None


def _normalize_goal(value: Any) -> str | None:
    text = str(value or "").strip()
    if not text:
        return None
    if text in GOAL_LABELS:
        return text
    normalized = _normalize_text(text)
    if normalized in GOAL_ALIASES:
        return GOAL_ALIASES[normalized]
    for phrase, goal in GOAL_ALIASES.items():
        if phrase and phrase in normalized:
            return goal
    return None


def _normalize_entity(value: Any) -> str | None:
    normalized = _normalize_text(value)
    return ENTITY_ALIASES.get(normalized)


def _normalize_energy_adjustment(value: Any) -> str | None:
    normalized = _normalize_text(value)
    return ENERGY_ALIASES.get(normalized)


def _normalize_complexity_level(value: Any) -> str | None:
    normalized = _normalize_text(value)
    if normalized in COMPLEXITY_ALIASES:
        return COMPLEXITY_ALIASES[normalized]
    for phrase, complexity in COMPLEXITY_ALIASES.items():
        if phrase and phrase in normalized:
            return complexity
    return None


def _clean_int(value: Any, *, min_value: int, max_value: int) -> int | None:
    try:
        number = int(float(str(value).replace(",", ".").strip()))
    except (TypeError, ValueError):
        return None
    if number < min_value or number > max_value:
        return None
    return number


def _clean_text_list(value: Any) -> list[str]:
    if isinstance(value, str):
        raw_values = list(value.replace(";", ",").split(","))
    elif isinstance(value, (list, tuple, set)):
        raw_values = list(value)
    else:
        raw_values = [value]
    cleaned: list[str] = []
    for item in raw_values:
        text = " ".join(str(item or "").strip().split())
        if text and text not in cleaned:
            cleaned.append(text)
    return cleaned


def _clean_source_map(value: Mapping[str, Any]) -> dict[str, str]:
    if not isinstance(value, Mapping):
        return {}
    cleaned: dict[str, str] = {}
    for key, raw_source in value.items():
        field_name = _normalize_field_name(key)
        if field_name not in PROPOSAL_PREFERENCE_FIELDS:
            continue
        source = _normalize_field_name(raw_source) or "chat_draft"
        cleaned[field_name] = source if source in SOURCE_LABELS else "chat_draft"
    return cleaned


def _field_definitions() -> dict[str, dict[str, str]]:
    return {
        "goal": {
            "label": FIELD_LABELS["goal"],
            "description": "Objetivo de esta propuesta: fat_loss, muscle_gain, maintenance, performance o healthy_eating.",
        },
        "meals_per_day": {
            "label": FIELD_LABELS["meals_per_day"],
            "description": "Número de comidas para esta propuesta. No es un dato fijo de ficha personal.",
        },
        "energy_adjustment": {
            "label": FIELD_LABELS["energy_adjustment"],
            "description": "Ajuste energético propuesto para este trabajo puntual.",
        },
        "complexity_level": {
            "label": FIELD_LABELS["complexity_level"],
            "description": "Complejidad operativa de esta propuesta: low, medium o high.",
        },
    }


def _format_value(field_name: str, value: Any) -> str:
    if field_name == "goal":
        return GOAL_LABELS.get(str(value), str(value))
    if field_name == "requested_entity":
        return REQUESTED_ENTITY_LABELS.get(str(value), str(value))
    if field_name == "energy_adjustment":
        return ENERGY_ADJUSTMENT_LABELS.get(str(value), str(value))
    if field_name == "complexity_level":
        return COMPLEXITY_LABELS.get(str(value), str(value))
    if field_name == "meals_per_day":
        return f"{int(value)} comida{'s' if int(value) != 1 else ''}"
    if field_name == "calorie_target":
        return f"{int(value)} kcal"
    if field_name in {"protein_target", "carb_target", "fat_target"}:
        return f"{int(value)} g"
    if field_name == "notes":
        return ", ".join(str(item) for item in list(value or []))
    return str(value)


def _is_missing(value: Any) -> bool:
    if value is None:
        return True
    if isinstance(value, str):
        return not value.strip()
    if isinstance(value, (list, tuple, set, dict)):
        return not bool(value)
    return False


def _normalize_text(value: Any) -> str:
    return " ".join(str(value or "").strip().lower().split())
