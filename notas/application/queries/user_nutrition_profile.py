from __future__ import annotations

from datetime import date
from typing import Any, Mapping

from notas.application.dto.nutrition_subject_context_dto import (
    PPK_WEIGHT_SOURCE_EXTERNAL,
    PPK_WEIGHT_SOURCE_MANUAL,
    PPK_WEIGHT_SOURCE_PROFILE,
    PPK_WEIGHT_SOURCE_UNKNOWN,
    SUBJECT_SOURCE_EXTERNAL_CHAT_DATA,
    SUBJECT_SOURCE_MANUAL_CHAT_DATA,
    SUBJECT_SOURCE_SELF_PROFILE,
    NutritionSubjectContextDTO,
    UserNutritionProfileDTO,
)
from notas.application.services.nutrition.body_metrics import (
    calculate_age_years,
    get_basic_body_profile,
)


class NutritionSubjectContextError(ValueError):
    """Raised when a subject context cannot be built from the requested source."""


def get_user_nutrition_profile(user) -> UserNutritionProfileDTO:
    """Return the persisted nutrition ficha for the authenticated user."""

    body_profile = get_basic_body_profile(user)
    weight_log = body_profile.current_weight_log

    return UserNutritionProfileDTO(
        user_id=user.id,
        username=user.username,
        birth_date=_date_to_iso(body_profile.birth_date),
        age_years=body_profile.age_years,
        sex=body_profile.sex or None,
        height_cm=body_profile.height_cm,
        current_weight_kg=_float_or_none(body_profile.current_weight_kg),
        current_weight_date=_date_to_iso(weight_log.date) if weight_log else None,
        current_weight_source=weight_log.source if weight_log else None,
        onboarding_completed_at=_datetime_to_iso(body_profile.onboarding_completed_at),
        onboarding_version=body_profile.onboarding_version,
    )


def build_nutrition_subject_context(
    *,
    user,
    source: str = SUBJECT_SOURCE_SELF_PROFILE,
    chat_context: Mapping[str, Any] | None = None,
) -> NutritionSubjectContextDTO:
    """Build the explicit calculation subject for a proposal.

    ONB v1 keeps `activity_level` and `training_frequency` in the first chat,
    while `birth_date`, `sex`, `height_cm` and weight come from onboarding for
    the user's own ficha. For external proposals, body fields must come from the
    chat context and must not silently fall back to the owner's body data.
    """

    chat_context = chat_context or {}

    if source == SUBJECT_SOURCE_SELF_PROFILE:
        return _build_self_profile_subject(user=user, chat_context=chat_context)

    if source in {SUBJECT_SOURCE_EXTERNAL_CHAT_DATA, SUBJECT_SOURCE_MANUAL_CHAT_DATA}:
        return _build_external_subject(user=user, source=source, chat_context=chat_context)

    raise NutritionSubjectContextError(f"Unsupported nutrition subject source: {source}")


def _build_self_profile_subject(*, user, chat_context: Mapping[str, Any]) -> NutritionSubjectContextDTO:
    profile = get_user_nutrition_profile(user)
    activity_level = _clean_string(chat_context.get("activity_level"))
    training_frequency = _int_or_none(chat_context.get("training_frequency"))

    return NutritionSubjectContextDTO(
        source=SUBJECT_SOURCE_SELF_PROFILE,
        owner_user_id=user.id,
        owner_username=user.username,
        weight_kg=profile.current_weight_kg,
        height_cm=profile.height_cm,
        age_years=profile.age_years,
        sex=profile.sex,
        activity_level=activity_level,
        training_frequency=training_frequency,
        ppk_weight_source=PPK_WEIGHT_SOURCE_PROFILE if profile.current_weight_kg is not None else PPK_WEIGHT_SOURCE_UNKNOWN,
        calculation_weight_kg=profile.current_weight_kg,
        calculation_height_cm=profile.height_cm,
        calculation_age_years=profile.age_years,
        calculation_sex=profile.sex,
        calculation_activity_level=activity_level,
        calculation_training_frequency=training_frequency,
    )


def _build_external_subject(
    *,
    user,
    source: str,
    chat_context: Mapping[str, Any],
) -> NutritionSubjectContextDTO:
    weight_kg = _float_or_none(_first_present(chat_context, "weight_kg", "weight", "body_weight"))
    height_cm = _int_or_none(_first_present(chat_context, "height_cm", "height"))
    age_years = _int_or_none(chat_context.get("age_years"))
    if age_years is None:
        birth_date = _date_or_none(chat_context.get("birth_date"))
        age_years = calculate_age_years(birth_date) if birth_date else None

    sex = _clean_string(chat_context.get("sex"))
    activity_level = _clean_string(chat_context.get("activity_level"))
    training_frequency = _int_or_none(chat_context.get("training_frequency"))
    ppk_source = (
        PPK_WEIGHT_SOURCE_EXTERNAL
        if source == SUBJECT_SOURCE_EXTERNAL_CHAT_DATA
        else PPK_WEIGHT_SOURCE_MANUAL
    )

    return NutritionSubjectContextDTO(
        source=source,
        owner_user_id=user.id,
        owner_username=user.username,
        weight_kg=weight_kg,
        height_cm=height_cm,
        age_years=age_years,
        sex=sex,
        activity_level=activity_level,
        training_frequency=training_frequency,
        ppk_weight_source=ppk_source if weight_kg is not None else PPK_WEIGHT_SOURCE_UNKNOWN,
        calculation_weight_kg=weight_kg,
        calculation_height_cm=height_cm,
        calculation_age_years=age_years,
        calculation_sex=sex,
        calculation_activity_level=activity_level,
        calculation_training_frequency=training_frequency,
    )


def _first_present(values: Mapping[str, Any], *keys: str) -> Any:
    for key in keys:
        value = values.get(key)
        if value not in (None, ""):
            return value
    return None


def _clean_string(value: Any) -> str | None:
    if value is None:
        return None
    cleaned = str(value).strip()
    return cleaned or None


def _float_or_none(value: Any) -> float | None:
    if value in (None, ""):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _int_or_none(value: Any) -> int | None:
    if value in (None, ""):
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _date_or_none(value: Any) -> date | None:
    if value in (None, ""):
        return None
    if isinstance(value, date):
        return value
    try:
        return date.fromisoformat(str(value))
    except ValueError:
        return None


def _date_to_iso(value: date | None) -> str | None:
    return value.isoformat() if value else None


def _datetime_to_iso(value) -> str | None:
    return value.isoformat() if value else None
