from datetime import date
from typing import Any, Literal

from ninja import Field, Schema

from mobile_api.schema_domains.libraries import LibraryFoodPanelItemData
from mobile_api.schema_domains.proposals import ProposalDetailData


class OnboardingInput(Schema):
    birth_date: date
    sex: str
    height_cm: int = Field(ge=80, le=250)
    weight_kg: float = Field(ge=25, le=350)


class OnboardingAnalyzeInput(OnboardingInput):
    goal: str
    activity_level: str
    training_frequency: int = Field(ge=0, le=7)
    dietary_pattern: str
    allergies_or_intolerances: list[str] = Field(default_factory=list)
    avoided_foods: list[str] = Field(default_factory=list)


class PersonalBodyInput(Schema):
    birth_date: date
    sex: str
    height_cm: int = Field(ge=80, le=250)


class PersonalPlanningInput(Schema):
    goal: str
    activity_level: str
    training_frequency: int = Field(ge=0, le=7)


class PersonalPreferencesInput(Schema):
    dietary_pattern: str
    allergies_or_intolerances: list[str] = Field(default_factory=list)
    avoided_foods: list[str] = Field(default_factory=list)


class PersonalWeightInput(Schema):
    weight_kg: float = Field(ge=25, le=350)


class OnboardingStateData(Schema):
    stage: str
    birth_date: date | None = None
    sex: str = ""
    height_cm: int | None = None
    weight_kg: float | None = None
    goal: str = ""
    activity_level: str = ""
    training_frequency: int | None = None
    dietary_pattern: str = ""
    allergies_or_intolerances: list[str] = Field(default_factory=list)
    avoided_foods: list[str] = Field(default_factory=list)
    estimate: dict[str, Any] | None = None
    proposal_id: int | None = None
    proposal_ids: list[int] = Field(default_factory=list)


class OnboardingStateEnvelope(Schema):
    ok: Literal[True] = True
    data: OnboardingStateData
    error: None = None


class OnboardingMinutasData(Schema):
    items: list[ProposalDetailData]


class OnboardingMinutasEnvelope(Schema):
    ok: Literal[True] = True
    data: OnboardingMinutasData
    error: None = None


class OnboardingCalendarPlanData(Schema):
    proposal_id: int
    dailyplan_id: int | None = None
    dates: list[date] = Field(default_factory=list)
    foods: list[LibraryFoodPanelItemData] = Field(default_factory=list)


class OnboardingCalendarizationData(Schema):
    plans: list[OnboardingCalendarPlanData]
    days_count: int
    foods: list[LibraryFoodPanelItemData]


class OnboardingCalendarizationEnvelope(Schema):
    ok: Literal[True] = True
    data: OnboardingCalendarizationData
    error: None = None
