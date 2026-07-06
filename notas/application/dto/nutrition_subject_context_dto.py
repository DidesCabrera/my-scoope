from __future__ import annotations

from dataclasses import asdict, dataclass


SUBJECT_SOURCE_SELF_PROFILE = "self_profile"
SUBJECT_SOURCE_EXTERNAL_CHAT_DATA = "external_chat_data"
SUBJECT_SOURCE_MANUAL_CHAT_DATA = "manual_chat_data"

SUBJECT_SOURCE_CHOICES = (
    SUBJECT_SOURCE_SELF_PROFILE,
    SUBJECT_SOURCE_EXTERNAL_CHAT_DATA,
    SUBJECT_SOURCE_MANUAL_CHAT_DATA,
)

PPK_WEIGHT_SOURCE_PROFILE = "profile_current_weight"
PPK_WEIGHT_SOURCE_EXTERNAL = "external_subject_weight"
PPK_WEIGHT_SOURCE_MANUAL = "manual_subject_weight"
PPK_WEIGHT_SOURCE_UNKNOWN = "unknown"


@dataclass(frozen=True)
class UserNutritionProfileDTO:
    """Persisted nutrition profile for the authenticated user.

    This DTO represents the user's personal ficha. It is intentionally not the
    same thing as the subject used to calculate a proposal, because a user may
    create a plan for themselves, for another person, or as a temporary model.
    """

    user_id: int
    username: str
    birth_date: str | None
    age_years: int | None
    sex: str | None
    height_cm: int | None
    current_weight_kg: float | None
    current_weight_date: str | None
    current_weight_source: str | None
    onboarding_completed_at: str | None
    onboarding_version: int

    @property
    def is_complete_for_body_basics(self) -> bool:
        return all(
            (
                self.birth_date,
                self.age_years is not None,
                self.sex,
                self.height_cm is not None,
                self.current_weight_kg is not None,
            )
        )

    @property
    def is_complete_for_energy_estimation(self) -> bool:
        # The persisted profile does not own activity_level in ONB v1. Energy
        # estimation becomes complete only after a NutritionSubjectContext adds
        # activity_level from chat/session or external data.
        return False

    def as_dict(self) -> dict:
        data = asdict(self)
        data["is_complete_for_body_basics"] = self.is_complete_for_body_basics
        data["is_complete_for_energy_estimation"] = self.is_complete_for_energy_estimation
        return data


@dataclass(frozen=True)
class NutritionSubjectContextDTO:
    """Concrete person/context used to calculate a nutrition proposal.

    `source` says whether the proposal is being calculated from the user's own
    ficha or from temporary chat data. PPK, kcal and macro estimation should use
    this object, not assume the authenticated user's profile.
    """

    source: str
    owner_user_id: int
    owner_username: str
    weight_kg: float | None
    height_cm: int | None
    age_years: int | None
    sex: str | None
    activity_level: str | None
    training_frequency: int | None
    ppk_weight_source: str
    calculation_weight_kg: float | None
    calculation_height_cm: int | None
    calculation_age_years: int | None
    calculation_sex: str | None
    calculation_activity_level: str | None
    calculation_training_frequency: int | None

    @property
    def is_self_profile(self) -> bool:
        return self.source == SUBJECT_SOURCE_SELF_PROFILE

    @property
    def is_external(self) -> bool:
        return self.source in {
            SUBJECT_SOURCE_EXTERNAL_CHAT_DATA,
            SUBJECT_SOURCE_MANUAL_CHAT_DATA,
        }

    @property
    def is_complete_for_energy_estimation(self) -> bool:
        return all(
            (
                self.weight_kg is not None,
                self.height_cm is not None,
                self.age_years is not None,
                self.sex,
                self.activity_level,
            )
        )

    @property
    def requires_library_ppk_warning(self) -> bool:
        return self.is_external

    def as_dict(self) -> dict:
        data = asdict(self)
        data["is_self_profile"] = self.is_self_profile
        data["is_external"] = self.is_external
        data["is_complete_for_energy_estimation"] = self.is_complete_for_energy_estimation
        data["requires_library_ppk_warning"] = self.requires_library_ppk_warning
        return data
