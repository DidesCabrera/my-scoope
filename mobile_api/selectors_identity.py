from notas.application.services.nutrition.body_metrics import get_basic_body_profile


def session_payload(auth) -> dict:
    user = auth.user
    display_name = user.get_full_name().strip() or user.username
    return {
        "user_id": user.id,
        "username": user.username,
        "email": user.email,
        "display_name": display_name,
        "date_joined": user.date_joined,
        "scopes": list(auth.token.scopes),
        "device_session_id": (str(auth.token.device_session.public_id) if auth.token.device_session_id else None),
        "is_staff": user.is_staff,
    }


def profile_payload(user) -> dict:
    body = get_basic_body_profile(user)
    profile = user.profile
    return {
        "birth_date": body.birth_date,
        "sex": body.sex,
        "height_cm": body.height_cm,
        "timezone_name": profile.timezone_name,
        "onboarding_completed": profile.onboarding_completed_at is not None,
        "onboarding_version": profile.onboarding_version,
        "current_weight_kg": body.current_weight_kg,
        "review_disclosure_required": (
            profile.mobile_disclosure_version != profile.MOBILE_DISCLOSURE_VERSION
            or profile.mobile_disclosure_accepted_at is None
        ),
        "review_disclosure_version": profile.MOBILE_DISCLOSURE_VERSION,
        "nutrition_goal": profile.nutrition_goal,
        "activity_level": profile.activity_level,
        "training_frequency": profile.training_frequency,
        "onboarding_stage": profile.onboarding_stage,
        "onboarding_plan_proposal_id": profile.onboarding_plan_proposal_id,
    }
