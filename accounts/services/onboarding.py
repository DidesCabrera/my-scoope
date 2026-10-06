from __future__ import annotations

from datetime import date
from typing import Iterable

from django.db import transaction
from django.utils import timezone

from notas.application.ai_intake.dailyplan_generator import generate_dailyplan_proposal_from_brief_proposal
from notas.application.ai_intake.proposal_from_brief import create_nutrition_brief_proposal
from notas.application.ai_tools.preference_tools import DIETARY_PATTERNS
from notas.application.ai_tools.proposal_tools import build_nutrition_brief_from_ai_drafts
from notas.application.nutrition_engine.target_estimator import TargetEstimationProfile, estimate_daily_targets
from notas.application.services.commands.proposal_commands import (
    apply_approved_create_dailyplan_proposal,
    approve_proposal,
    cancel_proposal,
)
from notas.application.services.nutrition.body_metrics import calculate_age_years, record_weight
from notas.domain.models import NutritionPreferenceProfile, NutritionProposal, Profile, WeightLog
from notas.domain.nutrition_profile_contracts import ACTIVITY_LEVEL_VALUES, NUTRITION_GOAL_VALUES


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


def _clean_preference_values(values: Iterable[str]) -> list[str]:
    cleaned: list[str] = []
    for raw_value in values:
        value = str(raw_value).strip()
        if value and value.casefold() not in {item.casefold() for item in cleaned}:
            cleaned.append(value[:120])
    return cleaned[:20]


def nutrition_onboarding_estimate(profile: Profile) -> dict:
    current_weight = profile.user.weight_logs.first()
    plan = estimate_daily_targets(TargetEstimationProfile(
        goal=profile.nutrition_goal or None,
        weight_kg=float(current_weight.weight_kg) if current_weight else None,
        height_cm=profile.height_cm,
        age_years=calculate_age_years(profile.birth_date),
        sex=profile.sex or None,
        activity_level=profile.activity_level or None,
        subject_source="self_profile",
        ppk_weight_source="profile_current_weight",
    ))
    return plan.as_targets_dict()


@transaction.atomic
def save_nutrition_onboarding_v2(
    *,
    user,
    birth_date: date,
    sex: str,
    height_cm: int,
    weight_kg: float,
    goal: str,
    activity_level: str,
    training_frequency: int,
    dietary_pattern: str,
    allergies_or_intolerances: Iterable[str] = (),
    avoided_foods: Iterable[str] = (),
) -> tuple[Profile, dict]:
    if goal not in NUTRITION_GOAL_VALUES:
        raise ValueError("onboarding_goal_invalid")
    if activity_level not in ACTIVITY_LEVEL_VALUES:
        raise ValueError("onboarding_activity_level_invalid")
    if not 0 <= training_frequency <= 7:
        raise ValueError("onboarding_training_frequency_invalid")
    if dietary_pattern not in DIETARY_PATTERNS:
        raise ValueError("onboarding_dietary_pattern_invalid")

    profile = Profile.objects.select_for_update().get(user=user)
    prior_proposal = NutritionProposal.objects.select_for_update().filter(
        pk=profile.onboarding_plan_proposal_id,
        created_by=user,
    ).first()
    if prior_proposal and not prior_proposal.is_final:
        cancel_proposal(user=user, proposal=prior_proposal)

    profile.birth_date = birth_date
    profile.sex = sex
    profile.height_cm = height_cm
    profile.nutrition_goal = goal
    profile.activity_level = activity_level
    profile.training_frequency = training_frequency
    profile.onboarding_stage = Profile.ONBOARDING_STAGE_SUMMARY
    profile.onboarding_plan_proposal_id = None
    profile.save(update_fields=[
        "birth_date", "sex", "height_cm", "nutrition_goal", "activity_level",
        "training_frequency", "onboarding_stage", "onboarding_plan_proposal_id",
    ])
    record_weight(user, weight_kg, source=WeightLog.SOURCE_ONBOARDING)

    preference_profile, _created = NutritionPreferenceProfile.objects.select_for_update().get_or_create(
        user=user,
        defaults={"preferences": {}},
    )
    preferences = dict(preference_profile.preferences or {})
    preferences.update({
        "dietary_pattern": dietary_pattern,
        "allergies_or_intolerances": _clean_preference_values(allergies_or_intolerances),
        "avoided_foods": _clean_preference_values(avoided_foods),
    })
    preference_profile.preferences = preferences
    preference_profile.save(update_fields=["preferences", "updated_at"])
    return profile, nutrition_onboarding_estimate(profile)


