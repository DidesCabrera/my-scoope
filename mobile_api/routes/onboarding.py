from ninja import Router

from accounts.forms import NutritionOnboardingForm, NutritionOnboardingV2Form
from accounts.services.onboarding import (
    accept_nutrition_onboarding_plan,
    complete_nutrition_onboarding,
    complete_nutrition_onboarding_v2,
    generate_nutrition_onboarding_plan,
    mark_nutrition_onboarding_intro_complete,
    nutrition_onboarding_estimate,
    save_nutrition_onboarding_v2,
)
from accounts.services.personal_records import (
    update_body_record,
    update_planning_record,
    update_preference_record,
    update_weight_record,
)
from mobile_api.api_support import form_error, require_scope, success
from mobile_api.auth import mobile_bearer
from mobile_api.errors import MobileAPIError
from mobile_api.schema_domains.identity import ProfileEnvelope
from mobile_api.schema_domains.onboarding import (
    OnboardingAnalyzeInput,
    OnboardingInput,
    OnboardingStateEnvelope,
    PersonalBodyInput,
    PersonalPlanningInput,
    PersonalPreferencesInput,
    PersonalWeightInput,
)
from mobile_api.schema_domains.proposals import ProposalDetailEnvelope
from mobile_api.schemas import ErrorEnvelope
from mobile_api.selectors_identity import profile_payload
from mobile_api.selectors_proposals import proposal_detail_payload
from notas.application.services.oauth_device_sessions import MOBILE_SCOPE_WRITE
from notas.domain.models import NutritionPreferenceProfile
from notas.interface.forms.forms import ProfileNutritionForm

router = Router()


@router.post(
    "/onboarding",
    operation_id="mobile_api_api_onboarding",
    auth=mobile_bearer,
    response={200: ProfileEnvelope, 403: ErrorEnvelope, 422: ErrorEnvelope},
)
def onboarding(request, payload: OnboardingInput):
    require_scope(request.auth, MOBILE_SCOPE_WRITE)
    form = NutritionOnboardingForm(
        {
            "birth_date": payload.birth_date.isoformat(),
            "sex": payload.sex,
            "height_cm": payload.height_cm,
            "weight_kg": payload.weight_kg,
        }
    )
    if not form.is_valid():
        raise form_error(form, code="onboarding_invalid", message="Onboarding data is invalid.")
    complete_nutrition_onboarding(
        user=request.auth.user,
        birth_date=form.cleaned_data["birth_date"],
        sex=form.cleaned_data["sex"],
        height_cm=form.cleaned_data["height_cm"],
        weight_kg=form.cleaned_data["weight_kg"],
    )
    return success(profile_payload(request.auth.user))

def _onboarding_state_payload(user):
    profile = user.profile
    preference_profile = NutritionPreferenceProfile.objects.filter(user=user).first()
    preferences = dict(preference_profile.preferences or {}) if preference_profile else {}
    estimate = None
    weight_log = user.weight_logs.first()
    if weight_log and all((profile.birth_date, profile.sex, profile.height_cm, profile.nutrition_goal, profile.activity_level)):
        estimate = nutrition_onboarding_estimate(profile)
    return {
        "stage": profile.onboarding_stage,
        "birth_date": profile.birth_date,
        "sex": profile.sex,
        "height_cm": profile.height_cm,
        "weight_kg": float(weight_log.weight_kg) if weight_log else None,
        "goal": profile.nutrition_goal,
        "activity_level": profile.activity_level,
        "training_frequency": profile.training_frequency,
        "dietary_pattern": preferences.get("dietary_pattern", ""),
        "allergies_or_intolerances": list(preferences.get("allergies_or_intolerances") or []),
        "avoided_foods": list(preferences.get("avoided_foods") or []),
        "estimate": estimate,
        "proposal_id": profile.onboarding_plan_proposal_id,
    }


@router.get(
    "/onboarding/state",
    operation_id="mobile_api_api_onboarding_state",
    auth=mobile_bearer,
    response={200: OnboardingStateEnvelope, 401: ErrorEnvelope, 403: ErrorEnvelope},
)
def onboarding_state(request):
    return success(_onboarding_state_payload(request.auth.user))


@router.patch(
    "/personal-records/body",
    operation_id="mobile_api_routes_onboarding_update_personal_body",
    auth=mobile_bearer,
    response={200: OnboardingStateEnvelope, 403: ErrorEnvelope, 422: ErrorEnvelope},
)
def update_personal_body(request, payload: PersonalBodyInput):
    require_scope(request.auth, MOBILE_SCOPE_WRITE)
    form = ProfileNutritionForm({"birth_date": payload.birth_date.isoformat(), "sex": payload.sex, "height_cm": payload.height_cm})
    if not form.is_valid():
        raise form_error(form, code="personal_record_invalid", message="Revisa la información ingresada.")
    update_body_record(user=request.auth.user, birth_date=form.cleaned_data["birth_date"], sex=form.cleaned_data["sex"], height_cm=form.cleaned_data["height_cm"])
    return success(_onboarding_state_payload(request.auth.user))


@router.patch(
    "/personal-records/planning",
    operation_id="mobile_api_routes_onboarding_update_personal_planning",
    auth=mobile_bearer,
    response={200: OnboardingStateEnvelope, 403: ErrorEnvelope, 422: ErrorEnvelope},
)
def update_personal_planning(request, payload: PersonalPlanningInput):
    require_scope(request.auth, MOBILE_SCOPE_WRITE)
    try:
        update_planning_record(user=request.auth.user, goal=payload.goal, activity_level=payload.activity_level, training_frequency=payload.training_frequency)
    except ValueError as exc:
        raise MobileAPIError(code=str(exc), message="Revisa la información ingresada.", status_code=422) from exc
    return success(_onboarding_state_payload(request.auth.user))


