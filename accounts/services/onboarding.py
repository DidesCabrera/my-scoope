from __future__ import annotations

from datetime import date
from typing import Iterable

from django.db import transaction
from django.utils import timezone

from notas.application.ai_intake.onboarding_catalog_minutas import generate_onboarding_catalog_minutas
from notas.application.ai_tools.preference_tools import DIETARY_PATTERNS
from notas.application.nutrition_engine.target_estimator import TargetEstimationProfile, estimate_daily_targets
from notas.application.services.commands.meal_commands import save_dailyplan_meal_to_library
from notas.application.services.commands.proposal_commands import (
    apply_approved_create_dailyplan_proposal,
    approve_proposal,
    cancel_proposal,
)
from notas.application.services.nutrition.body_metrics import calculate_age_years, record_weight
from notas.domain.models import (
    CalendarizedDay,
    DailyPlan,
    DailyPlanMeal,
    NutritionPreferenceProfile,
    NutritionProposal,
    NutritionProposalAuditEvent,
    Profile,
    WeightLog,
)
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


def onboarding_plan_proposal_ids(profile: Profile) -> list[int]:
    """Keep an in-flight single-plan onboarding readable after the pair migration."""
    ids = [value for value in profile.onboarding_plan_proposal_ids if type(value) is int and value > 0]
    if not ids and profile.onboarding_plan_proposal_id:
        ids = [profile.onboarding_plan_proposal_id]
    return ids[:2]