@transaction.atomic
def mark_nutrition_onboarding_intro_complete(*, user) -> Profile:
    profile = Profile.objects.select_for_update().get(user=user)
    if profile.onboarding_stage == Profile.ONBOARDING_STAGE_INTRO:
        profile.onboarding_stage = Profile.ONBOARDING_STAGE_PROFILE
        profile.save(update_fields=["onboarding_stage"])
    return profile


@transaction.atomic
def generate_nutrition_onboarding_plan(*, user) -> NutritionProposal:
    profile = Profile.objects.select_for_update().get(user=user)
    existing = NutritionProposal.objects.select_for_update().filter(
        pk=profile.onboarding_plan_proposal_id,
        created_by=user,
    ).first()
    if existing and existing.status in {
        NutritionProposal.STATUS_PENDING_REVIEW,
        NutritionProposal.STATUS_APPROVED,
        NutritionProposal.STATUS_APPLIED,
    }:
        return existing

    estimate = nutrition_onboarding_estimate(profile)
    preference_profile = NutritionPreferenceProfile.objects.filter(user=user).first()
    preferences = dict(preference_profile.preferences or {}) if preference_profile else {}
    weight_log = user.weight_logs.first()
    brief = build_nutrition_brief_from_ai_drafts(
        profile_draft={
            "weight_kg": float(weight_log.weight_kg) if weight_log else None,
            "height_cm": profile.height_cm,
            "age_years": calculate_age_years(profile.birth_date),
            "sex": profile.sex,
            "activity_level": profile.activity_level,
            "training_frequency": profile.training_frequency,
            "field_sources": {
                "weight_kg": "profile", "height_cm": "profile", "age_years": "profile",
                "sex": "profile", "activity_level": "profile", "training_frequency": "profile",
            },
        },
        preference_draft={**preferences, "field_sources": dict.fromkeys(preferences, "profile")},
        proposal_preferences={
            "goal": profile.nutrition_goal,
            "requested_entity": "daily_plan",
            "calorie_target": round(estimate["total_kcal"]),
            "protein_target": round(estimate["protein"]),
            "carb_target": round(estimate["carbs"]),
            "fat_target": round(estimate["fat"]),
            "protein_per_kg_target": estimate["protein_per_kg"],
        },
        raw_prompt="Generar el primer plan diario desde el onboarding.",
    )
    source = create_nutrition_brief_proposal(user=user, brief=brief, source=NutritionProposal.SOURCE_SYSTEM)
    generated = generate_dailyplan_proposal_from_brief_proposal(
        user=user,
        source_proposal=source.proposal,
        source=NutritionProposal.SOURCE_SYSTEM,
    )
    # The brief is an internal input artifact. Keep the concrete daily-plan
    # proposal as the only reviewable item shown to the user.
    cancel_proposal(user=user, proposal=source.proposal)
    profile.onboarding_plan_proposal_id = generated.proposal.id
    profile.onboarding_stage = Profile.ONBOARDING_STAGE_PLAN
    profile.save(update_fields=["onboarding_plan_proposal_id", "onboarding_stage"])
    return generated.proposal


@transaction.atomic
def accept_nutrition_onboarding_plan(*, user) -> NutritionProposal:
    profile = Profile.objects.select_for_update().get(user=user)
    proposal = NutritionProposal.objects.select_for_update().filter(
        pk=profile.onboarding_plan_proposal_id,
        created_by=user,
    ).first()
    if proposal is None:
        raise ValueError("onboarding_plan_not_generated")
    if proposal.status == NutritionProposal.STATUS_PENDING_REVIEW:
        approve_proposal(user=user, proposal=proposal)
        proposal.refresh_from_db()
    if proposal.status == NutritionProposal.STATUS_APPROVED:
        apply_approved_create_dailyplan_proposal(user=user, proposal=proposal)
        proposal.refresh_from_db()
    if proposal.status != NutritionProposal.STATUS_APPLIED:
        raise ValueError("onboarding_plan_not_applicable")
    profile.onboarding_stage = Profile.ONBOARDING_STAGE_PLANS
    profile.save(update_fields=["onboarding_stage"])
    return proposal


@transaction.atomic
def complete_nutrition_onboarding_v2(*, user) -> Profile:
    profile = Profile.objects.select_for_update().get(user=user)
    if profile.onboarding_stage != Profile.ONBOARDING_STAGE_PLANS:
        raise ValueError("onboarding_not_ready_to_complete")
    profile.onboarding_completed_at = profile.onboarding_completed_at or timezone.now()
    profile.onboarding_version = Profile.ONBOARDING_VERSION_NUTRITION_V2
    profile.onboarding_stage = Profile.ONBOARDING_STAGE_COMPLETED
    profile.save(update_fields=["onboarding_completed_at", "onboarding_version", "onboarding_stage"])
    return profile
