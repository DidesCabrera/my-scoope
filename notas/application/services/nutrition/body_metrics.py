from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime

from django.utils import timezone

from notas.domain.models import Profile, WeightLog


DEFAULT_CURRENT_WEIGHT_KG = 75
_WEIGHT_LOG_NOT_QUERIED = object()


@dataclass(frozen=True)
class BasicBodyProfile:
    """Persisted body basics used as the base user nutrition profile.

    This is intentionally not the full NutritionSubjectContext. Activity level,
    training frequency and proposal-specific preferences may still come from the
    first AI chat or from temporary external-person data.
    """

    birth_date: date | None
    age_years: int | None
    sex: str
    height_cm: int | None
    current_weight_kg: float | None
    current_weight_log: WeightLog | None
    onboarding_completed_at: datetime | None
    onboarding_version: int

    @property
    def is_complete_for_onboarding_basics(self) -> bool:
        return all(
            (
                self.birth_date,
                self.sex,
                self.height_cm,
                self.current_weight_kg,
            )
        )


def calculate_age_years(birth_date: date | None, on_date: date | None = None) -> int | None:
    if birth_date is None:
        return None

    today = on_date or timezone.localdate()
    years = today.year - birth_date.year
    if (today.month, today.day) < (birth_date.month, birth_date.day):
        years -= 1
    return years


def get_current_weight_log(user):
    cached_log = getattr(
        user,
        "_myscoope_current_weight_log",
        _WEIGHT_LOG_NOT_QUERIED,
    )

    if cached_log is not _WEIGHT_LOG_NOT_QUERIED:
        return cached_log

    last = user.weight_logs.first()
    setattr(user, "_myscoope_current_weight_log", last)
    return last


def get_current_weight(user):
    last = get_current_weight_log(user)
    return last.weight_kg if last else DEFAULT_CURRENT_WEIGHT_KG


def record_weight(
    user,
    weight_kg: float,
    *,
    measured_on: date | None = None,
    source: str = WeightLog.SOURCE_MANUAL,
) -> WeightLog:
    """Create or update the user's body-weight metric for a specific date."""

    if weight_kg <= 0:
        raise ValueError("weight_kg must be greater than zero")

    metric_date = measured_on or timezone.localdate()
    weight_log, _created = WeightLog.objects.update_or_create(
        user=user,
        date=metric_date,
        defaults={
            "weight_kg": weight_kg,
            "source": source,
        },
    )
    if hasattr(user, "_myscoope_current_weight_log"):
        delattr(user, "_myscoope_current_weight_log")
    return weight_log


def get_basic_body_profile(user) -> BasicBodyProfile:
    try:
        profile = user.profile
    except Profile.DoesNotExist:
        profile = None

    weight_log = get_current_weight_log(user)

    if profile is None:
        return BasicBodyProfile(
            birth_date=None,
            age_years=None,
            sex="",
            height_cm=None,
            current_weight_kg=weight_log.weight_kg if weight_log else None,
            current_weight_log=weight_log,
            onboarding_completed_at=None,
            onboarding_version=Profile.ONBOARDING_VERSION_UNSET,
        )

    return BasicBodyProfile(
        birth_date=profile.birth_date,
        age_years=calculate_age_years(profile.birth_date),
        sex=profile.sex,
        height_cm=profile.height_cm,
        current_weight_kg=weight_log.weight_kg if weight_log else None,
        current_weight_log=weight_log,
        onboarding_completed_at=profile.onboarding_completed_at,
        onboarding_version=profile.onboarding_version,
    )