@router.patch(
    "/personal-records/preferences",
    operation_id="mobile_api_routes_onboarding_update_personal_preferences",
    auth=mobile_bearer,
    response={200: OnboardingStateEnvelope, 403: ErrorEnvelope, 422: ErrorEnvelope},
)
def update_personal_preferences(request, payload: PersonalPreferencesInput):
    require_scope(request.auth, MOBILE_SCOPE_WRITE)
    try:
        update_preference_record(user=request.auth.user, dietary_pattern=payload.dietary_pattern, allergies_or_intolerances=payload.allergies_or_intolerances, avoided_foods=payload.avoided_foods)
    except ValueError as exc:
        raise MobileAPIError(code=str(exc), message="Revisa la información ingresada.", status_code=422) from exc
    return success(_onboarding_state_payload(request.auth.user))


@router.patch(
    "/personal-records/metrics",
    operation_id="mobile_api_routes_onboarding_update_personal_metrics",
    auth=mobile_bearer,
    response={200: OnboardingStateEnvelope, 403: ErrorEnvelope, 422: ErrorEnvelope},
)
def update_personal_metrics(request, payload: PersonalWeightInput):
    require_scope(request.auth, MOBILE_SCOPE_WRITE)
    update_weight_record(user=request.auth.user, weight_kg=payload.weight_kg)
    return success(_onboarding_state_payload(request.auth.user))


@router.post(
    "/onboarding/intro-complete",
    operation_id="mobile_api_api_onboarding_intro_complete",
    auth=mobile_bearer,
    response={200: OnboardingStateEnvelope, 403: ErrorEnvelope},
)
def onboarding_intro_complete(request):
    require_scope(request.auth, MOBILE_SCOPE_WRITE)
    mark_nutrition_onboarding_intro_complete(user=request.auth.user)
    return success(_onboarding_state_payload(request.auth.user))


@router.post(
    "/onboarding/analyze",
    operation_id="mobile_api_api_onboarding_analyze",
    auth=mobile_bearer,
    response={200: OnboardingStateEnvelope, 403: ErrorEnvelope, 422: ErrorEnvelope},
)
def onboarding_analyze(request, payload: OnboardingAnalyzeInput):
    require_scope(request.auth, MOBILE_SCOPE_WRITE)
    form = NutritionOnboardingV2Form({
        "birth_date": payload.birth_date.isoformat(),
        "sex": payload.sex,
        "height_cm": payload.height_cm,
        "weight_kg": payload.weight_kg,
        "goal": payload.goal,
        "activity_level": payload.activity_level,
        "training_frequency": payload.training_frequency,
    })
    if not form.is_valid():
        raise form_error(form, code="onboarding_invalid", message="Onboarding data is invalid.")
    try:
        save_nutrition_onboarding_v2(
            user=request.auth.user,
            dietary_pattern=payload.dietary_pattern,
            allergies_or_intolerances=payload.allergies_or_intolerances,
            avoided_foods=payload.avoided_foods,
            **form.cleaned_data,
        )
    except ValueError as exc:
        raise MobileAPIError(code=str(exc), message="Onboarding data is invalid.", status_code=422) from exc
    return success(_onboarding_state_payload(request.auth.user))


@router.post(
    "/onboarding/generate-plan",
    operation_id="mobile_api_api_onboarding_generate_plan",
    auth=mobile_bearer,
    response={200: ProposalDetailEnvelope, 403: ErrorEnvelope, 409: ErrorEnvelope, 422: ErrorEnvelope},
)
def onboarding_generate_plan(request):
    require_scope(request.auth, MOBILE_SCOPE_WRITE)
    try:
        proposal = generate_nutrition_onboarding_plan(user=request.auth.user)
    except (ValueError, RuntimeError) as exc:
        raise MobileAPIError(code=str(exc), message="We could not generate the first daily plan.", status_code=422) from exc
    return success(proposal_detail_payload(request.auth.user, proposal.id))


@router.post(
    "/onboarding/accept-plan",
    operation_id="mobile_api_api_onboarding_accept_plan",
    auth=mobile_bearer,
    response={200: ProposalDetailEnvelope, 403: ErrorEnvelope, 409: ErrorEnvelope, 422: ErrorEnvelope},
)
def onboarding_accept_plan(request):
    require_scope(request.auth, MOBILE_SCOPE_WRITE)
    try:
        proposal = accept_nutrition_onboarding_plan(user=request.auth.user)
    except ValueError as exc:
        raise MobileAPIError(code=str(exc), message="The first daily plan could not be applied.", status_code=409) from exc
    return success(proposal_detail_payload(request.auth.user, proposal.id))


@router.post(
    "/onboarding/complete",
    operation_id="mobile_api_api_onboarding_complete_v2",
    auth=mobile_bearer,
    response={200: ProfileEnvelope, 403: ErrorEnvelope, 409: ErrorEnvelope},
)
def onboarding_complete_v2(request):
    require_scope(request.auth, MOBILE_SCOPE_WRITE)
    try:
        complete_nutrition_onboarding_v2(user=request.auth.user)
    except ValueError as exc:
        raise MobileAPIError(code=str(exc), message="The onboarding is not ready to complete.", status_code=409) from exc
    return success(profile_payload(request.auth.user))