def onboarding_applied_dailyplan_ids(*, user, proposal_ids: list[int]) -> dict[int, int]:
    proposals = {row.pk: row for row in NutritionProposal.objects.filter(pk__in=proposal_ids, created_by=user)}
    applied_ids = {}
    for event in NutritionProposalAuditEvent.objects.filter(
        proposal_id__in=proposal_ids, action=NutritionProposalAuditEvent.ACTION_APPLIED,
    ).order_by("created_at", "id"):
        candidate = (event.metadata or {}).get("dailyplan_id")
        if type(candidate) is int and candidate > 0:
            applied_ids[event.proposal_id] = candidate
    owned_ids = set(DailyPlan.objects.filter(created_by=user, pk__in=applied_ids.values()).values_list("pk", flat=True))
    return {proposal_id: applied_ids[proposal_id] for proposal_id in proposal_ids
            if proposals.get(proposal_id) and proposals[proposal_id].status == NutritionProposal.STATUS_APPLIED
            and applied_ids.get(proposal_id) in owned_ids}


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
    for prior_proposal in NutritionProposal.objects.select_for_update().filter(
        pk__in=onboarding_plan_proposal_ids(profile), created_by=user,
    ):
        if not prior_proposal.is_final:
            cancel_proposal(user=user, proposal=prior_proposal)

    profile.birth_date = birth_date
    profile.sex = sex
    profile.height_cm = height_cm
    profile.nutrition_goal = goal
    profile.activity_level = activity_level
    profile.training_frequency = training_frequency
    profile.onboarding_stage = Profile.ONBOARDING_STAGE_SUMMARY
    profile.onboarding_plan_proposal_id = None
    profile.onboarding_plan_proposal_ids = []
    profile.save(update_fields=[
        "birth_date", "sex", "height_cm", "nutrition_goal", "activity_level",
        "training_frequency", "onboarding_stage", "onboarding_plan_proposal_id", "onboarding_plan_proposal_ids",
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
def generate_nutrition_onboarding_plan(*, user) -> tuple[NutritionProposal, NutritionProposal]:
    profile = Profile.objects.select_for_update().get(user=user)
    ids = onboarding_plan_proposal_ids(profile)
    owned = {proposal.pk: proposal for proposal in NutritionProposal.objects.select_for_update().filter(
        pk__in=ids, created_by=user,
    )}
    existing = [owned[pk] for pk in ids if pk in owned]
    if len(existing) == 2 and all(proposal.status in {
        NutritionProposal.STATUS_PENDING_REVIEW,
        NutritionProposal.STATUS_APPROVED,
        NutritionProposal.STATUS_APPLIED,
    } for proposal in existing):
        return existing[0], existing[1]
    for proposal in existing:
        if not proposal.is_final:
            cancel_proposal(user=user, proposal=proposal)

    estimate = nutrition_onboarding_estimate(profile)
    preference_profile = NutritionPreferenceProfile.objects.filter(user=user).first()
    preferences = dict(preference_profile.preferences or {}) if preference_profile else {}
    proposals = generate_onboarding_catalog_minutas(user=user, estimate=estimate, preferences=preferences)
    profile.onboarding_plan_proposal_id = proposals[0].id
    profile.onboarding_plan_proposal_ids = [proposal.id for proposal in proposals]
    profile.onboarding_stage = Profile.ONBOARDING_STAGE_PLAN
    profile.save(update_fields=["onboarding_plan_proposal_id", "onboarding_plan_proposal_ids", "onboarding_stage"])
    return proposals


@transaction.atomic
def accept_nutrition_onboarding_plan(*, user) -> tuple[NutritionProposal, ...]:
    profile = Profile.objects.select_for_update().get(user=user)
    ids = onboarding_plan_proposal_ids(profile)
    owned = {proposal.pk: proposal for proposal in NutritionProposal.objects.select_for_update().filter(
        pk__in=ids, created_by=user,
    )}
    if not ids or len(owned) != len(ids):
        raise ValueError("onboarding_plan_not_generated")
    proposals = tuple(owned[pk] for pk in ids)
    for proposal in proposals:
        if proposal.status == NutritionProposal.STATUS_PENDING_REVIEW:
            approve_proposal(user=user, proposal=proposal)
            proposal.refresh_from_db()
        if proposal.status == NutritionProposal.STATUS_APPROVED:
            applied = apply_approved_create_dailyplan_proposal(user=user, proposal=proposal)
            source_id = (proposal.current_snapshot or {}).get("source_dailyplan_id")
            source = DailyPlan.objects.filter(pk=source_id).first() if source_id else None
            if source is not None:
                applied.dailyplan.forked_from = source.forked_from or source
                applied.dailyplan.original_author = source.original_author or source.created_by
                applied.dailyplan.save(update_fields=["forked_from", "original_author"])
            proposal.refresh_from_db()
        if proposal.status != NutritionProposal.STATUS_APPLIED:
            raise ValueError("onboarding_plan_not_applicable")
    plan_ids = onboarding_applied_dailyplan_ids(user=user, proposal_ids=ids)
    if len(plan_ids) != len(proposals):
        raise ValueError("onboarding_plan_not_applicable")
    for proposal in proposals:
        applied_event = NutritionProposalAuditEvent.objects.select_for_update().filter(
            proposal=proposal, action=NutritionProposalAuditEvent.ACTION_APPLIED,
            metadata__dailyplan_id=plan_ids[proposal.id],
        ).order_by("-id").first()
        if applied_event is None:
            raise ValueError("onboarding_plan_not_applicable")
        if "onboarding_library_meal_ids" in (applied_event.metadata or {}):
            continue
        saved_ids = []
        slots = DailyPlanMeal.objects.filter(dailyplan_id=plan_ids[proposal.id]).select_related("meal").order_by("order", "id")
        for slot in slots:
            saved = save_dailyplan_meal_to_library(slot, user)
            saved.name = slot.meal.name
            saved.save(update_fields=["name"])
            saved_ids.append(saved.id)
        applied_event.metadata = {**(applied_event.metadata or {}), "onboarding_library_meal_ids": saved_ids}
        applied_event.save(update_fields=["metadata"])
    profile.onboarding_stage = Profile.ONBOARDING_STAGE_PLANS
    profile.save(update_fields=["onboarding_stage"])
    return proposals


@transaction.atomic
def complete_nutrition_onboarding_v2(*, user) -> Profile:
    profile = Profile.objects.select_for_update().get(user=user)
    if profile.onboarding_stage != Profile.ONBOARDING_STAGE_PLANS:
        raise ValueError("onboarding_not_ready_to_complete")
    proposal_ids = onboarding_plan_proposal_ids(profile)
    if len(proposal_ids) == 2:
        plan_ids = onboarding_applied_dailyplan_ids(user=user, proposal_ids=proposal_ids)
        calendarized_ids = set(CalendarizedDay.objects.filter(
            user=user, source_dailyplan_id__in=plan_ids.values(), source_kind=CalendarizedDay.SOURCE_MANUAL,
            assignment_state=CalendarizedDay.STATE_CURRENT, plan_snapshot__isnull=False,
        ).values_list("source_dailyplan_id", flat=True))
        if len(plan_ids) != 2 or calendarized_ids != set(plan_ids.values()):
            raise ValueError("onboarding_calendarization_incomplete")
    profile.onboarding_completed_at = profile.onboarding_completed_at or timezone.now()
    profile.onboarding_version = Profile.ONBOARDING_VERSION_NUTRITION_V2
    profile.onboarding_stage = Profile.ONBOARDING_STAGE_COMPLETED
    profile.save(update_fields=["onboarding_completed_at", "onboarding_version", "onboarding_stage"])
    return profile
