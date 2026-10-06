from datetime import date, datetime
from typing import Literal

from ninja import Schema


class SessionData(Schema):
    user_id: int
    username: str
    email: str
    display_name: str
    date_joined: datetime
    scopes: list[str]
    device_session_id: str | None = None
    is_staff: bool = False


class SessionEnvelope(Schema):
    ok: Literal[True] = True
    data: SessionData
    error: None = None


class ProfileData(Schema):
    birth_date: date | None = None
    sex: str
    height_cm: int | None = None
    timezone_name: str
    onboarding_completed: bool
    onboarding_version: int
    current_weight_kg: float | None = None
    review_disclosure_required: bool
    review_disclosure_version: str
    nutrition_goal: str = ""
    activity_level: str = ""
    training_frequency: int | None = None
    onboarding_stage: str = "intro"
    onboarding_plan_proposal_id: int | None = None


class ProfileEnvelope(Schema):
    ok: Literal[True] = True
    data: ProfileData
    error: None = None


class DisclosureAcceptanceInput(Schema):
    accepted: Literal[True]


class AccountDeletionInput(Schema):
    confirmation: str
    password: str = ""


class AccountDeletionData(Schema):
    receipt_id: str


class AccountDeletionEnvelope(Schema):
    ok: Literal[True] = True
    data: AccountDeletionData
    error: None = None


class RevokeSessionData(Schema):
    revoked: bool
    device_session_id: str


class RevokeSessionEnvelope(Schema):
    ok: Literal[True] = True
    data: RevokeSessionData
    error: None = None
