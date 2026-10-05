from django.conf import settings
from django.utils import timezone

from billing.models import AppleSandboxAccess, BillingProduct


class AppleEvidenceError(ValueError):
    pass


class UnsupportedAppleEnvironment(AppleEvidenceError):
    pass


class UnauthorizedAppleSandboxAccess(AppleEvidenceError):
    pass


def apple_catalog_environment(value: str) -> str:
    normalized = str(value or "").strip().lower()
    if normalized == "sandbox":
        return BillingProduct.Environment.SANDBOX
    if normalized == "production":
        return BillingProduct.Environment.LIVE
    raise UnsupportedAppleEnvironment("Apple evidence has an unsupported environment.")


def user_has_apple_sandbox_access(user) -> bool:
    access = AppleSandboxAccess.objects.filter(user=user, active=True).first()
    return bool(access and (access.expires_at is None or access.expires_at > timezone.now()))


def require_apple_sandbox_access_in_production(user, *, catalog_environment: str) -> None:
    if (
        catalog_environment == BillingProduct.Environment.SANDBOX
        and settings.BILLING_APPLE_ENVIRONMENT == "production"
        and not user_has_apple_sandbox_access(user)
    ):
        raise UnauthorizedAppleSandboxAccess("This account is not authorized for Apple sandbox evidence.")
