from __future__ import annotations

from typing import Any, Mapping

import re

from django.db import transaction

from notas.application.ai_tools.runtime import run_ai_tool
from notas.application.dto.nutrition_subject_context_dto import (
    PPK_WEIGHT_SOURCE_PROFILE,
    SUBJECT_SOURCE_SELF_PROFILE,
)
from notas.application.queries.user_nutrition_profile import get_user_nutrition_profile
from notas.application.services.nutrition.body_metrics import record_weight
from notas.domain.models import Profile

COMMITTABLE_PROFILE_FIELDS = (
    "weight_kg",
    "height_cm",
    "sex",
)

PROFILE_DRAFT_FIELDS = (
    "weight_kg",
    "height_cm",
    "age_years",
    "sex",
    "activity_level",
    "training_frequency",
)

BODY_BASICS_FIELDS = (
    "weight_kg",
    "height_cm",
    "age_years",
    "sex",
    "activity_level",
)

FIELD_LABELS = {
    "weight_kg": "Peso",
    "height_cm": "Altura",
    "age_years": "Edad",
    "sex": "Sexo",
    "activity_level": "Actividad",
    "training_frequency": "Entrenamiento semanal",
}

SOURCE_LABELS = {
    "profile": "Ficha personal",
    "chat_draft": "Este chat",
    "manual": "Manual",
    "unknown": "Pendiente",
}

ACTIVITY_LEVELS = {
    "sedentary",
    "light",
    "moderate",
    "high",
    "very_high",
}

SEX_ALIASES = {
    "male": "male",
    "m": "male",
    "man": "male",
    "hombre": "male",
    "masculino": "male",
    "female": "female",
    "f": "female",
    "woman": "female",
    "mujer": "female",
    "femenino": "female",
}


# READ TOOL --------------------------------------------------


def _read_user_profile_context_data(user) -> dict[str, Any]:
    profile = get_user_nutrition_profile(user).as_dict()
    profile_context = {
        "user_id": profile.get("user_id"),
        "username": profile.get("username"),
        "birth_date": profile.get("birth_date"),
        "age_years": profile.get("age_years"),
        "sex": profile.get("sex"),
        "height_cm": profile.get("height_cm"),
        "weight_kg": profile.get("current_weight_kg"),
        "weight_date": profile.get("current_weight_date"),
        "weight_source": profile.get("current_weight_source"),
        "onboarding_completed_at": profile.get("onboarding_completed_at"),
        "onboarding_version": profile.get("onboarding_version"),
    }
    missing_fields = [field for field in BODY_BASICS_FIELDS if _is_missing(profile_context.get(field))]
    profile_draft = _profile_draft_from_profile_context(profile_context)
    nutrition_brief_patch = _nutrition_brief_patch_from_profile_context(profile_context)
    return {
        "profile_context": profile_context,
        "profile_draft": profile_draft,
        "profile_draft_card": _build_profile_draft_card(profile_draft),
        "nutrition_brief_patch": nutrition_brief_patch,
        "missing_fields": missing_fields,
        "complete_for_body_basics": not any(field in missing_fields for field in ("weight_kg", "height_cm", "age_years", "sex")),
        "complete_for_energy_estimation": not missing_fields,
        "field_definitions": _field_definitions(),
        "source_boundary": {
            "object": "personal_nutrition_profile",
            "persistent_profile_read": True,
            "writes_allowed": False,
            "draft_updates_require_tool": "update_profile_draft",
            "persistence_requires_user_approval": True,
            "renders_profile_draft_card": True,
        },
    }


def read_user_profile_context_tool(user):
    """Read persisted nutrition profile context for the authenticated user."""

    return run_ai_tool(_read_user_profile_context_data, user, user=user)


def _profile_draft_from_profile_context(profile_context: Mapping[str, Any]) -> dict[str, Any]:
    """Expose persisted ficha data as a conversation draft for LLM-led turns."""

    draft = _normalize_profile_draft({
        "weight_kg": profile_context.get("weight_kg"),
        "height_cm": profile_context.get("height_cm"),
        "age_years": profile_context.get("age_years"),
        "sex": profile_context.get("sex"),
    })
    field_sources = dict(draft.get("field_sources") or {})
    for field_name in ("weight_kg", "height_cm", "age_years", "sex"):
        if not _is_missing(draft.get(field_name)):
            field_sources[field_name] = "profile"
    draft["field_sources"] = field_sources
    return _with_profile_draft_metadata(draft)


