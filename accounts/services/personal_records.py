from collections.abc import Iterable
from datetime import date

from django.db import transaction

from notas.application.ai_tools.preference_tools import DIETARY_PATTERNS
from notas.application.services.nutrition.weight import record_weight
from notas.domain.models import NutritionPreferenceProfile, Profile
from notas.domain.nutrition_profile_contracts import ACTIVITY_LEVEL_VALUES, NUTRITION_GOAL_VALUES


@transaction.atomic
def update_body_record(*, user, birth_date: date, sex: str, height_cm: int) -> None:
    profile = Profile.objects.select_for_update().get(user=user)
    profile.birth_date = birth_date
    profile.sex = sex
    profile.height_cm = height_cm
    profile.save(update_fields=["birth_date", "sex", "height_cm"])


@transaction.atomic
def update_planning_record(*, user, goal: str, activity_level: str, training_frequency: int) -> None:
    if goal not in NUTRITION_GOAL_VALUES or activity_level not in ACTIVITY_LEVEL_VALUES or not 0 <= training_frequency <= 7:
        raise ValueError("personal_record_invalid")
    profile = Profile.objects.select_for_update().get(user=user)
    profile.nutrition_goal = goal
    profile.activity_level = activity_level
    profile.training_frequency = training_frequency
    profile.save(update_fields=["nutrition_goal", "activity_level", "training_frequency"])


@transaction.atomic
def update_preference_record(*, user, dietary_pattern: str, allergies_or_intolerances: Iterable[str], avoided_foods: Iterable[str]) -> None:
    if dietary_pattern not in DIETARY_PATTERNS:
        raise ValueError("personal_record_invalid")
    stored, _created = NutritionPreferenceProfile.objects.select_for_update().get_or_create(user=user, defaults={"preferences": {}})
    preferences = dict(stored.preferences or {})
    preferences.update({
        "dietary_pattern": dietary_pattern,
        "allergies_or_intolerances": _clean_values(allergies_or_intolerances),
        "avoided_foods": _clean_values(avoided_foods),
    })
    stored.preferences = preferences
    stored.save(update_fields=["preferences", "updated_at"])


def update_weight_record(*, user, weight_kg: float) -> None:
    record_weight(user, weight_kg)


def _clean_values(values: Iterable[str]) -> list[str]:
    return list(dict.fromkeys(value.strip() for value in values if value and value.strip()))
