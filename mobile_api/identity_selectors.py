from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from django.utils import timezone

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
    }


def local_date_for_user(user, *, now=None):
    timezone_name = getattr(user.profile, "timezone_name", "UTC") or "UTC"
    try:
        user_timezone = ZoneInfo(timezone_name)
    except ZoneInfoNotFoundError:
        user_timezone = ZoneInfo("UTC")
    return timezone.localdate(now or timezone.now(), timezone=user_timezone)
