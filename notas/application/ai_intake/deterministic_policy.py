"""Conversation policy used only by the explicit deterministic intake runtime.

This module owns stage selection and visible-question copy for the legacy
rule-based chat engine. LLM runtimes must not import or call these helpers; they
receive typed state and tools and decide their own conversational pacing.
"""

from __future__ import annotations

from typing import Any


def _has_value(value: Any) -> bool:
    if value is None:
        return False
    if isinstance(value, str):
        return bool(value.strip())
    if isinstance(value, (list, tuple, set, dict)):
        return bool(value)
    return bool(value)


def _get(obj: Any, name: str, default: Any = None) -> Any:
    return getattr(obj, name, default)


def _uses_profile_source(brief: Any) -> bool:
    return _get(brief, "subject_source") == "self_profile"


def _missing_physical_context(brief: Any) -> list[str]:
    missing: list[str] = []
    if not _uses_profile_source(brief) and not _has_value(_get(brief, "weight_kg")):
        missing.append("peso")
    if not _has_value(_get(brief, "height_cm")):
        missing.append("altura")
    if not _has_value(_get(brief, "age_years")):
        missing.append("edad")
    if not _has_value(_get(brief, "sex")):
        missing.append("sexo")
    return missing


def _has_plan_shape(brief: Any) -> bool:
    return _has_value(_get(brief, "meals_per_day")) and (
        _has_value(_get(brief, "style_preferences"))
        or _has_value(_get(brief, "complexity_level"))
        or _has_value(_get(brief, "budget_level"))
    )


def deterministic_intake_stage(brief: Any) -> str:
    """Return the next stage for the explicit deterministic runtime."""

    if not _has_value(_get(brief, "subject_source")) or not _has_value(_get(brief, "goal")):
        return "orientation"
    if _missing_physical_context(brief):
        return "physical_context"
    if not _has_value(_get(brief, "activity_level")):
        return "activity"
    if not _has_plan_shape(brief):
        return "plan_shape"
    return "optional_refinement"


def deterministic_questions_for_brief(brief: Any) -> list[str]:
    """Suggest visible questions for the explicit deterministic runtime only."""

    stage = deterministic_intake_stage(brief)

    if stage == "orientation":
        if not _has_value(_get(brief, "goal")):
            return ["¿Cuál es tu objetivo principal ahora: bajar grasa, ganar masa, mantener o rendimiento?"]
        if not _has_value(_get(brief, "subject_source")):
            return ["¿Usamos tu ficha personal como base o prefieres entregar datos nuevos?"]
        return []

    if stage == "physical_context":
        missing = _missing_physical_context(brief)
        if not missing:
            return []
        next_field = missing[0]
        question_by_field = {
            "peso": "Cuéntame tu peso actual.",
            "altura": "Cuéntame tu altura.",
            "edad": "Cuéntame tu edad.",
            "sexo": "Cuéntame qué sexo debo usar para el cálculo: hombre o mujer.",
        }
        return [question_by_field.get(next_field, f"Cuéntame tu {next_field}.")]

    if stage == "activity":
        return ["Cuéntame cómo es tu actividad o entrenamiento durante una semana normal."]

    if stage == "plan_shape":
        if not _has_value(_get(brief, "meals_per_day")):
            return ["Cuéntame cuántas comidas te acomoda hacer al día."]
        if not (
            _has_value(_get(brief, "style_preferences"))
            or _has_value(_get(brief, "complexity_level"))
            or _has_value(_get(brief, "budget_level"))
        ):
            return ["Cuéntame qué estilo de plan te acomoda más: simple, económico, variado o con poco tiempo de preparación."]
        return []

    return ["Cuéntame si hay alimentos que quieras priorizar o evitar antes de preparar la propuesta."]
