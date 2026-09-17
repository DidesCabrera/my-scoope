"""Apply controlled assistant-tool payloads to a nutrition brief."""

from __future__ import annotations

import re
import unicodedata
from dataclasses import replace

from notas.application.ai_intake.nutrition_brief import (
    PPK_WEIGHT_SOURCE_MANUAL,
    PPK_WEIGHT_SOURCE_PROFILE,
    NutritionBrief,
)


def apply_profile_draft_to_brief(brief: NutritionBrief, profile_draft: dict) -> NutritionBrief:
    allowed_fields = {
        "weight_kg", "height_cm", "age_years", "sex", "activity_level", "training_frequency",
    }
    updates: dict[str, object] = {}
    source_updates: dict[str, str] = {}
    field_sources = profile_draft.get("field_sources") if isinstance(profile_draft.get("field_sources"), dict) else {}
    for field_name in allowed_fields:
        value = profile_draft.get(field_name)
        if field_name not in profile_draft or _tool_value_is_empty(value):
            continue
        updates[field_name] = value
        source_updates[field_name] = _normalize_tool_source(field_sources.get(field_name), default="chat_draft")

    if "weight_kg" in updates:
        weight_source = source_updates.get("weight_kg")
        if weight_source in {"chat_draft", "manual"}:
            updates["ppk_weight_source"] = PPK_WEIGHT_SOURCE_MANUAL
        elif weight_source == "profile" and not brief.ppk_weight_source:
            updates["ppk_weight_source"] = PPK_WEIGHT_SOURCE_PROFILE
    return _replace_brief_fields(brief, updates, source_updates=source_updates)


def apply_preference_draft_to_brief(brief: NutritionBrief, preference_draft: dict) -> NutritionBrief:
    updates: dict[str, object] = {}
    source_updates: dict[str, str] = {}
    field_sources = preference_draft.get("field_sources") if isinstance(preference_draft.get("field_sources"), dict) else {}

    avoided_foods = preference_draft.get("avoided_foods")
    if not _tool_value_is_empty(avoided_foods):
        updates["excluded_foods"] = _merge_text_lists(brief.excluded_foods, avoided_foods)
        source_updates["excluded_foods"] = _normalize_tool_source(field_sources.get("avoided_foods"), default="chat_draft")
    preferred_foods = preference_draft.get("preferred_foods")
    if not _tool_value_is_empty(preferred_foods):
        updates["preferred_foods"] = _merge_text_lists(brief.preferred_foods, preferred_foods)
        source_updates["preferred_foods"] = _normalize_tool_source(field_sources.get("preferred_foods"), default="chat_draft")
    preferred_meals = preference_draft.get("preferred_meals_per_day")
    if not _tool_value_is_empty(preferred_meals) and not brief.meals_per_day:
        updates["meals_per_day"] = preferred_meals
        source_updates["meals_per_day"] = _normalize_tool_source(field_sources.get("preferred_meals_per_day"), default="chat_draft")
    budget = preference_draft.get("budget_preference")
    if not _tool_value_is_empty(budget) and not brief.budget_level:
        updates["budget_level"] = budget
        source_updates["budget_level"] = _normalize_tool_source(field_sources.get("budget_preference"), default="chat_draft")

    _apply_style_preference_updates(
        brief,
        preference_draft,
        field_sources=field_sources,
        updates=updates,
        source_updates=source_updates,
    )

    dietary_pattern = preference_draft.get("dietary_pattern")
    allergies = preference_draft.get("allergies_or_intolerances")
    canonical_fields = (
        "dietary_pattern", "allergies_or_intolerances", "preferred_meals_per_day",
        "cooking_time_preference", "budget_preference", "simplicity_preference", "variety_preference",
    )
    for field_name in canonical_fields:
        value = preference_draft.get(field_name)
        if _tool_value_is_empty(value):
            continue
        updates[field_name] = value
        source_updates[field_name] = _normalize_tool_source(field_sources.get(field_name), default="chat_draft")
    notes = list(brief.notes)
    if not _tool_value_is_empty(dietary_pattern):
        notes = _merge_text_lists(notes, [f"Patrón alimentario declarado: {dietary_pattern}."])
    if not _tool_value_is_empty(allergies):
        notes = _merge_text_lists(notes, [f"Alergias o intolerancias declaradas: {', '.join(_coerce_text_list(allergies))}."])
    if notes != brief.notes:
        updates["notes"] = notes
        note_sources = [
            field_sources.get("dietary_pattern") if not _tool_value_is_empty(dietary_pattern) else None,
            field_sources.get("allergies_or_intolerances") if not _tool_value_is_empty(allergies) else None,
        ]
        source_updates["notes"] = next(
            (_normalize_tool_source(source, default="chat_draft") for source in note_sources if source),
            "chat_draft",
        )
    return _replace_brief_fields(brief, updates, source_updates=source_updates)


