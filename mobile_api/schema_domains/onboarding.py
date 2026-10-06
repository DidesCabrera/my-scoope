from datetime import date
from typing import Any, Literal

from ninja import Field, Schema


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


class OnboardingStateEnvelope(Schema):
    ok: Literal[True] = True
    data: OnboardingStateData
    error: None = None
