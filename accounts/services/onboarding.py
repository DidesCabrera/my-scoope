from __future__ import annotations

from datetime import date

from django.db import transaction
from django.utils import timezone

from notas.application.services.nutrition.body_metrics import record_weight
from notas.domain.models import Profile, WeightLog


@transaction.atomic
def complete_nutrition_onboarding(
    *,
    user,
    birth_date: date,
    sex: str,
    height_cm: int,
    weight_kg: float,
):
    profile = Profile.objects.select_for_update().get(user=user)
    profile.birth_date = birth_date
    profile.sex = sex
    profile.height_cm = height_cm
    profile.onboarding_completed_at = timezone.now()
    profile.onboarding_version = Profile.ONBOARDING_VERSION_NUTRITION_V1
    profile.save(
        update_fields=[
            "birth_date",
            "sex",
            "height_cm",
            "onboarding_completed_at",
            "onboarding_version",
        ]
    )
    weight_log = record_weight(
        user,
        weight_kg,
        source=WeightLog.SOURCE_ONBOARDING,
    )
    return profile, weight_log