def _apply_style_preference_updates(
    brief: NutritionBrief,
    preference_draft: dict,
    *,
    field_sources: dict,
    updates: dict[str, object],
    source_updates: dict[str, str],
) -> None:
    preference_specs = (
        ("simplicity_preference", "simple", "low"),
        ("variety_preference", "varied", "high"),
    )
    for field_name, style_name, complexity_level in preference_specs:
        value = preference_draft.get(field_name)
        if _tool_value_is_empty(value):
            continue
        source = _normalize_tool_source(field_sources.get(field_name), default="chat_draft")
        if str(value) in {"high", "medium"}:
            base_styles = updates.get("style_preferences", brief.style_preferences)
            updates["style_preferences"] = _merge_text_lists(base_styles, [style_name])
            source_updates["style_preferences"] = source
        if str(value) == "high" and not brief.complexity_level:
            updates["complexity_level"] = complexity_level
            source_updates["complexity_level"] = source


def apply_proposal_preferences_to_brief(brief: NutritionBrief, proposal_preferences: dict) -> NutritionBrief:
    fields = (
        "goal", "requested_entity", "meals_per_day", "energy_adjustment", "complexity_level",
        "calorie_target", "protein_target", "carb_target", "fat_target",
        "protein_per_kg_target", "macro_distribution", "notes",
    )
    updates = {
        field_name: proposal_preferences.get(field_name)
        for field_name in fields
        if field_name in proposal_preferences and not _tool_value_is_empty(proposal_preferences.get(field_name))
    }
    field_sources = proposal_preferences.get("field_sources") if isinstance(proposal_preferences.get("field_sources"), dict) else {}
    sources = {name: _normalize_tool_source(field_sources.get(name), default="chat_draft") for name in updates}
    return _replace_brief_fields(brief, updates, source_updates=sources)


def apply_nutrition_brief_patch(brief: NutritionBrief, patch: dict, *, default_source: str) -> NutritionBrief:
    allowed_fields = {
        "subject_source", "ppk_weight_source", "goal", "requested_entity", "meals_per_day",
        "energy_adjustment", "calorie_target", "protein_target", "carb_target", "fat_target",
        "protein_per_kg_target", "macro_distribution", "notes",
    }
    updates = {
        name: value for name, value in patch.items()
        if name in allowed_fields and not _tool_value_is_empty(value)
    }
    return _replace_brief_fields(brief, updates, source_updates=dict.fromkeys(updates, default_source))


def _replace_brief_fields(
    brief: NutritionBrief,
    updates: dict[str, object],
    *,
    source_updates: dict[str, str] | None = None,
) -> NutritionBrief:
    if not updates:
        return brief
    normalized_updates: dict[str, object] = {}
    list_fields = {"notes", "style_preferences", "excluded_foods", "preferred_foods", "allergies_or_intolerances"}
    for field_name, value in updates.items():
        if not hasattr(brief, field_name):
            continue
        normalized_updates[field_name] = _coerce_text_list(value) if field_name in list_fields else value
    if not normalized_updates:
        return brief
    field_sources = dict(brief.field_sources or {})
    for field_name, source in dict(source_updates or {}).items():
        if field_name in normalized_updates:
            field_sources[field_name] = _normalize_tool_source(source, default="chat_draft")
    if field_sources != (brief.field_sources or {}):
        normalized_updates["field_sources"] = field_sources
    return replace(brief, **normalized_updates)


def _normalize_tool_source(value: object, *, default: str) -> str:
    source = str(value or "").strip().lower()
    return source if source in {"profile", "chat_draft", "manual", "unknown"} else default


def _tool_value_is_empty(value: object) -> bool:
    if value is None:
        return True
    if isinstance(value, str):
        return not value.strip()
    if isinstance(value, (list, tuple, set, dict)):
        return len(value) == 0
    return False


def _merge_text_lists(existing: object, incoming: object) -> list[str]:
    values: list[str] = []
    seen: set[str] = set()
    for item in [*_coerce_text_list(existing), *_coerce_text_list(incoming)]:
        key = _normalize_text_key(item)
        if key and key not in seen:
            seen.add(key)
            values.append(str(item).strip())
    return values


def _normalize_text_key(value: object) -> str:
    text = " ".join(str(value or "").casefold().split())
    text = "".join(
        char for char in unicodedata.normalize("NFD", text)
        if unicodedata.category(char) != "Mn"
    )
    return re.sub(r"[^a-z0-9ñ\s]", "", text)


def _coerce_text_list(value: object) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        parts = value.replace(";", ",").split(",")
    elif isinstance(value, (list, tuple, set)):
        parts = list(value)
    else:
        parts = [value]
    return [" ".join(str(item or "").strip().split()) for item in parts if str(item or "").strip()]
