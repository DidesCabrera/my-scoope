from __future__ import annotations

from django.conf import settings
from django.shortcuts import redirect

from notas.domain.models import Profile


class NutritionOnboardingRequiredMiddleware:
    """Redirect authenticated app users to nutrition onboarding when required."""

    DEFAULT_ALLOWED_PREFIXES = (
        "/accounts/",
        "/admin/",
        "/static/",
        "/media/",
        "/favicon.ico",
        "/manifest.json",
        "/serviceworker.js",
        "/.well-known/",
        "/oauth/",
    )

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if self._should_redirect_to_onboarding(request):
            return redirect("accounts:nutrition_onboarding")
        return self.get_response(request)

    def _should_redirect_to_onboarding(self, request) -> bool:
        user = getattr(request, "user", None)
        if user is None or not user.is_authenticated:
            return False
        if user.is_staff or user.is_superuser:
            return False
        if not self._is_onboarding_gate_enabled():
            return False
        if self._is_allowed_path(request.path_info):
            return False
        return not self._has_completed_required_onboarding(user)

    def _is_onboarding_gate_enabled(self) -> bool:
        return bool(getattr(settings, "NUTRITION_ONBOARDING_GATE_ENABLED", True))

    def _is_allowed_path(self, path: str) -> bool:
        allowed_prefixes = getattr(
            settings,
            "NUTRITION_ONBOARDING_ALLOWED_PREFIXES",
            self.DEFAULT_ALLOWED_PREFIXES,
        )
        return any(path.startswith(prefix) for prefix in allowed_prefixes)

    def _has_completed_required_onboarding(self, user) -> bool:
        try:
            profile = user.profile
        except Profile.DoesNotExist:
            return False
        return (
            profile.onboarding_completed_at is not None
            and profile.onboarding_version >= Profile.ONBOARDING_VERSION_NUTRITION_V1
        )
