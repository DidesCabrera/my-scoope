from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Iterable

from django.db import transaction

from notas.application.ai_intake.nutrition_brief import (
    FIELD_SOURCE_PROFILE,
    NutritionBrief,
)
from notas.application.services.nutrition.body_metrics import record_weight
from notas.domain.models import Profile


@dataclass(frozen=True)
class ProfileDraftUpdateResult:
    """Outcome of an explicit user-approved profile draft update."""

    updated_fields: tuple[str, ...]
    unchanged_fields: tuple[str, ...]
    skipped_fields: tuple[str, ...]

    @property
    def has_updates(self) -> bool:
        return bool(self.updated_fields)

    @property
    def user_message(self) -> str:
        if self.has_updates:
            updated = _join_labels(self.updated_fields)
            pieces = [f"Listo, actualicé {updated} en tu ficha personal."]
            if self.skipped_fields:
                pieces.append(
                    f"{_join_labels(self.skipped_fields).capitalize()} quedan guardados para esta conversación."
                )
            return "\n\n".join(pieces)

        if self.unchanged_fields:
            return "Tu ficha personal ya tenía esos datos actualizados."

        if self.skipped_fields:
            return (
                "Todavía no hay datos de la ficha personal que pueda actualizar de forma permanente.\n\n"
                f"{_join_labels(self.skipped_fields).capitalize()} quedan guardados para esta conversación."
            )

        return "No encontré cambios nuevos para guardar en tu ficha personal."


def build_profile_draft_payload_from_brief(brief: NutritionBrief) -> dict:
    """Convert the current chat brief into the profile draft tool contract."""

    return {
        "weight_kg": brief.weight_kg,
        "height_cm": brief.height_cm,
        "age_years": brief.age_years,
        "sex": brief.sex,
        "activity_level": brief.activity_level,
        "training_frequency": brief.training_frequency,
        "field_sources": dict(brief.field_sources or {}),
    }


def profile_update_result_from_tool_data(data: dict) -> ProfileDraftUpdateResult:
    """Adapt commit_profile_update tool data to the legacy view result contract."""

    skipped = data.get("skipped_fields") or {}
    if isinstance(skipped, dict):
        skipped_fields = tuple(skipped.keys())
    else:
        skipped_fields = tuple(skipped or ())
    return ProfileDraftUpdateResult(
        updated_fields=tuple(data.get("updated_fields") or ()),
        unchanged_fields=tuple(data.get("unchanged_fields") or ()),
        skipped_fields=skipped_fields,
    )


def update_personal_profile_from_brief(*, user, brief: NutritionBrief) -> ProfileDraftUpdateResult:
    """Persist approved ficha-compatible fields from the current intake brief.

    The chat may contain proposal-only facts such as activity level or the
    user's preferred number of meals. Those are useful for the current proposal
    but should not be silently written into the personal ficha until the product
    has dedicated profile/preference objects for them.
    """

    if user is None or not getattr(user, "is_authenticated", False):
        raise ValueError("authenticated_user_required")

    updated: list[str] = []
    unchanged: list[str] = []
    skipped: list[str] = []

    with transaction.atomic():
        profile, _created = Profile.objects.get_or_create(
            user=user,
            defaults={"role": "member"},
        )

        profile_update_fields: list[str] = []

        if brief.height_cm and _is_user_draft_field(brief, "height_cm"):
            height_cm = int(brief.height_cm)
            if profile.height_cm != height_cm:
                profile.height_cm = height_cm
                profile_update_fields.append("height_cm")
                updated.append("height_cm")
            else:
                unchanged.append("height_cm")

        if brief.sex and _is_user_draft_field(brief, "sex"):
            sex = str(brief.sex).strip()
            if sex in {Profile.SEX_MALE, Profile.SEX_FEMALE}:
                if profile.sex != sex:
                    profile.sex = sex
                    profile_update_fields.append("sex")
                    updated.append("sex")
                else:
                    unchanged.append("sex")

        if profile_update_fields:
            profile.save(update_fields=profile_update_fields)

        if brief.weight_kg and _is_user_draft_field(brief, "weight_kg"):
            # Weight is intentionally persisted as a metric entry, not as a flat
            # Profile column, because weight changes over time.
            record_weight(user, float(brief.weight_kg), source="manual")
            updated.append("weight_kg")

    if brief.age_years and _is_user_draft_field(brief, "age_years"):
        skipped.append("age_years")
    if brief.activity_level and _is_user_draft_field(brief, "activity_level"):
        skipped.append("activity_level")

    return ProfileDraftUpdateResult(
        updated_fields=tuple(_dedupe(updated)),
        unchanged_fields=tuple(_dedupe(unchanged)),
        skipped_fields=tuple(_dedupe(skipped)),
    )


def apply_profile_update_result_to_brief(
    brief: NutritionBrief,
    result: ProfileDraftUpdateResult,
) -> NutritionBrief:
    """Mark persisted fields as coming from the personal ficha in chat state."""

    if not result.updated_fields:
        return brief

    field_sources = dict(brief.field_sources or {})
    for field_name in (*result.updated_fields, *result.unchanged_fields):
        if field_name in {"weight_kg", "height_cm", "sex"}:
            field_sources[field_name] = FIELD_SOURCE_PROFILE
    return replace(brief, field_sources=field_sources)


def _is_user_draft_field(brief: NutritionBrief, field_name: str) -> bool:
    return (brief.field_sources or {}).get(field_name) != FIELD_SOURCE_PROFILE


def _dedupe(values: Iterable[str]) -> list[str]:
    result = []
    for value in values:
        if value and value not in result:
            result.append(value)
    return result


def _join_labels(fields: Iterable[str]) -> str:
    labels = [_field_label(field) for field in fields]
    if not labels:
        return "los datos"
    if len(labels) == 1:
        return labels[0]
    return ", ".join(labels[:-1]) + f" y {labels[-1]}"


def _field_label(field_name: str) -> str:
    return {
        "weight_kg": "el peso",
        "height_cm": "la altura",
        "sex": "el sexo para cálculo",
        "age_years": "la edad",
        "activity_level": "la actividad",
    }.get(field_name, field_name.replace("_", " "))