def _nutrition_brief_patch_from_profile_context(profile_context: Mapping[str, Any]) -> dict[str, Any]:
    # The persisted ficha fields themselves are carried in profile_draft with
    # source=profile. This patch only records the user's source choice in the
    # conversation brief, so later turns do not ask again whether to use the ficha.
    return {
        "subject_source": SUBJECT_SOURCE_SELF_PROFILE,
        "ppk_weight_source": PPK_WEIGHT_SOURCE_PROFILE,
    }


# DRAFT TOOLS -----------------------------------------------


def _update_profile_draft_data(
    user,
    updates: Mapping[str, Any],
    current_draft: Mapping[str, Any] | None = None,
    field_sources: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    if not isinstance(updates, Mapping) or not updates:
        raise ValueError("profile_draft_updates_required")

    draft = _normalize_profile_draft(current_draft or {})
    incoming_sources = _clean_source_map(field_sources or {})
    changed_fields: list[str] = []
    rejected_fields: dict[str, str] = {}

    for field_name, raw_value in updates.items():
        field_name = _normalize_field_name(field_name)
        if field_name not in PROFILE_DRAFT_FIELDS:
            rejected_fields[str(field_name)] = "unsupported_profile_draft_field"
            continue
        value = _normalize_field_value(field_name, raw_value)
        if value is None:
            rejected_fields[field_name] = "invalid_or_empty_value"
            continue
        draft[field_name] = value
        draft["field_sources"][field_name] = incoming_sources.get(field_name) or "chat_draft"
        changed_fields.append(field_name)

    profile_draft = _with_profile_draft_metadata(draft)
    return {
        "profile_draft": profile_draft,
        "changed_fields": changed_fields,
        "rejected_fields": rejected_fields,
        "field_definitions": _field_definitions(),
        "source_boundary": {
            "object": "profile_draft",
            "persistent_profile_updated": False,
            "writes_allowed": False,
            "renderable_in_chat_thread": False,
            "presentation_mode": "silent_state_update",
            "share_tool": "share_profile_draft_card",
            "persistence_requires_user_approval": True,
            "commit_tool_planned": "commit_profile_update",
        },
    }


def update_profile_draft_tool(
    user,
    *,
    updates: Mapping[str, Any],
    current_draft: Mapping[str, Any] | None = None,
    field_sources: Mapping[str, Any] | None = None,
):
    """Update a non-persistent profile draft from LLM-interpreted user facts."""

    return run_ai_tool(
        _update_profile_draft_data,
        user,
        updates=updates,
        current_draft=current_draft,
        field_sources=field_sources,
        user=user,
    )


def _share_profile_draft_card_data(user, profile_draft: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(profile_draft, Mapping):
        raise ValueError("profile_draft_required")
    draft = _with_profile_draft_metadata(_normalize_profile_draft(profile_draft))
    return {
        "profile_draft_card": _build_profile_draft_card(draft),
        "profile_draft": draft,
        "source_boundary": {
            "object": "profile_draft_card",
            "persistent_profile_updated": False,
            "writes_allowed": False,
            "renderable_in_chat_thread": True,
            "persistence_requires_user_approval": True,
        },
    }


def share_profile_draft_card_tool(user, *, profile_draft: Mapping[str, Any]):
    """Return a chat-renderable card payload for a profile draft."""

    return run_ai_tool(
        _share_profile_draft_card_data,
        user,
        profile_draft=profile_draft,
        user=user,
    )


# COMMIT TOOL ------------------------------------------------


def _commit_profile_update_data(
    user,
    profile_draft: Mapping[str, Any],
    approved_fields: list[str] | tuple[str, ...] | None = None,
) -> dict[str, Any]:
    if not isinstance(profile_draft, Mapping):
        raise ValueError("profile_draft_required")

    draft = _with_profile_draft_metadata(_normalize_profile_draft(profile_draft))
    approved = {
        _normalize_field_name(field)
        for field in (approved_fields or draft.get("chat_draft_fields") or COMMITTABLE_PROFILE_FIELDS)
    }
    approved = {field for field in approved if field in PROFILE_DRAFT_FIELDS}

    updated_fields: list[str] = []
    unchanged_fields: list[str] = []
    skipped_fields: dict[str, str] = {}

    with transaction.atomic():
        profile, _created = Profile.objects.get_or_create(
            user=user,
            defaults={"role": "member"},
        )
        profile_update_fields: list[str] = []

        if "height_cm" in approved and _is_chat_draft_field(draft, "height_cm"):
            height_cm = draft.get("height_cm")
            if height_cm is not None:
                height_cm = int(height_cm)
                if profile.height_cm != height_cm:
                    profile.height_cm = height_cm
                    profile_update_fields.append("height_cm")
                    updated_fields.append("height_cm")
                else:
                    unchanged_fields.append("height_cm")

        if "sex" in approved and _is_chat_draft_field(draft, "sex"):
            sex = str(draft.get("sex") or "").strip()
            if sex in {Profile.SEX_MALE, Profile.SEX_FEMALE}:
                if profile.sex != sex:
                    profile.sex = sex
                    profile_update_fields.append("sex")
                    updated_fields.append("sex")
                else:
                    unchanged_fields.append("sex")

        if profile_update_fields:
            profile.save(update_fields=profile_update_fields)

        if "weight_kg" in approved and _is_chat_draft_field(draft, "weight_kg"):
            weight_kg = draft.get("weight_kg")
            if weight_kg is not None:
                record_weight(user, float(weight_kg), source="manual")
                updated_fields.append("weight_kg")

    for field_name in draft.get("chat_draft_fields") or ():
        if field_name not in COMMITTABLE_PROFILE_FIELDS:
            skipped_fields[field_name] = "no_persistent_field_yet"
        elif field_name not in approved:
            skipped_fields[field_name] = "not_approved"

    committed_draft = dict(draft)
    committed_sources = dict(committed_draft.get("field_sources") or {})
    for field_name in updated_fields + unchanged_fields:
        if field_name in COMMITTABLE_PROFILE_FIELDS:
            committed_sources[field_name] = "profile"
    committed_draft["field_sources"] = committed_sources
    committed_draft = _with_profile_draft_metadata(committed_draft)

    return {
        "profile_draft": committed_draft,
        "profile_draft_card": _build_profile_draft_card(committed_draft),
        "updated_fields": _dedupe(updated_fields),
        "unchanged_fields": _dedupe(unchanged_fields),
        "skipped_fields": skipped_fields,
        "user_message": _profile_commit_user_message(
            updated_fields=updated_fields,
            unchanged_fields=unchanged_fields,
            skipped_fields=tuple(skipped_fields),
        ),
        "source_boundary": {
            "object": "personal_nutrition_profile",
            "persistent_profile_updated": bool(updated_fields),
            "writes_allowed": True,
            "requires_user_approval": True,
            "approval_was_required_before_execution": True,
            "committed_fields": _dedupe(updated_fields + unchanged_fields),
            "skipped_fields": skipped_fields,
        },
    }


def commit_profile_update_tool(
    user,
    *,
    profile_draft: Mapping[str, Any],
    approved_fields: list[str] | tuple[str, ...] | None = None,
):
    """Persist explicitly approved profile draft fields to the user's ficha."""

    return run_ai_tool(
        _commit_profile_update_data,
        user,
        profile_draft=profile_draft,
        approved_fields=approved_fields,
        user=user,
    )


# NORMALIZATION ---------------------------------------------


def _normalize_profile_draft(value: Mapping[str, Any]) -> dict[str, Any]:
    payload = dict(value or {})
    draft: dict[str, Any] = {field: None for field in PROFILE_DRAFT_FIELDS}
    field_sources = _clean_source_map(payload.get("field_sources") or {})
    for field_name in PROFILE_DRAFT_FIELDS:
        normalized = _normalize_field_value(field_name, payload.get(field_name))
        draft[field_name] = normalized
        if normalized is not None and field_name not in field_sources:
            field_sources[field_name] = "unknown"
    draft["field_sources"] = field_sources
    return draft


def _with_profile_draft_metadata(draft: Mapping[str, Any]) -> dict[str, Any]:
    payload = _normalize_profile_draft(draft)
    missing_fields = [field for field in BODY_BASICS_FIELDS if _is_missing(payload.get(field))]
    chat_draft_fields = [
        field
        for field, source in payload.get("field_sources", {}).items()
        if source == "chat_draft" and not _is_missing(payload.get(field))
    ]
    payload["missing_fields"] = missing_fields
    payload["complete_for_body_basics"] = not any(field in missing_fields for field in ("weight_kg", "height_cm", "age_years", "sex"))
    payload["complete_for_energy_estimation"] = not missing_fields
    payload["chat_draft_fields"] = chat_draft_fields
    payload["requires_approval_for_persistence"] = bool(chat_draft_fields)
    return payload


def _build_profile_draft_card(profile_draft: Mapping[str, Any]) -> dict[str, Any]:
    items = []
    for field_name in BODY_BASICS_FIELDS:
        value = profile_draft.get(field_name)
        source = (profile_draft.get("field_sources") or {}).get(field_name) or "unknown"
        items.append(
            {
                "key": field_name,
                "label": FIELD_LABELS[field_name],
                "value": _format_profile_value(field_name, value),
                "is_pending": _is_missing(value),
                "source": source,
                "source_label": SOURCE_LABELS.get(source, SOURCE_LABELS["unknown"]),
            }
        )
    pending_count = sum(1 for item in items if item["is_pending"])
    chat_draft_fields = set(profile_draft.get("chat_draft_fields") or ())
    has_committable_chat_updates = bool(chat_draft_fields.intersection(COMMITTABLE_PROFILE_FIELDS))
    return {
        "title": "Ficha para esta propuesta",
        "subtitle": "Datos personales usados en esta conversación. Los cambios permanentes requieren aprobación.",
        "items": items,
        "pending_count": pending_count,
        "has_chat_draft_updates": bool(chat_draft_fields),
        "has_committable_profile_updates": has_committable_chat_updates,
        "can_update_personal_profile": has_committable_chat_updates and pending_count == 0,
        "status": "complete" if pending_count == 0 else "pending",
    }


def _field_definitions() -> dict[str, dict[str, Any]]:
    return {
        "weight_kg": {
            "label": "Peso",
            "description": (
                "Peso corporal actual en kilogramos. Puede venir de la ficha o del chat. "
                "Si el usuario entrega un peso durante la conversación, interprétalo como el peso actual para esta propuesta; "
                "no preguntes fecha, origen o recencia salvo que el usuario exprese incertidumbre."
            ),
            "examples": ["85 kg", "peso 84", "ochenta y cinco kilos"],
            "persisted_as": "WeightLog after explicit approval",
        },
        "height_cm": {
            "label": "Altura",
            "description": "Altura en centímetros. Si el usuario entrega 1.88, interpretarlo como 188 cm.",
            "examples": ["188", "1.88", "mido 188"],
            "persisted_as": "Profile.height_cm after explicit approval",
        },
        "age_years": {
            "label": "Edad",
            "description": "Edad en años para cálculo de esta propuesta. La ficha persistente usa fecha de nacimiento, no edad suelta.",
            "examples": ["38", "38 años"],
            "persisted_as": "conversation draft only until birth_date support exists",
        },
        "sex": {
            "label": "Sexo",
            "description": "Sexo usado por fórmulas de estimación energética.",
            "allowed_values": ["male", "female"],
            "examples": ["hombre", "masculino", "mujer", "femenino"],
            "persisted_as": "Profile.sex after explicit approval",
        },
        "activity_level": {
            "label": "Actividad",
            "description": "Nivel general de actividad semanal para estimación energética.",
            "allowed_values": sorted(ACTIVITY_LEVELS),
            "examples": ["entreno 3 veces", "actividad moderada", "muy activo"],
            "persisted_as": "conversation draft until activity/preference object exists",
        },
        "training_frequency": {
            "label": "Entrenamiento semanal",
            "description": "Cantidad de entrenamientos por semana, si el usuario lo declara.",
            "examples": ["3 veces por semana", "entreno cinco días"],
            "persisted_as": "conversation draft until activity/preference object exists",
        },
    }


def _normalize_field_name(value: Any) -> str:
    normalized = str(value or "").strip().lower().replace("-", "_").replace(" ", "_")
    aliases = {
        "weight": "weight_kg",
        "peso": "weight_kg",
        "height": "height_cm",
        "altura": "height_cm",
        "age": "age_years",
        "edad": "age_years",
        "gender": "sex",
        "sexo": "sex",
        "activity": "activity_level",
        "actividad": "activity_level",
        "training_days": "training_frequency",
        "training_days_per_week": "training_frequency",
        "frecuencia_entrenamiento": "training_frequency",
    }
    return aliases.get(normalized, normalized)


def _normalize_field_value(field_name: str, value: Any) -> Any:
    if _is_missing(value):
        return None
    if field_name == "weight_kg":
        number = _float_or_none(value)
        if number is None or not 20 <= number <= 400:
            return None
        return number
    if field_name == "height_cm":
        number = _float_or_none(value)
        if number is None:
            return None
        if 1.0 <= number <= 2.5:
            number *= 100
        height = int(round(number))
        if not 100 <= height <= 250:
            return None
        return height
    if field_name == "age_years":
        age = _int_or_none(value)
        if age is None or not 10 <= age <= 120:
            return None
        return age
    if field_name == "sex":
        normalized = str(value or "").strip().lower()
        return SEX_ALIASES.get(normalized)
    if field_name == "activity_level":
        normalized = str(value or "").strip().lower()
        return normalized if normalized in ACTIVITY_LEVELS else None
    if field_name == "training_frequency":
        frequency = _int_or_none(value)
        if frequency is None or not 0 <= frequency <= 14:
            return None
        return frequency
    return None


def _is_chat_draft_field(draft: Mapping[str, Any], field_name: str) -> bool:
    if _is_missing(draft.get(field_name)):
        return False
    return (draft.get("field_sources") or {}).get(field_name) == "chat_draft"


def _profile_commit_user_message(
    *,
    updated_fields: list[str],
    unchanged_fields: list[str],
    skipped_fields: tuple[str, ...],
) -> str:
    if updated_fields:
        message = f"Listo, actualicé {_join_labels(updated_fields)} en tu ficha personal."
        if skipped_fields:
            message += f"\n\n{_join_labels(skipped_fields).capitalize()} quedan guardados solo para esta conversación."
        return message
    if unchanged_fields:
        return "Tu ficha personal ya tenía esos datos actualizados."
    if skipped_fields:
        return f"{_join_labels(skipped_fields).capitalize()} quedan guardados solo para esta conversación."
    return "No encontré cambios nuevos para guardar en tu ficha personal."


def _join_labels(fields: list[str] | tuple[str, ...]) -> str:
    labels = [_profile_field_label(field) for field in fields if field]
    if not labels:
        return "los datos"
    if len(labels) == 1:
        return labels[0]
    return ", ".join(labels[:-1]) + f" y {labels[-1]}"


def _profile_field_label(field_name: str) -> str:
    return {
        "weight_kg": "el peso",
        "height_cm": "la altura",
        "sex": "el sexo para cálculo",
        "age_years": "la edad",
        "activity_level": "la actividad",
        "training_frequency": "el entrenamiento semanal",
    }.get(field_name, str(field_name).replace("_", " "))


def _dedupe(values: list[str]) -> list[str]:
    result = []
    for value in values:
        if value and value not in result:
            result.append(value)
    return result


def _clean_source_map(value: Mapping[str, Any]) -> dict[str, str]:
    if not isinstance(value, Mapping):
        return {}
    cleaned = {}
    for key, raw_source in value.items():
        field_name = _normalize_field_name(key)
        if field_name not in PROFILE_DRAFT_FIELDS:
            continue
        source = str(raw_source or "").strip().lower()
        cleaned[field_name] = source if source in SOURCE_LABELS else "unknown"
    return cleaned


def _format_profile_value(field_name: str, value: Any) -> str:
    if _is_missing(value):
        return "Pendiente"
    if field_name == "weight_kg":
        number = float(value)
        return f"{number:g} kg"
    if field_name == "height_cm":
        return f"{int(value)} cm"
    if field_name == "age_years":
        return f"{int(value)} años"
    if field_name == "sex":
        return "Hombre" if value == "male" else "Mujer" if value == "female" else str(value)
    if field_name == "activity_level":
        return {
            "sedentary": "Sedentaria",
            "light": "Ligera",
            "moderate": "Moderada",
            "high": "Alta",
            "very_high": "Muy alta",
        }.get(str(value), str(value))
    return str(value)


def _float_or_none(value: Any) -> float | None:
    text = str(value or "").strip().lower().replace(",", ".")
    if not text:
        return None
    try:
        return float(text)
    except (TypeError, ValueError):
        match = re.search(r"\d+(?:\.\d+)?", text)
        if not match:
            return None
        try:
            return float(match.group(0))
        except (TypeError, ValueError):
            return None


def _int_or_none(value: Any) -> int | None:
    number = _float_or_none(value)
    if number is None:
        return None
    return int(round(number))


def _is_missing(value: Any) -> bool:
    return value is None or value == ""
